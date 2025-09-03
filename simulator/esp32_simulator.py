"""
Simulador do ESP32 - Microcontrolador com conectividade WiFi e BLE.
Simula o comportamento do ESP32 incluindo modos de energia e comunicação.
"""

import asyncio
import random
import time
import uuid
from typing import Optional, Dict, Any, Callable
from enum import Enum
from dataclasses import dataclass

from .hx711_simulator import HX711Simulator


class ESP32PowerMode(Enum):
    """Modos de energia do ESP32."""
    ACTIVE = "active"
    LIGHT_SLEEP = "light_sleep"
    DEEP_SLEEP = "deep_sleep"
    HIBERNATION = "hibernation"


class WiFiStatus(Enum):
    """Status da conexão WiFi."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class BLEStatus(Enum):
    """Status do Bluetooth Low Energy."""
    DISABLED = "disabled"
    ADVERTISING = "advertising"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class ESP32Config:
    """Configuração do simulador ESP32."""
    device_name: str = "DAQ_Sensor"
    cpu_frequency_mhz: int = 240
    wifi_power_dbm: float = 20.0
    ble_power_dbm: float = 0.0
    deep_sleep_enabled: bool = True
    
    # Consumo de energia (mA)
    current_active: float = 240.0
    current_wifi_tx: float = 170.0
    current_ble_tx: float = 12.0
    current_light_sleep: float = 0.8
    current_deep_sleep: float = 0.005


class ESP32Simulator:
    """
    Simulador do microcontrolador ESP32.
    
    Simula funcionalidades principais incluindo:
    - Gerenciamento de energia e modos de sleep
    - Conectividade WiFi e BLE
    - Interface com sensores (HX711)
    - Processamento e buffering de dados
    """
    
    def __init__(self, config: Optional[ESP32Config] = None):
        """
        Inicializa o simulador ESP32.
        
        Args:
            config: Configuração do simulador
        """
        self.config = config or ESP32Config()
        self.device_id = str(uuid.uuid4())[:8]
        
        # Estado do sistema
        self._power_mode = ESP32PowerMode.ACTIVE
        self._wifi_status = WiFiStatus.DISCONNECTED
        self._ble_status = BLEStatus.DISABLED
        self._is_running = False
        self._boot_time = time.time()
        
        # Simulador do HX711
        self.hx711 = HX711Simulator()
        
        # Bateria simulada
        self._battery_capacity_mah = 2000.0  # Capacidade típica de bateria LiPo
        self._battery_level = 100.0  # Percentual inicial
        self._battery_voltage = 4.2  # Voltagem inicial (LiPo carregada)
        
        # Buffer de dados
        self._data_buffer = []
        self._max_buffer_size = 1000
        
        # Conectividade
        self._wifi_ssid = None
        self._wifi_password = None
        self._connected_clients = set()
        
        # Callbacks para eventos
        self._data_callbacks = []
        self._status_callbacks = []
        
        # Task de simulação
        self._simulation_task = None
        
    async def start(self) -> None:
        """Inicia a simulação do ESP32."""
        if self._is_running:
            return
            
        self._is_running = True
        self._boot_time = time.time()
        
        # Inicia task de simulação
        self._simulation_task = asyncio.create_task(self._simulation_loop())
        
    async def stop(self) -> None:
        """Para a simulação do ESP32."""
        self._is_running = False
        
        if self._simulation_task:
            self._simulation_task.cancel()
            try:
                await self._simulation_task
            except asyncio.CancelledError:
                pass
    
    async def _simulation_loop(self) -> None:
        """Loop principal de simulação."""
        while self._is_running:
            try:
                # Atualiza bateria
                self._update_battery()
                
                # Simula leitura de sensor se não estiver em deep sleep
                if self._power_mode != ESP32PowerMode.DEEP_SLEEP:
                    await self._simulate_sensor_reading()
                
                # Simula transmissão de dados
                if self._data_buffer and self._is_connected():
                    await self._transmit_buffered_data()
                
                # Notifica callbacks de status
                await self._notify_status_callbacks()
                
                # Simula deep sleep se habilitado e sem atividade
                if (self.config.deep_sleep_enabled and 
                    not self._is_connected() and
                    len(self._data_buffer) == 0):
                    await self._enter_deep_sleep()
                
                # Intervalo de simulação
                await asyncio.sleep(0.1)  # 100ms
                
            except Exception as e:
                print(f"Erro na simulação ESP32: {e}")
                await asyncio.sleep(1.0)
    
    def _update_battery(self) -> None:
        """Atualiza o nível da bateria baseado no consumo atual."""
        if self._battery_level <= 0:
            return
            
        # Calcula consumo atual baseado no modo de operação
        current_consumption = self._get_current_consumption()
        
        # Calcula descarga (assumindo 1 segundo)
        discharge_rate = (current_consumption / self._battery_capacity_mah) * 100
        
        # Aplica descarga
        self._battery_level = max(0, self._battery_level - discharge_rate / 3600)  # Por hora
        
        # Atualiza voltagem baseada no nível da bateria
        # LiPo: 4.2V (100%) -> 3.0V (0%)
        self._battery_voltage = 3.0 + (self._battery_level / 100.0) * 1.2
    
    def _get_current_consumption(self) -> float:
        """Calcula consumo atual de energia em mA."""
        base_current = {
            ESP32PowerMode.ACTIVE: self.config.current_active,
            ESP32PowerMode.LIGHT_SLEEP: self.config.current_light_sleep,
            ESP32PowerMode.DEEP_SLEEP: self.config.current_deep_sleep,
            ESP32PowerMode.HIBERNATION: 0.002
        }.get(self._power_mode, self.config.current_active)
        
        # Adiciona consumo de comunicação
        if self._wifi_status == WiFiStatus.CONNECTED:
            base_current += self.config.current_wifi_tx
        
        if self._ble_status == BLEStatus.CONNECTED:
            base_current += self.config.current_ble_tx
            
        return base_current
    
    async def _simulate_sensor_reading(self) -> None:
        """Simula leitura do sensor HX711."""
        try:
            # Simula carga dinâmica (vibração de máquina agrícola)
            self.hx711.simulate_dynamic_load()
            
            # Lê valor do sensor
            strain_value = self.hx711.read_strain_microstrains()
            raw_adc = self.hx711.read_adc_raw()
            
            # Cria pacote de dados
            data_point = {
                'timestamp': time.time(),
                'strain_value': strain_value,
                'raw_adc_value': raw_adc,
                'sensor_id': self.device_id,
                'battery_level': int(self._battery_level),
                'temperature': self.hx711._temperature,
                'device_status': self._power_mode.value
            }
            
            # Adiciona ao buffer
            if len(self._data_buffer) < self._max_buffer_size:
                self._data_buffer.append(data_point)
            else:
                # Remove dados mais antigos se buffer cheio
                self._data_buffer.pop(0)
                self._data_buffer.append(data_point)
            
            # Notifica callbacks
            await self._notify_data_callbacks(data_point)
            
        except Exception as e:
            print(f"Erro na leitura do sensor: {e}")
    
    async def _transmit_buffered_data(self) -> None:
        """Simula transmissão dos dados em buffer."""
        if not self._data_buffer:
            return
            
        # Simula latência de transmissão
        await asyncio.sleep(0.01)  # 10ms
        
        # Transmite alguns dados do buffer
        batch_size = min(10, len(self._data_buffer))
        transmitted_data = self._data_buffer[:batch_size]
        self._data_buffer = self._data_buffer[batch_size:]
        
        # Simula envio para clientes conectados
        for callback in self._data_callbacks:
            try:
                for data_point in transmitted_data:
                    await callback(data_point)
            except Exception as e:
                print(f"Erro no callback de dados: {e}")
    
    async def _enter_deep_sleep(self) -> None:
        """Simula entrada em modo deep sleep."""
        self._power_mode = ESP32PowerMode.DEEP_SLEEP
        
        # Deep sleep por período configurável (simula 1 segundo)
        await asyncio.sleep(1.0)
        
        # Acorda do deep sleep
        self._power_mode = ESP32PowerMode.ACTIVE
    
    def _is_connected(self) -> bool:
        """Verifica se há conexões ativas."""
        return (self._wifi_status == WiFiStatus.CONNECTED or 
                self._ble_status == BLEStatus.CONNECTED)
    
    # Métodos de conectividade WiFi
    async def wifi_connect(self, ssid: str, password: str) -> bool:
        """
        Conecta ao WiFi.
        
        Args:
            ssid: Nome da rede WiFi
            password: Senha da rede
            
        Returns:
            True se conectado com sucesso
        """
        self._wifi_status = WiFiStatus.CONNECTING
        self._wifi_ssid = ssid
        self._wifi_password = password
        
        # Simula tempo de conexão
        await asyncio.sleep(2.0)
        
        # Simula sucesso/falha (95% de sucesso)
        if random.random() < 0.95:
            self._wifi_status = WiFiStatus.CONNECTED
            return True
        else:
            self._wifi_status = WiFiStatus.ERROR
            return False
    
    def wifi_disconnect(self) -> None:
        """Desconecta do WiFi."""
        self._wifi_status = WiFiStatus.DISCONNECTED
        self._wifi_ssid = None
        self._wifi_password = None
    
    # Métodos de conectividade BLE
    async def ble_start_advertising(self) -> None:
        """Inicia advertising BLE."""
        self._ble_status = BLEStatus.ADVERTISING
        
    def ble_stop_advertising(self) -> None:
        """Para advertising BLE."""
        self._ble_status = BLEStatus.DISABLED
    
    async def ble_accept_connection(self, client_id: str) -> bool:
        """
        Aceita conexão BLE de um cliente.
        
        Args:
            client_id: ID do cliente
            
        Returns:
            True se conexão aceita
        """
        self._connected_clients.add(client_id)
        self._ble_status = BLEStatus.CONNECTED
        return True
    
    def ble_disconnect_client(self, client_id: str) -> None:
        """
        Desconecta cliente BLE.
        
        Args:
            client_id: ID do cliente
        """
        self._connected_clients.discard(client_id)
        if not self._connected_clients:
            self._ble_status = BLEStatus.ADVERTISING
    
    # Métodos de configuração
    def configure_sensor(self, config: Dict[str, Any]) -> bool:
        """
        Configura parâmetros do sensor.
        
        Args:
            config: Dicionário com configurações
            
        Returns:
            True se configuração aplicada com sucesso
        """
        try:
            if 'calibration_factor' in config:
                self.hx711.set_calibration_factor(config['calibration_factor'])
            
            if 'temperature' in config:
                self.hx711.set_temperature(config['temperature'])
                
            return True
        except Exception as e:
            print(f"Erro na configuração: {e}")
            return False
    
    # Callbacks e eventos
    def add_data_callback(self, callback: Callable) -> None:
        """Adiciona callback para dados."""
        self._data_callbacks.append(callback)
    
    def add_status_callback(self, callback: Callable) -> None:
        """Adiciona callback para status."""
        self._status_callbacks.append(callback)
    
    async def _notify_data_callbacks(self, data_point: Dict[str, Any]) -> None:
        """Notifica callbacks de dados."""
        for callback in self._data_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data_point)
                else:
                    callback(data_point)
            except Exception as e:
                print(f"Erro no callback: {e}")
    
    async def _notify_status_callbacks(self) -> None:
        """Notifica callbacks de status."""
        status = self.get_status()
        for callback in self._status_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(status)
                else:
                    callback(status)
            except Exception as e:
                print(f"Erro no callback de status: {e}")
    
    # Métodos de informação
    def get_status(self) -> Dict[str, Any]:
        """
        Retorna status completo do dispositivo.
        
        Returns:
            Dicionário com informações de status
        """
        return {
            'device_id': self.device_id,
            'device_name': self.config.device_name,
            'power_mode': self._power_mode.value,
            'wifi_status': self._wifi_status.value,
            'ble_status': self._ble_status.value,
            'battery_level': int(self._battery_level),
            'battery_voltage': round(self._battery_voltage, 2),
            'uptime_seconds': time.time() - self._boot_time,
            'buffer_size': len(self._data_buffer),
            'connected_clients': len(self._connected_clients),
            'hx711_status': self.hx711.get_status()
        }
    
    def get_device_info(self) -> Dict[str, Any]:
        """
        Retorna informações do dispositivo.
        
        Returns:
            Dicionário com informações do hardware/firmware
        """
        return {
            'device_id': self.device_id,
            'device_name': self.config.device_name,
            'hardware_version': "ESP32-WROOM-32",
            'firmware_version': "1.0.0",
            'cpu_frequency': self.config.cpu_frequency_mhz,
            'wifi_power': self.config.wifi_power_dbm,
            'ble_power': self.config.ble_power_dbm,
            'battery_capacity': self._battery_capacity_mah
        }
