"""
Simulador principal do sistema DAQ.
Integra ESP32 e HX711 simuladores com interface de comunicação.
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass

from .esp32_simulator import ESP32Simulator, ESP32Config
from .hx711_simulator import HX711Simulator, HX711SimulatorConfig
from ..core.models import StrainReading, SensorConfiguration, SensorInfo, SensorStatus, CommunicationProtocol
from ..communication import BLESimulator, MessageProtocol, MessageType, DataPacketEncoder


@dataclass
class SimulatorConfig:
    """Configuração do simulador completo."""
    device_name: str = "DAQ_Simulator"
    auto_start: bool = True
    simulation_speed: float = 1.0  # Multiplicador de velocidade
    enable_ble: bool = True
    enable_wifi: bool = False
    battery_simulation: bool = True
    realistic_loads: bool = True


class DAQSystemSimulator:
    """
    Simulador completo do sistema DAQ.
    
    Combina simuladores ESP32 e HX711 com comunicação BLE/WiFi
    para criar um ambiente de teste realístico sem hardware físico.
    """
    
    def __init__(self, config: Optional[SimulatorConfig] = None):
        """
        Inicializa o simulador completo.
        
        Args:
            config: Configuração do simulador
        """
        self.config = config or SimulatorConfig()
        
        # Componentes do sistema
        self.esp32 = ESP32Simulator(ESP32Config(device_name=self.config.device_name))
        self.hx711 = self.esp32.hx711  # Usa o HX711 do ESP32
        self.ble_comm = BLESimulator()
        
        # Estado do simulador
        self._is_running = False
        self._sensor_config = SensorConfiguration()
        self._data_callbacks: List[Callable] = []
        self._status_callbacks: List[Callable] = []
        
        # Tasks de simulação
        self._simulation_tasks: List[asyncio.Task] = []
        
        # Histórico de dados para análise
        self._data_history: List[StrainReading] = []
        self._max_history_size = 1000
        
        # Configurações de carga simulada
        self._load_scenarios = self._create_load_scenarios()
        self._current_scenario = "idle"
        
        self._setup_communication()
    
    def _create_load_scenarios(self) -> Dict[str, Dict[str, Any]]:
        """Cria cenários de carga para simulação realística."""
        return {
            "idle": {
                "description": "Máquina parada",
                "base_strain": 0.0,
                "amplitude": 5.0,
                "frequency": 0.1,
                "noise_level": 0.05
            },
            "transport": {
                "description": "Transporte em estrada",
                "base_strain": 10.0,
                "amplitude": 30.0,
                "frequency": 2.0,
                "noise_level": 0.1
            },
            "field_work_light": {
                "description": "Trabalho leve no campo",
                "base_strain": 50.0,
                "amplitude": 100.0,
                "frequency": 1.5,
                "noise_level": 0.15
            },
            "field_work_heavy": {
                "description": "Trabalho pesado no campo",
                "base_strain": 200.0,
                "amplitude": 300.0,
                "frequency": 3.0,
                "noise_level": 0.2
            },
            "harvest": {
                "description": "Operação de colheita",
                "base_strain": 150.0,
                "amplitude": 250.0,
                "frequency": 4.0,
                "noise_level": 0.18
            },
            "overload": {
                "description": "Sobrecarga do sistema",
                "base_strain": 400.0,
                "amplitude": 200.0,
                "frequency": 1.0,
                "noise_level": 0.1
            }
        }
    
    def _setup_communication(self) -> None:
        """Configura callbacks de comunicação."""
        # Callbacks do ESP32
        self.esp32.add_data_callback(self._on_esp32_data)
        self.esp32.add_status_callback(self._on_esp32_status)
        
        # Callbacks do BLE
        self.ble_comm.add_data_callback(self._on_ble_data_received)
        self.ble_comm.add_connection_callback(self._on_ble_connection)
    
    async def start(self) -> None:
        """Inicia a simulação completa."""
        if self._is_running:
            return
        
        self._is_running = True
        
        # Inicia componentes
        await self.esp32.start()
        
        if self.config.enable_ble:
            await self.ble_comm.start_advertising()
        
        # Inicia tasks de simulação
        self._simulation_tasks = [
            asyncio.create_task(self._load_simulation_loop()),
            asyncio.create_task(self._data_collection_loop()),
            asyncio.create_task(self._status_monitoring_loop())
        ]
        
        print(f"Simulador DAQ iniciado: {self.config.device_name}")
    
    async def stop(self) -> None:
        """Para a simulação."""
        self._is_running = False
        
        # Cancela tasks
        for task in self._simulation_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Para componentes
        await self.esp32.stop()
        await self.ble_comm.stop_scan()
        
        print("Simulador DAQ parado")
    
    async def _load_simulation_loop(self) -> None:
        """Loop de simulação de cargas dinâmicas."""
        while self._is_running:
            try:
                if self.config.realistic_loads:
                    scenario = self._load_scenarios[self._current_scenario]
                    
                    # Aplica carga baseada no cenário atual
                    current_time = time.time() * self.config.simulation_speed
                    
                    import math
                    strain = (
                        scenario["base_strain"] +
                        scenario["amplitude"] * math.sin(
                            2 * math.pi * scenario["frequency"] * current_time
                        )
                    )
                    
                    # Adiciona ruído
                    import random
                    noise = random.gauss(0, scenario["noise_level"] * abs(strain))
                    strain += noise
                    
                    self.hx711.apply_load(strain)
                
                await asyncio.sleep(0.1 / self.config.simulation_speed)
                
            except Exception as e:
                print(f"Erro na simulação de carga: {e}")
                await asyncio.sleep(1.0)
    
    async def _data_collection_loop(self) -> None:
        """Loop de coleta e processamento de dados."""
        while self._is_running:
            try:
                # Coleta dados dos sensores
                strain_value = self.hx711.read_strain_microstrains()
                raw_adc = self.hx711.read_adc_raw()
                
                # Cria leitura
                reading = StrainReading(
                    timestamp=datetime.now(),
                    strain_value=strain_value,
                    raw_adc_value=raw_adc,
                    sensor_id=self.esp32.device_id,
                    battery_level=int(self.esp32._battery_level),
                    temperature=self.hx711._temperature
                )
                
                # Adiciona ao histórico
                self._add_to_history(reading)
                
                # Notifica callbacks
                await self._notify_data_callbacks(reading)
                
                # Simula intervalo de amostragem
                await asyncio.sleep(
                    self._sensor_config.sampling_rate_ms / 1000.0 / self.config.simulation_speed
                )
                
            except Exception as e:
                print(f"Erro na coleta de dados: {e}")
                await asyncio.sleep(1.0)
    
    async def _status_monitoring_loop(self) -> None:
        """Loop de monitoramento de status."""
        while self._is_running:
            try:
                # Coleta status do sistema
                esp32_status = self.esp32.get_status()
                
                # Cria informações do sensor
                sensor_info = SensorInfo(
                    sensor_id=self.esp32.device_id,
                    name=self.config.device_name,
                    status=SensorStatus.ONLINE if self._is_running else SensorStatus.OFFLINE,
                    last_seen=datetime.now(),
                    protocol=CommunicationProtocol.BLE if self.config.enable_ble else None,
                    signal_strength=-50,  # RSSI simulado
                    firmware_version="1.0.0-sim",
                    hardware_version="ESP32-SIM"
                )
                
                # Notifica callbacks de status
                await self._notify_status_callbacks(sensor_info)
                
                await asyncio.sleep(5.0)  # Status a cada 5 segundos
                
            except Exception as e:
                print(f"Erro no monitoramento: {e}")
                await asyncio.sleep(5.0)
    
    def _add_to_history(self, reading: StrainReading) -> None:
        """Adiciona leitura ao histórico."""
        self._data_history.append(reading)
        
        # Limita tamanho do histórico
        if len(self._data_history) > self._max_history_size:
            self._data_history.pop(0)
    
    # Métodos de controle de cenários
    def set_load_scenario(self, scenario_name: str) -> bool:
        """
        Define o cenário de carga atual.
        
        Args:
            scenario_name: Nome do cenário
            
        Returns:
            True se cenário válido
        """
        if scenario_name in self._load_scenarios:
            self._current_scenario = scenario_name
            print(f"Cenário alterado para: {scenario_name} - {self._load_scenarios[scenario_name]['description']}")
            return True
        return False
    
    def get_available_scenarios(self) -> Dict[str, str]:
        """Retorna cenários disponíveis."""
        return {
            name: scenario["description"] 
            for name, scenario in self._load_scenarios.items()
        }
    
    def apply_custom_load(self, strain_microstrains: float) -> None:
        """
        Aplica uma carga personalizada.
        
        Args:
            strain_microstrains: Deformação em microstrains
        """
        self.hx711.apply_load(strain_microstrains)
    
    # Métodos de configuração
    async def configure_sensor(self, config: SensorConfiguration) -> bool:
        """
        Configura parâmetros do sensor.
        
        Args:
            config: Nova configuração
            
        Returns:
            True se configuração aplicada
        """
        try:
            self._sensor_config = config
            
            # Aplica configurações no ESP32
            esp32_config = {
                'calibration_factor': config.calibration_factor,
                'sampling_rate': config.sampling_rate_ms,
                'transmission_interval': config.transmission_interval_s
            }
            
            success = self.esp32.configure_sensor(esp32_config)
            
            if success:
                print(f"Sensor configurado: {config.sensor_id}")
            
            return success
            
        except Exception as e:
            print(f"Erro na configuração: {e}")
            return False
    
    def get_sensor_configuration(self) -> SensorConfiguration:
        """Retorna configuração atual do sensor."""
        return self._sensor_config
    
    # Callbacks de comunicação
    async def _on_esp32_data(self, data_point: Dict[str, Any]) -> None:
        """Callback para dados do ESP32."""
        # Converte para StrainReading se necessário
        if isinstance(data_point, dict):
            reading = StrainReading(
                timestamp=datetime.fromtimestamp(data_point['timestamp']),
                strain_value=data_point['strain_value'],
                raw_adc_value=data_point['raw_adc_value'],
                sensor_id=data_point['sensor_id'],
                battery_level=data_point['battery_level'],
                temperature=data_point['temperature']
            )
            
            self._add_to_history(reading)
            await self._notify_data_callbacks(reading)
    
    async def _on_esp32_status(self, status: Dict[str, Any]) -> None:
        """Callback para status do ESP32."""
        sensor_info = SensorInfo(
            sensor_id=status['device_id'],
            name=status['device_name'],
            status=SensorStatus.ONLINE,
            last_seen=datetime.now(),
            protocol=CommunicationProtocol.BLE
        )
        
        await self._notify_status_callbacks(sensor_info)
    
    async def _on_ble_data_received(self, address: str, data: bytes) -> None:
        """Callback para dados recebidos via BLE."""
        try:
            # Processa comando recebido
            message = MessageProtocol.parse_message(data)
            await self._process_received_command(address, message)
            
        except Exception as e:
            print(f"Erro ao processar dados BLE: {e}")
    
    async def _on_ble_connection(self, device, connected: bool) -> None:
        """Callback para eventos de conexão BLE."""
        if connected:
            print(f"Cliente conectado via BLE: {device.address}")
        else:
            print(f"Cliente desconectado via BLE: {device.address}")
    
    async def _process_received_command(self, address: str, message: Dict[str, Any]) -> None:
        """Processa comandos recebidos."""
        msg_type = message['type']
        payload = message['payload']
        
        if msg_type == MessageType.PING:
            # Responde com PONG
            pong_msg = MessageProtocol.create_message(MessageType.PONG, {})
            await self.ble_comm.send_data(address, pong_msg)
            
        elif msg_type == MessageType.STATUS_REQUEST:
            # Envia status atual
            status = self.get_system_status()
            response = MessageProtocol.create_message(MessageType.STATUS_RESPONSE, status)
            await self.ble_comm.send_data(address, response)
            
        elif msg_type == MessageType.CONFIG_SET:
            # Aplica nova configuração
            try:
                new_config = SensorConfiguration(**payload)
                success = await self.configure_sensor(new_config)
                
                response_payload = {'success': success, 'config': payload}
                response = MessageProtocol.create_message(MessageType.CONFIG_RESPONSE, response_payload)
                await self.ble_comm.send_data(address, response)
                
            except Exception as e:
                error_msg = MessageProtocol.create_message(
                    MessageType.ERROR, 
                    {'error': str(e)}
                )
                await self.ble_comm.send_data(address, error_msg)
    
    # Callbacks externos
    def add_data_callback(self, callback: Callable) -> None:
        """Adiciona callback para dados."""
        self._data_callbacks.append(callback)
    
    def add_status_callback(self, callback: Callable) -> None:
        """Adiciona callback para status."""
        self._status_callbacks.append(callback)
    
    async def _notify_data_callbacks(self, reading: StrainReading) -> None:
        """Notifica callbacks de dados."""
        for callback in self._data_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(reading)
                else:
                    callback(reading)
            except Exception as e:
                print(f"Erro no callback de dados: {e}")
    
    async def _notify_status_callbacks(self, sensor_info: SensorInfo) -> None:
        """Notifica callbacks de status."""
        for callback in self._status_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(sensor_info)
                else:
                    callback(sensor_info)
            except Exception as e:
                print(f"Erro no callback de status: {e}")
    
    # Métodos de informação
    def get_system_status(self) -> Dict[str, Any]:
        """Retorna status completo do sistema."""
        esp32_status = self.esp32.get_status()
        ble_status = {
            'state': self.ble_comm.state.value,
            'connected_devices': len(self.ble_comm.connected_devices)
        }
        
        return {
            'simulator': {
                'running': self._is_running,
                'current_scenario': self._current_scenario,
                'simulation_speed': self.config.simulation_speed
            },
            'esp32': esp32_status,
            'ble': ble_status,
            'data_history_size': len(self._data_history)
        }
    
    def get_data_history(self, max_items: Optional[int] = None) -> List[StrainReading]:
        """
        Retorna histórico de dados.
        
        Args:
            max_items: Número máximo de itens
            
        Returns:
            Lista de leituras históricas
        """
        history = self._data_history.copy()
        
        if max_items and len(history) > max_items:
            history = history[-max_items:]
        
        return history
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas dos dados."""
        if not self._data_history:
            return {'total_readings': 0}
        
        strain_values = [r.strain_value for r in self._data_history]
        
        return {
            'total_readings': len(self._data_history),
            'latest_reading': self._data_history[-1].timestamp.isoformat(),
            'strain_stats': {
                'min': min(strain_values),
                'max': max(strain_values),
                'avg': sum(strain_values) / len(strain_values),
                'current': strain_values[-1]
            },
            'battery_level': self.esp32._battery_level,
            'current_scenario': self._current_scenario
        }
