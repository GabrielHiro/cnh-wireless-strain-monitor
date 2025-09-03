"""Módulo de comunicação do sistema DAQ."""

from .protocol import (
    MessageProtocol,
    MessageType,
    CompressionType,
    DataPacketEncoder,
    ConfigurationProtocol,
    StatusProtocol,
    ProtocolError,
    create_ping_message,
    create_pong_message,
    create_error_message
)

from .ble_simulator import (
    BLESimulator,
    BLEDevice,
    BLEDeviceType,
    BLEConnectionState
)

__all__ = [
    # Protocol
    'MessageProtocol',
    'MessageType',
    'CompressionType',
    'DataPacketEncoder',
    'ConfigurationProtocol',
    'StatusProtocol',
    'ProtocolError',
    'create_ping_message',
    'create_pong_message',
    'create_error_message',
    
    # BLE Simulator
    'BLESimulator',
    'BLEDevice',
    'BLEDeviceType',
    'BLEConnectionState'
]
