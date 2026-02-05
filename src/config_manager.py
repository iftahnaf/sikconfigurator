"""
Radio configuration management and data handling.
"""

import logging
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


@dataclass
class RadioParameter:
    """Represents a single radio parameter"""
    param_id: str  # e.g., 'S4', '&E'
    name: str  # e.g., 'TXPOWER'
    value: str
    param_type: str  # 'int', 'enum', 'bool', 'string'
    min_value: Optional[int] = None
    max_value: Optional[int] = None
    options: Optional[Dict[str, str]] = None  # For enum types
    description: str = ""
    remote: bool = False  # True if this is a remote radio parameter


class RadioConfiguration:
    """Manages radio configuration state and operations"""
    
    # Parameter definitions with metadata
    PARAMETER_DEFINITIONS = {
        'S0': {
            'name': 'FORMAT',
            'description': 'Data format version',
            'type': 'int',
            'default': '25',
        },
        'S1': {
            'name': 'SERIAL_SPEED',
            'description': 'Serial port baud rate (1-9, 19, 38, 57, 115, 230, 460 = kbps)',
            'type': 'enum',
            'options': {
                '1': '1200',
                '2': '2400',
                '4': '4800',
                '9': '9600',
                '19': '19200',
                '38': '38400',
                '57': '57600',
                '115': '115200',
                '230': '230400',
                '460': '460800',
            },
            'default': '57',
        },
        'S2': {
            'name': 'AIR_SPEED',
            'description': 'Over-the-air data rate (kbps)',
            'type': 'enum',
            'options': {
                '4': '4 kbps',
                '64': '64 kbps',
                '125': '125 kbps',
                '250': '250 kbps',
                '500': '500 kbps',
            },
            'default': '64',
        },
        'S3': {
            'name': 'NETID',
            'description': 'Network ID (0-255 standard, 0-65535 extended)',
            'type': 'int',
            'min_value': 0,
            'max_value': 65535,
            'default': '25',
        },
        'S4': {
            'name': 'TXPOWER',
            'description': 'Transmit power in dBm',
            'type': 'int',
            'min_value': 0,
            'max_value': 30,
            'default': '20',
        },
        'S5': {
            'name': 'ECC',
            'description': 'Error correction code enabled',
            'type': 'bool',
            'default': '1',
        },
        'S6': {
            'name': 'MAVLINK',
            'description': 'MAVLink framing mode',
            'type': 'bool',
            'default': '1',
        },
        'S7': {
            'name': 'OPPRESEND',
            'description': 'Opportunistic retransmission',
            'type': 'bool',
            'default': '0',
        },
        'S8': {
            'name': 'MIN_FREQ',
            'description': 'Minimum frequency (Hz)',
            'type': 'int',
            'default': '902000',
        },
        'S9': {
            'name': 'MAX_FREQ',
            'description': 'Maximum frequency (Hz)',
            'type': 'int',
            'default': '928000',
        },
        'S10': {
            'name': 'NUM_CHANNELS',
            'description': 'Number of frequency hopping channels',
            'type': 'int',
            'min_value': 1,
            'max_value': 50,
            'default': '50',
        },
        'S11': {
            'name': 'DUTY_CYCLE',
            'description': 'TX duty cycle (percent)',
            'type': 'int',
            'min_value': 0,
            'max_value': 100,
            'default': '100',
        },
        'S12': {
            'name': 'LBT_RSSI',
            'description': 'Listen before transmit RSSI threshold',
            'type': 'int',
            'default': '0',
        },
        'S13': {
            'name': 'MANCHESTER',
            'description': 'Manchester encoding enabled',
            'type': 'bool',
            'default': '0',
        },
        'S14': {
            'name': 'RTSCTS',
            'description': 'Hardware flow control (RTS/CTS)',
            'type': 'bool',
            'default': '0',
        },
        'S15': {
            'name': 'MAX_WINDOW',
            'description': 'Maximum window size',
            'type': 'int',
            'min_value': 33,
            'max_value': 131,
            'default': '33',
        },
        '&E': {
            'name': 'ENCRYPTION_KEY',
            'description': 'AES encryption key (hex string)',
            'type': 'string',
            'default': '',
        },
    }

    def __init__(self):
        """Initialize radio configuration"""
        self.local_params: Dict[str, RadioParameter] = {}
        self.remote_params: Dict[str, RadioParameter] = {}
        self.radio_info: Dict[str, str] = {}
        self.board_info: Dict[str, str] = {}
        
    def load_parameters_from_dict(self, params_dict: Dict[str, Dict], remote: bool = False):
        """
        Load parameters from a dictionary (parsed from ATI5 response).
        
        Args:
            params_dict: Dictionary with format {param_id: {'name': ..., 'value': ...}}
            remote: If True, load into remote parameters
        """
        target_dict = self.remote_params if remote else self.local_params
        
        for param_id, param_info in params_dict.items():
            if param_id in self.PARAMETER_DEFINITIONS:
                definition = self.PARAMETER_DEFINITIONS[param_id]
                
                param = RadioParameter(
                    param_id=param_id,
                    name=definition.get('name', param_id),
                    value=param_info.get('value', ''),
                    param_type=definition.get('type', 'string'),
                    min_value=definition.get('min_value'),
                    max_value=definition.get('max_value'),
                    options=definition.get('options'),
                    description=definition.get('description', ''),
                    remote=remote
                )
                target_dict[param_id] = param
            else:
                # Handle unknown parameters
                param = RadioParameter(
                    param_id=param_id,
                    name=param_info.get('name', param_id),
                    value=param_info.get('value', ''),
                    param_type='string',
                    remote=remote
                )
                target_dict[param_id] = param

    def get_parameter(self, param_id: str, remote: bool = False) -> Optional[RadioParameter]:
        """Get a parameter object."""
        target_dict = self.remote_params if remote else self.local_params
        return target_dict.get(param_id)

    def set_parameter_value(self, param_id: str, value: str, remote: bool = False):
        """Update a parameter value."""
        target_dict = self.remote_params if remote else self.local_params
        
        if param_id in target_dict:
            target_dict[param_id].value = value
            logger.info(f"Set {param_id} = {value}")

    def get_all_parameters(self, remote: bool = False) -> List[RadioParameter]:
        """Get all parameters as a list."""
        target_dict = self.remote_params if remote else self.local_params
        return sorted(target_dict.values(), key=lambda p: p.param_id)

    def get_parameters_by_type(self, param_type: str, remote: bool = False) -> List[RadioParameter]:
        """Get parameters filtered by type."""
        target_dict = self.remote_params if remote else self.local_params
        return [p for p in target_dict.values() if p.param_type == param_type]

    def validate_parameter(self, param_id: str, value: str) -> Tuple[bool, str]:
        """
        Validate a parameter value.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if param_id not in self.PARAMETER_DEFINITIONS:
            return False, f"Unknown parameter: {param_id}"
        
        definition = self.PARAMETER_DEFINITIONS[param_id]
        param_type = definition.get('type', 'string')
        
        try:
            if param_type == 'int':
                int_val = int(value)
                min_val = definition.get('min_value')
                max_val = definition.get('max_value')
                
                if min_val is not None and int_val < min_val:
                    return False, f"Value must be >= {min_val}"
                if max_val is not None and int_val > max_val:
                    return False, f"Value must be <= {max_val}"
                    
            elif param_type == 'bool':
                if value not in ('0', '1'):
                    return False, "Boolean value must be 0 or 1"
                    
            elif param_type == 'enum':
                options = definition.get('options', {})
                if value not in options:
                    return False, f"Value must be one of: {', '.join(options.keys())}"
            
            return True, ""
            
        except ValueError:
            return False, f"Invalid value for type {param_type}"

    def get_description(self, param_id: str) -> str:
        """Get parameter description."""
        if param_id in self.PARAMETER_DEFINITIONS:
            return self.PARAMETER_DEFINITIONS[param_id].get('description', '')
        return ""

    def export_config(self, remote: bool = False) -> Dict:
        """Export configuration as dictionary."""
        target_dict = self.remote_params if remote else self.local_params
        config = {
            'timestamp': __import__('datetime').datetime.now().isoformat(),
            'radio_info': self.radio_info,
            'board_info': self.board_info,
            'parameters': {
                param_id: param.value 
                for param_id, param in target_dict.items()
            }
        }
        return config

    def import_config(self, config: Dict, remote: bool = False):
        """Import configuration from dictionary."""
        if 'parameters' in config:
            params_dict = {}
            for param_id, value in config['parameters'].items():
                params_dict[param_id] = {'name': param_id, 'value': value}
            self.load_parameters_from_dict(params_dict, remote=remote)
