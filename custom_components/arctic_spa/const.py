"""Constants for the Arctic Spa integration."""
from enum import IntEnum

DOMAIN = "arctic_spa"

# Configuration
CONF_HOST = "host"
CONF_TEMP_UNIT = "temperature_unit"

# Defaults
DEFAULT_PORT = 12121
DEFAULT_TEMP_UNIT = "C"

# UDP Discovery
UDP_SEND_PORT = 12122
UDP_RECV_PORT = 21212
UDP_QUERY_MSG = b"Query,BlueFalls,\n"

# Protocol
MAGIC = 0xABAD1D3A
HEADER_SIZE = 20

# Message Types
class MsgType(IntEnum):
    LIVE = 0
    COMMAND = 1
    SETTINGS = 2
    CONFIG = 3
    PEAK = 4
    CLOCK = 5
    INFO = 6
    ERROR = 7
    ROUTER = 9
    FILTERS = 13
    ONZEN_LIVE = 48
    ONZEN_SETTINGS = 50


# Pump Status
class PumpStatus(IntEnum):
    OFF = 0
    LOW = 1
    HIGH = 2


# Heater Status
class HeaterStatus(IntEnum):
    IDLE = 0
    WARMUP = 1
    HEATING = 2
    COOLDOWN = 3


# Filter Status
class FilterStatus(IntEnum):
    IDLE = 0
    PURGE = 1
    FILTERING = 2
    SUSPENDED = 3
    OVERTEMPERATURE = 4
    RESUMING = 5
    BOOST = 6
    SANITIZE = 7


# Protobuf Field Numbers - spa_live
class LiveField(IntEnum):
    TEMP = 1
    SETPOINT = 2
    PUMP1 = 3
    PUMP2 = 4
    PUMP3 = 5
    PUMP4 = 6
    PUMP5 = 7
    BLOWER1 = 8
    BLOWER2 = 9
    LIGHTS = 10
    STEREO = 11
    HEATER1 = 12
    HEATER2 = 13
    FILTER = 14
    ONZEN = 15
    OZONE = 16
    EXHAUST_FAN = 17
    SAUNA = 18
    HEATER_ADC = 20
    SAUNA_TIME = 21
    ECONOMY = 22
    CURRENT_ADC = 23
    ALL_ON = 24
    FOGGER = 25
    ERROR = 26
    ALARM = 27
    STATUS = 28
    PH = 29
    ORP = 30
    SDS = 31
    YESS = 32


# Protobuf Field Numbers - spa_command
class CmdField(IntEnum):
    SET_TEMP = 1
    SET_PUMP1 = 2
    SET_PUMP2 = 3
    SET_PUMP3 = 4
    SET_PUMP4 = 5
    SET_PUMP5 = 6
    SET_BLOWER1 = 7
    SET_BLOWER2 = 8
    SET_LIGHTS = 9
    SET_STEREO = 10
    SET_FILTER = 11
    SET_ONZEN = 12
    SET_OZONE = 13
    SET_EXHAUST_FAN = 14
    SET_SAUNA_STATE = 15
    SET_SAUNA_TIME = 16
    ALL_ON = 17
    SET_FOGGER = 18
    SPABOY_BOOST = 19
    PACK_RESET = 20
    LOG_DUMP = 21
    SET_SDS = 22
    SET_YESS = 23


# Update interval
SCAN_INTERVAL = 30
