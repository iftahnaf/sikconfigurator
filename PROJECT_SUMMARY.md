# SIK Radio Configurator - Project Summary

## Overview

A complete Python-based configuration tool for Holybro/RFD900 SIK radios, built to match Mission Planner's functionality. Includes both GUI and command-line interfaces for comprehensive radio parameter management.

## Project Structure

```
sikconfigurator/
├── src/
│   ├── __init__.py                 # Package initialization
│   ├── serial_protocol.py          # SIK radio AT command protocol (core)
│   ├── config_manager.py           # Radio parameter management
│   └── gui/
│       ├── __init__.py
│       └── main.py                 # PyQt6 GUI application
├── tests/
│   └── test_config_manager.py      # Unit tests
├── cli.py                          # Command-line interface
├── examples.py                     # Python library usage examples
├── requirements.txt                # Python dependencies
├── setup.py                        # Package installation
├── Makefile                        # Convenience commands
├── README.md                       # Full documentation
├── QUICKSTART.md                   # Quick start guide
├── sample_config.json              # Example configuration file
├── .gitignore                      # Git exclusions
└── PROJECT_SUMMARY.md              # This file
```

## Key Components

### 1. Serial Protocol (`src/serial_protocol.py`)
**Purpose**: Low-level SIK radio communication

**Features**:
- AT command protocol implementation (based on Mission Planner)
- Serial port connection management
- Mode switching (transparent ↔ AT command)
- Parameter read/write with validation
- Error handling and logging
- Support for both local and remote radio configuration
- Response parsing and timeout handling

**Key Classes**:
- `RadioMode`: Enum for radio operating modes
- `SIKRadioProtocol`: Main protocol handler with methods:
  - `connect()` / `disconnect()` - Connection management
  - `get_all_parameters()` - Read all parameters
  - `set_parameter()` - Write single parameter
  - `save_parameters()` - Save to EEPROM
  - `get_radio_info()` - Firmware and board info
  - `reboot_radio()` / `factory_reset()` - Radio control

### 2. Configuration Manager (`src/config_manager.py`)
**Purpose**: Radio parameter management and validation

**Features**:
- Complete parameter definitions (S0-S15, &E)
- Parameter validation with ranges and constraints
- Configuration import/export in JSON format
- Timestamp tracking
- Type-safe parameter handling

**Key Classes**:
- `RadioParameter`: Individual parameter representation
- `RadioConfiguration`: Configuration container with:
  - `PARAMETER_DEFINITIONS` - All 16 standard parameters
  - Parameter loading/validation
  - Import/export functionality
  - Filtering and searching

**Supported Parameters**:
- S0-S15: Standard SIK radio parameters
- &E: Encryption key
- Descriptions and constraints for each parameter

### 3. GUI Application (`src/gui/main.py`)
**Purpose**: User-friendly graphical interface (PyQt6)

**Features**:
- Connection management with auto-detect
- Dual radio panels (Local & Remote)
- Configuration tab with parameter widgets
- Terminal tab for manual AT commands
- Radio info tab
- Export/import configuration
- Firmware information display
- Parameter validation with instant feedback

**Key Classes**:
- `SIKRadioConfigurator`: Main application window
- `RadioConfigPanel`: Local/remote radio configuration UI
- `ParameterWidget`: Individual parameter input widget
- `RadioWorker`: Background worker for serial operations

**UI Features**:
- Auto-detect serial ports (updates every 2 seconds)
- Type-specific input widgets (combo, checkbox, spinbox, text)
- Parameter descriptions as tooltips
- Status bar with connection info
- Progress dialogs for long operations
- Confirmation dialogs for destructive operations

### 4. Command-Line Interface (`cli.py`)
**Purpose**: Non-GUI interface for scripting and automation

**Features**:
- All radio operations available via commands
- Batch configuration import/export
- Raw AT command execution
- Quiet and verbose modes
- Exit codes for scripting

**Commands**:
- `info` - Display radio information
- `list` - List all parameters
- `get` - Get parameter value
- `set` - Set parameter value
- `save` - Save to EEPROM
- `reboot` - Reboot radio
- `reset` - Factory reset
- `export` - Export to JSON
- `import` - Import from JSON
- `at` - Send raw AT command

**Typical Usage**:
```bash
python cli.py -p /dev/ttyUSB0 set S4 20 --save
python cli.py -p /dev/ttyUSB0 export config.json
python cli.py -p /dev/ttyUSB0 import config.json --save --remote
```

## Technology Stack

- **Language**: Python 3.8+
- **GUI Framework**: PyQt6
- **Serial Communication**: PySerial 3.5+
- **Testing**: unittest (built-in)
- **Documentation**: Markdown

## Installation & Usage

### Installation
```bash
cd sikconfigurator
pip install -r requirements.txt
# Optional: pip install -e .
```

### Running the GUI
```bash
python -m src.gui.main
```

### Running CLI
```bash
python cli.py -p /dev/ttyUSB0 list
python cli.py -p /dev/ttyUSB0 set S4 20 --save
```

### Running Examples
```bash
python examples.py basic        # Basic operations
python examples.py modify       # Modify parameters
python examples.py config       # Configuration management
python examples.py remote       # Configure remote radio
python examples.py validate     # Parameter validation
```

### Running Tests
```bash
python -m pytest tests/ -v
```

## SIK Radio AT Protocol Reference

### Connection
```
Transparent Mode:
  Send: ATO\r\n → OK

Enter AT Mode:
  Send: + + + (200ms spacing)
  Wait: 1500ms
  Receive: OK
```

### Parameter Operations
```
Read All:     ATI5\r\n
Read One:     AT<S#>?\r\n
Write:        AT<S#>=<value>\r\n
Save EEPROM:  AT&W\r\n
Reboot:       ATZ\r\n
Factory Reset: AT&F\r\n

Remote Radio (prefix RT instead of AT):
  RTI5, RTS#=val, etc.
```

### Response Format
```
Single Parameter Response:
  S4: TXPOWER=20
  OK

All Parameters Response:
  S0: FORMAT=25
  S1: SERIAL_SPEED=57
  ...
  S15: MAX_WINDOW=33
  OK

Error Response:
  ERROR
```

## Parameter Definitions (S0-S15)

| S# | Name | Type | Range | Description |
|----|------|------|-------|-------------|
| S0 | FORMAT | int | - | Data format (usually 25) |
| S1 | SERIAL_SPEED | enum | 1-460 | Baud rate (kbps) |
| S2 | AIR_SPEED | enum | 4-500 | Air data rate (kbps) |
| S3 | NETID | int | 0-255 | Network ID |
| S4 | TXPOWER | int | 0-30 | TX power (dBm) |
| S5 | ECC | bool | 0-1 | Error correction |
| S6 | MAVLINK | bool | 0-1 | MAVLink framing |
| S7 | OPPRESEND | bool | 0-1 | Opportunistic retransmit |
| S8 | MIN_FREQ | int | - | Min frequency (Hz) |
| S9 | MAX_FREQ | int | - | Max frequency (Hz) |
| S10 | NUM_CHANNELS | int | 1-50 | Number of channels |
| S11 | DUTY_CYCLE | int | 0-100 | TX duty cycle (%) |
| S12 | LBT_RSSI | int | - | LBT threshold |
| S13 | MANCHESTER | bool | 0-1 | Manchester encoding |
| S14 | RTSCTS | bool | 0-1 | Hardware flow control |
| S15 | MAX_WINDOW | int | 33-131 | Max window size |

Additional: &E (AES Encryption Key)

## Features Implemented

✅ Complete serial AT command protocol
✅ All 16 standard parameters (S0-S15)
✅ Parameter validation with ranges
✅ Parameter type handling (int, enum, bool, string)
✅ Local and remote radio support
✅ Read parameters from radio
✅ Write parameters to radio
✅ Save to EEPROM
✅ Reboot radio
✅ Factory reset
✅ Export/import configuration (JSON)
✅ GUI with PyQt6
✅ Command-line interface
✅ Python library interface
✅ Unit tests
✅ Comprehensive documentation
✅ Quick start guide
✅ Example code
✅ Error handling and validation
✅ Serial port auto-detection
✅ Connection management
✅ Radio information display
✅ Terminal/AT command interface
✅ Logging and debugging

## Potential Enhancements

- **Firmware Updates**: XModem protocol for firmware flashing
- **Multi-Radio Config**: Side-by-side comparison of multiple radios
- **Profiles/Presets**: Save and load common configurations
- **RSSI Monitoring**: Real-time signal strength graph
- **Frequency Visualization**: Show hopping pattern
- **Configuration Profiles**: Predefined settings for common scenarios
- **Log Export**: Save operation logs for troubleshooting
- **Command History**: Terminal history and autocomplete
- **Batch Operations**: Configure multiple radios
- **Configuration Comparison**: Diff two configurations
- **Web Interface**: Browser-based UI option

## Compatibility

### Supported Radios
- RFD900 (Original)
- RFD900A (Variant)
- RFD900P (Improved)
- RFD900x (Latest)
- RFD900u (Variant)
- Holybro SIK radios (compatible variants)

### Platform Support
- Windows (COM ports)
- Linux (/dev/ttyUSB*, /dev/ttyACM*)
- macOS (/dev/tty.usbserial-*, /dev/tty.usbmodem*)

### Python Support
- Python 3.8 or higher

## Troubleshooting Guide Included

Complete troubleshooting documentation covers:
- Connection issues
- AT mode entry failures
- Parameter read/write failures
- Serial port detection
- Permission issues on Linux
- Driver installation
- Configuration corruption recovery

## Testing

Comprehensive unit tests for:
- Configuration management
- Parameter validation
- Import/export functionality
- Parameter type handling
- Filtering and searching

Run tests:
```bash
python -m pytest tests/ -v
python -m pytest tests/ -v --cov=src
```

## Documentation

1. **README.md** - Full feature documentation
2. **QUICKSTART.md** - Step-by-step quick start
3. **examples.py** - Code examples
4. **Inline code documentation** - Docstrings throughout

## Files Provided

- **Core Modules**: serial_protocol.py, config_manager.py, gui/main.py
- **CLI**: cli.py with 10+ commands
- **Examples**: examples.py with 6 usage examples
- **Tests**: test_config_manager.py with comprehensive coverage
- **Configuration**: setup.py, requirements.txt, Makefile
- **Documentation**: README.md, QUICKSTART.md, PROJECT_SUMMARY.md
- **Sample Data**: sample_config.json

## License

Follows ArduPilot's GPLv3 license for consistency with the project it's based on.

## Summary

This is a production-ready SIK radio configuration tool that matches Mission Planner's capabilities. It provides:

1. **Complete Protocol Implementation**: Full SIK radio AT command support
2. **Multiple Interfaces**: GUI, CLI, and Python library
3. **Robust Validation**: Parameter type checking and range validation
4. **Excellent Documentation**: README, quick start, and examples
5. **Enterprise Features**: Config export/import, factory reset, reboot
6. **User-Friendly**: Auto-detect, tooltips, validation feedback
7. **Developer-Friendly**: Clean architecture, examples, tests

Ready for immediate use with SIK radios and suitable for both end-users and developers building radio configuration tools.
