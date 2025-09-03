"""
Interface gráfica para o sistema DAQ.
Fornece monitoramento em tempo real e controle do sistema.
"""

import sys
import asyncio
import qasync
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QGridLayout,
    QWidget, QPushButton, QLabel, QComboBox, QSpinBox, QDoubleSpinBox,
    QTextEdit, QProgressBar, QGroupBox, QTabWidget, QTableWidget,
    QTableWidgetItem, QFileDialog, QMessageBox, QCheckBox, QSlider
)
from PyQt5.QtCore import QTimer, pyqtSignal, QThread, Qt
from PyQt5.QtGui import QFont, QPixmap, QPalette, QColor

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

# Adiciona diretório pai ao path
sys.path.append(str(Path(__file__).parent.parent))

from main import DAQSystemApplication
from simulator import SimulatorConfig
from src.core.models import StrainReading, SensorConfiguration


class RealtimePlotWidget(FigureCanvas):
    """Widget para gráficos em tempo real."""
    
    def __init__(self, parent=None, width=8, height=4, dpi=100):
        """Inicializa widget de gráfico."""
        self.figure = Figure(figsize=(width, height), dpi=dpi, facecolor='white')
        super().__init__(self.figure)
        self.setParent(parent)
        
        # Configuração dos gráficos
        self.axes = self.figure.add_subplot(111)
        self.axes.set_title('Strain em Tempo Real')
        self.axes.set_xlabel('Tempo (s)')
        self.axes.set_ylabel('Strain (µε)')
        self.axes.grid(True, alpha=0.3)
        
        # Dados para plotagem
        self.max_points = 500  # Últimos 500 pontos
        self.time_data = []
        self.strain_data = []
        self.start_time = datetime.now()
        
        # Linha do gráfico
        self.line, = self.axes.plot([], [], 'b-', linewidth=1.5, label='Strain')
        self.axes.legend()
        
        # Atualiza layout
        self.figure.tight_layout()
    
    def add_data_point(self, reading: StrainReading) -> None:
        """
        Adiciona novo ponto ao gráfico.
        
        Args:
            reading: Leitura de strain
        """
        # Calcula tempo relativo
        elapsed = (reading.timestamp - self.start_time).total_seconds()
        
        # Adiciona dados
        self.time_data.append(elapsed)
        self.strain_data.append(reading.strain)
        
        # Mantém apenas os últimos pontos
        if len(self.time_data) > self.max_points:
            self.time_data.pop(0)
            self.strain_data.pop(0)
        
        # Atualiza gráfico
        self.update_plot()
    
    def update_plot(self) -> None:
        """Atualiza visualização do gráfico."""
        if not self.time_data:
            return
        
        # Atualiza dados da linha
        self.line.set_data(self.time_data, self.strain_data)
        
        # Ajusta limites dos eixos
        self.axes.set_xlim(min(self.time_data), max(self.time_data))
        
        y_min, y_max = min(self.strain_data), max(self.strain_data)
        y_range = y_max - y_min
        margin = y_range * 0.1 if y_range > 0 else 10
        
        self.axes.set_ylim(y_min - margin, y_max + margin)
        
        # Redesenha
        self.draw()
    
    def clear_plot(self) -> None:
        """Limpa o gráfico."""
        self.time_data.clear()
        self.strain_data.clear()
        self.start_time = datetime.now()
        self.line.set_data([], [])
        self.draw()


class StatusWidget(QWidget):
    """Widget para exibir status do sistema."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Configura interface do widget."""
        layout = QGridLayout(self)
        
        # Status do simulador
        self.simulator_status = QLabel("Parado")
        self.simulator_status.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(QLabel("Simulador:"), 0, 0)
        layout.addWidget(self.simulator_status, 0, 1)
        
        # Cenário atual
        self.current_scenario = QLabel("-")
        layout.addWidget(QLabel("Cenário:"), 1, 0)
        layout.addWidget(self.current_scenario, 1, 1)
        
        # Nível da bateria
        self.battery_level = QProgressBar()
        self.battery_level.setRange(0, 100)
        self.battery_level.setValue(0)
        layout.addWidget(QLabel("Bateria:"), 2, 0)
        layout.addWidget(self.battery_level, 2, 1)
        
        # Status BLE
        self.ble_status = QLabel("Desconectado")
        layout.addWidget(QLabel("BLE:"), 3, 0)
        layout.addWidget(self.ble_status, 3, 1)
        
        # Leituras recebidas
        self.readings_count = QLabel("0")
        layout.addWidget(QLabel("Leituras:"), 4, 0)
        layout.addWidget(self.readings_count, 4, 1)
        
        # Taxa de amostragem
        self.sample_rate = QLabel("0.0 Hz")
        layout.addWidget(QLabel("Taxa:"), 5, 0)
        layout.addWidget(self.sample_rate, 5, 1)
    
    def update_status(self, status_data: dict) -> None:
        """
        Atualiza exibição de status.
        
        Args:
            status_data: Dados de status do sistema
        """
        if 'simulator' in status_data:
            sim_data = status_data['simulator']
            self.simulator_status.setText("Executando")
            self.simulator_status.setStyleSheet("color: green; font-weight: bold;")
            
            if 'current_scenario' in sim_data:
                self.current_scenario.setText(sim_data['current_scenario'])
        
        if 'system' in status_data:
            sys_data = status_data['system']
            
            # Bateria
            if 'esp32' in sys_data and 'battery_level' in sys_data['esp32']:
                battery = sys_data['esp32']['battery_level']
                self.battery_level.setValue(int(battery))
                
                # Cor baseada no nível
                if battery > 50:
                    color = "green"
                elif battery > 20:
                    color = "orange"
                else:
                    color = "red"
                
                self.battery_level.setStyleSheet(f"""
                    QProgressBar::chunk {{ background-color: {color}; }}
                """)
            
            # BLE
            if 'ble' in sys_data and 'state' in sys_data['ble']:
                ble_state = sys_data['ble']['state']
                self.ble_status.setText(ble_state.title())
                
                if ble_state.lower() == 'connected':
                    self.ble_status.setStyleSheet("color: green; font-weight: bold;")
                else:
                    self.ble_status.setStyleSheet("color: red;")
        
        if 'application' in status_data:
            app_data = status_data['application']
            
            # Contadores
            if 'readings_received' in app_data:
                self.readings_count.setText(str(app_data['readings_received']))
            
            # Taxa de amostragem
            if 'start_time' in app_data and app_data['start_time']:
                import time
                elapsed = time.time() - app_data['start_time']
                readings = app_data.get('readings_received', 0)
                
                if elapsed > 0:
                    rate = readings / elapsed
                    self.sample_rate.setText(f"{rate:.1f} Hz")


class ControlWidget(QWidget):
    """Widget para controles do sistema."""
    
    # Sinais
    scenario_changed = pyqtSignal(str)
    speed_changed = pyqtSignal(float)
    config_changed = pyqtSignal(dict)
    export_requested = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Configura interface do widget."""
        layout = QVBoxLayout(self)
        
        # Controles do simulador
        sim_group = QGroupBox("Controles do Simulador")
        sim_layout = QGridLayout(sim_group)
        
        # Cenário
        sim_layout.addWidget(QLabel("Cenário:"), 0, 0)
        self.scenario_combo = QComboBox()
        self.scenario_combo.addItems([
            "idle", "transport", "field_work_light", 
            "field_work_heavy", "harvest", "overload"
        ])
        self.scenario_combo.currentTextChanged.connect(self.scenario_changed.emit)
        sim_layout.addWidget(self.scenario_combo, 0, 1)
        
        # Velocidade
        sim_layout.addWidget(QLabel("Velocidade:"), 1, 0)
        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(0.1, 10.0)
        self.speed_spin.setValue(1.0)
        self.speed_spin.setSingleStep(0.1)
        self.speed_spin.setSuffix("x")
        self.speed_spin.valueChanged.connect(self.speed_changed.emit)
        sim_layout.addWidget(self.speed_spin, 1, 1)
        
        layout.addWidget(sim_group)
        
        # Configuração do sensor
        sensor_group = QGroupBox("Configuração do Sensor")
        sensor_layout = QGridLayout(sensor_group)
        
        # Taxa de amostragem
        sensor_layout.addWidget(QLabel("Taxa (Hz):"), 0, 0)
        self.sample_rate_spin = QSpinBox()
        self.sample_rate_spin.setRange(1, 1000)
        self.sample_rate_spin.setValue(10)
        sensor_layout.addWidget(self.sample_rate_spin, 0, 1)
        
        # Filtro
        sensor_layout.addWidget(QLabel("Filtro:"), 1, 0)
        self.filter_check = QCheckBox("Habilitado")
        self.filter_check.setChecked(True)
        sensor_layout.addWidget(self.filter_check, 1, 1)
        
        # Calibração
        sensor_layout.addWidget(QLabel("Calibração:"), 2, 0)
        self.calibration_spin = QDoubleSpinBox()
        self.calibration_spin.setRange(0.1, 10.0)
        self.calibration_spin.setValue(1.0)
        self.calibration_spin.setDecimals(3)
        sensor_layout.addWidget(self.calibration_spin, 2, 1)
        
        # Botão aplicar
        apply_btn = QPushButton("Aplicar Configuração")
        apply_btn.clicked.connect(self._apply_sensor_config)
        sensor_layout.addWidget(apply_btn, 3, 0, 1, 2)
        
        layout.addWidget(sensor_group)
        
        # Exportação
        export_group = QGroupBox("Exportação de Dados")
        export_layout = QHBoxLayout(export_group)
        
        export_csv_btn = QPushButton("Exportar CSV")
        export_csv_btn.clicked.connect(lambda: self.export_requested.emit("csv"))
        export_layout.addWidget(export_csv_btn)
        
        export_json_btn = QPushButton("Exportar JSON")
        export_json_btn.clicked.connect(lambda: self.export_requested.emit("json"))
        export_layout.addWidget(export_json_btn)
        
        export_excel_btn = QPushButton("Exportar Excel")
        export_excel_btn.clicked.connect(lambda: self.export_requested.emit("excel"))
        export_layout.addWidget(export_excel_btn)
        
        layout.addWidget(export_group)
        
        # Espaçador
        layout.addStretch()
    
    def _apply_sensor_config(self):
        """Aplica configuração do sensor."""
        config = {
            'sample_rate': self.sample_rate_spin.value(),
            'filter_enabled': self.filter_check.isChecked(),
            'calibration_factor': self.calibration_spin.value()
        }
        self.config_changed.emit(config)


class DAQMainWindow(QMainWindow):
    """Janela principal da aplicação DAQ."""
    
    def __init__(self):
        super().__init__()
        self.daq_app: Optional[DAQSystemApplication] = None
        self.setup_ui()
        self.setup_timers()
    
    def setup_ui(self):
        """Configura interface da janela principal."""
        self.setWindowTitle("Sistema DAQ - Análise de Fadiga v1.0.0")
        self.setGeometry(100, 100, 1200, 800)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Layout de abas
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget, stretch=3)
        
        # Aba do gráfico
        plot_tab = QWidget()
        plot_layout = QVBoxLayout(plot_tab)
        
        # Gráfico em tempo real
        self.plot_widget = RealtimePlotWidget()
        plot_layout.addWidget(self.plot_widget)
        
        # Controles do gráfico
        plot_controls = QHBoxLayout()
        
        clear_btn = QPushButton("Limpar Gráfico")
        clear_btn.clicked.connect(self.plot_widget.clear_plot)
        plot_controls.addWidget(clear_btn)
        
        self.auto_scale_check = QCheckBox("Auto Scale")
        self.auto_scale_check.setChecked(True)
        plot_controls.addWidget(self.auto_scale_check)
        
        plot_controls.addStretch()
        plot_layout.addLayout(plot_controls)
        
        tab_widget.addTab(plot_tab, "Gráfico")
        
        # Aba de dados
        data_tab = QWidget()
        data_layout = QVBoxLayout(data_tab)
        
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(4)
        self.data_table.setHorizontalHeaderLabels([
            "Timestamp", "Strain (µε)", "Raw ADC", "Temperatura (°C)"
        ])
        data_layout.addWidget(self.data_table)
        
        tab_widget.addTab(data_tab, "Dados")
        
        # Painel lateral de controles
        controls_layout = QVBoxLayout()
        main_layout.addLayout(controls_layout, stretch=1)
        
        # Status
        self.status_widget = StatusWidget()
        controls_layout.addWidget(self.status_widget)
        
        # Controles
        self.control_widget = ControlWidget()
        controls_layout.addWidget(self.control_widget)
        
        # Conecta sinais
        self.control_widget.scenario_changed.connect(self._change_scenario)
        self.control_widget.speed_changed.connect(self._change_speed)
        self.control_widget.config_changed.connect(self._apply_config)
        self.control_widget.export_requested.connect(self._export_data)
        
        # Log de eventos
        log_group = QGroupBox("Log de Eventos")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        controls_layout.addWidget(log_group)
        
        # Botões principais
        buttons_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("Iniciar Sistema")
        self.start_btn.clicked.connect(self._start_system)
        buttons_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("Parar Sistema")
        self.stop_btn.clicked.connect(self._stop_system)
        self.stop_btn.setEnabled(False)
        buttons_layout.addWidget(self.stop_btn)
        
        controls_layout.addLayout(buttons_layout)
    
    def setup_timers(self):
        """Configura timers para atualizações."""
        # Timer para atualização de status
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_status)
        self.status_timer.start(1000)  # 1 segundo
        
        # Timer para atualização de dados
        self.data_timer = QTimer()
        self.data_timer.timeout.connect(self._update_data_table)
        self.data_timer.start(5000)  # 5 segundos
    
    def log_message(self, message: str):
        """
        Adiciona mensagem ao log.
        
        Args:
            message: Mensagem para log
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_message = f"[{timestamp}] {message}"
        
        self.log_text.append(full_message)
        
        # Mantém apenas as últimas 100 linhas
        doc = self.log_text.document()
        if doc.blockCount() > 100:
            cursor = self.log_text.textCursor()
            cursor.movePosition(cursor.Start)
            cursor.movePosition(cursor.Down, cursor.KeepAnchor, doc.blockCount() - 100)
            cursor.removeSelectedText()
    
    async def _start_system(self):
        """Inicia o sistema DAQ."""
        try:
            self.log_message("Iniciando sistema DAQ...")
            
            # Configuração padrão
            config = SimulatorConfig(
                device_name="DAQ_GUI",
                simulation_speed=1.0,
                enable_ble=True,
                enable_wifi=False,
                auto_start=True,
                realistic_loads=True
            )
            
            # Cria aplicação DAQ
            self.daq_app = DAQSystemApplication()
            
            # Registra callback para dados
            if self.daq_app.simulator:
                self.daq_app.simulator.add_data_callback(self._on_new_data)
            
            # Inicia sistema (de forma assíncrona)
            await self.daq_app.start(config)
            
            # Atualiza interface
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            
            self.log_message("Sistema DAQ iniciado com sucesso")
            
        except Exception as e:
            self.log_message(f"Erro ao iniciar sistema: {e}")
            QMessageBox.critical(self, "Erro", f"Falha ao iniciar sistema:\n{e}")
    
    async def _stop_system(self):
        """Para o sistema DAQ."""
        try:
            if self.daq_app:
                self.log_message("Parando sistema DAQ...")
                await self.daq_app._cleanup()
                self.daq_app = None
            
            # Atualiza interface
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            
            self.log_message("Sistema DAQ parado")
            
        except Exception as e:
            self.log_message(f"Erro ao parar sistema: {e}")
    
    async def _on_new_data(self, reading: StrainReading):
        """
        Callback para novos dados.
        
        Args:
            reading: Nova leitura de strain
        """
        # Atualiza gráfico
        self.plot_widget.add_data_point(reading)
    
    def _update_status(self):
        """Atualiza display de status."""
        if self.daq_app:
            try:
                status = self.daq_app.get_system_statistics()
                self.status_widget.update_status(status)
            except Exception as e:
                self.log_message(f"Erro ao atualizar status: {e}")
    
    def _update_data_table(self):
        """Atualiza tabela de dados."""
        if not self.daq_app:
            return
        
        try:
            # Obtém últimas 20 leituras
            # (implementação simplificada)
            pass
            
        except Exception as e:
            self.log_message(f"Erro ao atualizar tabela: {e}")
    
    async def _change_scenario(self, scenario: str):
        """Altera cenário de simulação."""
        if self.daq_app:
            success = await self.daq_app.set_scenario(scenario)
            if success:
                self.log_message(f"Cenário alterado para: {scenario}")
            else:
                self.log_message(f"Falha ao alterar cenário para: {scenario}")
    
    def _change_speed(self, speed: float):
        """Altera velocidade de simulação."""
        if self.daq_app and self.daq_app.simulator:
            self.daq_app.simulator.config.simulation_speed = speed
            self.log_message(f"Velocidade alterada para: {speed}x")
    
    async def _apply_config(self, config_data: dict):
        """Aplica configuração do sensor."""
        if self.daq_app:
            try:
                # Cria configuração
                sensor_config = SensorConfiguration(
                    sample_rate=config_data['sample_rate'],
                    filter_enabled=config_data['filter_enabled'],
                    calibration_factor=config_data['calibration_factor']
                )
                
                success = await self.daq_app.configure_sensor(sensor_config)
                if success:
                    self.log_message("Configuração do sensor aplicada")
                else:
                    self.log_message("Falha ao aplicar configuração")
                    
            except Exception as e:
                self.log_message(f"Erro na configuração: {e}")
    
    async def _export_data(self, format_type: str):
        """Exporta dados."""
        if not self.daq_app:
            QMessageBox.warning(self, "Aviso", "Sistema não está em execução")
            return
        
        # Diálogo para salvar arquivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"daq_data_{timestamp}.{format_type}"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, f"Exportar dados {format_type.upper()}", 
            default_name, f"Arquivos {format_type.upper()} (*.{format_type})"
        )
        
        if file_path:
            try:
                success = await self.daq_app.export_data(format_type, Path(file_path))
                if success:
                    self.log_message(f"Dados exportados: {file_path}")
                    QMessageBox.information(
                        self, "Sucesso", f"Dados exportados com sucesso:\n{file_path}"
                    )
                else:
                    self.log_message("Falha na exportação")
                    
            except Exception as e:
                self.log_message(f"Erro na exportação: {e}")
                QMessageBox.critical(self, "Erro", f"Falha na exportação:\n{e}")
    
    def closeEvent(self, event):
        """Intercepta fechamento da janela."""
        if self.daq_app:
            reply = QMessageBox.question(
                self, 'Confirmação',
                'Sistema DAQ está em execução. Deseja realmente sair?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Para sistema antes de fechar
                asyncio.create_task(self._stop_system())
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


async def main_gui():
    """Função principal da interface gráfica."""
    app = QApplication(sys.argv)
    
    # Configura loop de eventos assíncrono
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    # Cria janela principal
    window = DAQMainWindow()
    window.show()
    
    # Executa aplicação
    with loop:
        loop.run_forever()


if __name__ == "__main__":
    # Executa interface gráfica
    asyncio.run(main_gui())
