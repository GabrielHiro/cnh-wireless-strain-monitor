"""
Modelos de dados para o sistema DAQ.
Define as estruturas de dados utilizadas em todo o sistema.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
import uuid


class SensorStatus(Enum):
    """Estados possíveis do sensor."""
    OFFLINE = "offline"
    CONNECTING = "connecting" 
    ONLINE = "online"
    ERROR = "error"
    LOW_BATTERY = "low_battery"


class CommunicationProtocol(Enum):
    """Protocolos de comunicação suportados."""
    BLE = "bluetooth_low_energy"
    WIFI = "wifi"


@dataclass
class StrainReading:
    """
    Representa uma leitura de deformação do strain gauge.
    
    Attributes:
        timestamp: Momento da leitura
        strain_value: Valor da deformação em microstrains (µε)
        raw_adc_value: Valor bruto do ADC (HX711)
        sensor_id: Identificador único do sensor
        battery_level: Nível da bateria (0-100%)
        temperature: Temperatura do sensor (°C)
        checksum: Verificação de integridade dos dados
    """
    timestamp: datetime
    strain_value: float  # microstrains (µε)
    raw_adc_value: int
    sensor_id: str
    battery_level: int  # 0-100%
    temperature: float  # °C
    checksum: Optional[str] = None
    
    def __post_init__(self):
        """Calcula checksum se não fornecido."""
        if self.checksum is None:
            self.checksum = self._calculate_checksum()
    
    def _calculate_checksum(self) -> str:
        """Calcula checksum simples para verificação de integridade."""
        data_str = f"{self.timestamp.isoformat()}{self.strain_value}{self.raw_adc_value}{self.battery_level}"
        return str(hash(data_str))
    
    def is_valid(self) -> bool:
        """Verifica se a leitura é válida."""
        return (
            self.checksum == self._calculate_checksum() and
            0 <= self.battery_level <= 100 and
            -40 <= self.temperature <= 85  # Faixa operacional típica
        )


@dataclass 
class SensorConfiguration:
    """
    Configuração do nó sensor.
    
    Attributes:
        sensor_id: Identificador único do sensor
        sampling_rate_ms: Taxa de amostragem em milissegundos
        transmission_interval_s: Intervalo de transmissão em segundos
        calibration_factor: Fator de calibração do strain gauge
        offset: Offset para correção de zero
        deep_sleep_enabled: Habilita modo deep sleep
        wifi_ssid: SSID da rede WiFi (opcional)
        wifi_password: Senha da rede WiFi (opcional)
    """
    sensor_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    sampling_rate_ms: int = 100
    transmission_interval_s: int = 1
    calibration_factor: float = 1.0
    offset: float = 0.0
    deep_sleep_enabled: bool = True
    wifi_ssid: Optional[str] = None
    wifi_password: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário para serialização."""
        return {
            'sensor_id': self.sensor_id,
            'sampling_rate_ms': self.sampling_rate_ms,
            'transmission_interval_s': self.transmission_interval_s,
            'calibration_factor': self.calibration_factor,
            'offset': self.offset,
            'deep_sleep_enabled': self.deep_sleep_enabled,
            'wifi_ssid': self.wifi_ssid,
            'wifi_password': self.wifi_password
        }


@dataclass
class SensorInfo:
    """
    Informações sobre um sensor conectado.
    
    Attributes:
        sensor_id: Identificador único
        name: Nome amigável do sensor
        status: Status atual do sensor
        last_seen: Última comunicação
        protocol: Protocolo de comunicação usado
        signal_strength: Força do sinal (-100 a 0 dBm)
        firmware_version: Versão do firmware
        hardware_version: Versão do hardware
    """
    sensor_id: str
    name: str
    status: SensorStatus = SensorStatus.OFFLINE
    last_seen: Optional[datetime] = None
    protocol: Optional[CommunicationProtocol] = None
    signal_strength: Optional[int] = None  # dBm
    firmware_version: Optional[str] = None
    hardware_version: Optional[str] = None
    
    def is_online(self) -> bool:
        """Verifica se o sensor está online."""
        return self.status == SensorStatus.ONLINE
    
    def time_since_last_seen(self) -> Optional[float]:
        """Retorna tempo em segundos desde a última comunicação."""
        if self.last_seen is None:
            return None
        return (datetime.now() - self.last_seen).total_seconds()


@dataclass
class DataPacket:
    """
    Pacote de dados transmitido pelo sensor.
    
    Attributes:
        packet_id: Identificador único do pacote
        sensor_id: ID do sensor que enviou
        readings: Lista de leituras no pacote
        timestamp: Momento da criação do pacote
        sequence_number: Número sequencial para ordenação
        total_packets: Total de pacotes na sequência (para buffer)
    """
    packet_id: str
    sensor_id: str
    readings: list[StrainReading]
    timestamp: datetime
    sequence_number: int = 0
    total_packets: int = 1
    
    def __post_init__(self):
        """Gera ID do pacote se não fornecido."""
        if not self.packet_id:
            self.packet_id = str(uuid.uuid4())[:8]
    
    def is_complete_sequence(self) -> bool:
        """Verifica se é o último pacote da sequência."""
        return self.sequence_number >= self.total_packets - 1
    
    def get_data_size(self) -> int:
        """Retorna tamanho estimado dos dados em bytes."""
        # Estimativa baseada na serialização dos dados
        return len(self.readings) * 32  # ~32 bytes por leitura
