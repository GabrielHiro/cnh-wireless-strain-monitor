"""
Gerenciador de dados para o sistema DAQ.
Responsável por armazenamento, buffer, persistência e exportação de dados.
"""

import os
import json
import csv
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from dataclasses import asdict
import pandas as pd

from ..core.models import StrainReading, DataPacket, SensorInfo
from ..core.config import get_data_file_path, config, EXPORT_CONFIG


class DataStorageError(Exception):
    """Erro de armazenamento de dados."""
    pass


class DataBuffer:
    """
    Buffer em memória para dados de sensores.
    
    Implementa buffer circular com persistência automática
    quando atinge limite de tamanho ou tempo.
    """
    
    def __init__(self, max_size: int = 10000, flush_interval: int = 60):
        """
        Inicializa o buffer de dados.
        
        Args:
            max_size: Tamanho máximo do buffer
            flush_interval: Intervalo de flush em segundos
        """
        self._buffer: List[StrainReading] = []
        self._max_size = max_size
        self._flush_interval = flush_interval
        self._last_flush = datetime.now()
        self._lock = threading.Lock()
        
    def add_reading(self, reading: StrainReading) -> None:
        """
        Adiciona uma leitura ao buffer.
        
        Args:
            reading: Leitura a ser adicionada
        """
        with self._lock:
            self._buffer.append(reading)
            
            # Remove dados antigos se buffer cheio
            if len(self._buffer) > self._max_size:
                self._buffer.pop(0)
    
    def add_readings(self, readings: List[StrainReading]) -> None:
        """
        Adiciona múltiplas leituras ao buffer.
        
        Args:
            readings: Lista de leituras
        """
        with self._lock:
            self._buffer.extend(readings)
            
            # Remove dados antigos se necessário
            if len(self._buffer) > self._max_size:
                excess = len(self._buffer) - self._max_size
                self._buffer = self._buffer[excess:]
    
    def get_readings(self, sensor_id: Optional[str] = None,
                    start_time: Optional[datetime] = None,
                    end_time: Optional[datetime] = None,
                    max_count: Optional[int] = None) -> List[StrainReading]:
        """
        Recupera leituras do buffer com filtros opcionais.
        
        Args:
            sensor_id: Filtrar por ID do sensor
            start_time: Tempo inicial
            end_time: Tempo final
            max_count: Número máximo de leituras
            
        Returns:
            Lista de leituras filtradas
        """
        with self._lock:
            readings = self._buffer.copy()
        
        # Aplica filtros
        if sensor_id:
            readings = [r for r in readings if r.sensor_id == sensor_id]
        
        if start_time:
            readings = [r for r in readings if r.timestamp >= start_time]
        
        if end_time:
            readings = [r for r in readings if r.timestamp <= end_time]
        
        # Ordena por timestamp
        readings.sort(key=lambda r: r.timestamp)
        
        # Limita quantidade se especificado
        if max_count and len(readings) > max_count:
            readings = readings[-max_count:]  # Pega os mais recentes
        
        return readings
    
    def get_latest_reading(self, sensor_id: Optional[str] = None) -> Optional[StrainReading]:
        """
        Retorna a leitura mais recente.
        
        Args:
            sensor_id: ID do sensor (opcional)
            
        Returns:
            Leitura mais recente ou None
        """
        readings = self.get_readings(sensor_id=sensor_id, max_count=1)
        return readings[0] if readings else None
    
    def clear(self) -> None:
        """Limpa todo o buffer."""
        with self._lock:
            self._buffer.clear()
    
    def size(self) -> int:
        """Retorna tamanho atual do buffer."""
        with self._lock:
            return len(self._buffer)
    
    def should_flush(self) -> bool:
        """Verifica se é hora de fazer flush do buffer."""
        return (
            len(self._buffer) >= self._max_size or
            (datetime.now() - self._last_flush).seconds >= self._flush_interval
        )
    
    def mark_flushed(self) -> None:
        """Marca que o flush foi realizado."""
        self._last_flush = datetime.now()


class DatabaseManager:
    """
    Gerenciador do banco de dados SQLite para persistência.
    
    Armazena dados de forma persistente para análise posterior
    e recuperação em caso de falhas.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Inicializa o gerenciador de banco de dados.
        
        Args:
            db_path: Caminho para o arquivo do banco
        """
        if db_path is None:
            db_path = get_data_file_path("daq_data.db")
        
        self._db_path = db_path
        self._connection = None
        self._lock = threading.Lock()
        
        self._init_database()
    
    def _init_database(self) -> None:
        """Inicializa o banco de dados e cria tabelas."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Tabela de leituras de strain
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS strain_readings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        strain_value REAL NOT NULL,
                        raw_adc_value INTEGER NOT NULL,
                        sensor_id TEXT NOT NULL,
                        battery_level INTEGER NOT NULL,
                        temperature REAL NOT NULL,
                        checksum TEXT,
                        created_at REAL DEFAULT (datetime('now'))
                    )
                """)
                
                # Tabela de informações de sensores
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sensor_info (
                        sensor_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        status TEXT NOT NULL,
                        last_seen REAL,
                        protocol TEXT,
                        signal_strength INTEGER,
                        firmware_version TEXT,
                        hardware_version TEXT,
                        updated_at REAL DEFAULT (datetime('now'))
                    )
                """)
                
                # Tabela de configurações
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sensor_configs (
                        sensor_id TEXT PRIMARY KEY,
                        sampling_rate_ms INTEGER NOT NULL,
                        transmission_interval_s INTEGER NOT NULL,
                        calibration_factor REAL NOT NULL,
                        offset REAL NOT NULL,
                        deep_sleep_enabled BOOLEAN NOT NULL,
                        wifi_ssid TEXT,
                        wifi_password TEXT,
                        updated_at REAL DEFAULT (datetime('now'))
                    )
                """)
                
                # Índices para performance
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_readings_timestamp 
                    ON strain_readings(timestamp)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_readings_sensor 
                    ON strain_readings(sensor_id)
                """)
                
                conn.commit()
                
        except Exception as e:
            raise DataStorageError(f"Erro ao inicializar banco: {e}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Retorna conexão thread-safe com o banco."""
        with self._lock:
            if self._connection is None:
                self._connection = sqlite3.connect(
                    str(self._db_path),
                    check_same_thread=False,
                    timeout=30.0
                )
                self._connection.row_factory = sqlite3.Row
        
        return self._connection
    
    def store_reading(self, reading: StrainReading) -> None:
        """
        Armazena uma leitura no banco.
        
        Args:
            reading: Leitura a ser armazenada
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO strain_readings 
                    (timestamp, strain_value, raw_adc_value, sensor_id, 
                     battery_level, temperature, checksum)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    reading.timestamp.timestamp(),
                    reading.strain_value,
                    reading.raw_adc_value,
                    reading.sensor_id,
                    reading.battery_level,
                    reading.temperature,
                    reading.checksum
                ))
                conn.commit()
                
        except Exception as e:
            raise DataStorageError(f"Erro ao armazenar leitura: {e}")
    
    def store_readings(self, readings: List[StrainReading]) -> None:
        """
        Armazena múltiplas leituras em lote.
        
        Args:
            readings: Lista de leituras
        """
        if not readings:
            return
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                data = [
                    (
                        r.timestamp.timestamp(),
                        r.strain_value,
                        r.raw_adc_value,
                        r.sensor_id,
                        r.battery_level,
                        r.temperature,
                        r.checksum
                    )
                    for r in readings
                ]
                
                cursor.executemany("""
                    INSERT INTO strain_readings 
                    (timestamp, strain_value, raw_adc_value, sensor_id, 
                     battery_level, temperature, checksum)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, data)
                
                conn.commit()
                
        except Exception as e:
            raise DataStorageError(f"Erro ao armazenar leituras: {e}")
    
    def get_readings(self, sensor_id: Optional[str] = None,
                    start_time: Optional[datetime] = None,
                    end_time: Optional[datetime] = None,
                    limit: Optional[int] = None) -> List[StrainReading]:
        """
        Recupera leituras do banco com filtros.
        
        Args:
            sensor_id: ID do sensor
            start_time: Tempo inicial
            end_time: Tempo final
            limit: Número máximo de registros
            
        Returns:
            Lista de leituras
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM strain_readings WHERE 1=1"
                params = []
                
                if sensor_id:
                    query += " AND sensor_id = ?"
                    params.append(sensor_id)
                
                if start_time:
                    query += " AND timestamp >= ?"
                    params.append(start_time.timestamp())
                
                if end_time:
                    query += " AND timestamp <= ?"
                    params.append(end_time.timestamp())
                
                query += " ORDER BY timestamp DESC"
                
                if limit:
                    query += " LIMIT ?"
                    params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                readings = []
                for row in rows:
                    reading = StrainReading(
                        timestamp=datetime.fromtimestamp(row['timestamp']),
                        strain_value=row['strain_value'],
                        raw_adc_value=row['raw_adc_value'],
                        sensor_id=row['sensor_id'],
                        battery_level=row['battery_level'],
                        temperature=row['temperature'],
                        checksum=row['checksum']
                    )
                    readings.append(reading)
                
                return readings
                
        except Exception as e:
            raise DataStorageError(f"Erro ao recuperar leituras: {e}")
    
    def store_sensor_info(self, sensor_info: SensorInfo) -> None:
        """
        Armazena informações de sensor.
        
        Args:
            sensor_info: Informações do sensor
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO sensor_info 
                    (sensor_id, name, status, last_seen, protocol, 
                     signal_strength, firmware_version, hardware_version)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    sensor_info.sensor_id,
                    sensor_info.name,
                    sensor_info.status.value,
                    sensor_info.last_seen.timestamp() if sensor_info.last_seen else None,
                    sensor_info.protocol.value if sensor_info.protocol else None,
                    sensor_info.signal_strength,
                    sensor_info.firmware_version,
                    sensor_info.hardware_version
                ))
                conn.commit()
                
        except Exception as e:
            raise DataStorageError(f"Erro ao armazenar info do sensor: {e}")
    
    def cleanup_old_data(self, days: int = 30) -> int:
        """
        Remove dados antigos do banco.
        
        Args:
            days: Número de dias para manter
            
        Returns:
            Número de registros removidos
        """
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM strain_readings 
                    WHERE timestamp < ?
                """, (cutoff_time.timestamp(),))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                return deleted_count
                
        except Exception as e:
            raise DataStorageError(f"Erro na limpeza: {e}")
    
    def close(self) -> None:
        """Fecha conexão com o banco."""
        with self._lock:
            if self._connection:
                self._connection.close()
                self._connection = None


class DataExporter:
    """
    Exportador de dados para diferentes formatos.
    
    Suporta exportação para CSV, JSON e Excel para análise externa.
    """
    
    @staticmethod
    def export_to_csv(readings: List[StrainReading], 
                     output_path: Path,
                     include_metadata: bool = True) -> None:
        """
        Exporta leituras para arquivo CSV.
        
        Args:
            readings: Lista de leituras
            output_path: Caminho do arquivo de saída
            include_metadata: Se incluir metadados no cabeçalho
        """
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Cabeçalho com metadados
                if include_metadata:
                    writer.writerow(['# Sistema DAQ - Dados de Deformação'])
                    writer.writerow([f'# Exportado em: {datetime.now().isoformat()}'])
                    writer.writerow([f'# Total de leituras: {len(readings)}'])
                    if readings:
                        writer.writerow([f'# Período: {readings[0].timestamp} a {readings[-1].timestamp}'])
                    writer.writerow(['#'])
                
                # Cabeçalho das colunas
                writer.writerow([
                    'timestamp',
                    'strain_value_microstrains',
                    'raw_adc_value',
                    'sensor_id',
                    'battery_level_percent',
                    'temperature_celsius',
                    'checksum'
                ])
                
                # Dados
                for reading in readings:
                    writer.writerow([
                        reading.timestamp.strftime(EXPORT_CONFIG['csv']['date_format']),
                        reading.strain_value,
                        reading.raw_adc_value,
                        reading.sensor_id,
                        reading.battery_level,
                        reading.temperature,
                        reading.checksum
                    ])
                    
        except Exception as e:
            raise DataStorageError(f"Erro ao exportar CSV: {e}")
    
    @staticmethod
    def export_to_json(readings: List[StrainReading], output_path: Path) -> None:
        """
        Exporta leituras para arquivo JSON.
        
        Args:
            readings: Lista de leituras
            output_path: Caminho do arquivo de saída
        """
        try:
            data = {
                'metadata': {
                    'exported_at': datetime.now().isoformat(),
                    'total_readings': len(readings),
                    'system': 'Sistema DAQ CNH Industrial'
                },
                'readings': [
                    {
                        'timestamp': reading.timestamp.isoformat(),
                        'strain_value': reading.strain_value,
                        'raw_adc_value': reading.raw_adc_value,
                        'sensor_id': reading.sensor_id,
                        'battery_level': reading.battery_level,
                        'temperature': reading.temperature,
                        'checksum': reading.checksum
                    }
                    for reading in readings
                ]
            }
            
            with open(output_path, 'w', encoding='utf-8') as jsonfile:
                json.dump(data, jsonfile, **EXPORT_CONFIG['json'])
                
        except Exception as e:
            raise DataStorageError(f"Erro ao exportar JSON: {e}")
    
    @staticmethod
    def export_to_excel(readings: List[StrainReading], output_path: Path) -> None:
        """
        Exporta leituras para arquivo Excel.
        
        Args:
            readings: Lista de leituras
            output_path: Caminho do arquivo de saída
        """
        try:
            # Converte para DataFrame do pandas
            data = []
            for reading in readings:
                data.append({
                    'Timestamp': reading.timestamp,
                    'Strain (µε)': reading.strain_value,
                    'Raw ADC': reading.raw_adc_value,
                    'Sensor ID': reading.sensor_id,
                    'Battery (%)': reading.battery_level,
                    'Temperature (°C)': reading.temperature,
                    'Checksum': reading.checksum
                })
            
            df = pd.DataFrame(data)
            
            # Exporta para Excel com formatação
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Strain Data', index=False)
                
                # Adiciona metadados em uma segunda aba
                metadata_df = pd.DataFrame({
                    'Property': ['Export Date', 'Total Readings', 'System'],
                    'Value': [
                        datetime.now().isoformat(),
                        len(readings),
                        'Sistema DAQ CNH Industrial'
                    ]
                })
                metadata_df.to_excel(writer, sheet_name='Metadata', index=False)
                
        except Exception as e:
            raise DataStorageError(f"Erro ao exportar Excel: {e}")


class OscilloscopeStreamer:
    """
    Streamer de dados otimizado para visualização tipo osciloscópio.
    
    Fornece dados em formato otimizado para gráficos em tempo real.
    """
    
    def __init__(self, max_points: int = 1000):
        """
        Inicializa o streamer de osciloscópio.
        
        Args:
            max_points: Número máximo de pontos a manter na janela
        """
        self._data_streams: Dict[str, List[Dict]] = {}
        self._max_points = max_points
        self._lock = threading.Lock()
        
    def add_reading(self, reading: StrainReading) -> None:
        """
        Adiciona leitura ao stream de osciloscópio.
        
        Args:
            reading: Leitura do sensor
        """
        with self._lock:
            # Inicializa stream do sensor se não existir
            if reading.sensor_id not in self._data_streams:
                self._data_streams[reading.sensor_id] = []
            
            # Converte timestamp para valor numérico (ms desde epoch)
            time_ms = reading.timestamp.timestamp() * 1000
            
            # Formato otimizado para gráficos
            data_point = {
                't': time_ms,                    # Timestamp em ms
                'v': reading.strain_value,       # Valor principal
                'r': reading.raw_adc_value,      # Valor ADC bruto
                'b': reading.battery_level,      # Bateria
                'temp': reading.temperature      # Temperatura
            }
            
            stream = self._data_streams[reading.sensor_id]
            stream.append(data_point)
            
            # Mantém apenas os últimos N pontos
            if len(stream) > self._max_points:
                stream.pop(0)
    
    def get_stream_data(self, sensor_id: str, last_n: Optional[int] = None) -> List[Dict]:
        """
        Retorna dados do stream para um sensor.
        
        Args:
            sensor_id: ID do sensor
            last_n: Número de pontos mais recentes (None = todos)
            
        Returns:
            Lista de pontos de dados
        """
        with self._lock:
            if sensor_id not in self._data_streams:
                return []
            
            stream = self._data_streams[sensor_id]
            
            if last_n is not None:
                return stream[-last_n:]
            
            return stream.copy()
    
    def get_all_streams(self) -> Dict[str, List[Dict]]:
        """
        Retorna todos os streams ativos.
        
        Returns:
            Dict com sensor_id como chave e lista de pontos como valor
        """
        with self._lock:
            return {
                sensor_id: stream.copy() 
                for sensor_id, stream in self._data_streams.items()
            }
    
    def get_latest_values(self) -> Dict[str, Dict]:
        """
        Retorna os valores mais recentes de todos os sensores.
        
        Returns:
            Dict com valores mais recentes por sensor
        """
        with self._lock:
            latest = {}
            for sensor_id, stream in self._data_streams.items():
                if stream:
                    latest[sensor_id] = stream[-1]
            return latest
    
    def clear_stream(self, sensor_id: str) -> None:
        """
        Limpa stream de um sensor específico.
        
        Args:
            sensor_id: ID do sensor
        """
        with self._lock:
            if sensor_id in self._data_streams:
                self._data_streams[sensor_id].clear()
    
    def clear_all_streams(self) -> None:
        """Limpa todos os streams."""
        with self._lock:
            self._data_streams.clear()
    
    def get_stream_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas dos streams ativos.
        
        Returns:
            Estatísticas dos streams
        """
        with self._lock:
            stats = {
                'active_sensors': len(self._data_streams),
                'total_points': sum(len(stream) for stream in self._data_streams.values()),
                'sensors': {}
            }
            
            for sensor_id, stream in self._data_streams.items():
                if stream:
                    values = [point['v'] for point in stream]
                    stats['sensors'][sensor_id] = {
                        'points': len(stream),
                        'latest_time': stream[-1]['t'],
                        'min_value': min(values),
                        'max_value': max(values),
                        'avg_value': sum(values) / len(values)
                    }
            
            return stats


class DataManager:
    """
    Gerenciador principal de dados do sistema DAQ.
    
    Coordena buffer em memória, persistência em banco, exportação e streaming.
    """
    
    def __init__(self):
        """Inicializa o gerenciador de dados."""
        self.buffer = DataBuffer(
            max_size=config.MAX_BUFFER_SIZE,
            flush_interval=config.BUFFER_FLUSH_INTERVAL
        )
        self.database = DatabaseManager()
        self.exporter = DataExporter()
        self.oscilloscope_streamer = OscilloscopeStreamer()
        
        # Controle de flush automático
        self._auto_flush_enabled = True
        self._flush_thread = None
        
    def add_reading(self, reading: StrainReading) -> None:
        """
        Adiciona uma leitura ao sistema.
        
        Args:
            reading: Leitura a ser adicionada
        """
        # Adiciona ao buffer
        self.buffer.add_reading(reading)
        
        # Adiciona ao streamer de osciloscópio
        self.oscilloscope_streamer.add_reading(reading)
        
        # Verifica se precisa fazer flush
        if self.buffer.should_flush():
            self._flush_buffer()
    
    def add_readings(self, readings: List[StrainReading]) -> None:
        """
        Adiciona múltiplas leituras ao sistema.
        
        Args:
            readings: Lista de leituras
        """
        self.buffer.add_readings(readings)
        
        # Adiciona ao streamer também
        for reading in readings:
            self.oscilloscope_streamer.add_reading(reading)
        
        if self.buffer.should_flush():
            self._flush_buffer()
    
    def _flush_buffer(self) -> None:
        """Persiste dados do buffer no banco."""
        try:
            readings = self.buffer.get_readings()
            if readings:
                self.database.store_readings(readings)
                self.buffer.clear()
                self.buffer.mark_flushed()
                
        except Exception as e:
            print(f"Erro no flush do buffer: {e}")
    
    def get_recent_readings(self, sensor_id: Optional[str] = None,
                          minutes: int = 60,
                          max_count: Optional[int] = None) -> List[StrainReading]:
        """
        Retorna leituras recentes (buffer + banco).
        
        Args:
            sensor_id: ID do sensor
            minutes: Minutos para trás
            max_count: Número máximo de leituras
            
        Returns:
            Lista de leituras ordenadas por timestamp
        """
        start_time = datetime.now() - timedelta(minutes=minutes)
        
        # Busca no buffer
        buffer_readings = self.buffer.get_readings(
            sensor_id=sensor_id,
            start_time=start_time
        )
        
        # Busca no banco
        db_readings = self.database.get_readings(
            sensor_id=sensor_id,
            start_time=start_time,
            limit=max_count
        )
        
        # Combina e ordena
        all_readings = buffer_readings + db_readings
        all_readings.sort(key=lambda r: r.timestamp)
        
        # Remove duplicatas (baseado em timestamp e sensor_id)
        unique_readings = []
        seen = set()
        for reading in all_readings:
            key = (reading.timestamp, reading.sensor_id)
            if key not in seen:
                seen.add(key)
                unique_readings.append(reading)
        
        # Limita se necessário
        if max_count and len(unique_readings) > max_count:
            unique_readings = unique_readings[-max_count:]
        
        return unique_readings
    
    def export_data(self, format_type: str, output_path: Path,
                   sensor_id: Optional[str] = None,
                   start_time: Optional[datetime] = None,
                   end_time: Optional[datetime] = None) -> None:
        """
        Exporta dados em formato específico.
        
        Args:
            format_type: Formato ('csv', 'json', 'excel')
            output_path: Caminho do arquivo de saída
            sensor_id: ID do sensor (opcional)
            start_time: Tempo inicial (opcional)
            end_time: Tempo final (opcional)
        """
        # Busca dados
        readings = self.database.get_readings(
            sensor_id=sensor_id,
            start_time=start_time,
            end_time=end_time
        )
        
        # Exporta no formato solicitado
        if format_type.lower() == 'csv':
            self.exporter.export_to_csv(readings, output_path)
        elif format_type.lower() == 'json':
            self.exporter.export_to_json(readings, output_path)
        elif format_type.lower() == 'excel':
            self.exporter.export_to_excel(readings, output_path)
        else:
            raise ValueError(f"Formato não suportado: {format_type}")
    
    def cleanup_old_data(self, days: int = None) -> int:
        """
        Remove dados antigos do sistema.
        
        Args:
            days: Dias para manter (usa config se None)
            
        Returns:
            Número de registros removidos
        """
        if days is None:
            days = config.DATA_RETENTION_DAYS
        
        return self.database.cleanup_old_data(days)
    
    def get_oscilloscope_data(self, sensor_id: Optional[str] = None, 
                             last_n: Optional[int] = None) -> Union[List[Dict], Dict[str, List[Dict]]]:
        """
        Retorna dados formatados para visualização em osciloscópio.
        
        Args:
            sensor_id: ID do sensor específico (None = todos)
            last_n: Número de pontos mais recentes
            
        Returns:
            Dados formatados para osciloscópio
        """
        if sensor_id is not None:
            return self.oscilloscope_streamer.get_stream_data(sensor_id, last_n)
        else:
            return self.oscilloscope_streamer.get_all_streams()
    
    def get_realtime_values(self) -> Dict[str, Dict]:
        """
        Retorna valores em tempo real de todos os sensores.
        
        Returns:
            Valores mais recentes por sensor
        """
        return self.oscilloscope_streamer.get_latest_values()
    
    def get_stream_statistics(self) -> Dict[str, Any]:
        """
        Retorna estatísticas dos streams de dados.
        
        Returns:
            Estatísticas dos streams ativos
        """
        return self.oscilloscope_streamer.get_stream_stats()
    
    def get_statistics(self, sensor_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Retorna estatísticas dos dados.
        
        Args:
            sensor_id: ID do sensor (opcional)
            
        Returns:
            Dicionário com estatísticas
        """
        recent_readings = self.get_recent_readings(sensor_id=sensor_id, minutes=1440)  # 24h
        
        if not recent_readings:
            return {
                'total_readings': 0,
                'sensors_count': 0,
                'latest_reading': None
            }
        
        # Calcula estatísticas
        strain_values = [r.strain_value for r in recent_readings]
        sensors = set(r.sensor_id for r in recent_readings)
        
        return {
            'total_readings': len(recent_readings),
            'sensors_count': len(sensors),
            'latest_reading': recent_readings[-1].timestamp.isoformat(),
            'strain_stats': {
                'min': min(strain_values),
                'max': max(strain_values),
                'avg': sum(strain_values) / len(strain_values)
            },
            'buffer_size': self.buffer.size()
        }
    
    def close(self) -> None:
        """Encerra o gerenciador de dados."""
        # Flush final do buffer
        self._flush_buffer()
        
        # Limpa streams
        self.oscilloscope_streamer.clear_all_streams()
        
        # Fecha banco de dados
        self.database.close()
