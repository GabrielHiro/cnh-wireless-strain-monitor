"""
Simulador de comunicação BLE (Bluetooth Low Energy).
Simula descoberta, conexão e troca de dados via BLE.
"""

import asyncio
import random
import time
import uuid
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum

from .protocol import MessageProtocol, MessageType, ProtocolError


class BLEDeviceType(Enum):
    """Tipos de dispositivos BLE."""
    UNKNOWN = "unknown"
    DAQ_SENSOR = "daq_sensor"
    SMARTPHONE = "smartphone"
    COMPUTER = "computer"


@dataclass
class BLEDevice:
    """Representa um dispositivo BLE descoberto."""
    address: str
    name: str
    device_type: BLEDeviceType = BLEDeviceType.UNKNOWN
    rssi: int = -50  # Signal strength in dBm
    manufacturer_data: Optional[bytes] = None
    service_uuids: List[str] = None
    
    def __post_init__(self):
        if self.service_uuids is None:
            self.service_uuids = []


class BLEConnectionState(Enum):
    """Estados de conexão BLE."""
    DISCONNECTED = "disconnected"
    SCANNING = "scanning"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class BLESimulator:
    """
    Simulador de comunicação Bluetooth Low Energy.
    
    Simula o comportamento de um adaptador BLE incluindo:
    - Descoberta de dispositivos
    - Conexão e desconexão
    - Troca de dados via características
    - Gerenciamento de múltiplas conexões
    """
    
    def __init__(self):
        """Inicializa o simulador BLE."""
        self._state = BLEConnectionState.DISCONNECTED
        self._discovered_devices: Dict[str, BLEDevice] = {}
        self._connected_devices: Dict[str, BLEDevice] = {}
        self._scan_callbacks: List[Callable] = []
        self._connection_callbacks: List[Callable] = []
        self._data_callbacks: List[Callable] = []
        
        # Simulação de dispositivos DAQ próximos
        self._simulate_nearby_devices()
        
        # Tasks de simulação
        self._scan_task: Optional[asyncio.Task] = None
        self._connection_tasks: Dict[str, asyncio.Task] = {}
        
    def _simulate_nearby_devices(self) -> None:
        """Simula dispositivos DAQ próximos."""
        # Simula 2-3 sensores DAQ próximos
        for i in range(random.randint(2, 3)):
            device_id = f"DAQ_{uuid.uuid4().hex[:6].upper()}"
            address = self._generate_mac_address()
            
            device = BLEDevice(
                address=address,
                name=f"DAQ Sensor {i+1}",
                device_type=BLEDeviceType.DAQ_SENSOR,
                rssi=random.randint(-80, -30),
                service_uuids=["12345678-1234-1234-1234-123456789abc"],
                manufacturer_data=b"CNH_DAQ"
            )
            
            self._discovered_devices[address] = device
    
    def _generate_mac_address(self) -> str:
        """Gera um endereço MAC simulado."""
        return ":".join([
            f"{random.randint(0, 255):02X}" for _ in range(6)
        ])
    
    async def start_scan(self, timeout: float = 10.0) -> None:
        """
        Inicia varredura por dispositivos BLE.
        
        Args:
            timeout: Tempo limite em segundos
        """
        if self._state == BLEConnectionState.SCANNING:
            return
        
        self._state = BLEConnectionState.SCANNING
        self._scan_task = asyncio.create_task(self._scan_loop(timeout))
    
    async def stop_scan(self) -> None:
        """Para a varredura de dispositivos."""
        if self._scan_task and not self._scan_task.done():
            self._scan_task.cancel()
            try:
                await self._scan_task
            except asyncio.CancelledError:
                pass
        
        if self._state == BLEConnectionState.SCANNING:
            self._state = BLEConnectionState.DISCONNECTED
    
    async def _scan_loop(self, timeout: float) -> None:
        """Loop de varredura de dispositivos."""
        start_time = time.time()
        
        try:
            while time.time() - start_time < timeout:
                # Simula descoberta de novos dispositivos periodicamente
                if random.random() < 0.3:  # 30% chance por iteração
                    await self._simulate_device_discovery()
                
                # Simula mudanças no RSSI dos dispositivos conhecidos
                await self._update_device_rssi()
                
                await asyncio.sleep(0.5)  # Intervalo de varredura
                
        except asyncio.CancelledError:
            pass
        finally:
            if self._state == BLEConnectionState.SCANNING:
                self._state = BLEConnectionState.DISCONNECTED
    
    async def _simulate_device_discovery(self) -> None:
        """Simula descoberta de um novo dispositivo."""
        # Ocasionalmente "descobre" dispositivos já conhecidos
        # (simula dispositivos entrando/saindo de alcance)
        
        for address, device in self._discovered_devices.items():
            # Simula dispositivo aparecendo/desaparecendo
            if random.random() < 0.1:  # 10% chance
                # Notifica callbacks de descoberta
                for callback in self._scan_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(device)
                        else:
                            callback(device)
                    except Exception as e:
                        print(f"Erro no callback de scan: {e}")
    
    async def _update_device_rssi(self) -> None:
        """Atualiza RSSI dos dispositivos (simula movimento)."""
        for device in self._discovered_devices.values():
            # Simula pequenas variações no RSSI
            variation = random.randint(-5, 5)
            device.rssi = max(-100, min(-20, device.rssi + variation))
    
    async def connect(self, address: str, timeout: float = 30.0) -> bool:
        """
        Conecta a um dispositivo BLE.
        
        Args:
            address: Endereço MAC do dispositivo
            timeout: Tempo limite para conexão
            
        Returns:
            True se conectado com sucesso
        """
        if address in self._connected_devices:
            return True
        
        device = self._discovered_devices.get(address)
        if not device:
            return False
        
        # Inicia processo de conexão
        self._state = BLEConnectionState.CONNECTING
        
        try:
            # Simula tempo de conexão
            connection_time = random.uniform(1.0, 3.0)
            await asyncio.sleep(connection_time)
            
            # Simula falha ocasional (5% de chance)
            if random.random() < 0.05:
                raise Exception("Falha simulada na conexão")
            
            # Conexão bem-sucedida
            self._connected_devices[address] = device
            self._state = BLEConnectionState.CONNECTED
            
            # Inicia task de manutenção da conexão
            self._connection_tasks[address] = asyncio.create_task(
                self._maintain_connection(address)
            )
            
            # Notifica callbacks
            await self._notify_connection_callbacks(device, True)
            
            return True
            
        except Exception as e:
            self._state = BLEConnectionState.ERROR
            print(f"Erro na conexão BLE: {e}")
            return False
    
    async def disconnect(self, address: str) -> None:
        """
        Desconecta de um dispositivo BLE.
        
        Args:
            address: Endereço MAC do dispositivo
        """
        if address not in self._connected_devices:
            return
        
        device = self._connected_devices[address]
        
        # Para task de manutenção
        if address in self._connection_tasks:
            self._connection_tasks[address].cancel()
            try:
                await self._connection_tasks[address]
            except asyncio.CancelledError:
                pass
            del self._connection_tasks[address]
        
        # Remove da lista de conectados
        del self._connected_devices[address]
        
        # Atualiza estado se não há mais conexões
        if not self._connected_devices:
            self._state = BLEConnectionState.DISCONNECTED
        
        # Notifica callbacks
        await self._notify_connection_callbacks(device, False)
    
    async def _maintain_connection(self, address: str) -> None:
        """
        Mantém a conexão com um dispositivo.
        
        Args:
            address: Endereço do dispositivo
        """
        try:
            while address in self._connected_devices:
                # Simula perda ocasional de conexão (1% chance)
                if random.random() < 0.01:
                    print(f"Conexão perdida com {address}")
                    await self.disconnect(address)
                    break
                
                # Simula dados chegando do dispositivo
                if random.random() < 0.8:  # 80% chance de ter dados
                    await self._simulate_incoming_data(address)
                
                await asyncio.sleep(1.0)  # Verifica a cada segundo
                
        except asyncio.CancelledError:
            pass
    
    async def _simulate_incoming_data(self, address: str) -> None:
        """
        Simula dados chegando de um dispositivo conectado.
        
        Args:
            address: Endereço do dispositivo
        """
        device = self._connected_devices.get(address)
        if not device:
            return
        
        # Simula diferentes tipos de mensagens
        message_types = [
            MessageType.DATA_SINGLE,
            MessageType.DATA_BATCH,
            MessageType.STATUS_RESPONSE
        ]
        
        msg_type = random.choice(message_types)
        
        # Cria payload simulado baseado no tipo
        if msg_type == MessageType.DATA_SINGLE:
            payload = {
                'timestamp': time.time(),
                'strain_value': random.uniform(-100, 100),
                'raw_adc_value': random.randint(-8388608, 8388607),
                'sensor_id': device.address,
                'battery_level': random.randint(20, 100),
                'temperature': random.uniform(20, 40)
            }
        elif msg_type == MessageType.STATUS_RESPONSE:
            payload = {
                'device_id': device.address,
                'battery_level': random.randint(20, 100),
                'wifi_status': 'disconnected',
                'ble_status': 'connected',
                'uptime': random.randint(100, 10000)
            }
        else:  # DATA_BATCH
            payload = {
                'readings': [
                    {
                        'timestamp': time.time() - i,
                        'strain_value': random.uniform(-100, 100),
                        'raw_adc_value': random.randint(-8388608, 8388607),
                        'battery_level': random.randint(20, 100),
                        'temperature': random.uniform(20, 40)
                    }
                    for i in range(5)  # Batch de 5 leituras
                ]
            }
        
        # Cria mensagem usando protocolo
        try:
            message_data = MessageProtocol.create_message(msg_type, payload)
            
            # Notifica callbacks de dados
            for callback in self._data_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(address, message_data)
                    else:
                        callback(address, message_data)
                except Exception as e:
                    print(f"Erro no callback de dados: {e}")
                    
        except Exception as e:
            print(f"Erro ao criar mensagem simulada: {e}")
    
    async def send_data(self, address: str, data: bytes) -> bool:
        """
        Envia dados para um dispositivo conectado.
        
        Args:
            address: Endereço do dispositivo
            data: Dados a serem enviados
            
        Returns:
            True se enviado com sucesso
        """
        if address not in self._connected_devices:
            return False
        
        try:
            # Simula latência de transmissão
            await asyncio.sleep(random.uniform(0.01, 0.05))
            
            # Simula falha ocasional (2% chance)
            if random.random() < 0.02:
                raise Exception("Falha simulada na transmissão")
            
            # Simula processamento da mensagem pelo dispositivo
            await self._process_sent_message(address, data)
            
            return True
            
        except Exception as e:
            print(f"Erro ao enviar dados BLE: {e}")
            return False
    
    async def _process_sent_message(self, address: str, data: bytes) -> None:
        """
        Processa mensagem enviada (simula resposta do dispositivo).
        
        Args:
            address: Endereço do dispositivo
            data: Dados enviados
        """
        try:
            message = MessageProtocol.parse_message(data)
            
            # Simula resposta baseada no tipo de mensagem
            if message['type'] == MessageType.PING:
                # Responde com PONG
                response = MessageProtocol.create_message(MessageType.PONG, {})
                await asyncio.sleep(0.01)  # Simula tempo de resposta
                await self._simulate_device_response(address, response)
                
            elif message['type'] == MessageType.STATUS_REQUEST:
                # Responde com status
                status_payload = {
                    'device_id': address,
                    'battery_level': random.randint(20, 100),
                    'temperature': random.uniform(20, 40),
                    'wifi_status': 'disconnected',
                    'ble_status': 'connected'
                }
                response = MessageProtocol.create_message(
                    MessageType.STATUS_RESPONSE, 
                    status_payload
                )
                await self._simulate_device_response(address, response)
                
        except ProtocolError as e:
            print(f"Erro no protocolo: {e}")
    
    async def _simulate_device_response(self, address: str, response: bytes) -> None:
        """
        Simula resposta do dispositivo.
        
        Args:
            address: Endereço do dispositivo
            response: Dados de resposta
        """
        # Notifica callbacks como se fosse dados recebidos
        for callback in self._data_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(address, response)
                else:
                    callback(address, response)
            except Exception as e:
                print(f"Erro no callback de resposta: {e}")
    
    async def _notify_connection_callbacks(self, device: BLEDevice, connected: bool) -> None:
        """Notifica callbacks de conexão."""
        for callback in self._connection_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(device, connected)
                else:
                    callback(device, connected)
            except Exception as e:
                print(f"Erro no callback de conexão: {e}")
    
    # Métodos para registro de callbacks
    def add_scan_callback(self, callback: Callable) -> None:
        """Adiciona callback para descoberta de dispositivos."""
        self._scan_callbacks.append(callback)
    
    def add_connection_callback(self, callback: Callable) -> None:
        """Adiciona callback para eventos de conexão."""
        self._connection_callbacks.append(callback)
    
    def add_data_callback(self, callback: Callable) -> None:
        """Adiciona callback para dados recebidos."""
        self._data_callbacks.append(callback)
    
    # Propriedades de estado
    @property
    def state(self) -> BLEConnectionState:
        """Estado atual da conexão BLE."""
        return self._state
    
    @property
    def discovered_devices(self) -> Dict[str, BLEDevice]:
        """Dispositivos descobertos."""
        return self._discovered_devices.copy()
    
    @property
    def connected_devices(self) -> Dict[str, BLEDevice]:
        """Dispositivos conectados."""
        return self._connected_devices.copy()
    
    def is_connected(self, address: str) -> bool:
        """Verifica se está conectado a um dispositivo específico."""
        return address in self._connected_devices
    
    def get_device_rssi(self, address: str) -> Optional[int]:
        """Retorna RSSI de um dispositivo."""
        device = self._discovered_devices.get(address)
        return device.rssi if device else None
