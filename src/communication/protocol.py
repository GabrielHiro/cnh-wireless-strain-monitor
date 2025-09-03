"""
Protocolo de comunicação para o sistema DAQ.
Define o formato de dados e protocolos de comunicação BLE/WiFi.
"""

import json
import struct
import zlib
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from dataclasses import asdict

from ..core.models import StrainReading, DataPacket, SensorConfiguration


class ProtocolError(Exception):
    """Erro de protocolo de comunicação."""
    pass


class MessageType:
    """Tipos de mensagens do protocolo."""
    # Comandos de controle
    PING = 0x01
    PONG = 0x02
    CONNECT = 0x10
    DISCONNECT = 0x11
    
    # Configuração
    CONFIG_SET = 0x20
    CONFIG_GET = 0x21
    CONFIG_RESPONSE = 0x22
    
    # Dados
    DATA_SINGLE = 0x30
    DATA_BATCH = 0x31
    DATA_BUFFER = 0x32
    
    # Status
    STATUS_REQUEST = 0x40
    STATUS_RESPONSE = 0x41
    ERROR = 0x50


class CompressionType:
    """Tipos de compressão suportados."""
    NONE = 0x00
    ZLIB = 0x01


class MessageProtocol:
    """
    Protocolo de mensagens para comunicação DAQ.
    
    Formato do pacote:
    [HEADER][PAYLOAD]
    
    HEADER (8 bytes):
    - Magic Number (2 bytes): 0xDACC (Data Acquisition Communication)
    - Message Type (1 byte): Tipo da mensagem
    - Compression (1 byte): Tipo de compressão
    - Payload Length (2 bytes): Tamanho do payload
    - Checksum (2 bytes): CRC16 do payload
    
    PAYLOAD (variável):
    - Dados da mensagem (JSON ou binário)
    """
    
    MAGIC_NUMBER = 0xDACC
    HEADER_SIZE = 8
    MAX_PAYLOAD_SIZE = 8192  # 8KB máximo
    
    @classmethod
    def create_message(cls, 
                      message_type: int, 
                      payload: Union[Dict, bytes], 
                      compression: int = CompressionType.NONE) -> bytes:
        """
        Cria uma mensagem no formato do protocolo.
        
        Args:
            message_type: Tipo da mensagem
            payload: Dados da mensagem
            compression: Tipo de compressão
            
        Returns:
            Mensagem codificada em bytes
            
        Raises:
            ProtocolError: Se erro na criação da mensagem
        """
        try:
            # Serializa payload
            if isinstance(payload, dict):
                payload_bytes = json.dumps(payload, default=cls._json_serializer).encode('utf-8')
            elif isinstance(payload, bytes):
                payload_bytes = payload
            else:
                raise ProtocolError(f"Tipo de payload não suportado: {type(payload)}")
            
            # Aplica compressão se necessário
            if compression == CompressionType.ZLIB:
                payload_bytes = zlib.compress(payload_bytes)
            
            # Verifica tamanho
            if len(payload_bytes) > cls.MAX_PAYLOAD_SIZE:
                raise ProtocolError(f"Payload muito grande: {len(payload_bytes)} bytes")
            
            # Calcula checksum
            checksum = cls._calculate_crc16(payload_bytes)
            
            # Monta header
            header = struct.pack(
                '>HBBHH',
                cls.MAGIC_NUMBER,
                message_type,
                compression,
                len(payload_bytes),
                checksum
            )
            
            return header + payload_bytes
            
        except Exception as e:
            raise ProtocolError(f"Erro ao criar mensagem: {e}")
    
    @classmethod
    def parse_message(cls, data: bytes) -> Dict[str, Any]:
        """
        Analisa uma mensagem recebida.
        
        Args:
            data: Dados recebidos
            
        Returns:
            Dicionário com campos da mensagem
            
        Raises:
            ProtocolError: Se erro na análise
        """
        try:
            if len(data) < cls.HEADER_SIZE:
                raise ProtocolError("Dados insuficientes para header")
            
            # Extrai header
            magic, msg_type, compression, payload_len, checksum = struct.unpack(
                '>HBBHH', data[:cls.HEADER_SIZE]
            )
            
            # Verifica magic number
            if magic != cls.MAGIC_NUMBER:
                raise ProtocolError(f"Magic number inválido: {magic:04X}")
            
            # Verifica se temos payload completo
            if len(data) < cls.HEADER_SIZE + payload_len:
                raise ProtocolError("Dados insuficientes para payload")
            
            # Extrai payload
            payload_bytes = data[cls.HEADER_SIZE:cls.HEADER_SIZE + payload_len]
            
            # Verifica checksum
            if cls._calculate_crc16(payload_bytes) != checksum:
                raise ProtocolError("Checksum inválido")
            
            # Descomprime se necessário
            if compression == CompressionType.ZLIB:
                payload_bytes = zlib.decompress(payload_bytes)
            
            # Decodifica payload
            try:
                payload = json.loads(payload_bytes.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Se não é JSON válido, mantém como bytes
                payload = payload_bytes
            
            return {
                'type': msg_type,
                'compression': compression,
                'payload': payload,
                'checksum': checksum
            }
            
        except Exception as e:
            raise ProtocolError(f"Erro ao analisar mensagem: {e}")
    
    @staticmethod
    def _calculate_crc16(data: bytes) -> int:
        """
        Calcula CRC16 para verificação de integridade.
        
        Args:
            data: Dados para calcular CRC
            
        Returns:
            Valor CRC16
        """
        crc = 0xFFFF
        polynomial = 0x1021
        
        for byte in data:
            crc ^= (byte << 8)
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ polynomial
                else:
                    crc <<= 1
                crc &= 0xFFFF
        
        return crc
    
    @staticmethod
    def _json_serializer(obj) -> str:
        """Serializer customizado para JSON."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Objeto não serializável: {type(obj)}")


class DataPacketEncoder:
    """Codificador/decodificador especializado para pacotes de dados."""
    
    @staticmethod
    def encode_strain_reading(reading: StrainReading) -> Dict[str, Any]:
        """
        Codifica uma leitura de strain para transmissão.
        
        Args:
            reading: Leitura a ser codificada
            
        Returns:
            Dicionário codificado
        """
        return {
            'timestamp': reading.timestamp.isoformat(),
            'strain_value': reading.strain_value,
            'raw_adc_value': reading.raw_adc_value,
            'sensor_id': reading.sensor_id,
            'battery_level': reading.battery_level,
            'temperature': reading.temperature,
            'checksum': reading.checksum
        }
    
    @staticmethod
    def decode_strain_reading(data: Dict[str, Any]) -> StrainReading:
        """
        Decodifica uma leitura de strain recebida.
        
        Args:
            data: Dados recebidos
            
        Returns:
            Objeto StrainReading
        """
        return StrainReading(
            timestamp=datetime.fromisoformat(data['timestamp']),
            strain_value=float(data['strain_value']),
            raw_adc_value=int(data['raw_adc_value']),
            sensor_id=str(data['sensor_id']),
            battery_level=int(data['battery_level']),
            temperature=float(data['temperature']),
            checksum=data.get('checksum')
        )
    
    @staticmethod
    def encode_data_packet(packet: DataPacket) -> Dict[str, Any]:
        """
        Codifica um pacote de dados para transmissão.
        
        Args:
            packet: Pacote a ser codificado
            
        Returns:
            Dicionário codificado
        """
        return {
            'packet_id': packet.packet_id,
            'sensor_id': packet.sensor_id,
            'timestamp': packet.timestamp.isoformat(),
            'sequence_number': packet.sequence_number,
            'total_packets': packet.total_packets,
            'readings': [
                DataPacketEncoder.encode_strain_reading(reading) 
                for reading in packet.readings
            ]
        }
    
    @staticmethod
    def decode_data_packet(data: Dict[str, Any]) -> DataPacket:
        """
        Decodifica um pacote de dados recebido.
        
        Args:
            data: Dados recebidos
            
        Returns:
            Objeto DataPacket
        """
        readings = [
            DataPacketEncoder.decode_strain_reading(reading_data)
            for reading_data in data['readings']
        ]
        
        return DataPacket(
            packet_id=data['packet_id'],
            sensor_id=data['sensor_id'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            sequence_number=data['sequence_number'],
            total_packets=data['total_packets'],
            readings=readings
        )


class ConfigurationProtocol:
    """Protocolo para configuração de sensores."""
    
    @staticmethod
    def create_config_message(config: SensorConfiguration) -> bytes:
        """
        Cria mensagem de configuração.
        
        Args:
            config: Configuração a ser enviada
            
        Returns:
            Mensagem codificada
        """
        payload = asdict(config)
        return MessageProtocol.create_message(
            MessageType.CONFIG_SET,
            payload,
            CompressionType.NONE
        )
    
    @staticmethod
    def parse_config_response(data: bytes) -> SensorConfiguration:
        """
        Analisa resposta de configuração.
        
        Args:
            data: Dados recebidos
            
        Returns:
            Objeto SensorConfiguration
        """
        message = MessageProtocol.parse_message(data)
        
        if message['type'] != MessageType.CONFIG_RESPONSE:
            raise ProtocolError(f"Tipo de mensagem inesperado: {message['type']}")
        
        payload = message['payload']
        
        return SensorConfiguration(
            sensor_id=payload['sensor_id'],
            sampling_rate_ms=payload['sampling_rate_ms'],
            transmission_interval_s=payload['transmission_interval_s'],
            calibration_factor=payload['calibration_factor'],
            offset=payload['offset'],
            deep_sleep_enabled=payload['deep_sleep_enabled'],
            wifi_ssid=payload.get('wifi_ssid'),
            wifi_password=payload.get('wifi_password')
        )


class StatusProtocol:
    """Protocolo para informações de status."""
    
    @staticmethod
    def create_status_request() -> bytes:
        """
        Cria mensagem de solicitação de status.
        
        Returns:
            Mensagem codificada
        """
        return MessageProtocol.create_message(
            MessageType.STATUS_REQUEST,
            {},
            CompressionType.NONE
        )
    
    @staticmethod
    def create_status_response(status_data: Dict[str, Any]) -> bytes:
        """
        Cria mensagem de resposta de status.
        
        Args:
            status_data: Dados de status
            
        Returns:
            Mensagem codificada
        """
        return MessageProtocol.create_message(
            MessageType.STATUS_RESPONSE,
            status_data,
            CompressionType.NONE
        )
    
    @staticmethod
    def parse_status_response(data: bytes) -> Dict[str, Any]:
        """
        Analisa resposta de status.
        
        Args:
            data: Dados recebidos
            
        Returns:
            Dicionário com dados de status
        """
        message = MessageProtocol.parse_message(data)
        
        if message['type'] != MessageType.STATUS_RESPONSE:
            raise ProtocolError(f"Tipo de mensagem inesperado: {message['type']}")
        
        return message['payload']


# Funções de conveniência
def create_ping_message() -> bytes:
    """Cria mensagem de ping."""
    return MessageProtocol.create_message(MessageType.PING, {})


def create_pong_message() -> bytes:
    """Cria mensagem de pong."""
    return MessageProtocol.create_message(MessageType.PONG, {})


def create_error_message(error_code: int, error_message: str) -> bytes:
    """
    Cria mensagem de erro.
    
    Args:
        error_code: Código do erro
        error_message: Descrição do erro
        
    Returns:
        Mensagem codificada
    """
    payload = {
        'error_code': error_code,
        'error_message': error_message,
        'timestamp': datetime.now().isoformat()
    }
    
    return MessageProtocol.create_message(MessageType.ERROR, payload)
