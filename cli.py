#!/usr/bin/env python3
"""
Command-line interface for SIK Radio Configurator.
Allows configuration and management of SIK radios without GUI.
"""

import sys
import argparse
import json
import logging
from typing import Optional
from pathlib import Path

from src.serial_protocol import SIKRadioProtocol
from src.config_manager import RadioConfiguration


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_separator(title: str = ""):
    """Print formatted separator"""
    if title:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}\n")
    else:
        print()


def cmd_info(protocol: SIKRadioProtocol, args) -> int:
    """Show radio information"""
    print_separator("Radio Information")
    
    try:
        info = protocol.get_radio_info()
        for key, value in info.items():
            print(f"{key}: {value}")
        
        print("\nBoard Information:")
        board_info = protocol.get_board_info()
        for key, value in board_info.items():
            print(f"  {key}: {value}")
        
        print("\nFrequency Information:")
        freq_info = protocol.get_frequency_info()
        for key, value in freq_info.items():
            print(f"  {key}: {value}")
        
        return 0
    except Exception as e:
        logger.error(f"Failed to get radio info: {e}")
        return 1


def cmd_list(protocol: SIKRadioProtocol, args) -> int:
    """List all parameters"""
    print_separator("Radio Parameters")
    
    try:
        params = protocol.get_all_parameters(remote=args.remote)
        
        if not params:
            print("No parameters found")
            return 1
        
        print(f"{'Param':<8} {'Name':<20} {'Value':<20}")
        print("-" * 50)
        
        for param_id, param_info in sorted(params.items()):
            name = param_info.get('name', '')
            value = param_info.get('value', '')
            print(f"{param_id:<8} {name:<20} {value:<20}")
        
        return 0
    except Exception as e:
        logger.error(f"Failed to list parameters: {e}")
        return 1


def cmd_get(protocol: SIKRadioProtocol, args) -> int:
    """Get a parameter value"""
    try:
        value = protocol.get_parameter(args.parameter, remote=args.remote)
        if value:
            print(f"{args.parameter}: {value}")
            return 0
        else:
            logger.error(f"Parameter {args.parameter} not found")
            return 1
    except Exception as e:
        logger.error(f"Failed to get parameter: {e}")
        return 1


def cmd_set(protocol: SIKRadioProtocol, args) -> int:
    """Set a parameter value"""
    config = RadioConfiguration()
    
    # Validate parameter
    is_valid, msg = config.validate_parameter(args.parameter, args.value)
    if not is_valid:
        logger.error(f"Invalid value: {msg}")
        return 1
    
    try:
        protocol.set_parameter(args.parameter, args.value, remote=args.remote)
        
        if args.save:
            logger.info("Saving to EEPROM...")
            protocol.save_parameters(remote=args.remote)
            print(f"✓ Parameter {args.parameter} set to {args.value} and saved")
        else:
            print(f"✓ Parameter {args.parameter} set to {args.value} (not saved)")
        
        return 0
    except Exception as e:
        logger.error(f"Failed to set parameter: {e}")
        return 1


def cmd_save(protocol: SIKRadioProtocol, args) -> int:
    """Save parameters to EEPROM"""
    try:
        protocol.save_parameters(remote=args.remote)
        print("✓ Parameters saved to EEPROM")
        return 0
    except Exception as e:
        logger.error(f"Failed to save parameters: {e}")
        return 1


def cmd_reboot(protocol: SIKRadioProtocol, args) -> int:
    """Reboot the radio"""
    try:
        protocol.reboot_radio(remote=args.remote)
        print("✓ Reboot command sent")
        return 0
    except Exception as e:
        logger.error(f"Failed to reboot: {e}")
        return 1


def cmd_reset(protocol: SIKRadioProtocol, args) -> int:
    """Factory reset the radio"""
    if not args.force:
        print("WARNING: This will reset the radio to factory defaults!")
        response = input("Type 'yes' to confirm: ")
        if response.lower() != 'yes':
            print("Cancelled")
            return 0
    
    try:
        protocol.factory_reset(remote=args.remote)
        print("✓ Factory reset completed")
        return 0
    except Exception as e:
        logger.error(f"Failed to reset: {e}")
        return 1


def cmd_export(protocol: SIKRadioProtocol, args) -> int:
    """Export configuration to file"""
    config = RadioConfiguration()
    
    try:
        # Read current parameters
        logger.info("Reading current configuration...")
        params = protocol.get_all_parameters(remote=args.remote)
        config.load_parameters_from_dict(params, remote=args.remote)
        
        # Also get radio info
        try:
            config.radio_info = protocol.get_radio_info()
        except:
            pass
        
        # Export
        export_data = config.export_config(remote=args.remote)
        
        with open(args.output, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"✓ Configuration exported to {args.output}")
        return 0
    except Exception as e:
        logger.error(f"Failed to export configuration: {e}")
        return 1


def cmd_import(protocol: SIKRadioProtocol, args) -> int:
    """Import configuration from file"""
    config = RadioConfiguration()
    
    try:
        # Load configuration
        with open(args.input, 'r') as f:
            import_data = json.load(f)
        
        config.import_config(import_data, remote=args.remote)
        
        # Apply settings
        logger.info("Applying configuration...")
        for param in config.get_all_parameters(remote=args.remote):
            logger.debug(f"Setting {param.param_id} = {param.value}")
            protocol.set_parameter(param.param_id, param.value, remote=args.remote)
        
        if args.save:
            logger.info("Saving to EEPROM...")
            protocol.save_parameters(remote=args.remote)
        
        print(f"✓ Configuration imported from {args.input}")
        if args.save:
            print("✓ Changes saved to EEPROM")
        return 0
    except Exception as e:
        logger.error(f"Failed to import configuration: {e}")
        return 1


def cmd_at(protocol: SIKRadioProtocol, args) -> int:
    """Send raw AT command"""
    try:
        protocol._send_command(args.command)
        response = protocol._read_response(timeout=args.timeout)
        print(response)
        return 0
    except Exception as e:
        logger.error(f"Failed to send command: {e}")
        return 1


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='SIK Radio Configurator - Command-line tool for SIK radios',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Get radio info
  %(prog)s -p /dev/ttyUSB0 info
  
  # List all parameters
  %(prog)s -p /dev/ttyUSB0 list
  
  # Set TX power to 20 dBm
  %(prog)s -p /dev/ttyUSB0 set S4 20 --save
  
  # Export configuration
  %(prog)s -p /dev/ttyUSB0 export config.json
  
  # Import and apply configuration
  %(prog)s -p /dev/ttyUSB0 import config.json --save
  
  # Configure remote radio
  %(prog)s -p /dev/ttyUSB0 list --remote
  %(prog)s -p /dev/ttyUSB0 set S4 25 --remote --save
        """
    )
    
    # Global arguments
    parser.add_argument('-p', '--port', required=True, help='Serial port (e.g., /dev/ttyUSB0, COM3)')
    parser.add_argument('-b', '--baud', type=int, default=57600, help='Baud rate (default: 57600)')
    parser.add_argument('-t', '--timeout', type=float, default=1.0, help='Command timeout in seconds')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--remote', action='store_true', help='Configure remote radio instead of local')
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Info command
    subparsers.add_parser('info', help='Show radio information')
    
    # List command
    subparsers.add_parser('list', help='List all parameters')
    
    # Get command
    get_parser = subparsers.add_parser('get', help='Get a parameter value')
    get_parser.add_argument('parameter', help='Parameter ID (e.g., S4, &E)')
    
    # Set command
    set_parser = subparsers.add_parser('set', help='Set a parameter value')
    set_parser.add_argument('parameter', help='Parameter ID (e.g., S4)')
    set_parser.add_argument('value', help='Parameter value')
    set_parser.add_argument('--save', action='store_true', help='Save to EEPROM after setting')
    
    # Save command
    subparsers.add_parser('save', help='Save parameters to EEPROM')
    
    # Reboot command
    subparsers.add_parser('reboot', help='Reboot the radio')
    
    # Reset command
    reset_parser = subparsers.add_parser('reset', help='Factory reset the radio')
    reset_parser.add_argument('--force', action='store_true', help='Skip confirmation')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export configuration to file')
    export_parser.add_argument('output', help='Output JSON file')
    
    # Import command
    import_parser = subparsers.add_parser('import', help='Import configuration from file')
    import_parser.add_argument('input', help='Input JSON file')
    import_parser.add_argument('--save', action='store_true', help='Save to EEPROM after importing')
    
    # AT command
    at_parser = subparsers.add_parser('at', help='Send raw AT command')
    at_parser.add_argument('command', help='AT command (e.g., ATI5, AT&W)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Setup logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Connect to radio
    logger.info(f"Connecting to {args.port} at {args.baud} baud...")
    protocol = SIKRadioProtocol(args.port, baudrate=args.baud, timeout=args.timeout)
    
    if not protocol.connect():
        logger.error(f"Failed to connect to radio on {args.port}")
        return 1
    
    logger.info("Connected successfully")
    
    try:
        # Execute command
        commands = {
            'info': cmd_info,
            'list': cmd_list,
            'get': cmd_get,
            'set': cmd_set,
            'save': cmd_save,
            'reboot': cmd_reboot,
            'reset': cmd_reset,
            'export': cmd_export,
            'import': cmd_import,
            'at': cmd_at,
        }
        
        if args.command in commands:
            return commands[args.command](protocol, args)
        else:
            logger.error(f"Unknown command: {args.command}")
            return 1
    
    finally:
        protocol.disconnect()
        logger.info("Disconnected")


if __name__ == '__main__':
    sys.exit(main())
