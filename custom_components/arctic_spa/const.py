"""Constants for the Arctic Spa integration (firmware 3.1.x+ WS protocol)."""
from enum import IntEnum

DOMAIN = "arctic_spa"

CONF_HOST = "host"
CONF_TEMP_UNIT = "temperature_unit"
# Use "entity_prefix" rather than HA's reserved CONF_NAME="name" key — HA's
# frontend has special-case handling for the "name" key that overrides
# custom translations, so the field label couldn't be set to anything other
# than "Name".
CONF_ENTITY_PREFIX = "entity_prefix"

DEFAULT_PORT = 8765
DEFAULT_TEMP_UNIT = "F"
DEFAULT_ENTITY_PREFIX = "arctic_spa"  # literal entity-id prefix root
WS_PATH = "/"

BOOTSTRAP_QUERY = {"query": 0}
RECONNECT_DELAY = 5
FALLBACK_REFRESH_INTERVAL = 300

DEFAULT_MIN_TEMP_F = 59
DEFAULT_MAX_TEMP_F = 104
HARD_MAX_TEMP_F = 107
DEFAULT_MIN_TEMP_C = 15
DEFAULT_MAX_TEMP_C = 40


class PumpStatus(IntEnum):
    OFF = 0
    LOW = 1
    HIGH = 2


class HeaterStatus(IntEnum):
    IDLE = 0
    WARMUP = 1
    HEATING = 2
    COOLDOWN = 3


# Customer Portal-matching labels for aggregate heat-cycle display
# (max of H1/H2 → text per heatCycle.enum.ts in the React source).
HEAT_CYCLE_PORTAL_LABELS = {
    HeaterStatus.IDLE: "Idle",
    HeaterStatus.WARMUP: "Heater Warm-Up",
    HeaterStatus.HEATING: "Heating",
    HeaterStatus.COOLDOWN: "Heater Cool-Down",
}


class FilterStatus(IntEnum):
    IDLE = 0
    PURGE = 1
    FILTERING = 2
    SUSPENDED = 3
    OVERTEMPERATURE = 4
    RESUMING = 5
    BOOST = 6
    SANITIZE = 7


# Live-topic field names (firmware 3.1.x JSON)
LIVE_TEMP = "STemp"
LIVE_PHSM = "phSM"
LIVE_SBSM = "sbSM"
LIVE_PUMP = ("P1", "P2", "P3", "P4", "P5")
LIVE_BLOWER = ("BL1", "BL2")
LIVE_LIGHTS = "Li"
LIVE_HEATER = ("H1", "H2")
LIVE_FILTER = "Filter"
LIVE_OZONE = "Oz"
LIVE_ONZEN = "On"
LIVE_FAN = "Fan"
LIVE_FOGGER = "Fogger"
LIVE_SDS = "SDS"
LIVE_YESS = "Yess"
LIVE_ECON = "Econ"
LIVE_ALL_ON = "AllOn"
LIVE_CURRENT = "Current"
LIVE_HTEMP = "HTemp"

LIVE_SB_TEMP = "sbTemp"
LIVE_SB_VIN = "sbVin"
LIVE_SB_VOUT = "sbVout"
LIVE_SB_I1 = "sbI1"
LIVE_SB_I2 = "sbI2"
LIVE_SB_PH = "sbpH"
LIVE_SB_ORP = "sbORP"
LIVE_SB_STAT = "sbStat"
LIVE_SB_PH_IND = "sbpHind"
LIVE_SB_ORP_IND = "sbORPind"
LIVE_SB_WEAR = "sbWear"
LIVE_SB_WEAR_E1 = "sbWearE1"
LIVE_SB_WEAR_E2 = "sbWearE2"
LIVE_SB_E1P = "sbE1p"
LIVE_SB_E1N = "sbE1n"
LIVE_SB_E2P = "sbE2p"
LIVE_SB_E2N = "sbE2n"
LIVE_SB_PRODUCING = "sbProducing"
LIVE_SB_BOOST = "sbBoost"

# Settings-topic field names (read keys are bare, write keys have set/cfg prefix)
SETT_TSP_READ = "TSP"
SETT_TAG1 = "TAG1"
SETT_TAG2 = "TAG2"
SETT_FS_READ = "FS"
SETT_SB_HR_READ = "SBHr"
SETT_SPA_SERIAL = "SPASN"
SETT_FW_YOC = "YOCFWVer"
SETT_FW_LPC = "LPCFWVer"
SETT_FW_SB = "SBFWVer"
SETT_SB_CONNECTED = "SBConnected"
SETT_RFID_CONNECTED = "RFIDConnected"
SETT_CFG_PUMP = ("cfgP1", "cfgP2", "cfgP3", "cfgP4", "cfgP5")
SETT_CFG_BLOWER = ("cfgB1", "cfgB2")
SETT_CFG_LIGHTS = "cfgLi"
SETT_CFG_HEATER = ("cfgH1", "cfgH2")
SETT_CFG_SB = "cfgSB"
SETT_CFG_FG = "cfgFG"
SETT_CFG_SDS = "cfgSDS"
SETT_CFG_YESS = "cfgYESS"
SETT_CFG_ON = "cfgOn"
SETT_RDT_RED = "RDT_red"
SETT_RDT_GREEN = "RDT_green"
SETT_RDT_BLUE = "RDT_blue"
SETT_RDT_BRIGHT = "RDT_bright"
SETT_RDT_PATTERN = "RDT_pattern"
SETT_FF_READ = "FF"  # filter frequency (effective)
SETT_FD_READ = "FD"  # filter duration (effective)
SETT_SB_ORP_HI = "SBORPhi"
SETT_SB_ORP_LO = "SBORPlo"
SETT_SB_PH_HI = "SBpHhi"
SETT_SB_PH_LO = "SBpHlo"

# Const-topic bound names
CONST_TSP_MIN = "setTSPmin"
CONST_TSP_MAX = "setTSPmax"

# Write keys (sent in raw JSON over the WS, no envelope)
CMD_SET_TSP = "setTSP"
CMD_PUMP_NEXT = ("P1next", "P2next", "P3next", "P4next", "P5next")
CMD_BLOWER_NEXT = ("BL1next", "BL2next")
CMD_LIGHTS_NEXT = "Linext"
CMD_SDS_NEXT = "SDSnext"
CMD_YESS_NEXT = "YESSnext"
CMD_FOGGER_NEXT = "Fgnext"
CMD_ONZEN_NEXT = "Onznext"
CMD_FILTER_BOOST = "FLTRboost"
CMD_SB_BOOST = "SBboost"
CMD_PH_BOOST = "PHboost"
CMD_OZ_PEAK_1 = "OzPeak1"
CMD_OZ_PEAK_2 = "OzPeak2"
CMD_RESET = "Reset"
CMD_SET_FF = "setFF"
CMD_SET_FD = "setFD"
CMD_SET_FS = "setFS"
CMD_SET_SB_HRS = "setSBHrs"
# RDT light write keys differ from read keys (read = bare, write = set-prefixed).
CMD_SET_RDT_RED = "setRDTred"
CMD_SET_RDT_GREEN = "setRDTgreen"
CMD_SET_RDT_BLUE = "setRDTblue"
CMD_SET_RDT_BRIGHT = "setRDTbright"
CMD_SET_RDT_PATTERN = "setRDTpattern"
CMD_SET_ON_HR = "setOnHr"
CMD_SET_ON_CY = "setOnCy"
CMD_SET_OZ_HR = "setOzHr"
CMD_SET_OZ_CY = "setOzCy"
CMD_QUERY = "query"

# Error/status code labels (from upstream arcticLabels.enums.ts; blanks omitted)
SPA_ERROR_LABELS = {
    0: "NO FLOW",
    1: "FLOW SWITCH",
    2: "HEATER OVER TEMPERATURE",
    3: "SPA OVER TEMPERATURE",
    4: "SPA TEMPERATURE PROBE",
    5: "SPA HIGH LIMIT",
    7: "FREEZE PROTECT",
    8: "PH HIGH",
    9: "HEATER PROBE DISCONNECTED",
    11: "SPABOY COMM ERROR",
    13: "HEATER WAY ABOVE WATER TEMP",
    14: "ORP NOT RESPONDING TO PRODUCTION",
    15: "PH TOO LOW (<6.5)",
}

SPA_STATUS_LABELS = {
    6: "SEEPROM ERROR",
    10: "HEATER PROBE TEST FAILED",
    12: "HEATER SPA MISMATCH",
    13: "HEATER WAY ABOVE WATER",
    16: "PH PUMP NONRESPONSIVE",
    17: "TARGET TEMPERATURE REACHED",
    20: "NO CURRENT PUMP1L",
    21: "NO CURRENT PUMP1H",
    22: "NO CURRENT PUMP2",
    23: "NO CURRENT PUMP3",
    24: "NO CURRENT PUMP4",
    25: "NO CURRENT YESS",
    26: "NO CURRENT ONZEN",
    27: "NO CURRENT HEATER1",
    28: "NO CURRENT HEATER2",
    29: "ERRONEOUS JSON LABEL",
    30: "ERRONEOUS JSON DATA",
    33: "PUMP1 START CAP FAILED",
    34: "PUMP1H START CAP FAILED",
    35: "PUMP2 START CAP FAILED",
    36: "PUMP3 START CAP FAILED",
    37: "PUMP4 START CAP FAILED",
    38: "YESS START CAP FAILED",
    39: "ONZEN START CAP FAILED",
    53: "SPABOY PH TIMEOUT",
    54: "SPABOY ORP TIMEOUT",
    59: "PCBID0",
    60: "PCBID1",
    61: "PCBID2",
    62: "PCBID3",
    63: "PCBID4",
}

# Codes that surface as STAT but are NOT problems — exclude from alarm sensor.
# - 17 "TARGET TEMPERATURE REACHED": informational (good news)
# - 59-63 "PCBID0..4": board-revision identifier, exactly one is always set
SPA_STATUS_INFORMATIONAL = {17, 59, 60, 61, 62, 63}

# RDT light patterns — names per Customer Portal LightsDialog.tsx (only 4 defined)
RDT_PATTERN_NAMES = {
    0: "Solid",
    1: "Fade In",
    2: "Blinking",
    3: "Spectrum",
}

# SpaBoy ORP indicator bands (sbORPind 0-4). Raw value + ppm range live in
# the entity's extra_state_attributes; pH Level / ORP sensors carry the literal.
SB_ORP_BAND_LABELS = {
    0: "Very Low",  # <0.1 ppm
    1: "Low",       # 0.1-0.5 ppm
    2: "OK",        # 0.6-1.5 ppm
    3: "High",      # 1.6-3.0 ppm
    4: "Very High", # >3.0 ppm
}

# SpaBoy pH indicator bands (sbpHind 0-4).
SB_PH_BAND_LABELS = {
    0: "Very Low",  # <6.8
    1: "Low",       # 6.8-7.2
    2: "OK",        # 7.3-7.8
    3: "High",      # 7.9-8.2
    4: "Very High", # >8.2
}

# Filter replacement-frequency presets (days). User selects one; HA-side
# calculator decreases filter_X_life_remaining at this cadence.
FILTER_LIFESPAN_OPTIONS = {
    "90 days": 90,
    "180 days": 180,
    "365 days": 365,
}
FILTER_LIFESPAN_DEFAULT = "180 days"

# Chlorine production presets per Customer Portal SpaBoy.tsx orpLevelMapper.
# Each preset is (SBORPlo, SBORPhi). When the user picks a level the portal
# also resets SBHr to 0 (likely meaning "auto duty cycle" for that band).
CHLORINE_LEVEL_PRESETS = {
    "Low":    (545, 555),  # ~550 mV target
    "Medium": (645, 655),  # ~650 mV target
    "High":   (745, 755),  # ~750 mV target
}

# SmartPH state machine (live.phSM) — from upstream smartPhState.enums.ts
SMARTPH_LABELS = {
    0: "Idle",
    1: "Check Conditions",
    2: "Priming",
    3: "Preamble Pulse",
    4: "Dosing",
    5: "Wait Between Shots",
    6: "Evaluate Recovery",
    7: "Error Recovery",
    8: "Post Preamble Wait",
    9: "Abort Sequence",
}

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
