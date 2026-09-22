# Vallox RS485 Integration for Home Assistant

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=skjall&repository=home-assistant-vallox-rs485&category=integration)

Home Assistant integration for older Vallox ventilation systems with RS485 interface.

> **Status: Beta** - Core functionality works, testing in progress.

## Supported Models

- Vallox 90 SE
- Vallox Digit SE
- Vallox 080 SE, 090 SE, 096 SE
- Vallox 110 SE, 121 SE, 145 SE
- Vallox ValloPlus 350 SE, 510 SE
- Helios KWL EC/ET series (same protocol)
- Other models using the Digit RS485 protocol

## Features

### Working
- ✅ USB-RS485 adapter auto-discovery with bus validation
- ✅ UI-based configuration with serial port auto-detection
- ✅ Temperature sensors (outside, exhaust, inside, incoming)
- ✅ Humidity sensors (main, sensor 1, sensor 2)
- ✅ CO2 sensor (ppm calculation from high/low bytes)
- ✅ Heat recovery efficiency calculation
- ✅ Fan speed control (levels 1-8, percentage, presets)
- ✅ Power state control
- ✅ Post-heating switch control
- ✅ CO2/humidity adjustment switches
- ✅ Binary sensors (fan status, fault, filter guard, bypass, pre-heating, service reminder)
- ✅ Temperature setpoint controls (heating, pre-heating, bypass, frost protection)
- ✅ Fan speed min/max limits
- ✅ Service reminder interval setting
- ✅ CO2 and humidity threshold settings
- ✅ Passive bus monitoring with active polling for missing/stale registers
- ✅ Lazy entity creation (only creates entities for available sensors)
- ✅ Multi-language support (15 languages)
- ✅ Diagnostics support for troubleshooting
- ✅ Reconfiguration flow (change settings without removing integration)

## Hardware

Requires a USB-RS485 adapter connected to the Vallox panel's RS485 bus.

### Tested Adapters

| Adapter | Chip | Status |
|---------|------|--------|
| **Waveshare USB to RS232/485/TTL** | FT232RNL | ✅ Tested, recommended |

### Compatible Adapters

Most USB-RS485 adapters should work:
- FTDI-based adapters (VID: 0403, PID: 6001)
- CH340-based adapters (VID: 1A86, PID: 7523)
- CP210x-based adapters (VID: 10C4, PID: EA60)
- Prolific PL2303 (VID: 067B, PID: 2303)

### Request Support for Your Adapter

If your USB-RS485 adapter is not auto-detected, you can request support by opening an issue:

1. **Find your adapter's VID and PID:**

   **Linux / Home Assistant OS:**
   ```bash
   lsusb
   # Example output: Bus 001 Device 003: ID 0403:6001 Future Technology Devices International
   #                                        ^^^^:^^^^ = VID:PID
   ```

   **macOS:**
   ```bash
   system_profiler SPUSBDataType | grep -A5 "RS485\|Serial\|USB"
   ```

   **Windows:**
   - Open Device Manager
   - Find your adapter under "Ports (COM & LPT)"
   - Right-click → Properties → Details → Hardware Ids
   - Look for `VID_xxxx&PID_xxxx`

2. **Open an issue** with the [Device Support template](https://github.com/skjall/ha-vallox-rs485/issues/new?template=device_support.md) including:
   - Adapter name and manufacturer
   - VID and PID values
   - Link to product page (if available)
   - Confirmation that the adapter works with your Vallox system

### Wiring

```
Adapter          Vallox Panel
───────          ────────────
A (Data+)   →    A
B (Data-)   →    B
GND         →    M (Ground)
```

**Do not** connect to + or - (24V power supply)!

## Installation

### HACS (recommended)

1. Open HACS
2. "Custom repositories" → Add repository URL
3. Install "Vallox RS485"
4. Restart Home Assistant

### Manual

1. Copy `custom_components/vallox_rs485/` to `<config>/custom_components/`
2. Restart Home Assistant

### Removal

1. Settings → Devices & Services
2. Find "Vallox RS485" integration
3. Click the three dots menu → Delete
4. Restart Home Assistant
5. (Optional) Remove `custom_components/vallox_rs485/` folder if manually installed

## Configuration

### Automatic Discovery (recommended)

The integration automatically detects USB-RS485 adapters and validates Vallox bus traffic.

**To trigger auto-discovery:**
1. **Unplug** your USB-RS485 adapter
2. **Wait 5 seconds**
3. **Plug it back in**
4. Home Assistant will show a notification: "Vallox ventilation discovered"
5. Click to configure

> **Why hotplug?** USB discovery runs once at Home Assistant startup. If the adapter was already connected before HA started, unplugging and replugging triggers immediate detection.

### Manual Configuration

If auto-discovery doesn't work:

1. Settings → Devices & Services → Add Integration
2. Search for "Vallox RS485"
3. Select serial port
4. Done

> **Note:** The integration automatically uses stable device paths (`/dev/serial/by-id/...`) instead of `/dev/ttyUSBx` to prevent issues after system reboots.

### Configuration Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| Serial Port | Yes | - | The USB-RS485 adapter serial port (auto-detected) |
| Name | No | "Vallox" | Display name for the device |
| Scan Interval | No | 30 | Polling interval in seconds (10-300) |
| Device Address | No | 0x2E (46) | RS485 device address for this integration |

**Device Address Notes:**
- Default 0x2E works for most installations
- Only change if you have multiple devices on the same RS485 bus
- Valid range: 0x22-0x2F (34-47)

## Important Warnings

> **⚠️ Power Switch Warning:** When you turn off the Vallox unit via the Power switch, the RS485 bus also shuts down. The integration will lose communication and show entities as unavailable. **You must power-cycle the Vallox unit** (turn off at breaker, wait 10 seconds, turn back on) to restore communication. The software power switch cannot turn the unit back on once the bus is down.

## How It Works

### Lazy Entity Creation
**All entities** are created lazily - they only appear if the corresponding register data is received from the Vallox unit. This means:
- Your Home Assistant only shows entities your unit actually supports
- Optional sensors (CO2, humidity) won't clutter your interface if not installed
- No "unavailable" entities for features your model doesn't have

### Active Polling
The integration uses a hybrid approach:
1. **Passive monitoring**: Listens to existing bus traffic between panel and mainboard
2. **Active polling**: Requests missing or stale registers (older than 5 minutes)

This ensures all available data is captured even if not regularly broadcast.

## Entities

### Sensors
| Entity | Description |
|--------|-------------|
| Outside temperature | Outdoor air temperature |
| Exhaust temperature | Exhaust air after heat exchanger |
| Inside temperature | Indoor extract air |
| Incoming temperature | Supply air after heat exchanger |
| Humidity | Main relative humidity sensor |
| Humidity sensor 1/2 | Secondary humidity sensors |
| CO2 | CO2 concentration in ppm |
| Heat recovery efficiency | Calculated efficiency percentage |
| Fan speed | Current speed level (1-8) |
| Last fault | Last error code |
| Fireplace countdown | Fireplace mode remaining time |
| Post-heating counter | Post-heating activation counter |

### Fan
| Entity | Description |
|--------|-------------|
| Ventilation | Fan with speed 1-8 / percentage / presets |

### Switches
| Entity | Description |
|--------|-------------|
| Power | System on/off |
| Post-heating | Post-heating control |
| CO2 adjustment | CO2-based speed adjustment |
| Humidity adjustment | Humidity-based speed adjustment |

### Binary Sensors
| Entity | Description |
|--------|-------------|
| Supply fan | Supply fan running |
| Exhaust fan | Exhaust fan running |
| Pre-heating | Pre-heater active |
| Bypass | Summer bypass open |
| Fireplace booster | Fireplace switch status |
| Fireplace/Boost active | Fireplace/boost mode currently running |
| Remote control | Remote control panel communication |
| Fault | Fault indicator |
| Filter guard | Filter maintenance needed |
| Service reminder | Service due |
| Heating active | Post-heating currently running |

### Number Controls
| Entity | Description | Range |
|--------|-------------|-------|
| Heating setpoint | Target heating temperature | 10-30°C |
| Pre-heating setpoint | Pre-heater activation threshold | -6 to 15°C |
| Bypass setpoint | Bypass activation temperature | 0-20°C |
| Frost protection threshold | Supply fan stop threshold | -6 to 15°C |
| Cell defrost setpoint | Defrost hysteresis | 0-10°C |
| Minimum fan speed | Minimum allowed speed | 1-8 |
| Maximum fan speed | Maximum allowed speed | 1-8 |
| Service reminder interval | Service reminder period | 1-15 months |
| CO2 setpoint | CO2 threshold for speed boost | 500-2000 ppm |
| Humidity threshold | Humidity threshold for speed boost | 0-100% |

## Use Cases

### Energy-Efficient Ventilation
Optimize ventilation based on occupancy and air quality:
- Reduce fan speed when home is empty
- Boost ventilation when CO2 levels rise during gatherings
- Automatically increase airflow when humidity is high (bathroom, cooking)

### Seasonal Optimization
Adapt ventilation to weather conditions:
- Use bypass mode in summer to bring in cool night air
- Monitor heat recovery efficiency in winter
- Adjust pre-heating thresholds based on outdoor temperature

### Air Quality Monitoring
Track indoor air quality metrics:
- Monitor CO2 levels for proper ventilation
- Track humidity to prevent mold and condensation
- View temperature differentials across heat exchanger

### Maintenance Tracking
Stay on top of filter changes and service:
- Get notified when filter needs replacement
- Track service reminder intervals
- Monitor post-heating activation patterns

## Automation Examples

### Boost Ventilation When Cooking
```yaml
automation:
  - alias: "Boost ventilation when cooking"
    trigger:
      - platform: state
        entity_id: binary_sensor.kitchen_stove
        to: "on"
    action:
      - service: fan.set_percentage
        target:
          entity_id: fan.vallox_ventilation
        data:
          percentage: 100
      - delay: "00:30:00"
      - service: fan.set_percentage
        target:
          entity_id: fan.vallox_ventilation
        data:
          percentage: 50
```

### Night Mode - Reduce Fan Speed
```yaml
automation:
  - alias: "Vallox night mode"
    trigger:
      - platform: time
        at: "22:00:00"
    condition:
      - condition: state
        entity_id: input_boolean.home_occupied
        state: "on"
    action:
      - service: fan.set_preset_mode
        target:
          entity_id: fan.vallox_ventilation
        data:
          preset_mode: "away"
```

### Alert on Filter Change Needed
```yaml
automation:
  - alias: "Notify filter change needed"
    trigger:
      - platform: state
        entity_id: binary_sensor.vallox_filter_guard
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "Vallox Filter Alert"
          message: "Filter replacement needed"
```

### Boost on High CO2
```yaml
automation:
  - alias: "Boost ventilation on high CO2"
    trigger:
      - platform: numeric_state
        entity_id: sensor.vallox_co2
        above: 1000
    action:
      - service: fan.set_percentage
        target:
          entity_id: fan.vallox_ventilation
        data:
          percentage: 87  # Speed level 7
```

### Summer Bypass Notification
```yaml
automation:
  - alias: "Notify bypass active"
    trigger:
      - platform: state
        entity_id: binary_sensor.vallox_bypass
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "Vallox Bypass"
          message: "Summer bypass is now active"
```

## Troubleshooting

### No Entities Appearing
**Problem**: Integration loads but no entities are created.

**Causes and Solutions**:
1. **No bus traffic**: The Vallox unit might be in standby. Try adjusting temperature on the panel to generate traffic.
2. **Wrong serial port**: Verify the correct USB-RS485 adapter is selected.
3. **Wiring issues**: Check A/B connections (some adapters have reversed labels).

### Entities Show "Unavailable"
**Problem**: Entities appear but show unavailable state.

**Causes and Solutions**:
1. **Power switch turned off**: When the Vallox unit is powered off via the integration's power switch, the RS485 bus shuts down. You must power-cycle the unit at the breaker.
2. **USB adapter disconnected**: Check if the adapter is still connected.
3. **Bus conflict**: Another device on the RS485 bus might be interfering.

### Incorrect Temperature Readings
**Problem**: Temperature sensors show wrong values.

**Causes and Solutions**:
1. **NTC sensor fault**: Physical sensor may be damaged.
2. **Value 0xFF (255)**: Indicates sensor not connected or fault.
3. **Calibration**: Some units may have slight offsets - this is normal.

### Fan Speed Not Changing
**Problem**: Setting fan speed has no effect.

**Causes and Solutions**:
1. **Auto mode active**: CO2 or humidity adjustment might be overriding manual speed.
2. **Min/max limits**: Check if fan speed min/max settings are restricting the range.
3. **Fireplace mode**: Active fireplace mode locks the fan speed temporarily.

### USB Adapter Not Detected
**Problem**: Serial port doesn't appear in the configuration dropdown.

**Causes and Solutions**:
1. **Driver not loaded**: Install appropriate drivers for your adapter chip (FTDI, CH340, CP210x).
2. **Permission issues**: On Linux, add user to `dialout` group: `sudo usermod -aG dialout homeassistant`
3. **Try different USB port**: Some ports may have power issues.

### Diagnostics
For detailed troubleshooting, download diagnostics from the integration:
1. Settings → Devices & Services → Vallox RS485
2. Click three dots menu → Download diagnostics
3. Share the (redacted) JSON when reporting issues

### Getting Help
If issues persist:
1. Check [GitHub Issues](https://github.com/skjall/ha-vallox-rs485/issues) for similar problems
2. Enable debug logging:
   ```yaml
   logger:
     logs:
       custom_components.vallox_rs485: debug
   ```
3. Open a new issue with debug logs and diagnostics file

## Documentation

- [Protocol Reference](docs/PROTOCOL.md) - RS485 protocol documentation
- [Quality Checklist](QUALITY_CHECKLIST.md) - Home Assistant quality scale compliance

## Protocol

Based on the Vallox Digit RS485 protocol:
- 9600 Baud, 8N1
- 6-byte telegrams
- Passive bus monitoring

See [docs/PROTOCOL.md](docs/PROTOCOL.md) for detailed protocol documentation.

## Credits
Based on the [FHEM Vallox module](https://wiki.fhem.de/wiki/Vallox).
Based on the official Vallox DIGIT bus protocol documentation (Vallox/Petteri Kähärä, 2011) and the [FHEM Vallox module](https://wiki.fhem.de/wiki/Vallox).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[MIT](LICENSE)
