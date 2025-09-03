"""
Módulo de gerenciamento de dados do sistema DAQ.

Este módulo é responsável por:
- Buffer em memória para dados em tempo real
- Persistência em banco de dados SQLite
- Exportação de dados em vários formatos
- API otimizada para visualização tipo osciloscópio
- Streaming de dados em tempo real

Classes principais:
- DataManager: Gerenciador principal de dados
- OscilloscopeAPI: API para visualização em tempo real
- WebSocketStreamer: Streaming via WebSocket
"""

from .data_manager import (
    DataManager,
    DataBuffer,
    DatabaseManager,
    DataExporter,
    OscilloscopeStreamer,
    DataStorageError
)

from .oscilloscope_api import (
    OscilloscopeAPI,
    OscilloscopeConfig,
    WebSocketStreamer
)

__all__ = [
    # Gerenciamento principal
    'DataManager',
    'DataStorageError',
    
    # Componentes internos
    'DataBuffer',
    'DatabaseManager', 
    'DataExporter',
    'OscilloscopeStreamer',
    
    # API de osciloscópio
    'OscilloscopeAPI',
    'OscilloscopeConfig',
    'WebSocketStreamer',
]
