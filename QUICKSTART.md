# Quick Start Guide - SIK Radio Configurator

## Installation (5 minutes)

### Prerequisites
- Python 3.8 or higher
- USB cable to connect radio to computer
- SIK radio (RFD900, RFD900x, or Holybro variant)

### Step 1: Install Python Dependencies

```bash
cd sikconfigurator
pip install -r requirements.txt
```

### Step 2: Identify Your Serial Port

**Linux/Mac:**
```bash
ls /dev/tty* | grep -E "USB|ACM"
# Look for /dev/ttyUSB0 or /dev/ttyACM0
```

**Windows:**
- Open Device Manager
- Look under "Ports (COM & LPT)"
- Your radio will show as "USB Serial Device" or similar
- Note the COM port (e.g., COM3)

## Using the GUI Application

### Start the Application

```bash
python -m src.gui.main
```

### Basic Workflow

1. **Connect**
   - Select serial port from dropdown (or auto-detect)
   - Verify baud rate is 57600
   - Click "Connect"
   - Status bar should show "Connected to /dev/ttyUSB0 at 57600 baud"

2. **Read Parameters**
   - Click "Read Parameters"
   - Left panel shows local radio settings
   - Right panel shows remote radio settings (if paired)

3. **Modify Settings**
   - Adjust parameters as needed
   - Settings are validated automatically
   - Hover over parameter for description

4. **Save Changes**
   - Click "Write & Save"
   - Confirm the action
   - Radio will reboot automatically
   - Status message confirms success

## Using the Command-Line Interface

### Basic Commands

```bash
# Show radio information
python cli.py -p /dev/ttyUSB0 info

# List all parameters
python cli.py -p /dev/ttyUSB0 list

# Get a specific parameter
python cli.py -p /dev/ttyUSB0 get S4

# Set a parameter and save
python cli.py -p /dev/ttyUSB0 set S4 20 --save

# Export current configuration
python cli.py -p /dev/ttyUSB0 export my_radio_config.json

# Import and apply configuration
python cli.py -p /dev/ttyUSB0 import my_radio_config.json --save

# Reboot radio
python cli.py -p /dev/ttyUSB0 reboot

# Factory reset (requires confirmation)
python cli.py -p /dev/ttyUSB0 reset
```

## Common Configuration Tasks

### Set Transmit Power to 25 dBm

**GUI:**
1. Read Parameters
2. Find "S4: TXPOWER" on left panel
3. Change value to 25
4. Click Write & Save

**CLI:**
```bash
python cli.py -p /dev/ttyUSB0 set S4 25 --save
```

### Change Serial Baud Rate to 115200

**GUI:**
1. Find "S1: SERIAL_SPEED" (shown as dropdown)
2. Select "115200"
3. Click Write & Save
4. Disconnect and reconnect with new baud rate

**CLI:**
```bash
python cli.py -p /dev/ttyUSB0 set S1 115 --save
```

### Configure Frequency Hopping (915 MHz band)

**GUI:**
1. Find "S8: MIN_FREQ" - set to 902000
2. Find "S9: MAX_FREQ" - set to 928000
3. Find "S10: NUM_CHANNELS" - set to 50
4. Click Write & Save

**CLI:**
```bash
python cli.py -p /dev/ttyUSB0 set S8 902000 --save
python cli.py -p /dev/ttyUSB0 set S9 928000 --save
python cli.py -p /dev/ttyUSB0 set S10 50 --save
```

### Enable MAVLink Mode

**GUI:**
1. Find "S6: MAVLINK" 
2. Check the checkbox
3. Click Write & Save

**CLI:**
```bash
python cli.py -p /dev/ttyUSB0 set S6 1 --save
```

### Enable Error Correction

**GUI:**
1. Find "S5: ECC"
2. Check the checkbox
3. Click Write & Save

**CLI:**
```bash
python cli.py -p /dev/ttyUSB0 set S5 1 --save
```

## Backup and Restore Configuration

### Backup Current Settings

**GUI:**
1. Read Parameters
2. Click "Export Config"
3. Save to a location (e.g., `backup_2024_01_15.json`)

**CLI:**
```bash
python cli.py -p /dev/ttyUSB0 export backup_$(date +%Y%m%d_%H%M%S).json
```

### Restore from Backup

**GUI:**
1. Click "Import Config"
2. Select backup JSON file
3. Review parameters
4. Click "Write & Save"

**CLI:**
```bash
python cli.py -p /dev/ttyUSB0 import backup_2024_01_15.json --save
```

## Troubleshooting

### Cannot Find Serial Port

**Linux/Mac:**
```bash
ls -la /dev/tty*
# Check for USB devices
sudo dmesg | grep -i serial
# Try: python cli.py -p /dev/ttyUSB0 info
```

**Windows:**
- Device Manager → Ports (COM & LPT)
- Install drivers if needed (CH340 or CP2102)

### "Failed to Connect"

1. Check cable is properly connected
2. Verify port name is correct
3. Ensure baud rate is 57600 (or your configured rate)
4. Radio should be powered on
5. Try disconnecting and reconnecting radio
6. Restart application

### "Failed to Enter AT Mode"

1. Radio may already be in AT mode (try `python cli.py -p /dev/ttyUSB0 at "ATO"`)
2. Try pressing reset button on radio
3. Increase timeout if on slow system
4. Check connection is stable

### Parameters Not Saving

1. Ensure you clicked "Write & Save" (not just modifying)
2. Confirm the save operation in dialog
3. Wait for reboot to complete
4. Try reading parameters again to verify

### Serial Port Permission Denied (Linux)

```bash
# Add user to dialout group
sudo usermod -a -G dialout $USER
# Log out and log back in, or:
newgrp dialout
```

## Parameter Reference

| Param | Name | Range | Description |
|-------|------|-------|-------------|
| S0 | Format | - | Data format version |
| S1 | Serial Speed | 1-460 | Baud rate (kbps) |
| S2 | Air Speed | 4-500 | Over-the-air rate (kbps) |
| S3 | Network ID | 0-255 | Radio network identifier |
| S4 | TX Power | 0-30 | Transmit power (dBm) |
| S5 | ECC | 0-1 | Error correction enabled |
| S6 | MAVLink | 0-1 | MAVLink framing mode |
| S7 | Opp Retrans | 0-1 | Opportunistic retransmission |
| S8 | Min Freq | - | Minimum frequency (Hz) |
| S9 | Max Freq | - | Maximum frequency (Hz) |
| S10 | Channels | 1-50 | Number of hop channels |
| S11 | Duty Cycle | 0-100 | TX duty cycle (%) |
| S12 | LBT RSSI | - | Listen before transmit threshold |
| S13 | Manchester | 0-1 | Manchester encoding |
| S14 | RTS/CTS | 0-1 | Hardware flow control |
| S15 | Max Window | 33-131 | Maximum window size |

## Advanced Usage

### Send Raw AT Commands

**GUI:**
1. Go to "Terminal" tab
2. Type command (e.g., `ATI5`)
3. Press Enter or click Send
4. View response in output area

**CLI:**
```bash
python cli.py -p /dev/ttyUSB0 at "ATI5"
python cli.py -p /dev/ttyUSB0 at "RTI5"  # Remote radio
```

### Python Library Usage

```python
from src.serial_protocol import SIKRadioProtocol

# Connect
radio = SIKRadioProtocol('/dev/ttyUSB0', baudrate=57600)
radio.connect()

# Read parameters
params = radio.get_all_parameters()
print(params)

# Set parameter
radio.set_parameter('S4', '20')
radio.save_parameters()

# Get specific value
power = radio.get_parameter('S4')
print(f"TX Power: {power} dBm")

# Disconnect
radio.disconnect()
```

See `examples.py` for more examples.

## Getting Help

- Check README.md for full documentation
- Review error messages in terminal output
- Consult RFD Documentation: https://docs.rfd.com.au/
- Check ArduPilot Forums: https://discuss.ardupilot.org/
- Look at example scripts in `examples.py`

## Safety Notes

⚠️ **Important:**
- Always save configuration backups before major changes
- Factory reset cannot be undone - backup first!
- Ensure proper antenna is connected before transmitting
- Radio frequency regulations vary by country
- Do not operate outside your region's frequency band
- Keep transmit power within legal limits for your area

## Next Steps

1. Read full [README.md](README.md) for comprehensive documentation
2. Review [examples.py](examples.py) for code examples
3. Check the Terminal tab for raw AT command experiments
4. Experiment with configuration export/import
5. Join ArduPilot community for tips and support
