"""Arctic Spa WebSocket Client (firmware 3.1.x JSON protocol over ws://<spa>:8765/)."""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional

import websockets
from websockets.client import WebSocketClientProtocol

from .const import (
    ALARM_CODES,
    BOOTSTRAP_QUERY,
    CMD_BLOWER_NEXT,
    CMD_FILTER_BOOST,
    CMD_FOGGER_NEXT,
    CMD_LIGHTS_NEXT,
    CMD_ONZEN_NEXT,
    CMD_OZ_PEAK_1,
    CMD_OZ_PEAK_2,
    CMD_PH_BOOST,
    CMD_PUMP_NEXT,
    CMD_RESET,
    CMD_SB_BOOST,
    CMD_SDS_NEXT,
    CMD_SET_FD,
    CMD_SET_FF,
    CMD_SET_FS,
    CMD_SET_RDT_BLUE,
    CMD_SET_RDT_BRIGHT,
    CMD_SET_RDT_GREEN,
    CMD_SET_RDT_PATTERN,
    CMD_SET_RDT_RED,
    CMD_SET_SB_HRS,
    CMD_SET_TSP,
    CMD_YESS_NEXT,
    CONST_TSP_MAX,
    CONST_TSP_MIN,
    DEFAULT_MAX_TEMP_F,
    DEFAULT_MIN_TEMP_F,
    DEFAULT_PORT,
    ERROR_CODES,
    FilterStatus,
    HeaterStatus,
    LIVE_ALL_ON,
    LIVE_BLOWER,
    LIVE_CURRENT,
    LIVE_ECON,
    LIVE_FAN,
    LIVE_FILTER,
    LIVE_FOGGER,
    LIVE_HEATER,
    LIVE_HTEMP,
    LIVE_LIGHTS,
    LIVE_ONZEN,
    LIVE_OZONE,
    LIVE_PHSM,
    LIVE_PUMP,
    LIVE_SB_BOOST,
    LIVE_SB_E1N,
    LIVE_SB_E1P,
    LIVE_SB_E2N,
    LIVE_SB_E2P,
    LIVE_SB_I1,
    LIVE_SB_I2,
    LIVE_SB_ORP,
    LIVE_SB_ORP_IND,
    LIVE_SB_PH,
    LIVE_SB_PH_IND,
    LIVE_SB_PRODUCING,
    LIVE_SB_STAT,
    LIVE_SB_TEMP,
    LIVE_SB_VIN,
    LIVE_SB_VOUT,
    LIVE_SB_WEAR,
    LIVE_SB_WEAR_E1,
    LIVE_SB_WEAR_E2,
    LIVE_SBSM,
    LIVE_SDS,
    LIVE_TEMP,
    LIVE_YESS,
    PumpStatus,
    RECONNECT_DELAY,
    SETT_CFG_BLOWER,
    SETT_CFG_FG,
    SETT_CFG_HEATER,
    SETT_CFG_LIGHTS,
    SETT_CFG_ON,
    SETT_CFG_PUMP,
    SETT_CFG_SB,
    SETT_CFG_SDS,
    SETT_CFG_YESS,
    SETT_FD_READ,
    SETT_FF_READ,
    SETT_FS_READ,
    SETT_FW_LPC,
    SETT_FW_SB,
    SETT_FW_YOC,
    SETT_RDT_BLUE,
    SETT_RDT_BRIGHT,
    SETT_RDT_GREEN,
    SETT_RDT_PATTERN,
    SETT_RDT_RED,
    SETT_SB_HR_READ,
    SETT_SB_ORP_HI,
    SETT_SB_ORP_LO,
    SETT_SB_PH_HI,
    SETT_SB_PH_LO,
    SETT_SPA_SERIAL,
    SETT_TAG1,
    SETT_TAG2,
    SETT_TSP_READ,
    SMARTPH_LABELS,
    SPA_ERROR_LABELS,
    SPA_STATUS_INFORMATIONAL,
    SPA_STATUS_LABELS,
    WS_PATH,
)

_LOGGER = logging.getLogger(__name__)

CONNECT_TIMEOUT = 10
PING_INTERVAL = 20
PING_TIMEOUT = 10


def _pump_level(raw: Any) -> PumpStatus:
    """Map raw pump value to off/low/high (per Customer Portal pumpLevel())."""
    try:
        v = int(raw or 0)
    except (TypeError, ValueError):
        return PumpStatus.OFF
    if v > 15:
        return PumpStatus.HIGH
    if v > 0:
        return PumpStatus.LOW
    return PumpStatus.OFF


def _bool(raw: Any) -> bool:
    try:
        return bool(int(raw or 0))
    except (TypeError, ValueError):
        return bool(raw)


def _int(raw: Any, default: int = 0) -> int:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _float(raw: Any, default: float = 0.0) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


@dataclass
class SpaStatus:
    """Aggregate spa state across live / sett / const / error topics."""

    temperature_f: int = 0
    setpoint_f: int = 0
    pump1: PumpStatus = PumpStatus.OFF
    pump2: PumpStatus = PumpStatus.OFF
    pump3: PumpStatus = PumpStatus.OFF
    pump4: PumpStatus = PumpStatus.OFF
    pump5: PumpStatus = PumpStatus.OFF
    pump_raw: list[int] = field(default_factory=lambda: [0, 0, 0, 0, 0])
    blower1: PumpStatus = PumpStatus.OFF
    blower2: PumpStatus = PumpStatus.OFF
    blower_raw: list[int] = field(default_factory=lambda: [0, 0])
    lights: bool = False
    heater1: HeaterStatus = HeaterStatus.IDLE
    heater2: HeaterStatus = HeaterStatus.IDLE
    filter_status: FilterStatus = FilterStatus.IDLE
    onzen: bool = False
    ozone: bool = False
    fan: bool = False
    fogger: bool = False
    sds: bool = False
    yess: bool = False
    economy: bool = False
    all_on: bool = False
    current_draw: int = 0
    heater_temp: int = 0
    # Error/status (rebuilt from ERR0..ERR63 / STAT0..STAT63 boolean dict)
    error: int = 0  # first active labeled ERR index, 0 = none
    alarm: int = 0  # first active alarm-worthy STAT index, 0 = none
    active_errors: list[int] = field(default_factory=list)
    active_statuses: list[int] = field(default_factory=list)  # alarm-worthy only
    informational_statuses: list[int] = field(default_factory=list)  # PCBID, target reached
    # State machines
    smartph_state: int = 0
    spaboy_state_machine: int = 0
    # Filter accessory state. TAG1/TAG2 are RFID hex IDs of installed cartridges
    # (empty string = no cartridge in that slot). The portal computes
    # "Good" / "No Filter Present" from truthy-ness of the string.
    filter_tag1: str = ""
    filter_tag2: str = ""
    filter_stop_above_3: bool = False  # FS — stop filtering 3F above setpoint

    # SpaBoy (Onzen chlorinator)
    sb_present: bool = False
    sb_temp_f: int = 0
    sb_voltage_in: float = 0.0
    sb_voltage_out: float = 0.0
    sb_current_1: float = 0.0
    sb_current_2: float = 0.0
    sb_ph: int = 0
    sb_orp: int = 0
    sb_status: int = 0
    sb_ph_indicator: int = 0
    sb_orp_indicator: int = 0
    sb_life_remaining_pct: int = 0       # field name 'sbWear' — actually remaining capacity, not wear
    sb_life_remaining_e1_pct: int = 0    # per-electrode (within single cell — bipolar plates)
    sb_life_remaining_e2_pct: int = 0
    sb_e1_pos: int = 0
    sb_e1_neg: int = 0
    sb_e2_pos: int = 0
    sb_e2_neg: int = 0
    sb_producing: bool = False
    sb_boost: bool = False

    # Settings + config flags
    spa_serial: str = ""
    fw_yoc: str = ""
    fw_lpc: str = ""
    fw_sb: str = ""
    filter_frequency: int = 0
    filter_duration: int = 0
    spaboy_hours_per_day: int = 0
    cfg_pump: list[bool] = field(default_factory=lambda: [False] * 5)
    cfg_blower: list[bool] = field(default_factory=lambda: [False] * 2)
    cfg_lights: bool = False
    cfg_heater: list[bool] = field(default_factory=lambda: [False] * 2)
    cfg_spaboy: bool = False
    cfg_fogger: bool = False
    cfg_sds: bool = False
    cfg_yess: bool = False
    cfg_onzen: bool = False

    # RGB Lights (RDT)
    rdt_red: int = 0
    rdt_green: int = 0
    rdt_blue: int = 0
    rdt_brightness: int = 0
    rdt_pattern: int = 0

    # SpaBoy chemistry setpoint bands
    sb_orp_hi: int = 0
    sb_orp_lo: int = 0
    sb_ph_hi: int = 0
    sb_ph_lo: int = 0

    # Const-topic bounds (dynamic min/max from spa)
    setpoint_min_f: int = DEFAULT_MIN_TEMP_F
    setpoint_max_f: int = DEFAULT_MAX_TEMP_F

    connected: bool = False
    last_update: Optional[datetime] = None
    energy_kwh: float = 0.0
    _last_energy_update: Optional[datetime] = None

    @property
    def temperature_c(self) -> float:
        c = (self.temperature_f - 32) * 5 / 9
        return round(c * 2) / 2

    @property
    def setpoint_c(self) -> float:
        c = (self.setpoint_f - 32) * 5 / 9
        return round(c * 2) / 2

    @property
    def heater_active(self) -> bool:
        active = (HeaterStatus.WARMUP, HeaterStatus.HEATING)
        return self.heater1 in active or self.heater2 in active

    @property
    def heat_cycle(self) -> HeaterStatus:
        """Aggregate heat cycle = max(H1, H2). Matches Customer Portal display."""
        return HeaterStatus(max(self.heater1.value, self.heater2.value))

    @property
    def filter_boost_active(self) -> bool:
        return self.filter_status == FilterStatus.BOOST

    @property
    def has_error(self) -> bool:
        return bool(self.active_errors)

    @property
    def has_alarm(self) -> bool:
        return bool(self.active_statuses)

    @property
    def error_message(self) -> str:
        if not self.active_errors:
            return "No Error"
        return ", ".join(SPA_ERROR_LABELS.get(i, f"ERR{i}") for i in self.active_errors)

    @property
    def alarm_message(self) -> str:
        if not self.active_statuses:
            return "No Alarm"
        return ", ".join(SPA_STATUS_LABELS.get(i, f"STAT{i}") for i in self.active_statuses)

    @property
    def informational_status_message(self) -> str:
        if not self.informational_statuses:
            return "None"
        return ", ".join(SPA_STATUS_LABELS.get(i, f"STAT{i}") for i in self.informational_statuses)

    @property
    def pcb_revision(self) -> int | None:
        """Returns the PCB revision number (0-4) from active PCBID STATs, or None."""
        for i in (59, 60, 61, 62, 63):
            if i in self.informational_statuses:
                return i - 59
        return None

    @property
    def target_temperature_reached(self) -> bool:
        return 17 in self.informational_statuses

    @property
    def smartph_state_label(self) -> str:
        return SMARTPH_LABELS.get(self.smartph_state, f"State {self.smartph_state}")

    @property
    def filter_run_hours_per_day(self) -> int:
        return self.filter_frequency * self.filter_duration

    @property
    def estimated_power_watts(self) -> int:
        HEATER_HEATING_WATTS = 6500
        HEATER_WARMUP_WATTS = 350
        HEATER_COOLDOWN_WATTS = 350
        PUMP_HIGH_WATTS = 1700
        PUMP_LOW_WATTS = 370
        IDLE_WATTS = 15

        power = IDLE_WATTS
        high_pumps = sum(1 for p in (self.pump1, self.pump2, self.pump3) if p == PumpStatus.HIGH)

        if high_pumps > 0:
            power = high_pumps * PUMP_HIGH_WATTS
        elif self.heater1 == HeaterStatus.HEATING:
            power = HEATER_HEATING_WATTS
        elif self.heater1 == HeaterStatus.WARMUP:
            power = HEATER_WARMUP_WATTS
        elif self.heater1 == HeaterStatus.COOLDOWN:
            power = HEATER_COOLDOWN_WATTS
        elif self.pump1 == PumpStatus.LOW:
            power = PUMP_LOW_WATTS

        if self.blower1 != PumpStatus.OFF:
            power += 500
        return max(0, power)  # Defensive — Power sensor must never be negative

    def update_energy(self) -> None:
        now = datetime.now()
        if self._last_energy_update is not None:
            elapsed_h = (now - self._last_energy_update).total_seconds() / 3600.0
            self.energy_kwh += (self.estimated_power_watts / 1000.0) * elapsed_h
        self._last_energy_update = now


class ArcticSpaClient:
    """WebSocket client for Arctic Spa (firmware 3.1.x)."""

    def __init__(self, host: str, port: int = DEFAULT_PORT) -> None:
        self.host = host
        self.port = port
        self._url = f"ws://{host}:{port}{WS_PATH}"
        self._ws: Optional[WebSocketClientProtocol] = None
        self._status = SpaStatus()
        self._send_lock = asyncio.Lock()
        self._listener_task: Optional[asyncio.Task] = None
        self._running = False
        self._state_callbacks: list[Callable[[], None]] = []

    @property
    def status(self) -> SpaStatus:
        return self._status

    @property
    def connected(self) -> bool:
        return self._status.connected and self._ws is not None

    def register_state_callback(self, callback: Callable[[], None]) -> None:
        if callback not in self._state_callbacks:
            self._state_callbacks.append(callback)

    def unregister_state_callback(self, callback: Callable[[], None]) -> None:
        if callback in self._state_callbacks:
            self._state_callbacks.remove(callback)

    def _notify(self) -> None:
        for cb in self._state_callbacks:
            try:
                cb()
            except Exception as err:  # pragma: no cover
                _LOGGER.error("state callback raised: %s", err)

    async def async_start(self) -> bool:
        if self._running:
            return True
        self._running = True
        ok = await self._connect_once()
        self._listener_task = asyncio.create_task(self._supervise())
        return ok

    async def async_stop(self) -> None:
        self._running = False
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None
        await self._close_ws()

    async def _close_ws(self) -> None:
        ws = self._ws
        self._ws = None
        self._status.connected = False
        if ws is not None:
            try:
                await ws.close()
            except Exception:
                pass

    async def _connect_once(self) -> bool:
        try:
            _LOGGER.info("Connecting to spa WebSocket %s", self._url)
            ws = await asyncio.wait_for(
                websockets.connect(
                    self._url,
                    ping_interval=PING_INTERVAL,
                    ping_timeout=PING_TIMEOUT,
                    open_timeout=CONNECT_TIMEOUT,
                    max_size=1_000_000,
                ),
                timeout=CONNECT_TIMEOUT,
            )
        except Exception as err:
            _LOGGER.warning("Spa WS connect failed: %s", err)
            return False

        self._ws = ws
        self._status.connected = True
        try:
            await ws.send(json.dumps(BOOTSTRAP_QUERY))
        except Exception as err:
            _LOGGER.warning("Spa WS bootstrap send failed: %s", err)
            await self._close_ws()
            return False
        _LOGGER.info("Spa WS connected; bootstrap sent")
        self._notify()
        return True

    async def _supervise(self) -> None:
        """Listen + auto-reconnect loop."""
        while self._running:
            if self._ws is None:
                if not await self._connect_once():
                    await asyncio.sleep(RECONNECT_DELAY)
                    continue
            try:
                async for raw in self._ws:
                    self._handle_raw(raw)
            except websockets.ConnectionClosed as err:
                _LOGGER.info("Spa WS closed (code=%s); will reconnect", getattr(err, "code", "?"))
            except asyncio.CancelledError:
                break
            except Exception as err:  # pragma: no cover
                _LOGGER.warning("Spa WS listener error: %s", err)
            await self._close_ws()
            if self._running:
                await asyncio.sleep(RECONNECT_DELAY)

    def _handle_raw(self, raw: Any) -> None:
        if isinstance(raw, (bytes, bytearray)):
            try:
                raw = raw.decode("utf-8")
            except Exception:
                return
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            _LOGGER.debug("non-JSON frame ignored: %r", raw[:80])
            return

        if "command" in msg:
            _LOGGER.debug("server command: %s", msg)
            return

        topic = msg.get("topic")
        data = msg.get("data")
        if not topic or data is None:
            return
        try:
            if topic == "live":
                self._apply_live(data)
            elif topic == "sett":
                self._apply_settings(data)
            elif topic == "const":
                self._apply_const(data)
            elif topic == "error":
                self._apply_error(data)
            elif topic == "status":
                self._apply_status(data)
            elif topic == "update-status":
                pass  # firmware update progress; could be surfaced later
            else:
                _LOGGER.debug("unhandled topic: %s", topic)
                return
        except Exception as err:  # pragma: no cover
            _LOGGER.warning("error applying topic=%s: %s", topic, err)
            return
        self._status.last_update = datetime.now()
        self._status.update_energy()
        self._notify()

    def _apply_live(self, d: dict) -> None:
        s = self._status
        if LIVE_TEMP in d:
            s.temperature_f = _int(d[LIVE_TEMP])
        for i, key in enumerate(LIVE_PUMP):
            if key in d:
                raw = _int(d[key])
                s.pump_raw[i] = raw
                level = _pump_level(raw)
                if i == 0: s.pump1 = level
                elif i == 1: s.pump2 = level
                elif i == 2: s.pump3 = level
                elif i == 3: s.pump4 = level
                elif i == 4: s.pump5 = level
        for i, key in enumerate(LIVE_BLOWER):
            if key in d:
                raw = _int(d[key])
                s.blower_raw[i] = raw
                level = _pump_level(raw)
                if i == 0: s.blower1 = level
                else: s.blower2 = level
        if LIVE_LIGHTS in d:
            s.lights = _bool(d[LIVE_LIGHTS])
        for i, key in enumerate(LIVE_HEATER):
            if key in d:
                try:
                    hs = HeaterStatus(min(_int(d[key]), 3))
                except ValueError:
                    hs = HeaterStatus.IDLE
                if i == 0: s.heater1 = hs
                else: s.heater2 = hs
        if LIVE_FILTER in d:
            try:
                s.filter_status = FilterStatus(min(_int(d[LIVE_FILTER]), 7))
            except ValueError:
                s.filter_status = FilterStatus.IDLE
        if LIVE_OZONE in d: s.ozone = _bool(d[LIVE_OZONE])
        if LIVE_ONZEN in d: s.onzen = _bool(d[LIVE_ONZEN])
        if LIVE_FAN in d: s.fan = _bool(d[LIVE_FAN])
        if LIVE_FOGGER in d: s.fogger = _bool(d[LIVE_FOGGER])
        if LIVE_SDS in d: s.sds = _bool(d[LIVE_SDS])
        if LIVE_YESS in d: s.yess = _bool(d[LIVE_YESS])
        if LIVE_ECON in d: s.economy = _bool(d[LIVE_ECON])
        if LIVE_ALL_ON in d: s.all_on = _bool(d[LIVE_ALL_ON])
        if LIVE_CURRENT in d: s.current_draw = _int(d[LIVE_CURRENT])
        if LIVE_HTEMP in d: s.heater_temp = _int(d[LIVE_HTEMP])
        if LIVE_PHSM in d: s.smartph_state = _int(d[LIVE_PHSM])
        if LIVE_SBSM in d: s.spaboy_state_machine = _int(d[LIVE_SBSM])

        if LIVE_SB_TEMP in d: s.sb_temp_f = _int(d[LIVE_SB_TEMP])
        if LIVE_SB_VIN in d:
            s.sb_voltage_in = _float(d[LIVE_SB_VIN])
            s.sb_present = True
        if LIVE_SB_VOUT in d: s.sb_voltage_out = _float(d[LIVE_SB_VOUT])
        if LIVE_SB_I1 in d: s.sb_current_1 = _float(d[LIVE_SB_I1])
        if LIVE_SB_I2 in d: s.sb_current_2 = _float(d[LIVE_SB_I2])
        if LIVE_SB_PH in d: s.sb_ph = _int(d[LIVE_SB_PH])
        if LIVE_SB_ORP in d: s.sb_orp = _int(d[LIVE_SB_ORP])
        if LIVE_SB_STAT in d: s.sb_status = _int(d[LIVE_SB_STAT])
        if LIVE_SB_PH_IND in d: s.sb_ph_indicator = _int(d[LIVE_SB_PH_IND])
        if LIVE_SB_ORP_IND in d: s.sb_orp_indicator = _int(d[LIVE_SB_ORP_IND])
        # Field 'sbWear' is REMAINING capacity (high = fresh, low = needs replacement),
        # not wear consumed. Confirmed by Customer Portal CSS bands: <=20 worst,
        # >80 best. Aggregate value; sbWearE1/E2 are per-plate inside the single
        # bipolar cell (chlorinators have one cell with two electrode plates that
        # alternate polarity to prevent scaling).
        if LIVE_SB_WEAR in d: s.sb_life_remaining_pct = _int(d[LIVE_SB_WEAR])
        if LIVE_SB_WEAR_E1 in d: s.sb_life_remaining_e1_pct = _int(d[LIVE_SB_WEAR_E1])
        if LIVE_SB_WEAR_E2 in d: s.sb_life_remaining_e2_pct = _int(d[LIVE_SB_WEAR_E2])
        if LIVE_SB_E1P in d: s.sb_e1_pos = _int(d[LIVE_SB_E1P])
        if LIVE_SB_E1N in d: s.sb_e1_neg = _int(d[LIVE_SB_E1N])
        if LIVE_SB_E2P in d: s.sb_e2_pos = _int(d[LIVE_SB_E2P])
        if LIVE_SB_E2N in d: s.sb_e2_neg = _int(d[LIVE_SB_E2N])
        if LIVE_SB_PRODUCING in d: s.sb_producing = _bool(d[LIVE_SB_PRODUCING])
        if LIVE_SB_BOOST in d: s.sb_boost = _bool(d[LIVE_SB_BOOST])

    def _apply_settings(self, d: dict) -> None:
        s = self._status
        if SETT_TSP_READ in d: s.setpoint_f = _int(d[SETT_TSP_READ])
        if SETT_SPA_SERIAL in d: s.spa_serial = str(d[SETT_SPA_SERIAL])
        if SETT_FW_YOC in d: s.fw_yoc = str(d[SETT_FW_YOC])
        if SETT_FW_LPC in d: s.fw_lpc = str(d[SETT_FW_LPC])
        if SETT_FW_SB in d: s.fw_sb = str(d[SETT_FW_SB])
        if SETT_FF_READ in d: s.filter_frequency = _int(d[SETT_FF_READ])
        if SETT_FD_READ in d: s.filter_duration = _int(d[SETT_FD_READ])
        if SETT_FS_READ in d: s.filter_stop_above_3 = _bool(d[SETT_FS_READ])
        if SETT_TAG1 in d: s.filter_tag1 = str(d[SETT_TAG1] or "")
        if SETT_TAG2 in d: s.filter_tag2 = str(d[SETT_TAG2] or "")
        if SETT_SB_HR_READ in d: s.spaboy_hours_per_day = _int(d[SETT_SB_HR_READ])

        for i, key in enumerate(SETT_CFG_PUMP):
            if key in d: s.cfg_pump[i] = _bool(d[key])
        for i, key in enumerate(SETT_CFG_BLOWER):
            if key in d: s.cfg_blower[i] = _bool(d[key])
        if SETT_CFG_LIGHTS in d: s.cfg_lights = _bool(d[SETT_CFG_LIGHTS])
        for i, key in enumerate(SETT_CFG_HEATER):
            if key in d: s.cfg_heater[i] = _bool(d[key])
        if SETT_CFG_SB in d: s.cfg_spaboy = _bool(d[SETT_CFG_SB])
        if SETT_CFG_FG in d: s.cfg_fogger = _bool(d[SETT_CFG_FG])
        if SETT_CFG_SDS in d: s.cfg_sds = _bool(d[SETT_CFG_SDS])
        if SETT_CFG_YESS in d: s.cfg_yess = _bool(d[SETT_CFG_YESS])
        if SETT_CFG_ON in d: s.cfg_onzen = _bool(d[SETT_CFG_ON])

        if SETT_RDT_RED in d: s.rdt_red = _int(d[SETT_RDT_RED])
        if SETT_RDT_GREEN in d: s.rdt_green = _int(d[SETT_RDT_GREEN])
        if SETT_RDT_BLUE in d: s.rdt_blue = _int(d[SETT_RDT_BLUE])
        if SETT_RDT_BRIGHT in d: s.rdt_brightness = _int(d[SETT_RDT_BRIGHT])
        if SETT_RDT_PATTERN in d: s.rdt_pattern = _int(d[SETT_RDT_PATTERN])

        if SETT_SB_ORP_HI in d: s.sb_orp_hi = _int(d[SETT_SB_ORP_HI])
        if SETT_SB_ORP_LO in d: s.sb_orp_lo = _int(d[SETT_SB_ORP_LO])
        if SETT_SB_PH_HI in d: s.sb_ph_hi = _int(d[SETT_SB_PH_HI])
        if SETT_SB_PH_LO in d: s.sb_ph_lo = _int(d[SETT_SB_PH_LO])

    def _apply_const(self, d: dict) -> None:
        s = self._status
        if CONST_TSP_MIN in d: s.setpoint_min_f = _int(d[CONST_TSP_MIN], DEFAULT_MIN_TEMP_F)
        if CONST_TSP_MAX in d: s.setpoint_max_f = _int(d[CONST_TSP_MAX], DEFAULT_MAX_TEMP_F)

    def _apply_error(self, d: dict) -> None:
        """Error topic: {ERR0:bool,...,ERR63:bool, Lower_ERR_Word:hex, Upper_ERR_Word:hex}."""
        s = self._status
        if not isinstance(d, dict):
            return
        active_errs: list[int] = []
        for k, v in d.items():
            if not v or not isinstance(k, str) or not k.startswith("ERR"):
                continue
            try:
                idx = int(k[3:])
            except ValueError:
                continue
            if idx in SPA_ERROR_LABELS:
                active_errs.append(idx)
        s.active_errors = sorted(active_errs)
        s.error = s.active_errors[0] if s.active_errors else 0

    def _apply_status(self, d: dict) -> None:
        """Status topic: {STAT0:bool,...,STAT63:bool, Lower_STAT_Word:hex, Upper_STAT_Word:hex}.

        Splits codes into alarm-worthy (active_statuses) vs informational
        (informational_statuses). PCBID0-4 + TARGET TEMPERATURE REACHED are
        normal operational signals and don't belong on the alarm sensor.
        """
        s = self._status
        if not isinstance(d, dict):
            return
        active_stats: list[int] = []
        info_stats: list[int] = []
        for k, v in d.items():
            if not v or not isinstance(k, str) or not k.startswith("STAT"):
                continue
            try:
                idx = int(k[4:])
            except ValueError:
                continue
            if idx not in SPA_STATUS_LABELS:
                continue
            if idx in SPA_STATUS_INFORMATIONAL:
                info_stats.append(idx)
            else:
                active_stats.append(idx)
        s.active_statuses = sorted(active_stats)
        s.informational_statuses = sorted(info_stats)
        s.alarm = s.active_statuses[0] if s.active_statuses else 0

    async def _send(self, payload: dict) -> bool:
        ws = self._ws
        if ws is None or not self._status.connected:
            _LOGGER.warning("send while disconnected: %s", payload)
            return False
        async with self._send_lock:
            try:
                await ws.send(json.dumps(payload))
                return True
            except Exception as err:
                _LOGGER.warning("send failed: %s (%s)", payload, err)
                return False

    async def async_request_status(self) -> bool:
        return await self._send(BOOTSTRAP_QUERY)

    async def async_set_temperature(self, temp_f: int) -> bool:
        bounded = max(self._status.setpoint_min_f, min(temp_f, self._status.setpoint_max_f))
        return await self._send({CMD_SET_TSP: int(bounded)})

    async def async_set_temperature_c(self, temp_c: float) -> bool:
        return await self.async_set_temperature(round(temp_c * 9 / 5 + 32))

    async def async_cycle_pump(self, pump_num: int) -> bool:
        if not 1 <= pump_num <= 5:
            return False
        return await self._send({CMD_PUMP_NEXT[pump_num - 1]: 1})

    async def async_set_pump(self, pump_num: int, target: PumpStatus) -> bool:
        """Cycle pump from current state to target."""
        if not 1 <= pump_num <= 5:
            return False
        current = (self._status.pump1, self._status.pump2, self._status.pump3,
                   self._status.pump4, self._status.pump5)[pump_num - 1]
        return await self._cycle_to(target.value, current.value, lambda: self.async_cycle_pump(pump_num))

    async def async_cycle_blower(self, blower_num: int) -> bool:
        if not 1 <= blower_num <= 2:
            return False
        return await self._send({CMD_BLOWER_NEXT[blower_num - 1]: 1})

    async def async_set_blower(self, blower_num: int, target: PumpStatus) -> bool:
        if not 1 <= blower_num <= 2:
            return False
        current = (self._status.blower1, self._status.blower2)[blower_num - 1]
        return await self._cycle_to(target.value, current.value, lambda: self.async_cycle_blower(blower_num))

    async def _cycle_to(self, target: int, current: int, cycle_fn: Callable[[], Any]) -> bool:
        """Cycle (0→1→2→0) until current matches target. Cap at 3 calls."""
        if current == target:
            return True
        cycles = (target - current) % 3
        ok = True
        for _ in range(cycles):
            ok = await cycle_fn() and ok
            await asyncio.sleep(0.25)
        return ok

    async def async_cycle_lights(self) -> bool:
        return await self._send({CMD_LIGHTS_NEXT: 1})

    async def async_set_lights(self, on: bool) -> bool:
        if self._status.lights == on:
            return True
        return await self.async_cycle_lights()

    async def async_cycle_sds(self) -> bool:
        return await self._send({CMD_SDS_NEXT: 1})

    async def async_set_sds(self, on: bool) -> bool:
        if self._status.sds == on:
            return True
        return await self.async_cycle_sds()

    async def async_cycle_yess(self) -> bool:
        return await self._send({CMD_YESS_NEXT: 1})

    async def async_set_yess(self, on: bool) -> bool:
        if self._status.yess == on:
            return True
        return await self.async_cycle_yess()

    async def async_cycle_fogger(self) -> bool:
        return await self._send({CMD_FOGGER_NEXT: 1})

    async def async_set_fogger(self, on: bool) -> bool:
        if self._status.fogger == on:
            return True
        return await self.async_cycle_fogger()

    async def async_cycle_onzen(self) -> bool:
        return await self._send({CMD_ONZEN_NEXT: 1})

    async def async_set_onzen(self, on: bool) -> bool:
        if self._status.onzen == on:
            return True
        return await self.async_cycle_onzen()

    async def async_set_filter_boost(self, on: bool) -> bool:
        return await self._send({CMD_FILTER_BOOST: 1 if on else 0})

    async def async_set_spaboy_boost(self, on: bool) -> bool:
        return await self._send({CMD_SB_BOOST: 1 if on else 0})

    async def async_set_rdt(self, *, red: int | None = None, green: int | None = None,
                            blue: int | None = None, brightness: int | None = None,
                            pattern: int | None = None) -> bool:
        # Write keys for RDT lights use the set-prefixed form per LightsDialog.tsx:
        # setRDTred / setRDTgreen / setRDTblue / setRDTbright / setRDTpattern.
        # The read keys (RDT_red etc.) are different — read vs write asymmetry.
        payload: dict[str, int] = {}
        if red is not None: payload[CMD_SET_RDT_RED] = max(0, min(int(red), 255))
        if green is not None: payload[CMD_SET_RDT_GREEN] = max(0, min(int(green), 255))
        if blue is not None: payload[CMD_SET_RDT_BLUE] = max(0, min(int(blue), 255))
        if brightness is not None: payload[CMD_SET_RDT_BRIGHT] = max(0, min(int(brightness), 255))
        if pattern is not None: payload[CMD_SET_RDT_PATTERN] = int(pattern)
        if not payload:
            return False
        return await self._send(payload)

    async def async_set_chlorine_band(self, target_orp: int, band: int = 5) -> bool:
        return await self._send({SETT_SB_ORP_HI: int(target_orp) + band,
                                 SETT_SB_ORP_LO: int(target_orp) - band})

    async def async_set_chlorine_level(self, lo: int, hi: int) -> bool:
        """Set ORP band + reset SBHr to 0, matching Customer Portal UX."""
        return await self._send({
            SETT_SB_ORP_HI: int(hi),
            SETT_SB_ORP_LO: int(lo),
            CMD_SET_SB_HRS: 0,
        })

    async def async_set_ph_band(self, target_ph_x100: int, band: int = 5) -> bool:
        return await self._send({SETT_SB_PH_HI: int(target_ph_x100) + band,
                                 SETT_SB_PH_LO: int(target_ph_x100) - band})

    async def async_set_filter_frequency(self, freq: int) -> bool:
        return await self._send({CMD_SET_FF: int(freq)})

    async def async_set_filter_duration(self, dur: int) -> bool:
        return await self._send({CMD_SET_FD: int(dur)})

    async def async_set_stop_filter_above(self, on: bool) -> bool:
        return await self._send({CMD_SET_FS: 1 if on else 0})

    async def async_set_spaboy_hours(self, hours: int) -> bool:
        return await self._send({CMD_SET_SB_HRS: int(hours)})

    async def async_ph_boost(self) -> bool:
        # PHboost takes value 0 per Customer Portal SpaBoy page
        return await self._send({CMD_PH_BOOST: 0})

    async def async_oz_peak1(self, off: bool = False) -> bool:
        return await self._send({CMD_OZ_PEAK_1: "off" if off else 1})

    async def async_oz_peak2(self) -> bool:
        return await self._send({CMD_OZ_PEAK_2: 1})

    async def async_reset(self, scope: str = "all") -> bool:
        return await self._send({CMD_RESET: scope})
