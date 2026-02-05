# SIK Radio Configurator

A Python-based configuration tool for Holybro/RFD900 SIK radios, similar to Mission Planner's radio configuration interface.

## Features

- **GUI Application**: Easy-to-use graphical interface for configuring SIK radios
- **Parameter Management**: Read, modify, and write all radio parameters (S0-S15, encryption, etc.)
- **Local & Remote Radio Support**: Configure both local and remote radio simultaneously
- **Manual AT Commands**: Terminal interface for manual AT command execution
- **Radio Information**: View firmware version, board ID, frequency information
- **Configuration Export/Import**: Save and load radio configurations in JSON format
- **Factory Reset**: Reset radio to factory defaults
- **Reboot**: Reboot radio with confirmation dialog

## Requirements

- Python 3.8 or higher
- PySerial 3.5+
- PyQt6 6.0.0+

## Installation

```bash
# Clone or navigate to the project directory
cd sikconfigurator

# Install dependencies
pip install -r requirements.txt

# Optional: Install in editable mode
pip install -e .
```

## Usage

### GUI Application

```bash
python -m src.gui.main
```

Or if installed via setup.py:

```bash
sik-configurator
```

### Serial Connection

1. **Select Serial Port**: Choose from auto-detected ports or manually select
2. **Set Baud Rate**: Default is 57600 (standard for SIK radios)
3. **Click Connect**: Establishes AT command mode connection

### Configuring Parameters

1. **Read Parameters**: Click "Read Parameters" to fetch current radio settings
2. **Modify Settings**: Adjust parameters in the "Configuration" tab
   - Local Radio: First radio panel
   - Remote Radio: Second radio panel
3. **Write Parameters**: Click "Write & Save" to apply changes
4. **Reboot**: Radio will reboot automatically after saving

### Parameter Types

- **S0**: Format version (usually 25)
- **S1**: Serial baud rate (1200 to 460800 bps)
- **S2**: Over-the-air air speed (4-500 kbps)
- **S3**: Network ID (0-255 or 0-65535)
- **S4**: Transmit power (0-30 dBm)
- **S5**: Error correction code
- **S6**: MAVLink framing mode
- **S7**: Opportunistic retransmission
- **S8**: Minimum frequency
- **S9**: Maximum frequency
- **S10**: Number of channels (1-50)
- **S11**: TX duty cycle (%)
- **S12**: LBT RSSI threshold
- **S13**: Manchester encoding
- **S14**: Hardware flow control (RTS/CTS)
- **S15**: Maximum window size (33-131)
- **&E**: AES encryption key (hex)

### Advanced Features

#### Terminal Tab

Execute raw AT commands for advanced configuration:

```
ATI              - Get radio info
ATI2             - Get board ID
ATI3             - Get frequency info
ATI5             - Get all parameters
ATI7             - Get signal strength (RSSI)
AT&W             - Write to EEPROM
ATZ              - Reboot radio
AT&F             - Factory reset
AT<S#>=<value>   - Set parameter
AT<S#>?          - Query parameter
RTI5             - Get remote radio parameters
RT<S#>=<value>   - Set remote parameter
```

#### Export/Import Configuration

Save current configuration:
1. Click "Export Config"
2. Choose a JSON file location
3. Configuration saved with timestamp and all parameters

Load previously saved configuration:
1. Click "Import Config"
2. Select a JSON file
3. Configuration loaded into the editor

#### Factory Reset

Completely reset a radio to factory defaults:
1. Click "Factory Reset"
2. Confirm the action (non-reversible)
3. Radio will be reset and rebooted

## Serial Communication Protocol

The configurator uses the SIK radio AT command protocol:

### Entering AT Mode

1. Send three '+' characters (200ms spacing)
2. Wait for "OK" response
3. Now in AT command mode

### Command Format

```
AT<PARAMETER>=<VALUE>\r\n    - Set parameter
AT<PARAMETER>?\r\n           - Query parameter
AT&W\r\n                     - Save to EEPROM
ATZ\r\n                      - Reboot
ATO\r\n                      - Exit AT mode
RT<PARAMETER>=<VALUE>\r\n    - Set remote parameter
```

### Responses

- `OK` - Command successful
- `ERROR` - Command failed
- Multi-line responses for ATI5, ATI commands

## Architecture

### Modules

- **serial_protocol.py**: Low-level SIK radio AT command protocol
- **config_manager.py**: Radio parameter management and validation
- **gui/main.py**: PyQt6 GUI application

### Class Hierarchy

```
SIKRadioProtocol
  - Handles serial communication
  - AT command execution
  - Response parsing
  
RadioConfiguration
  - Parameter definitions
  - Parameter validation
  - Configuration export/import

SIKRadioConfigurator (Main Window)
  - RadioConfigPanel (Local/Remote)
    - ParameterWidget (Individual parameter)
```

## Example Python Usage

```python
from src.serial_protocol import SIKRadioProtocol
from src.config_manager import RadioConfiguration

# Connect to radio
protocol = SIKRadioProtocol('/dev/ttyUSB0', baudrate=57600)
if protocol.connect():
    # Read all parameters
    params = protocol.get_all_parameters()
    print("Parameters:", params)
    
    # Get specific parameter
    power = protocol.get_parameter('S4')
    print(f"TX Power: {power} dBm")
    
    # Set parameter
    protocol.set_parameter('S4', '20')
    
    # Save to EEPROM
    protocol.save_parameters()
    
    # Get radio info
    info = protocol.get_radio_info()
    print("Radio Info:", info)
    
    # Reboot
    protocol.reboot_radio()
    
    protocol.disconnect()
```

## Supported Radios

- RFD900 (Original)
- RFD900A (Variant)
- RFD900P (Improved)
- RFD900x (Latest, recommended)
- RFD900u (Variant)
- Holybro SIK radios (compatible variants)

## Troubleshooting

### "Failed to connect to radio"
- Check serial port is correct
- Verify baud rate (default 57600)
- Ensure radio is powered and not in use by another application
- Check USB drivers are installed

### "Failed to enter AT mode"
- Ensure radio is in transparent mode first
- Try pressing reset on the radio
- Check connection/wiring
- Increase timeout in code if needed

### "Parameters not reading"
- Radio may already be in AT mode (try ATO command)
- Check network ID matches if using multiple radios
- Try factory reset if configuration is corrupted

### Serial Port Not Detected
- Install CH340 or CP2102 drivers (depending on USB adapter)
- Check USB cable is properly connected
- Try different USB port
- Check device manager for COM port

## Future Enhancements

- Firmware update capability
- Multi-radio configuration (side-by-side comparison)
- Configuration profiles/presets
- RSSI monitoring graph
- Signal strength visualization
- Frequency hopping visualization
- Log file export for troubleshooting
- Command history in terminal tab
- Batch configuration of multiple radios

## References

- [Mission Planner Radio Configuration](https://github.com/ArduPilot/MissionPlanner)
- [RFD900 Documentation](https://docs.rfd.com.au/)
- SIK Radio AT Command Protocol (based on RFD900x firmware)

## License

This project follows the same license as ArduPilot (GPLv3).

## Author

Created for Holybro SIK Radio configuration similar to Mission Planner.

## Support

For issues and questions:
- Check the troubleshooting section
- Review ArduPilot forums
- Check RFD documentation for radio-specific issues
