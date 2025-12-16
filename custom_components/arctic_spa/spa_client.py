"""Arctic Spa TCP/UDP Client with persistent connection."""
from __future__ import annotations

import asyncio
import logging
import socket
import struct
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from .const import (
    MAGIC,
    HEADER_SIZE,
    DEFAULT_PORT,
    UDP_SEND_PORT,
    UDP_RECV_PORT,
    UDP_QUERY_MSG,
    MsgType,
    PumpStatus,
    HeaterStatus,
    FilterStatus,
    LiveField,
    CmdField,
)

_LOGGER = logging.getLogger(__name__)

# Keepalive interval in seconds
KEEPALIVE_INTERVAL = 30
# Reconnect delay in seconds
RECONNECT_DELAY = 5
# Connection timeout
CONNECT_TIMEOUT = 10
# Max reconnect attempts before giving up temporarily
MAX_RECONNECT_ATTEMPTS = 3


@dataclass
class SpaStatus:
    """Spa status data."""
    
    temperature_f: int = 0
    setpoint_f: int = 0
    pump1: PumpStatus = PumpStatus.OFF
    pump2: PumpStatus = PumpStatus.OFF
    pump3: PumpStatus = PumpStatus.OFF
    pump4: PumpStatus = PumpStatus.OFF
    pump5: PumpStatus = PumpStatus.OFF
    blower1: PumpStatus = PumpStatus.OFF
    blower2: PumpStatus = PumpStatus.OFF
    lights: bool = False
    stereo: bool = False
    heater1: HeaterStatus = HeaterStatus.IDLE
    heater2: HeaterStatus = HeaterStatus.IDLE
    filter_status: FilterStatus = FilterStatus.IDLE
    onzen: bool = False
    ozone: bool = False
    economy: bool = False
    all_on: bool = False
    sds: bool = False
    yess: bool = False
    error: int = 0
    alarm: int = 0
    ph: int = 0
    orp: int = 0
    connected: bool = False
    last_update: datetime | None = None
    
    # Energy tracking
    energy_kwh: float = 0.0
    _last_energy_update: datetime | None = None

    # Error code descriptions (from Arctic Spas documentation)
    ERROR_CODES = {
        0: "No Error",
        1: "Temperature Sensor A Fault",
        2: "Temperature Sensor B Fault",
        3: "Water Temperature Too Hot",
        4: "Water Temperature Too Cold",
        5: "Flow Switch Error",
        6: "Dry Fire Protection",
        7: "GFCI Trip",
        8: "Heater Fault",
        9: "Communication Error",
        10: "Sensor Sync Error",
    }

    ALARM_CODES = {
        0: "No Alarm",
        1: "Water Flow Alarm",
        2: "High Temperature Alarm",
        3: "Heater Alarm",
        4: "Sensor Alarm",
    }

    @property
    def temperature_c(self) -> float:
        """Get temperature in Celsius, rounded to nearest 0.5."""
        c = (self.temperature_f - 32) * 5 / 9
        return round(c * 2) / 2  # Round to nearest 0.5

    @property
    def setpoint_c(self) -> float:
        """Get setpoint in Celsius, rounded to nearest 0.5."""
        c = (self.setpoint_f - 32) * 5 / 9
        return round(c * 2) / 2  # Round to nearest 0.5

    @property
    def heater_active(self) -> bool:
        """Check if any heater is actively heating."""
        return self.heater1 in (HeaterStatus.WARMUP, HeaterStatus.HEATING) or \
               self.heater2 in (HeaterStatus.WARMUP, HeaterStatus.HEATING)

    @property
    def filter_boost_active(self) -> bool:
        """Check if filter boost is active."""
        return self.filter_status == FilterStatus.BOOST

    @property
    def error_message(self) -> str:
        """Get human-readable error message."""
        return self.ERROR_CODES.get(self.error, f"Unknown Error ({self.error})")

    @property
    def alarm_message(self) -> str:
        """Get human-readable alarm message."""
        return self.ALARM_CODES.get(self.alarm, f"Unknown Alarm ({self.alarm})")

    @property
    def has_error(self) -> bool:
        """Check if there's an active error."""
        return self.error != 0

    @property
    def has_alarm(self) -> bool:
        """Check if there's an active alarm."""
        return self.alarm != 0

    @property
    def estimated_power_watts(self) -> int:
        """Estimate current power consumption in watts."""
        # Power constants (measured values)
        HEATER_HEATING_WATTS = 6500   # Full heating (includes Pump 1 Low)
        HEATER_WARMUP_WATTS = 350     # Heater warming up
        HEATER_COOLDOWN_WATTS = 350   # Heater cooling down
        PUMP_HIGH_WATTS = 1700        # Pump 1/2/3 on High
        PUMP_LOW_WATTS = 370          # Pump 1 Low only
        IDLE_WATTS = 15               # Electronics standby
        
        power = IDLE_WATTS
        
        # Count high-speed pumps
        high_pumps = sum([
            1 if self.pump1 == PumpStatus.HIGH else 0,
            1 if self.pump2 == PumpStatus.HIGH else 0,
            1 if self.pump3 == PumpStatus.HIGH else 0,
        ])
        
        if high_pumps > 0:
            # High power mode - heater is load-shed when pumps are on high
            power = high_pumps * PUMP_HIGH_WATTS
        elif self.heater1 == HeaterStatus.HEATING:
            # Full heating mode (includes circulation pump)
            power = HEATER_HEATING_WATTS
        elif self.heater1 == HeaterStatus.WARMUP:
            # Heater warming up
            power = HEATER_WARMUP_WATTS
        elif self.heater1 == HeaterStatus.COOLDOWN:
            # Heater cooling down
            power = HEATER_COOLDOWN_WATTS
        elif self.pump1 == PumpStatus.LOW:
            # Circulation mode only
            power = PUMP_LOW_WATTS
        
        # Add blower if running
        if self.blower1 != PumpStatus.OFF:
            power += 500  # Approximate blower power
            
        return power

    def update_energy(self) -> None:
        """Update cumulative energy based on current power and elapsed time."""
        now = datetime.now()
        
        if self._last_energy_update is not None:
            # Calculate time elapsed in hours
            elapsed_hours = (now - self._last_energy_update).total_seconds() / 3600.0
            # Add energy: kWh = kW * hours
            power_kw = self.estimated_power_watts / 1000.0
            self.energy_kwh += power_kw * elapsed_hours
        
        self._last_energy_update = now


class ArcticSpaClient:
    """Client for communicating with Arctic Spa with persistent connection."""

    def __init__(self, host: str, port: int = DEFAULT_PORT) -> None:
        """Initialize the client."""
        self.host = host
        self.port = port
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._status = SpaStatus()
        self._lock = asyncio.Lock()
        self._listener_task: asyncio.Task | None = None
        self._keepalive_task: asyncio.Task | None = None
        self._running = False
        self._reconnect_attempts = 0
        self._state_callbacks: list[Callable[[], None]] = []

    @property
    def status(self) -> SpaStatus:
        """Get current spa status."""
        return self._status

    @property
    def connected(self) -> bool:
        """Check if connected."""
        return self._status.connected and self._writer is not None

    def register_state_callback(self, callback: Callable[[], None]) -> None:
        """Register a callback for state changes."""
        if callback not in self._state_callbacks:
            self._state_callbacks.append(callback)

    def unregister_state_callback(self, callback: Callable[[], None]) -> None:
        """Unregister a state callback."""
        if callback in self._state_callbacks:
            self._state_callbacks.remove(callback)

    def _notify_state_change(self) -> None:
        """Notify all registered callbacks of state change."""
        for callback in self._state_callbacks:
            try:
                callback()
            except Exception as err:
                _LOGGER.error("Error in state callback: %s", err)

    async def _wake_udp(self) -> bool:
        """Send UDP wake-up packet to spa."""
        loop = asyncio.get_event_loop()
        
        try:
            # Create UDP socket for sending
            send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            send_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            send_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            send_sock.setblocking(False)

            # Send to specific host
            await loop.sock_sendto(send_sock, UDP_QUERY_MSG, (self.host, UDP_SEND_PORT))
            _LOGGER.debug("Sent UDP wake to %s:%d", self.host, UDP_SEND_PORT)
            
            # Also send broadcast
            try:
                await loop.sock_sendto(send_sock, UDP_QUERY_MSG, ("255.255.255.255", UDP_SEND_PORT))
            except Exception:
                pass
            
            send_sock.close()

            # Try to receive response (optional, spa may not respond)
            recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            recv_sock.setblocking(False)
            
            try:
                recv_sock.bind(('', UDP_RECV_PORT))
                data = await asyncio.wait_for(
                    loop.sock_recv(recv_sock, 256),
                    timeout=2.0
                )
                _LOGGER.debug("UDP response: %s", data)
            except (asyncio.TimeoutError, OSError):
                pass
            finally:
                recv_sock.close()

            return True

        except Exception as err:
            _LOGGER.warning("UDP wake failed: %s", err)
            return False

    async def async_start(self) -> bool:
        """Start the client with persistent connection."""
        if self._running:
            return True
        
        self._running = True
        self._reconnect_attempts = 0
        
        success = await self._connect()
        if success:
            # Start background tasks
            self._listener_task = asyncio.create_task(self._listener_loop())
            self._keepalive_task = asyncio.create_task(self._keepalive_loop())
        
        return success

    async def async_stop(self) -> None:
        """Stop the client and disconnect."""
        self._running = False
        
        # Cancel background tasks
        if self._keepalive_task:
            self._keepalive_task.cancel()
            try:
                await self._keepalive_task
            except asyncio.CancelledError:
                pass
            self._keepalive_task = None
        
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None
        
        await self._disconnect()

    async def _connect(self) -> bool:
        """Establish connection to spa."""
        async with self._lock:
            try:
                # Wake up spa with UDP
                await self._wake_udp()
                await asyncio.sleep(0.5)
                
                # Connect TCP
                _LOGGER.info("Connecting to spa at %s:%d", self.host, self.port)
                self._reader, self._writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, self.port),
                    timeout=CONNECT_TIMEOUT
                )
                
                self._status.connected = True
                self._reconnect_attempts = 0
                _LOGGER.info("Connected to spa")
                
                # Send initial requests to get state
                await self._send_packet(MsgType.INFO)
                await asyncio.sleep(0.1)
                await self._send_packet(MsgType.LIVE)
                await asyncio.sleep(0.1)
                await self._send_packet(MsgType.CONFIG)
                await asyncio.sleep(0.1)
                await self._send_packet(MsgType.ONZEN_LIVE)  # Request SpaBoy data
                
                return True
                
            except Exception as err:
                _LOGGER.error("Failed to connect to spa: %s", err)
                self._status.connected = False
                self._reader = None
                self._writer = None
                return False

    async def _disconnect(self) -> None:
        """Disconnect from spa."""
        async with self._lock:
            if self._writer:
                try:
                    self._writer.close()
                    await self._writer.wait_closed()
                except Exception:
                    pass
            self._reader = None
            self._writer = None
            self._status.connected = False
            _LOGGER.info("Disconnected from spa")

    async def _reconnect(self) -> bool:
        """Attempt to reconnect to spa."""
        if not self._running:
            return False
        
        self._reconnect_attempts += 1
        
        if self._reconnect_attempts > MAX_RECONNECT_ATTEMPTS:
            _LOGGER.warning(
                "Max reconnect attempts (%d) reached, waiting longer",
                MAX_RECONNECT_ATTEMPTS
            )
            await asyncio.sleep(RECONNECT_DELAY * 3)
            self._reconnect_attempts = 0
        
        _LOGGER.info("Attempting reconnect (attempt %d)", self._reconnect_attempts)
        await self._disconnect()
        await asyncio.sleep(RECONNECT_DELAY)
        
        return await self._connect()

    async def _listener_loop(self) -> None:
        """Background task that listens for incoming data."""
        buffer = b''
        
        while self._running:
            try:
                if not self._reader or not self._status.connected:
                    await asyncio.sleep(1)
                    continue
                
                # Read data with timeout
                try:
                    data = await asyncio.wait_for(
                        self._reader.read(4096),
                        timeout=KEEPALIVE_INTERVAL + 10
                    )
                except asyncio.TimeoutError:
                    _LOGGER.warning("Read timeout, checking connection")
                    continue
                
                if not data:
                    _LOGGER.warning("Connection closed by spa")
                    self._status.connected = False
                    await self._reconnect()
                    continue
                
                buffer += data
                
                # Parse packets from buffer
                while len(buffer) >= HEADER_SIZE:
                    # Find magic
                    if buffer[:4] != struct.pack('>I', MAGIC):
                        idx = buffer.find(struct.pack('>I', MAGIC))
                        if idx > 0:
                            buffer = buffer[idx:]
                        else:
                            buffer = b''
                            break
                        continue
                    
                    # Parse header
                    _, _, _, _, pkt_type, size = struct.unpack(
                        '>IIIIHH', buffer[:HEADER_SIZE]
                    )
                    
                    # Check if we have full packet
                    if len(buffer) < HEADER_SIZE + size:
                        break
                    
                    # Extract payload
                    payload = buffer[HEADER_SIZE:HEADER_SIZE + size]
                    buffer = buffer[HEADER_SIZE + size:]
                    
                    # Process packet
                    await self._process_packet(pkt_type, payload)
                    
            except asyncio.CancelledError:
                break
            except Exception as err:
                _LOGGER.error("Error in listener loop: %s", err)
                if self._running:
                    await self._reconnect()

    async def _keepalive_loop(self) -> None:
        """Background task that sends keepalive requests."""
        while self._running:
            try:
                await asyncio.sleep(KEEPALIVE_INTERVAL)
                
                if not self._status.connected:
                    continue
                
                # Send LIVE request as keepalive
                _LOGGER.debug("Sending keepalive LIVE request")
                async with self._lock:
                    if self._writer:
                        await self._send_packet(MsgType.LIVE)
                        await self._send_packet(MsgType.ONZEN_LIVE)  # Also refresh SpaBoy
                        
            except asyncio.CancelledError:
                break
            except Exception as err:
                _LOGGER.error("Error in keepalive loop: %s", err)

    async def _process_packet(self, pkt_type: int, payload: bytes) -> None:
        """Process received packet."""
        type_name = MsgType(pkt_type).name if pkt_type in MsgType._value2member_map_ else f"TYPE_{pkt_type}"
        _LOGGER.debug("Received %s (%d bytes)", type_name, len(payload))
        
        if pkt_type == MsgType.LIVE and payload:
            self._parse_live_data(payload)
            self._notify_state_change()
        elif pkt_type == MsgType.ONZEN_LIVE and payload:
            self._parse_onzen_live_data(payload)
            self._notify_state_change()

    def _make_packet(self, msg_type: int, payload: bytes = b'') -> bytes:
        """Create a packet with header."""
        return struct.pack('>IIIIHH', MAGIC, 0, 0, 0, msg_type, len(payload)) + payload

    def _encode_varint(self, value: int) -> bytes:
        """Encode a value as varint."""
        result = []
        while value > 127:
            result.append((value & 0x7F) | 0x80)
            value >>= 7
        result.append(value)
        return bytes(result)

    def _encode_field(self, field_num: int, value: int) -> bytes:
        """Encode a protobuf field."""
        tag = (field_num << 3) | 0
        return self._encode_varint(tag) + self._encode_varint(value)

    def _decode_varint(self, data: bytes, offset: int) -> tuple[int, int]:
        """Decode a varint from data at offset."""
        value = 0
        shift = 0
        while offset < len(data):
            b = data[offset]
            offset += 1
            value |= (b & 0x7F) << shift
            if not (b & 0x80):
                break
            shift += 7
        return value, offset

    def _parse_live_data(self, data: bytes) -> None:
        """Parse live status protobuf data."""
        offset = 0
        while offset < len(data):
            try:
                tag = data[offset]
                offset += 1
                field_num = tag >> 3
                wire_type = tag & 0x07
                
                if wire_type == 0:  # Varint
                    value, offset = self._decode_varint(data, offset)
                    
                    if field_num == LiveField.TEMP:
                        self._status.temperature_f = value
                    elif field_num == LiveField.SETPOINT:
                        self._status.setpoint_f = value
                    elif field_num == LiveField.PUMP1:
                        self._status.pump1 = PumpStatus(min(value, 2))
                    elif field_num == LiveField.PUMP2:
                        self._status.pump2 = PumpStatus(min(value, 2))
                    elif field_num == LiveField.PUMP3:
                        self._status.pump3 = PumpStatus(min(value, 2))
                    elif field_num == LiveField.PUMP4:
                        self._status.pump4 = PumpStatus(min(value, 2))
                    elif field_num == LiveField.PUMP5:
                        self._status.pump5 = PumpStatus(min(value, 2))
                    elif field_num == LiveField.BLOWER1:
                        self._status.blower1 = PumpStatus(min(value, 2))
                    elif field_num == LiveField.BLOWER2:
                        self._status.blower2 = PumpStatus(min(value, 2))
                    elif field_num == LiveField.LIGHTS:
                        self._status.lights = bool(value)
                    elif field_num == LiveField.STEREO:
                        self._status.stereo = bool(value)
                    elif field_num == LiveField.HEATER1:
                        self._status.heater1 = HeaterStatus(min(value, 3))
                    elif field_num == LiveField.HEATER2:
                        self._status.heater2 = HeaterStatus(min(value, 3))
                    elif field_num == LiveField.FILTER:
                        self._status.filter_status = FilterStatus(min(value, 7))
                    elif field_num == LiveField.ONZEN:
                        self._status.onzen = bool(value)
                    elif field_num == LiveField.OZONE:
                        self._status.ozone = bool(value)
                    elif field_num == LiveField.ECONOMY:
                        self._status.economy = bool(value)
                    elif field_num == LiveField.ALL_ON:
                        self._status.all_on = bool(value)
                    elif field_num == LiveField.ERROR:
                        self._status.error = value
                    elif field_num == LiveField.ALARM:
                        self._status.alarm = value
                    elif field_num == LiveField.PH:
                        self._status.ph = value
                    elif field_num == LiveField.ORP:
                        self._status.orp = value
                    elif field_num == LiveField.SDS:
                        self._status.sds = bool(value)
                    elif field_num == LiveField.YESS:
                        self._status.yess = bool(value)
                else:
                    break
                    
            except Exception as err:
                _LOGGER.debug("Error parsing live data: %s", err)
                break
        
        self._status.last_update = datetime.now()
        self._status.update_energy()  # Update cumulative energy tracking
        _LOGGER.debug(
            "Status: temp=%d°F, setpoint=%d°F, lights=%s, pump1=%s, heater=%s",
            self._status.temperature_f,
            self._status.setpoint_f,
            self._status.lights,
            self._status.pump1.name,
            self._status.heater1.name,
        )

    def _parse_onzen_live_data(self, data: bytes) -> None:
        """Parse Onzen/SpaBoy live data (Type 48) for pH and ORP."""
        offset = 0
        while offset < len(data):
            try:
                tag = data[offset]
                offset += 1
                field_num = tag >> 3
                wire_type = tag & 0x07
                
                if wire_type == 0:  # Varint
                    value, offset = self._decode_varint(data, offset)
                    
                    # Field 2 = ORP (raw mV value)
                    if field_num == 2:
                        self._status.orp = value
                        _LOGGER.debug("SpaBoy ORP: %d mV", value)
                    # Field 3 = pH (divide by 100 for actual value)
                    elif field_num == 3:
                        self._status.ph = value
                        _LOGGER.debug("SpaBoy pH raw: %d (%.2f)", value, value / 100.0)
                        
                elif wire_type == 2:  # Length-delimited (string/bytes)
                    length, offset = self._decode_varint(data, offset)
                    offset += length
                else:
                    # Skip unknown wire types
                    break
                    
            except Exception as err:
                _LOGGER.debug("Error parsing onzen live data: %s", err)
                break

    async def _send_packet(self, msg_type: int, payload: bytes = b'') -> bool:
        """Send a packet (must be called with lock held or from single task)."""
        if not self._writer:
            return False
        
        try:
            packet = self._make_packet(msg_type, payload)
            self._writer.write(packet)
            await self._writer.drain()
            return True
        except Exception as err:
            _LOGGER.error("Error sending packet: %s", err)
            self._status.connected = False
            return False

    async def async_send_command(self, payload: bytes) -> bool:
        """Send a command to the spa."""
        async with self._lock:
            if not self._status.connected:
                _LOGGER.error("Not connected to spa")
                return False
            
            return await self._send_packet(MsgType.COMMAND, payload)

    def _make_toggle_command(self, field_num: int, value: int) -> bytes:
        """Create a toggle command with stereo suffix."""
        payload = self._encode_field(field_num, value)
        payload += self._encode_field(CmdField.SET_STEREO, 1)  # Required!
        return payload

    async def async_set_lights(self, on: bool) -> bool:
        """Set lights on/off."""
        payload = self._make_toggle_command(CmdField.SET_LIGHTS, 1 if on else 0)
        return await self.async_send_command(payload)

    async def async_set_pump(self, pump_num: int, status: PumpStatus) -> bool:
        """Set pump status (1-5)."""
        field_map = {
            1: CmdField.SET_PUMP1,
            2: CmdField.SET_PUMP2,
            3: CmdField.SET_PUMP3,
            4: CmdField.SET_PUMP4,
            5: CmdField.SET_PUMP5,
        }
        if pump_num not in field_map:
            return False
        payload = self._make_toggle_command(field_map[pump_num], status.value)
        return await self.async_send_command(payload)

    async def async_set_blower(self, blower_num: int, status: PumpStatus) -> bool:
        """Set blower status (1-2)."""
        field_map = {
            1: CmdField.SET_BLOWER1,
            2: CmdField.SET_BLOWER2,
        }
        if blower_num not in field_map:
            return False
        payload = self._make_toggle_command(field_map[blower_num], status.value)
        return await self.async_send_command(payload)

    async def async_set_temperature(self, temp_f: int) -> bool:
        """Set temperature setpoint in Fahrenheit."""
        # Temperature commands don't need stereo suffix
        payload = self._encode_field(CmdField.SET_TEMP, temp_f)
        return await self.async_send_command(payload)

    async def async_set_temperature_c(self, temp_c: float) -> bool:
        """Set temperature setpoint in Celsius."""
        temp_f = round(temp_c * 9 / 5 + 32)
        return await self.async_set_temperature(temp_f)

    async def async_set_filter_boost(self, on: bool) -> bool:
        """Set filter/spa boost on/off."""
        payload = self._make_toggle_command(CmdField.SPABOY_BOOST, 1 if on else 0)
        return await self.async_send_command(payload)

    async def async_set_onzen(self, on: bool) -> bool:
        """Set Onzen on/off."""
        payload = self._make_toggle_command(CmdField.SET_ONZEN, 1 if on else 0)
        return await self.async_send_command(payload)

    async def async_set_ozone(self, on: bool) -> bool:
        """Set ozone on/off."""
        payload = self._make_toggle_command(CmdField.SET_OZONE, 1 if on else 0)
        return await self.async_send_command(payload)

    async def async_set_filter(self, on: bool) -> bool:
        """Set filter on/off."""
        payload = self._make_toggle_command(CmdField.SET_FILTER, 1 if on else 0)
        return await self.async_send_command(payload)

    async def async_set_sds(self, on: bool) -> bool:
        """Set SDS (bubbles) on/off."""
        payload = self._make_toggle_command(CmdField.SET_SDS, 1 if on else 0)
        return await self.async_send_command(payload)

    async def async_request_status(self) -> bool:
        """Request current status from spa."""
        async with self._lock:
            if not self._status.connected:
                return False
            return await self._send_packet(MsgType.LIVE)
