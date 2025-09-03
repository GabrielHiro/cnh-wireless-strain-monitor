"""
Configurações globais do sistema DAQ.
Centraliza todas as configurações e constantes do sistema.
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


# Configurações de arquivo e diretórios
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
CONFIG_DIR = PROJECT_ROOT / "config"

# Criar diretórios se não existirem
for directory in [DATA_DIR, LOGS_DIR, CONFIG_DIR]:
    directory.mkdir(exist_ok=True)


@dataclass
class SystemConfig:
    """Configurações globais do sistema."""
    
    # Comunicação BLE
    BLE_SERVICE_UUID: str = "12345678-1234-1234-1234-123456789abc"
    BLE_CHARACTERISTIC_UUID: str = "12345678-1234-1234-1234-123456789abd"
    BLE_SCAN_TIMEOUT: int = 10  # segundos
    BLE_CONNECTION_TIMEOUT: int = 30  # segundos
    
    # Comunicação WiFi
    WIFI_PORT: int = 8080
    WIFI_TIMEOUT: int = 5  # segundos
    
    # Armazenamento e buffer
    MAX_BUFFER_SIZE: int = 10000  # número máximo de leituras em buffer
    BUFFER_FLUSH_INTERVAL: int = 60  # segundos
    DATA_RETENTION_DAYS: int = 30  # dias para manter dados
    
    # Interface de usuário
    GUI_UPDATE_INTERVAL: int = 100  # milissegundos
    PLOT_MAX_POINTS: int = 1000  # pontos máximos no gráfico em tempo real
    
    # Sensor e calibração
    DEFAULT_SAMPLING_RATE: int = 100  # milissegundos
    DEFAULT_TRANSMISSION_INTERVAL: int = 1  # segundos
    STRAIN_GAUGE_SENSITIVITY: float = 2.0  # mV/V típico
    ADC_RESOLUTION: int = 24  # bits (HX711)
    ADC_MAX_VALUE: int = 2**23 - 1  # valor máximo do ADC
    
    # Limites operacionais
    MIN_BATTERY_LEVEL: int = 10  # %
    MAX_TEMPERATURE: float = 80.0  # °C
    MIN_TEMPERATURE: float = -20.0  # °C
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE_MAX_SIZE: int = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT: int = 5
    
    # Simulador
    SIMULATOR_NOISE_LEVEL: float = 0.1  # % de ruído nos dados simulados
    SIMULATOR_DRIFT_RATE: float = 0.001  # deriva por segundo
    SIMULATOR_BATTERY_DRAIN_RATE: float = 0.001  # % por segundo em operação
    
    # Osciloscópio/Visualização
    OSCILLOSCOPE_MAX_POINTS: int = 1000  # pontos máximos por sensor
    OSCILLOSCOPE_TIME_WINDOW: float = 10.0  # segundos
    OSCILLOSCOPE_UPDATE_RATE: float = 50.0  # Hz
    STREAMING_BUFFER_SIZE: int = 100  # pontos por update
    WEBSOCKET_HEARTBEAT: int = 30  # segundos


# Instância global da configuração
config = SystemConfig()


def get_data_file_path(filename: str) -> Path:
    """Retorna caminho completo para arquivo de dados."""
    return DATA_DIR / filename


def get_log_file_path(filename: str) -> Path:
    """Retorna caminho completo para arquivo de log."""
    return LOGS_DIR / filename


def get_config_file_path(filename: str) -> Path:
    """Retorna caminho completo para arquivo de configuração."""
    return CONFIG_DIR / filename


# Configurações específicas para exportação de dados
EXPORT_CONFIG = {
    'csv': {
        'separator': ',',
        'decimal': '.',
        'date_format': '%Y-%m-%d %H:%M:%S.%f',
        'encoding': 'utf-8'
    },
    'json': {
        'indent': 2,
        'ensure_ascii': False
    }
}

# Configurações de comunicação específicas
COMMUNICATION_CONFIG = {
    'retry_attempts': 3,
    'retry_delay': 1.0,  # segundos
    'connection_keepalive': 30,  # segundos
    'packet_timeout': 5.0,  # segundos
    'max_packet_size': 512  # bytes
}

# Configurações específicas do osciloscópio
OSCILLOSCOPE_CONFIG = {
    'default': {
        'time_window_seconds': 10.0,
        'max_points': 1000,
        'sample_rate_hz': 100.0,
        'auto_scale': True,
        'decimation_factor': 1
    },
    'high_performance': {
        'time_window_seconds': 5.0,
        'max_points': 500,
        'sample_rate_hz': 200.0,
        'auto_scale': True,
        'decimation_factor': 2
    },
    'long_term': {
        'time_window_seconds': 60.0,
        'max_points': 2000,
        'sample_rate_hz': 50.0,
        'auto_scale': True,
        'decimation_factor': 1
    }
}

# Configurações de streaming
STREAMING_CONFIG = {
    'websocket': {
        'heartbeat_interval': 30,
        'max_clients': 10,
        'buffer_size': 100,
        'compression': True
    },
    'api': {
        'rate_limit': 50,  # requests per second
        'cache_ttl': 1,    # segundos
        'max_points_per_request': 2000
    }
}
