"""
Unit tests for SIK Radio Configurator
"""

import unittest
from src.config_manager import RadioConfiguration, RadioParameter


class TestRadioConfiguration(unittest.TestCase):
    """Test RadioConfiguration class"""
    
    def setUp(self):
        self.config = RadioConfiguration()
    
    def test_parameter_definition_exists(self):
        """Test that parameter definitions exist"""
        self.assertIn('S0', self.config.PARAMETER_DEFINITIONS)
        self.assertIn('S4', self.config.PARAMETER_DEFINITIONS)
    
    def test_validate_integer_parameter(self):
        """Test integer parameter validation"""
        # Valid value
        is_valid, msg = self.config.validate_parameter('S4', '20')
        self.assertTrue(is_valid)
        
        # Too high
        is_valid, msg = self.config.validate_parameter('S4', '50')
        self.assertFalse(is_valid)
        
        # Too low
        is_valid, msg = self.config.validate_parameter('S4', '-5')
        self.assertFalse(is_valid)
    
    def test_validate_boolean_parameter(self):
        """Test boolean parameter validation"""
        # Valid values
        is_valid, msg = self.config.validate_parameter('S5', '0')
        self.assertTrue(is_valid)
        
        is_valid, msg = self.config.validate_parameter('S5', '1')
        self.assertTrue(is_valid)
        
        # Invalid
        is_valid, msg = self.config.validate_parameter('S5', '2')
        self.assertFalse(is_valid)
    
    def test_validate_enum_parameter(self):
        """Test enum parameter validation"""
        # Valid
        is_valid, msg = self.config.validate_parameter('S1', '57')
        self.assertTrue(is_valid)
        
        # Invalid
        is_valid, msg = self.config.validate_parameter('S1', '999')
        self.assertFalse(is_valid)
    
    def test_load_parameters(self):
        """Test loading parameters from dictionary"""
        params_dict = {
            'S0': {'name': 'FORMAT', 'value': '25'},
            'S4': {'name': 'TXPOWER', 'value': '20'},
        }
        
        self.config.load_parameters_from_dict(params_dict)
        
        param_s0 = self.config.get_parameter('S0')
        self.assertIsNotNone(param_s0)
        self.assertEqual(param_s0.value, '25')
        
        param_s4 = self.config.get_parameter('S4')
        self.assertIsNotNone(param_s4)
        self.assertEqual(param_s4.value, '20')
    
    def test_set_parameter_value(self):
        """Test setting parameter value"""
        params_dict = {'S4': {'name': 'TXPOWER', 'value': '20'}}
        self.config.load_parameters_from_dict(params_dict)
        
        self.config.set_parameter_value('S4', '25')
        
        param = self.config.get_parameter('S4')
        self.assertEqual(param.value, '25')
    
    def test_export_config(self):
        """Test configuration export"""
        params_dict = {
            'S4': {'name': 'TXPOWER', 'value': '20'},
            'S2': {'name': 'AIR_SPEED', 'value': '64'},
        }
        self.config.load_parameters_from_dict(params_dict)
        
        export_data = self.config.export_config()
        
        self.assertIn('timestamp', export_data)
        self.assertIn('parameters', export_data)
        self.assertEqual(export_data['parameters']['S4'], '20')
        self.assertEqual(export_data['parameters']['S2'], '64')
    
    def test_import_config(self):
        """Test configuration import"""
        import_data = {
            'timestamp': '2024-01-01T00:00:00',
            'parameters': {
                'S4': '25',
                'S2': '125',
            }
        }
        
        self.config.import_config(import_data)
        
        param_s4 = self.config.get_parameter('S4')
        self.assertEqual(param_s4.value, '25')
        
        param_s2 = self.config.get_parameter('S2')
        self.assertEqual(param_s2.value, '125')
    
    def test_get_all_parameters(self):
        """Test getting all parameters"""
        params_dict = {
            'S0': {'name': 'FORMAT', 'value': '25'},
            'S4': {'name': 'TXPOWER', 'value': '20'},
        }
        self.config.load_parameters_from_dict(params_dict)
        
        all_params = self.config.get_all_parameters()
        
        self.assertEqual(len(all_params), 2)
        self.assertTrue(all(isinstance(p, RadioParameter) for p in all_params))
    
    def test_get_parameters_by_type(self):
        """Test filtering parameters by type"""
        params_dict = {
            'S0': {'name': 'FORMAT', 'value': '25'},
            'S5': {'name': 'ECC', 'value': '1'},
        }
        self.config.load_parameters_from_dict(params_dict)
        
        bool_params = self.config.get_parameters_by_type('bool')
        
        # S5 should be boolean
        bool_param_ids = [p.param_id for p in bool_params]
        self.assertIn('S5', bool_param_ids)


class TestRadioParameter(unittest.TestCase):
    """Test RadioParameter class"""
    
    def test_parameter_creation(self):
        """Test parameter object creation"""
        param = RadioParameter(
            param_id='S4',
            name='TXPOWER',
            value='20',
            param_type='int',
            min_value=0,
            max_value=30,
            description='Transmit power in dBm'
        )
        
        self.assertEqual(param.param_id, 'S4')
        self.assertEqual(param.name, 'TXPOWER')
        self.assertEqual(param.value, '20')
        self.assertEqual(param.param_type, 'int')
        self.assertEqual(param.min_value, 0)
        self.assertEqual(param.max_value, 30)


if __name__ == '__main__':
    unittest.main()
