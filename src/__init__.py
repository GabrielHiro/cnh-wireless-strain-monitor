"""Módulo principal do sistema DAQ."""

from .core import *
from .communication import *
from .data import *

__version__ = "1.0.0"
__author__ = "Gabriel Hiro Furukawa, Rafael Perassi Zanchetta"
__description__ = "Sistema DAQ Autônomo e Sem Fio para Análise de Fadiga Estrutural"

__all__ = [
    # Core
    'SensorStatus',
    'CommunicationProtocol',
    'StrainReading',
    'SensorConfiguration', 
    'SensorInfo',
    'DataPacket',
    'config',
    
    # Communication
    'BLESimulator',
    'MessageProtocol',
    'MessageType',
    
    # Data
    'DataManager'
]
