"""
Serial communication protocol for SIK radios (RFD900/RFD900x).
Implements AT command interface based on Mission Planner's radio.cs
"""

import serial
import time
import logging
from typing import Optional, Dict, List, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class RadioMode(Enum):
    """Radio operating modes"""
    INIT = "INIT"
    TRANSPARENT = "TRANSPARENT"
    AT_COMMAND = "AT_COMMAND"
    BOOTLOADER = "BOOTLOADER"
    BOOTLOADER_X = "BOOTLOADER_X"
    UNKNOWN = "UNKNOWN"


class SIKRadioProtocol:
    """
    SIK Radio serial communication protocol.
    Handles AT commands, parameter reading/writing, and mode switching.
    """

    # AT Command constants
    AT_TIMEOUT = 1.0  # seconds
    ENTER_AT_MODE_TIMEOUT = 3.0
    ECHO_TIMEOUT = 0.5
    
    # Baud rates supported by radios (codes)
    BAUD_RATES = {
        1: 1200,
        2: 2400,
        4: 4800,
        9: 9600,
        19: 19200,
        38: 38400,
        57: 57600,
        115: 115200,
        230: 230400,
        460: 460800,
    }

    # Air data rates (kbps)
    AIR_SPEEDS = {
        4: 4,
        64: 64,
        125: 125,
        250: 250,
        500: 500,
    }

    # Standard radio parameters (S0-S15)
    STANDARD_PARAMETERS = {
        'S0': {'name': 'FORMAT', 'type': 'int'},
        'S1': {'name': 'SERIAL_SPEED', 'type': 'enum', 'values': BAUD_RATES},
        'S2': {'name': 'AIR_SPEED', 'type': 'enum', 'values': AIR_SPEEDS},
        'S3': {'name': 'NETID', 'type': 'int', 'min': 0, 'max': 255},
        'S4': {'name': 'TXPOWER', 'type': 'int', 'min': 0, 'max': 30},
        'S5': {'name': 'ECC', 'type': 'bool'},
        'S6': {'name': 'MAVLINK', 'type': 'bool'},
        'S7': {'name': 'OPPRESEND', 'type': 'bool'},
        'S8': {'name': 'MIN_FREQ', 'type': 'int'},
        'S9': {'name': 'MAX_FREQ', 'type': 'int'},
        'S10': {'name': 'NUM_CHANNELS', 'type': 'int', 'min': 1, 'max': 50},
        'S11': {'name': 'DUTY_CYCLE', 'type': 'int'},
        'S12': {'name': 'LBT_RSSI', 'type': 'int'},
        'S13': {'name': 'MANCHESTER', 'type': 'bool'},
        'S14': {'name': 'RTSCTS', 'type': 'bool'},
        'S15': {'name': 'MAX_WINDOW', 'type': 'int', 'min': 33, 'max': 131},
    }

    def __init__(self, port: str, baudrate: int = 57600, timeout: float = 1.0):
        """
        Initialize SIK radio protocol handler.
        
        Args:
            port: Serial port name (e.g., '/dev/ttyUSB0' or 'COM3')
            baudrate: Serial port baudrate (default 57600)
            timeout: Serial read timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser: Optional[serial.Serial] = None
        self.mode = RadioMode.UNKNOWN
        self.is_remote = False  # Track if commands are for remote radio
        
    def connect(self) -> bool:
        """
        Connect to radio and detect mode.
        
        Returns:
            True if successfully connected, False otherwise
        """
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                write_timeout=self.timeout
            )
            logger.info(f"Opened serial port {self.port} at {self.baudrate} baud")
            
            # Discard any pending data
            self._discard_input()
            
            # Ensure we're in transparent mode
            self._send_command("ATO", timeout=0.5)
            time.sleep(0.1)
            
            # Try to enter AT command mode
            return self._enter_at_mode()
            
        except serial.SerialException as e:
            logger.error(f"Failed to connect to {self.port}: {e}")
            return False

    def disconnect(self):
        """Close serial connection."""
        if self.ser and self.ser.is_open:
            self.ser.close()
            logger.info("Serial connection closed")

    def is_connected(self) -> bool:
        """Check if serial connection is active."""
        return self.ser is not None and self.ser.is_open

    def _enter_at_mode(self) -> bool:
        """
        Enter AT command mode by sending three '+' characters.
        
        Returns:
            True if successfully entered AT mode, False otherwise
        """
        try:
            logger.debug("Attempting to enter AT command mode")
            self._discard_input()

            # Guard time before +++ (no data)
            time.sleep(1.0)

            # Attempt 1: send +++ as a single burst
            self.ser.write(b'+++')
            self.ser.flush()

            # Guard time after +++
            time.sleep(1.0)

            response = self._read_response(timeout=self.ENTER_AT_MODE_TIMEOUT)
            if response and 'OK' in response:
                logger.info("Successfully entered AT command mode")
                self.mode = RadioMode.AT_COMMAND
                self._send_command("AT&T")
                self._discard_input()
                return True

            logger.debug(f"AT mode attempt 1 response: {response}")

            # Attempt 2: send three '+' characters with 200ms spacing
            self._discard_input()
            time.sleep(1.0)
            for _ in range(3):
                self.ser.write(b'+')
                self.ser.flush()
                time.sleep(0.2)
            time.sleep(1.0)

            response = self._read_response(timeout=self.ENTER_AT_MODE_TIMEOUT)
            if response and 'OK' in response:
                logger.info("Successfully entered AT command mode")
                self.mode = RadioMode.AT_COMMAND
                self._send_command("AT&T")
                self._discard_input()
                return True

            logger.debug(f"AT mode attempt 2 response: {response}")

            # Attempt 3: already in AT mode? try plain AT
            self._discard_input()
            self._send_command("AT")
            response = self._read_response(timeout=self.ENTER_AT_MODE_TIMEOUT)
            if response and 'OK' in response:
                logger.info("Radio already in AT command mode")
                self.mode = RadioMode.AT_COMMAND
                self._send_command("AT&T")
                self._discard_input()
                return True

            logger.warning(f"Failed to enter AT mode. Response: {response}")
            return False

        except Exception as e:
            logger.error(f"Error entering AT mode: {e}")
            return False

    def _send_command(self, command: str, timeout: Optional[float] = None) -> bool:
        """
        Send an AT command and verify it was sent correctly.
        
        Args:
            command: Command to send (without \r\n)
            timeout: Response timeout in seconds
            
        Returns:
            True if command was sent successfully
        """
        if not self.is_connected():
            logger.error("Not connected to radio")
            return False
        
        if timeout is None:
            timeout = self.AT_TIMEOUT
        
        try:
            # Ensure command starts with AT or RT
            if not command.startswith(('AT', 'RT')):
                command = f"AT{command}"
            
            logger.debug(f"Sending command: {command}")
            self.ser.write((command + '\r\n').encode())
            time.sleep(0.05)  # Brief delay for radio to process
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending command '{command}': {e}")
            return False

    def _read_response(self, timeout: Optional[float] = None) -> str:
        """
        Read response from radio until OK or ERROR.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Response string (may be multi-line)
        """
        if not self.is_connected():
            return ""
        
        if timeout is None:
            timeout = self.AT_TIMEOUT
        
        response = ""
        start_time = time.time()
        
        try:
            while time.time() - start_time < timeout:
                if self.ser.in_waiting > 0:
                    char = self.ser.read(1).decode('utf-8', errors='ignore')
                    response += char
                    
                    # Check for command termination
                    if response.strip().endswith(('OK', 'ERROR')):
                        break
                else:
                    time.sleep(0.01)
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error reading response: {e}")
            return ""

    def _discard_input(self):
        """Discard all pending input data."""
        if self.is_connected() and self.ser.in_waiting > 0:
            self.ser.read(self.ser.in_waiting)

    def get_radio_info(self) -> Dict[str, str]:
        """
        Get radio firmware information (ATI command).
        
        Returns:
            Dictionary with radio info
        """
        self._send_command("ATI")
        response = self._read_response()
        
        info = {'raw': response}
        for line in response.split('\n'):
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                info[key.strip()] = value.strip()
        
        return info

    def get_board_info(self) -> Dict[str, str]:
        """Get board device ID and info (ATI2 command)."""
        self._send_command("ATI2")
        response = self._read_response()
        return {'device_id': response}

    def get_frequency_info(self) -> Dict[str, str]:
        """Get frequency band information (ATI3 command)."""
        self._send_command("ATI3")
        response = self._read_response()
        return {'frequency_info': response}

    def get_all_parameters(self, remote: bool = False) -> Dict[str, str]:
        """
        Get all radio parameters (ATI5 command).
        
        Args:
            remote: If True, get remote radio parameters (RTI5)
            
        Returns:
            Dictionary of parameter names and values
        """
        prefix = "RT" if remote else "AT"
        self._send_command(f"{prefix}I5")
        response = self._read_response(timeout=2.0)
        
        parameters = {}
        for line in response.split('\n'):
            line = line.strip()
            if line and '=' in line:
                # Parse format: S0: FORMAT=25
                if ':' in line:
                    param_part, value_part = line.split(':', 1)
                    param = param_part.strip()
                    
                    if '=' in value_part:
                        name, value = value_part.split('=', 1)
                        parameters[param] = {
                            'name': name.strip(),
                            'value': value.strip()
                        }
        
        return parameters

    def get_parameter(self, param_id: str, remote: bool = False) -> Optional[str]:
        """
        Get a single parameter value.
        
        Args:
            param_id: Parameter ID (e.g., 'S4', '&E')
            remote: If True, query remote radio
            
        Returns:
            Parameter value or None if not found
        """
        prefix = "RT" if remote else "AT"
        self._send_command(f"{prefix}{param_id}?")
        response = self._read_response()
        
        # Parse response format: S4: TXPOWER=20
        if '=' in response:
            _, value = response.split('=', 1)
            return value.split('\n')[0].strip()
        
        return None

    def set_parameter(self, param_id: str, value: str, remote: bool = False) -> bool:
        """
        Set a parameter value.
        
        Args:
            param_id: Parameter ID (e.g., 'S4', '&E')
            value: New value
            remote: If True, set remote radio parameter
            
        Returns:
            True if successful, False otherwise
        """
        prefix = "RT" if remote else "AT"
        self._send_command(f"{prefix}{param_id}={value}")
        response = self._read_response()
        
        success = 'OK' in response and 'ERROR' not in response
        if success:
            logger.info(f"Set {param_id} = {value}")
        else:
            logger.error(f"Failed to set {param_id} = {value}. Response: {response}")
        
        return success

    def save_parameters(self, remote: bool = False) -> bool:
        """
        Save parameters to EEPROM.
        
        Args:
            remote: If True, save remote radio parameters
            
        Returns:
            True if successful
        """
        prefix = "RT" if remote else "AT"
        self._send_command(f"{prefix}&W")
        response = self._read_response()
        
        success = 'OK' in response
        if success:
            logger.info("Parameters saved to EEPROM")
        else:
            logger.error(f"Failed to save parameters: {response}")
        
        return success

    def reboot_radio(self, remote: bool = False) -> bool:
        """
        Reboot the radio.
        
        Args:
            remote: If True, reboot remote radio
            
        Returns:
            True if command sent successfully
        """
        prefix = "RT" if remote else "AT"
        self._send_command(f"{prefix}Z")
        response = self._read_response()
        
        logger.info(f"Reboot command sent to {'remote' if remote else 'local'} radio")
        return True

    def factory_reset(self, remote: bool = False) -> bool:
        """
        Reset radio to factory defaults.
        
        Args:
            remote: If True, reset remote radio
            
        Returns:
            True if successful
        """
        prefix = "RT" if remote else "AT"
        self._send_command(f"{prefix}&F")
        response = self._read_response()
        
        success = 'OK' in response
        if success:
            logger.info(f"{'Remote' if remote else 'Local'} radio reset to factory defaults")
            # Save parameters after reset
            self.save_parameters(remote=remote)
        else:
            logger.error(f"Failed to reset radio: {response}")
        
        return success

    def get_rssi(self, remote: bool = False) -> Optional[int]:
        """
        Get signal strength (RSSI).
        
        Args:
            remote: If True, get remote radio RSSI
            
        Returns:
            RSSI value or None
        """
        prefix = "RT" if remote else "AT"
        self._send_command(f"{prefix}I7")
        response = self._read_response()
        
        try:
            # Response format might be: RSSI: -105 dBm
            if 'RSSI' in response:
                # Extract numeric value
                parts = response.split(':')
                if len(parts) > 1:
                    value_str = parts[1].strip().split()[0]
                    return int(value_str)
        except (ValueError, IndexError):
            pass
        
        return None

    def enter_transparent_mode(self) -> bool:
        """Exit AT command mode and return to transparent mode."""
        self._send_command("ATO")
        response = self._read_response()
        
        if 'OK' in response:
            self.mode = RadioMode.TRANSPARENT
            logger.info("Entered transparent mode")
            return True
        
        return False
