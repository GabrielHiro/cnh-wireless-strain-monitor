"""
API otimizada para visualização de dados em formato osciloscópio.

Este módulo fornece uma interface simplificada para acessar dados
em tempo real formatados especificamente para gráficos tipo osciloscópio.
"""

import json
import time
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass

from .data_manager import DataManager
from ..core.models import StrainReading


@dataclass
class OscilloscopeConfig:
    """Configuração do osciloscópio virtual."""
    time_window_seconds: float = 10.0  # Janela de tempo visível
    sample_rate_hz: float = 100.0      # Taxa de amostragem efetiva
    max_points: int = 1000             # Máximo de pontos na tela
    auto_scale: bool = True            # Auto-escala vertical
    y_min: Optional[float] = None      # Escala Y mínima (se auto_scale=False)
    y_max: Optional[float] = None      # Escala Y máxima (se auto_scale=False)


class OscilloscopeAPI:
    """
    API para visualização de dados em tempo real tipo osciloscópio.
    
    Fornece dados otimizados para gráficos de alta performance.
    """
    
    def __init__(self, data_manager: DataManager):
        """
        Inicializa a API do osciloscópio.
        
        Args:
            data_manager: Gerenciador de dados principal
        """
        self.data_manager = data_manager
        self.config = OscilloscopeConfig()
        self._last_update_time = 0
        
    def get_trace_data(self, sensor_id: str, 
                      decimation_factor: int = 1) -> Dict[str, Any]:
        """
        Retorna dados de traço para um sensor específico.
        
        Args:
            sensor_id: ID do sensor
            decimation_factor: Fator de decimação para reduzir pontos
            
        Returns:
            Dados do traço formatados para gráfico
        """
        # Busca dados do stream
        stream_data = self.data_manager.get_oscilloscope_data(
            sensor_id=sensor_id,
            last_n=self.config.max_points * decimation_factor
        )
        
        if not stream_data:
            return self._empty_trace()
        
        # Aplica decimação se necessário
        if decimation_factor > 1:
            stream_data = stream_data[::decimation_factor]
        
        # Extrai arrays para plotagem rápida
        times = [point['t'] for point in stream_data]
        values = [point['v'] for point in stream_data]
        
        # Calcula estatísticas
        if values:
            y_min = min(values)
            y_max = max(values)
            y_range = y_max - y_min if y_max != y_min else 1.0
        else:
            y_min = y_max = y_range = 0
        
        return {
            'sensor_id': sensor_id,
            'times': times,
            'values': values,
            'point_count': len(times),
            'time_span': (max(times) - min(times)) / 1000.0 if len(times) > 1 else 0,
            'y_min': y_min,
            'y_max': y_max,
            'y_range': y_range,
            'last_update': time.time() * 1000
        }
    
    def get_multi_trace_data(self, sensor_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Retorna dados de múltiplos traços.
        
        Args:
            sensor_ids: Lista de IDs dos sensores
            
        Returns:
            Dict com dados de cada sensor
        """
        traces = {}
        for sensor_id in sensor_ids:
            traces[sensor_id] = self.get_trace_data(sensor_id)
        
        return traces
    
    def get_realtime_snapshot(self) -> Dict[str, Any]:
        """
        Retorna snapshot em tempo real de todos os sensores ativos.
        
        Returns:
            Snapshot com valores instantâneos
        """
        latest_values = self.data_manager.get_realtime_values()
        stream_stats = self.data_manager.get_stream_statistics()
        
        snapshot = {
            'timestamp': time.time() * 1000,
            'active_sensors': stream_stats.get('active_sensors', 0),
            'total_points': stream_stats.get('total_points', 0),
            'sensors': {}
        }
        
        for sensor_id, latest in latest_values.items():
            sensor_stats = stream_stats.get('sensors', {}).get(sensor_id, {})
            
            snapshot['sensors'][sensor_id] = {
                'current_value': latest['v'],
                'timestamp': latest['t'],
                'battery': latest['b'],
                'temperature': latest['temp'],
                'raw_adc': latest['r'],
                'min_value': sensor_stats.get('min_value', latest['v']),
                'max_value': sensor_stats.get('max_value', latest['v']),
                'avg_value': sensor_stats.get('avg_value', latest['v']),
                'point_count': sensor_stats.get('points', 0)
            }
        
        return snapshot
    
    def get_streaming_data(self, sensor_id: str, 
                          since_timestamp: Optional[float] = None) -> Dict[str, Any]:
        """
        Retorna dados novos desde um timestamp específico.
        
        Args:
            sensor_id: ID do sensor
            since_timestamp: Timestamp em ms (None = todos os dados)
            
        Returns:
            Dados incrementais para streaming
        """
        stream_data = self.data_manager.get_oscilloscope_data(sensor_id=sensor_id)
        
        if not stream_data:
            return self._empty_streaming_data()
        
        # Filtra dados novos
        if since_timestamp is not None:
            stream_data = [
                point for point in stream_data 
                if point['t'] > since_timestamp
            ]
        
        return {
            'sensor_id': sensor_id,
            'new_points': len(stream_data),
            'data': stream_data,
            'latest_timestamp': stream_data[-1]['t'] if stream_data else since_timestamp,
            'has_more': len(stream_data) > 0
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Retorna métricas de performance do sistema.
        
        Returns:
            Métricas de performance
        """
        stats = self.data_manager.get_stream_statistics()
        buffer_stats = self.data_manager.get_statistics()
        
        return {
            'stream_stats': stats,
            'buffer_stats': buffer_stats,
            'api_update_rate': self._calculate_update_rate(),
            'memory_usage': self._estimate_memory_usage(),
            'config': {
                'time_window': self.config.time_window_seconds,
                'max_points': self.config.max_points,
                'sample_rate': self.config.sample_rate_hz
            }
        }
    
    def set_config(self, **kwargs) -> None:
        """
        Atualiza configuração do osciloscópio.
        
        Args:
            **kwargs: Parâmetros de configuração
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
    
    def export_trace_data(self, sensor_id: str, 
                         format_type: str = 'json') -> Union[str, bytes]:
        """
        Exporta dados do traço em formato específico.
        
        Args:
            sensor_id: ID do sensor
            format_type: Formato ('json', 'csv', 'binary')
            
        Returns:
            Dados exportados
        """
        trace_data = self.get_trace_data(sensor_id)
        
        if format_type == 'json':
            return json.dumps(trace_data, indent=2)
        
        elif format_type == 'csv':
            lines = ['timestamp_ms,strain_value']
            for t, v in zip(trace_data['times'], trace_data['values']):
                lines.append(f'{t},{v}')
            return '\n'.join(lines)
        
        elif format_type == 'binary':
            # Formato binário simples: float64 para cada valor
            import struct
            data = b''
            for t, v in zip(trace_data['times'], trace_data['values']):
                data += struct.pack('dd', t, v)  # 2 doubles por ponto
            return data
        
        else:
            raise ValueError(f"Formato não suportado: {format_type}")
    
    def _empty_trace(self) -> Dict[str, Any]:
        """Retorna estrutura vazia de traço."""
        return {
            'sensor_id': '',
            'times': [],
            'values': [],
            'point_count': 0,
            'time_span': 0,
            'y_min': 0,
            'y_max': 0,
            'y_range': 0,
            'last_update': time.time() * 1000
        }
    
    def _empty_streaming_data(self) -> Dict[str, Any]:
        """Retorna estrutura vazia de streaming."""
        return {
            'sensor_id': '',
            'new_points': 0,
            'data': [],
            'latest_timestamp': time.time() * 1000,
            'has_more': False
        }
    
    def _calculate_update_rate(self) -> float:
        """Calcula taxa de atualização da API."""
        current_time = time.time()
        if self._last_update_time > 0:
            rate = 1.0 / (current_time - self._last_update_time)
        else:
            rate = 0.0
        
        self._last_update_time = current_time
        return rate
    
    def _estimate_memory_usage(self) -> Dict[str, int]:
        """Estima uso de memória do sistema."""
        stats = self.data_manager.get_stream_statistics()
        
        # Estimativas aproximadas
        points_per_sensor = stats.get('total_points', 0) / max(stats.get('active_sensors', 1), 1)
        bytes_per_point = 32  # Estimativa baseada na estrutura dos dados
        
        return {
            'total_points': stats.get('total_points', 0),
            'estimated_bytes': stats.get('total_points', 0) * bytes_per_point,
            'points_per_sensor': int(points_per_sensor),
            'active_sensors': stats.get('active_sensors', 0)
        }


class WebSocketStreamer:
    """
    Streamer WebSocket para dados em tempo real.
    
    Permite streaming de dados para aplicações web.
    """
    
    def __init__(self, oscilloscope_api: OscilloscopeAPI):
        """
        Inicializa o streamer WebSocket.
        
        Args:
            oscilloscope_api: API do osciloscópio
        """
        self.api = oscilloscope_api
        self._clients = set()
        self._is_streaming = False
        
    def add_client(self, client_id: str) -> None:
        """Adiciona cliente ao streaming."""
        self._clients.add(client_id)
        
    def remove_client(self, client_id: str) -> None:
        """Remove cliente do streaming."""
        self._clients.discard(client_id)
        
    def broadcast_snapshot(self) -> Dict[str, Any]:
        """
        Gera snapshot para broadcast.
        
        Returns:
            Dados para broadcast
        """
        return {
            'type': 'realtime_snapshot',
            'data': self.api.get_realtime_snapshot(),
            'client_count': len(self._clients)
        }
    
    def get_trace_update(self, sensor_id: str, 
                        since_timestamp: float) -> Dict[str, Any]:
        """
        Gera atualização de traço para WebSocket.
        
        Args:
            sensor_id: ID do sensor
            since_timestamp: Timestamp da última atualização
            
        Returns:
            Dados de atualização
        """
        streaming_data = self.api.get_streaming_data(sensor_id, since_timestamp)
        
        return {
            'type': 'trace_update',
            'sensor_id': sensor_id,
            'data': streaming_data
        }
