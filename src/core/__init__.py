"""Módulo core do sistema DAQ."""

from .models import (
    SensorStatus,
    CommunicationProtocol,
    StrainReading,
    SensorConfiguration,
    SensorInfo,
    DataPacket
)

from .config import (
    config,
    SystemConfig,
    get_data_file_path,
    get_log_file_path,
    get_config_file_path,
    EXPORT_CONFIG,
    COMMUNICATION_CONFIG
)

__all__ = [
    # Models
    'SensorStatus',
    'CommunicationProtocol', 
    'StrainReading',
    'SensorConfiguration',
    'SensorInfo',
    'DataPacket',
    
    # Config
    'config',
    'SystemConfig',
    'get_data_file_path',
    'get_log_file_path', 
    'get_config_file_path',
    'EXPORT_CONFIG',
    'COMMUNICATION_CONFIG'
]
