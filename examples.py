"""
Example usage of SIK Radio Configurator as a Python library.
"""

from src.serial_protocol import SIKRadioProtocol
from src.config_manager import RadioConfiguration


def example_basic_operations():
    """Basic radio operations example"""
    
    # Create protocol instance
    protocol = SIKRadioProtocol('/dev/ttyUSB0', baudrate=57600)
    
    # Connect to radio
    print("Connecting to radio...")
    if not protocol.connect():
        print("Failed to connect!")
        return
    
    print("Connected successfully!")
    
    # Get radio information
    print("\n=== Radio Information ===")
    info = protocol.get_radio_info()
    for key, value in info.items():
        print(f"{key}: {value}")
    
    # Get all parameters
    print("\n=== Reading Parameters ===")
    params = protocol.get_all_parameters()
    for param_id, param_info in params.items():
        print(f"{param_id}: {param_info}")
    
    # Get specific parameter
    print("\n=== Specific Parameter ===")
    tx_power = protocol.get_parameter('S4')
    print(f"TX Power: {tx_power} dBm")
    
    # Disconnect
    protocol.disconnect()
    print("\nDisconnected")


def example_modify_parameters():
    """Modify and save parameters"""
    
    protocol = SIKRadioProtocol('/dev/ttyUSB0', baudrate=57600)
    
    if not protocol.connect():
        print("Failed to connect!")
        return
    
    print("Setting parameters...")
    
    # Set parameters
    protocol.set_parameter('S4', '20')  # TX Power
    protocol.set_parameter('S2', '64')  # Air speed
    protocol.set_parameter('S1', '57')  # Serial speed
    
    # Save to EEPROM
    print("Saving to EEPROM...")
    protocol.save_parameters()
    
    # Reboot radio
    print("Rebooting radio...")
    protocol.reboot_radio()
    
    protocol.disconnect()
    print("Done!")


def example_configuration_management():
    """Configuration export and import"""
    
    protocol = SIKRadioProtocol('/dev/ttyUSB0', baudrate=57600)
    config = RadioConfiguration()
    
    if not protocol.connect():
        print("Failed to connect!")
        return
    
    # Read configuration
    print("Reading configuration...")
    params = protocol.get_all_parameters()
    config.load_parameters_from_dict(params)
    
    # Export configuration
    print("Exporting configuration...")
    export_data = config.export_config()
    
    import json
    with open('radio_config.json', 'w') as f:
        json.dump(export_data, f, indent=2)
    
    print("Configuration exported to radio_config.json")
    
    # Later: Import and apply configuration
    print("\nImporting configuration...")
    with open('radio_config.json', 'r') as f:
        import_data = json.load(f)
    
    config.import_config(import_data)
    
    # Apply settings
    for param in config.get_all_parameters():
        print(f"Setting {param.param_id} = {param.value}")
        protocol.set_parameter(param.param_id, param.value)
    
    protocol.save_parameters()
    protocol.disconnect()
    print("Configuration applied!")


def example_remote_radio():
    """Configure remote radio"""
    
    protocol = SIKRadioProtocol('/dev/ttyUSB0', baudrate=57600)
    
    if not protocol.connect():
        print("Failed to connect!")
        return
    
    print("Configuring remote radio...")
    
    # Read remote parameters
    print("\n=== Remote Radio Parameters ===")
    remote_params = protocol.get_all_parameters(remote=True)
    for param_id, param_info in remote_params.items():
        print(f"{param_id}: {param_info}")
    
    # Modify remote parameters
    print("\nSetting remote TX power to 25 dBm...")
    protocol.set_parameter('S4', '25', remote=True)
    protocol.save_parameters(remote=True)
    
    protocol.disconnect()
    print("Done!")


def example_factory_reset():
    """Factory reset example"""
    
    protocol = SIKRadioProtocol('/dev/ttyUSB0', baudrate=57600)
    
    if not protocol.connect():
        print("Failed to connect!")
        return
    
    print("WARNING: About to factory reset radio!")
    response = input("Type 'yes' to confirm: ")
    
    if response.lower() == 'yes':
        print("Performing factory reset...")
        protocol.factory_reset()
        print("Reset complete!")
    else:
        print("Cancelled")
    
    protocol.disconnect()


def example_parameter_validation():
    """Parameter validation example"""
    
    config = RadioConfiguration()
    
    # Test valid values
    print("=== Parameter Validation ===")
    
    test_cases = [
        ('S4', '20'),      # Valid TX power
        ('S4', '50'),      # Invalid (too high)
        ('S2', '64'),      # Valid air speed
        ('S2', '100'),     # Invalid
        ('S3', '25'),      # Valid network ID
        ('S3', '300'),     # Valid (extended range)
        ('S5', '1'),       # Valid boolean
        ('S5', '2'),       # Invalid boolean
    ]
    
    for param_id, value in test_cases:
        is_valid, message = config.validate_parameter(param_id, value)
        status = "✓" if is_valid else "✗"
        print(f"{status} {param_id}={value}: {message if message else 'Valid'}")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        example_name = sys.argv[1]
        
        examples = {
            'basic': example_basic_operations,
            'modify': example_modify_parameters,
            'config': example_configuration_management,
            'remote': example_remote_radio,
            'reset': example_factory_reset,
            'validate': example_parameter_validation,
        }
        
        if example_name in examples:
            examples[example_name]()
        else:
            print(f"Unknown example: {example_name}")
            print(f"Available examples: {', '.join(examples.keys())}")
    else:
        print("Available examples:")
        print("  python examples.py basic      - Basic operations")
        print("  python examples.py modify     - Modify and save parameters")
        print("  python examples.py config     - Configuration export/import")
        print("  python examples.py remote     - Configure remote radio")
        print("  python examples.py reset      - Factory reset")
        print("  python examples.py validate   - Parameter validation")
