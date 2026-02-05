"""
Main GUI application for SIK Radio Configurator.
Similar to Mission Planner's radio configuration interface.
"""

import sys
import logging
import json
from typing import Optional
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QGroupBox, QFormLayout, QLabel, QComboBox, QSpinBox, QCheckBox,
    QLineEdit, QPushButton, QTextEdit, QStatusBar, QMessageBox,
    QFileDialog, QProgressBar, QScrollArea, QDialog, QDialogButtonBox,
    QProgressDialog
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread
from PyQt6.QtGui import QFont, QIcon

from src.serial_protocol import SIKRadioProtocol, RadioMode
from src.config_manager import RadioConfiguration, RadioParameter


logger = logging.getLogger(__name__)


class RadioWorker(QObject):
    """Worker thread for radio operations"""
    
    finished = pyqtSignal()
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    parameters_loaded = pyqtSignal(dict)  # remote=False
    remote_parameters_loaded = pyqtSignal(dict)  # remote=True
    info_loaded = pyqtSignal(dict)

    def __init__(self, protocol: SIKRadioProtocol):
        super().__init__()
        self.protocol = protocol

    def load_parameters(self):
        """Load local radio parameters"""
        try:
            self.progress.emit("Loading local radio parameters...")
            params = self.protocol.get_all_parameters(remote=False)
            self.parameters_loaded.emit(params)
            self.progress.emit("Local parameters loaded")
        except Exception as e:
            self.error.emit(f"Failed to load parameters: {str(e)}")
        finally:
            self.finished.emit()

    def load_remote_parameters(self):
        """Load remote radio parameters"""
        try:
            self.progress.emit("Loading remote radio parameters...")
            params = self.protocol.get_all_parameters(remote=True)
            self.remote_parameters_loaded.emit(params)
            self.progress.emit("Remote parameters loaded")
        except Exception as e:
            self.error.emit(f"Failed to load remote parameters: {str(e)}")
        finally:
            self.finished.emit()

    def load_radio_info(self):
        """Load radio information"""
        try:
            self.progress.emit("Loading radio information...")
            info = self.protocol.get_radio_info()
            self.info_loaded.emit(info)
            self.progress.emit("Radio info loaded")
        except Exception as e:
            self.error.emit(f"Failed to load radio info: {str(e)}")
        finally:
            self.finished.emit()


class ParameterWidget(QWidget):
    """Widget for editing a single radio parameter"""
    
    value_changed = pyqtSignal(str, str)  # param_id, new_value

    def __init__(self, parameter: RadioParameter):
        super().__init__()
        self.parameter = parameter
        self.init_ui()

    def init_ui(self):
        """Initialize UI based on parameter type"""
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Label with parameter name and ID
        label_text = f"{self.parameter.param_id}: {self.parameter.name}"
        label = QLabel(label_text)
        label.setMinimumWidth(150)
        layout.addWidget(label)

        # Input widget based on type
        if self.parameter.param_type == 'enum':
            self.input_widget = QComboBox()
            if self.parameter.options:
                for key, display in self.parameter.options.items():
                    self.input_widget.addItem(f"{display}", userData=key)
            self.input_widget.currentIndexChanged.connect(self._on_value_changed)
            # Set current value
            if self.parameter.options and self.parameter.value in self.parameter.options:
                index = list(self.parameter.options.keys()).index(self.parameter.value)
                self.input_widget.setCurrentIndex(index)

        elif self.parameter.param_type == 'bool':
            self.input_widget = QCheckBox()
            self.input_widget.setChecked(self.parameter.value == '1')
            self.input_widget.stateChanged.connect(self._on_value_changed)

        elif self.parameter.param_type == 'int':
            self.input_widget = QSpinBox()
            if self.parameter.min_value is not None:
                self.input_widget.setMinimum(self.parameter.min_value)
            if self.parameter.max_value is not None:
                self.input_widget.setMaximum(self.parameter.max_value)
            else:
                self.input_widget.setMaximum(999999)
            self.input_widget.setValue(int(self.parameter.value) if self.parameter.value.isdigit() else 0)
            self.input_widget.valueChanged.connect(self._on_value_changed)

        else:  # string
            self.input_widget = QLineEdit()
            self.input_widget.setText(self.parameter.value)
            self.input_widget.textChanged.connect(self._on_value_changed)

        layout.addWidget(self.input_widget)

        # Description tooltip
        if self.parameter.description:
            self.setToolTip(self.parameter.description)

        self.setLayout(layout)

    def _on_value_changed(self):
        """Emit value changed signal"""
        if isinstance(self.input_widget, QComboBox):
            value = self.input_widget.currentData()
        elif isinstance(self.input_widget, QCheckBox):
            value = '1' if self.input_widget.isChecked() else '0'
        elif isinstance(self.input_widget, QSpinBox):
            value = str(self.input_widget.value())
        else:  # QLineEdit
            value = self.input_widget.text()

        self.value_changed.emit(self.parameter.param_id, value)

    def get_value(self) -> str:
        """Get current widget value"""
        if isinstance(self.input_widget, QComboBox):
            return self.input_widget.currentData()
        elif isinstance(self.input_widget, QCheckBox):
            return '1' if self.input_widget.isChecked() else '0'
        elif isinstance(self.input_widget, QSpinBox):
            return str(self.input_widget.value())
        else:  # QLineEdit
            return self.input_widget.text()


class RadioConfigPanel(QWidget):
    """Panel for configuring one radio (local or remote)"""
    
    parameter_changed = pyqtSignal(str, str)  # param_id, new_value

    def __init__(self, title: str = "Local Radio", remote: bool = False):
        super().__init__()
        self.title = title
        self.remote = remote
        self.config = RadioConfiguration()
        self.param_widgets = {}
        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout()

        # Title
        title_label = QLabel(self.title)
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(11)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # Scrollable parameter area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        params_container = QWidget()
        params_layout = QVBoxLayout()

        self.param_widgets = {}

        # Add parameter widgets
        for param_id, definition in RadioConfiguration.PARAMETER_DEFINITIONS.items():
            param = RadioParameter(
                param_id=param_id,
                name=definition['name'],
                value=definition.get('default', ''),
                param_type=definition.get('type', 'string'),
                min_value=definition.get('min_value'),
                max_value=definition.get('max_value'),
                options=definition.get('options'),
                description=definition.get('description', ''),
                remote=self.remote
            )
            
            widget = ParameterWidget(param)
            widget.value_changed.connect(self._on_parameter_changed)
            params_layout.addWidget(widget)
            self.param_widgets[param_id] = widget

        params_layout.addStretch()
        params_container.setLayout(params_layout)
        scroll.setWidget(params_container)
        layout.addWidget(scroll)

        self.setLayout(layout)

    def _on_parameter_changed(self, param_id: str, value: str):
        """Handle parameter value change"""
        self.parameter_changed.emit(param_id, value)

    def load_configuration(self, config: RadioConfiguration):
        """Load configuration into UI"""
        self.config = config
        params = config.get_all_parameters(remote=self.remote)
        
        for param in params:
            if param.param_id in self.param_widgets:
                widget = self.param_widgets[param.param_id]
                # Update the parameter widget with new values
                widget.parameter = param
                # Note: In production, we'd update the widget's display here

    def get_modified_parameters(self) -> dict:
        """Get all modified parameters"""
        modified = {}
        for param_id, widget in self.param_widgets.items():
            modified[param_id] = widget.get_value()
        return modified


class SIKRadioConfigurator(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SIK Radio Configurator - Mission Planner Style")
        self.setGeometry(100, 100, 900, 700)

        self.protocol: Optional[SIKRadioProtocol] = None
        self.config = RadioConfiguration()
        self.serial_ports = []

        self.init_ui()
        self.setup_logging()
        self.update_serial_ports()

    def init_ui(self):
        """Initialize UI"""
        # Central widget with tab interface
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()

        # Connection panel
        connection_layout = QHBoxLayout()

        QLabel("Serial Port:")
        self.port_combo = QComboBox()
        self.port_combo.addItem("Auto-detect", userData="")
        connection_layout.addWidget(QLabel("Serial Port:"))
        connection_layout.addWidget(self.port_combo)

        QLabel("Baud Rate:")
        self.baud_combo = QComboBox()
        for baud in [9600, 57600, 115200]:
            self.baud_combo.addItem(str(baud), userData=baud)
        self.baud_combo.setCurrentText("57600")
        connection_layout.addWidget(QLabel("Baud Rate:"))
        connection_layout.addWidget(self.baud_combo)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.on_connect)
        connection_layout.addWidget(self.connect_btn)

        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.clicked.connect(self.on_disconnect)
        self.disconnect_btn.setEnabled(False)
        connection_layout.addWidget(self.disconnect_btn)

        connection_layout.addStretch()

        main_layout.addLayout(connection_layout)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("Disconnected")
        self.status_bar.addWidget(self.status_label)

        # Tab widget
        self.tabs = QTabWidget()

        # Settings tab
        settings_widget = QWidget()
        settings_layout = QHBoxLayout()

        self.local_panel = RadioConfigPanel("Local Radio", remote=False)
        self.remote_panel = RadioConfigPanel("Remote Radio", remote=True)

        settings_layout.addWidget(self.local_panel)
        settings_layout.addWidget(self.remote_panel)

        settings_widget.setLayout(settings_layout)
        self.tabs.addTab(settings_widget, "Configuration")

        # Terminal tab
        terminal_widget = QWidget()
        terminal_layout = QVBoxLayout()

        QLabel("Manual AT Commands:")
        self.terminal_input = QLineEdit()
        self.terminal_input.setPlaceholderText("Enter AT command (e.g., ATI5, ATS3?, RTI5)")
        self.terminal_input.returnPressed.connect(self.on_send_command)
        terminal_layout.addWidget(self.terminal_input)

        # Button row for common commands
        btn_row = QHBoxLayout()
        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self.on_send_command)
        btn_row.addWidget(send_btn)
        
        # Quick command buttons
        quick_ati5_btn = QPushButton("ATI5 (All Params)")
        quick_ati5_btn.clicked.connect(lambda: self.send_quick_command("ATI5"))
        btn_row.addWidget(quick_ati5_btn)
        
        quick_netid_btn = QPushButton("ATS3? (Net ID)")
        quick_netid_btn.clicked.connect(lambda: self.send_quick_command("ATS3?"))
        btn_row.addWidget(quick_netid_btn)
        
        quick_power_btn = QPushButton("ATS4? (TX Power)")
        quick_power_btn.clicked.connect(lambda: self.send_quick_command("ATS4?"))
        btn_row.addWidget(quick_power_btn)
        
        quick_rssi_btn = QPushButton("ATI7 (RSSI)")
        quick_rssi_btn.clicked.connect(lambda: self.send_quick_command("ATI7"))
        btn_row.addWidget(quick_rssi_btn)
        
        btn_row.addStretch()
        terminal_layout.addLayout(btn_row)

        QLabel("Response:")
        self.terminal_output = QTextEdit()
        self.terminal_output.setReadOnly(True)
        self.terminal_output.setFont(QFont("Courier", 9))
        terminal_layout.addWidget(self.terminal_output)

        terminal_widget.setLayout(terminal_layout)
        self.tabs.addTab(terminal_widget, "Terminal")

        # Radio Info tab
        info_widget = QWidget()
        info_layout = QVBoxLayout()
        self.info_output = QTextEdit()
        self.info_output.setReadOnly(True)
        info_layout.addWidget(self.info_output)
        info_widget.setLayout(info_layout)
        self.tabs.addTab(info_widget, "Radio Info")

        main_layout.addWidget(self.tabs)

        # Action buttons
        button_layout = QHBoxLayout()

        self.read_btn = QPushButton("Read Parameters")
        self.read_btn.clicked.connect(self.on_read_parameters)
        self.read_btn.setEnabled(False)
        button_layout.addWidget(self.read_btn)

        self.write_btn = QPushButton("Write & Save")
        self.write_btn.clicked.connect(self.on_write_parameters)
        self.write_btn.setEnabled(False)
        button_layout.addWidget(self.write_btn)

        self.reboot_btn = QPushButton("Reboot Radio")
        self.reboot_btn.clicked.connect(self.on_reboot)
        self.reboot_btn.setEnabled(False)
        button_layout.addWidget(self.reboot_btn)

        self.factory_reset_btn = QPushButton("Factory Reset")
        self.factory_reset_btn.clicked.connect(self.on_factory_reset)
        self.factory_reset_btn.setEnabled(False)
        button_layout.addWidget(self.factory_reset_btn)

        self.export_btn = QPushButton("Export Config")
        self.export_btn.clicked.connect(self.on_export_config)
        self.export_btn.setEnabled(False)
        button_layout.addWidget(self.export_btn)

        self.import_btn = QPushButton("Import Config")
        self.import_btn.clicked.connect(self.on_import_config)
        self.import_btn.setEnabled(False)
        button_layout.addWidget(self.import_btn)

        main_layout.addLayout(button_layout)

        central_widget.setLayout(main_layout)

        # Update serial ports periodically
        self.port_timer = QTimer()
        self.port_timer.timeout.connect(self.update_serial_ports)
        self.port_timer.start(2000)  # Every 2 seconds

    def setup_logging(self):
        """Setup logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    def update_serial_ports(self):
        """Update available serial ports"""
        try:
            import serial.tools.list_ports
            ports = [port.device for port in serial.tools.list_ports.comports()]
            
            if ports != self.serial_ports:
                self.serial_ports = ports
                current = self.port_combo.currentData()
                
                self.port_combo.clear()
                self.port_combo.addItem("Auto-detect", userData="")
                
                for port in ports:
                    self.port_combo.addItem(port, userData=port)
                
                if current and current in ports:
                    self.port_combo.setCurrentText(current)
                elif ports:
                    self.port_combo.setCurrentIndex(1)  # First real port
        except Exception as e:
            logger.error(f"Error updating serial ports: {e}")

    def on_connect(self):
        """Connect to radio"""
        port = self.port_combo.currentData()
        baud = self.baud_combo.currentData()

        if not port:
            # Auto-detect
            if self.serial_ports:
                port = self.serial_ports[0]
            else:
                QMessageBox.warning(self, "Error", "No serial ports found")
                return

        self.protocol = SIKRadioProtocol(port, baudrate=baud)
        
        if self.protocol.connect():
            self.status_label.setText(f"Connected to {port} at {baud} baud")
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            self.read_btn.setEnabled(True)
            self.write_btn.setEnabled(True)
            self.reboot_btn.setEnabled(True)
            self.factory_reset_btn.setEnabled(True)
            self.export_btn.setEnabled(True)
            self.import_btn.setEnabled(True)
            
            # Load radio info
            self.on_read_info()
        else:
            QMessageBox.critical(self, "Error", f"Failed to connect to {port}")
            self.status_label.setText("Connection failed")

    def on_disconnect(self):
        """Disconnect from radio"""
        if self.protocol:
            self.protocol.disconnect()
        
        self.protocol = None
        self.status_label.setText("Disconnected")
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.read_btn.setEnabled(False)
        self.write_btn.setEnabled(False)
        self.reboot_btn.setEnabled(False)
        self.factory_reset_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.import_btn.setEnabled(False)

    def on_read_parameters(self):
        """Read parameters from radio"""
        if not self.protocol:
            QMessageBox.warning(self, "Error", "Not connected to radio")
            return

        # Show progress
        progress = QProgressDialog("Reading radio parameters...", None, 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()

        try:
            # Read local parameters
            params = self.protocol.get_all_parameters(remote=False)
            self.config.load_parameters_from_dict(params, remote=False)
            self.local_panel.load_configuration(self.config)
            
            # Read remote parameters
            params = self.protocol.get_all_parameters(remote=True)
            self.config.load_parameters_from_dict(params, remote=True)
            self.remote_panel.load_configuration(self.config)
            
            self.status_label.setText("Parameters read successfully")
            QMessageBox.information(self, "Success", "Parameters read successfully")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to read parameters: {str(e)}")
            self.status_label.setText("Read failed")
        finally:
            progress.close()

    def on_write_parameters(self):
        """Write parameters to radio"""
        if not self.protocol:
            QMessageBox.warning(self, "Error", "Not connected to radio")
            return

        reply = QMessageBox.question(
            self, "Confirm",
            "Write parameters to radio and save to EEPROM?\nThis will reboot the radio.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.No:
            return

        try:
            # Write local parameters
            local_params = self.local_panel.get_modified_parameters()
            for param_id, value in local_params.items():
                is_valid, msg = self.config.validate_parameter(param_id, value)
                if not is_valid:
                    QMessageBox.warning(self, "Validation Error", f"{param_id}: {msg}")
                    return
                self.protocol.set_parameter(param_id, value, remote=False)

            # Save parameters
            self.protocol.save_parameters(remote=False)
            
            self.status_label.setText("Parameters written and saved")
            QMessageBox.information(self, "Success", "Parameters written successfully")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to write parameters: {str(e)}")

    def on_read_info(self):
        """Read radio information"""
        if not self.protocol:
            return

        try:
            info = self.protocol.get_radio_info()
            board_info = self.protocol.get_board_info()
            freq_info = self.protocol.get_frequency_info()
            
            output = "=== Local Radio Info ===\n"
            for key, value in info.items():
                output += f"{key}: {value}\n"
            
            output += "\n=== Board Info ===\n"
            for key, value in board_info.items():
                output += f"{key}: {value}\n"
            
            output += "\n=== Frequency Info ===\n"
            for key, value in freq_info.items():
                output += f"{key}: {value}\n"
            
            self.info_output.setText(output)
        except Exception as e:
            self.info_output.setText(f"Error reading radio info: {str(e)}")

    def send_quick_command(self, command: str):
        """Send a quick AT command from button"""
        if not self.protocol:
            QMessageBox.warning(self, "Error", "Not connected to radio")
            return
        
        try:
            self.protocol._send_command(command)
            response = self.protocol._read_response()
            
            self.terminal_output.append(f"> {command}")
            self.terminal_output.append(response)
            self.terminal_output.append("")  # Blank line for readability
        except Exception as e:
            self.terminal_output.append(f"Error: {str(e)}")

    def on_send_command(self):
        """Send manual AT command"""
        if not self.protocol:
            QMessageBox.warning(self, "Error", "Not connected to radio")
            return

        command = self.terminal_input.text().strip()
        if not command:
            return

        try:
            self.protocol._send_command(command)
            response = self.protocol._read_response()
            
            self.terminal_output.append(f"> {command}")
            self.terminal_output.append(response)
            self.terminal_output.append("")  # Blank line for readability
            self.terminal_input.clear()
        except Exception as e:
            self.terminal_output.append(f"Error: {str(e)}")

    def on_reboot(self):
        """Reboot radio"""
        if not self.protocol:
            return

        reply = QMessageBox.question(
            self, "Confirm",
            "Reboot the radio?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.protocol.reboot_radio()
                QMessageBox.information(self, "Success", "Reboot command sent")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to reboot: {str(e)}")

    def on_factory_reset(self):
        """Factory reset radio"""
        if not self.protocol:
            return

        reply = QMessageBox.question(
            self, "Confirm",
            "Reset radio to factory defaults?\nThis cannot be undone!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.protocol.factory_reset()
                QMessageBox.information(self, "Success", "Factory reset completed")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to reset: {str(e)}")

    def on_export_config(self):
        """Export configuration to file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Configuration", "",
            "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            try:
                config_data = self.config.export_config(remote=False)
                with open(file_path, 'w') as f:
                    json.dump(config_data, f, indent=2)
                QMessageBox.information(self, "Success", f"Configuration exported to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export: {str(e)}")

    def on_import_config(self):
        """Import configuration from file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Configuration", "",
            "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'r') as f:
                    config_data = json.load(f)
                self.config.import_config(config_data, remote=False)
                self.local_panel.load_configuration(self.config)
                QMessageBox.information(self, "Success", "Configuration imported")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to import: {str(e)}")


def main():
    """Main entry point"""
    app = __import__('PyQt6.QtWidgets', fromlist=['QApplication']).QApplication(sys.argv)
    window = SIKRadioConfigurator()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
