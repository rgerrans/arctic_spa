# Arctic Spa Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Home Assistant integration for Arctic Spas hot tubs with WiFi connectivity (2020+ models with Yoctub protocol).

## Features

- **Climate Control**: Set and monitor water temperature (°C or °F)
- **Pump Control**: Control pumps 1-3 (Off/Low/High)
- **Blower Control**: Control blower (Off/Low/High)
- **Lights**: Toggle spa lights on/off
- **Spa Boost**: Enable/disable boost mode
- **Onzen**: Enable/disable Onzen sanitization
- **Sensors**:
  - Current water temperature
  - Target temperature
  - Heater status (Idle/Warming Up/Heating/Cooling Down)
  - Filter status
  - pH level (if equipped)
  - ORP/Chlorine level (if equipped)
- **Binary Sensors**:
  - Heater active
  - Connection status
  - Boost active
  - Onzen active
  - Economy mode

## Requirements

- Arctic Spa with WiFi module (2020+ models)
- Spa connected to your local network
- Home Assistant 2023.1.0 or newer

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots in the top right corner
3. Select "Custom repositories"
4. Add this repository URL and select "Integration" as the category
5. Click "Add"
6. Search for "Arctic Spa" and install
7. Restart Home Assistant

### Manual Installation

1. Download the `arctic_spa` folder from this repository
2. Copy it to your `custom_components` folder in Home Assistant
3. Restart Home Assistant

## Configuration

1. Go to Settings → Devices & Services
2. Click "Add Integration"
3. Search for "Arctic Spa"
4. Enter your spa's IP address
5. Select temperature unit (Celsius or Fahrenheit)

## Protocol Details

This integration uses the BlueFalls/Yoctub protocol:
- UDP discovery on port 12122
- TCP communication on port 12121
- Protobuf-encoded messages

## Troubleshooting

### Cannot Connect
- Ensure your spa is powered on
- Check that the spa is connected to your WiFi network
- Try pinging the spa's IP address
- Make sure no other app is connected to the spa (only one connection allowed)

### Commands Not Working
- The spa requires a UDP wake-up before responding to TCP commands
- This integration handles this automatically, but network firewalls may block UDP

## License

MIT License

## Credits

Protocol reverse-engineered from the Arctic Spas Android app.
