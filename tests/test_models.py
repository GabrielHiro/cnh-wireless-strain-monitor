"""
Testes unitários para os modelos de dados.
Valida a integridade e comportamento das estruturas de dados principais.
"""

import pytest
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Adiciona diretório pai ao path para importações
sys.path.append(str(Path(__file__).parent.parent))

from src.core.models import (
    StrainReading, 
    SensorConfiguration, 
    SensorInfo, 
    DataPacket,
    SensorStatus,
    CommunicationProtocol
)


class TestStrainReading:
    """Testes para a classe StrainReading."""
    
    def test_strain_reading_creation(self):
        """Testa criação básica de StrainReading."""
        timestamp = datetime.now()
        reading = StrainReading(
            timestamp=timestamp,
            strain_value=100.5,
            raw_adc_value=12345,
            sensor_id="TEST_001",
            battery_level=85,
            temperature=25.5
        )
        
        assert reading.timestamp == timestamp
        assert reading.strain_value == 100.5
        assert reading.raw_adc_value == 12345
        assert reading.sensor_id == "TEST_001"
        assert reading.battery_level == 85
        assert reading.temperature == 25.5
        assert reading.checksum is not None
    
    def test_strain_reading_checksum_calculation(self):
        """Testa cálculo automático de checksum."""
        reading1 = StrainReading(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            strain_value=100.0,
            raw_adc_value=1000,
            sensor_id="TEST",
            battery_level=50,
            temperature=20.0
        )
        
        reading2 = StrainReading(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            strain_value=100.0,
            raw_adc_value=1000,
            sensor_id="TEST",
            battery_level=50,
            temperature=20.0
        )
        
        # Checksums devem ser iguais para dados idênticos
        assert reading1.checksum == reading2.checksum
    
    def test_strain_reading_validation(self):
        """Testa validação de leituras."""
        # Leitura válida
        valid_reading = StrainReading(
            timestamp=datetime.now(),
            strain_value=50.0,
            raw_adc_value=1000,
            sensor_id="TEST",
            battery_level=75,
            temperature=25.0
        )
        assert valid_reading.is_valid()
        
        # Leitura inválida - bateria fora de faixa
        invalid_reading = StrainReading(
            timestamp=datetime.now(),
            strain_value=50.0,
            raw_adc_value=1000,
            sensor_id="TEST",
            battery_level=150,  # Inválido
            temperature=25.0
        )
        assert not invalid_reading.is_valid()
        
        # Leitura inválida - temperatura fora de faixa
        invalid_temp_reading = StrainReading(
            timestamp=datetime.now(),
            strain_value=50.0,
            raw_adc_value=1000,
            sensor_id="TEST",
            battery_level=75,
            temperature=100.0  # Muito alta
        )
        assert not invalid_temp_reading.is_valid()
    
    def test_strain_reading_checksum_integrity(self):
        """Testa integridade do checksum."""
        reading = StrainReading(
            timestamp=datetime.now(),
            strain_value=100.0,
            raw_adc_value=1000,
            sensor_id="TEST",
            battery_level=50,
            temperature=20.0
        )
        
        original_checksum = reading.checksum
        
        # Modifica dados (simulando corrupção)
        reading.strain_value = 200.0
        
        # Checksum não deve mais bater
        assert reading.checksum != reading._calculate_checksum()
        
        # Mas ainda mantém o valor original
        assert reading.checksum == original_checksum


class TestSensorConfiguration:
    """Testes para a classe SensorConfiguration."""
    
    def test_sensor_config_creation(self):
        """Testa criação de configuração de sensor."""
        config = SensorConfiguration(
            sensor_id="CONFIG_TEST",
            sampling_rate_ms=200,
            transmission_interval_s=5,
            calibration_factor=1.5,
            offset=10.0,
            deep_sleep_enabled=False,
            wifi_ssid="TestNetwork",
            wifi_password="password123"
        )
        
        assert config.sensor_id == "CONFIG_TEST"
        assert config.sampling_rate_ms == 200
        assert config.transmission_interval_s == 5
        assert config.calibration_factor == 1.5
        assert config.offset == 10.0
        assert config.deep_sleep_enabled is False
        assert config.wifi_ssid == "TestNetwork"
        assert config.wifi_password == "password123"
    
    def test_sensor_config_defaults(self):
        """Testa valores padrão da configuração."""
        config = SensorConfiguration()
        
        assert len(config.sensor_id) == 8  # UUID truncado
        assert config.sampling_rate_ms == 100
        assert config.transmission_interval_s == 1
        assert config.calibration_factor == 1.0
        assert config.offset == 0.0
        assert config.deep_sleep_enabled is True
        assert config.wifi_ssid is None
        assert config.wifi_password is None
    
    def test_sensor_config_to_dict(self):
        """Testa conversão para dicionário."""
        config = SensorConfiguration(
            sensor_id="DICT_TEST",
            sampling_rate_ms=150
        )
        
        config_dict = config.to_dict()
        
        assert isinstance(config_dict, dict)
        assert config_dict['sensor_id'] == "DICT_TEST"
        assert config_dict['sampling_rate_ms'] == 150
        assert 'calibration_factor' in config_dict
        assert 'deep_sleep_enabled' in config_dict


class TestSensorInfo:
    """Testes para a classe SensorInfo."""
    
    def test_sensor_info_creation(self):
        """Testa criação de informações de sensor."""
        now = datetime.now()
        info = SensorInfo(
            sensor_id="INFO_TEST",
            name="Sensor de Teste",
            status=SensorStatus.ONLINE,
            last_seen=now,
            protocol=CommunicationProtocol.BLE,
            signal_strength=-45,
            firmware_version="1.0.0",
            hardware_version="ESP32-v1"
        )
        
        assert info.sensor_id == "INFO_TEST"
        assert info.name == "Sensor de Teste"
        assert info.status == SensorStatus.ONLINE
        assert info.last_seen == now
        assert info.protocol == CommunicationProtocol.BLE
        assert info.signal_strength == -45
        assert info.firmware_version == "1.0.0"
        assert info.hardware_version == "ESP32-v1"
    
    def test_sensor_info_is_online(self):
        """Testa verificação se sensor está online."""
        online_sensor = SensorInfo(
            sensor_id="ONLINE_TEST",
            name="Sensor Online",
            status=SensorStatus.ONLINE
        )
        assert online_sensor.is_online()
        
        offline_sensor = SensorInfo(
            sensor_id="OFFLINE_TEST",
            name="Sensor Offline",
            status=SensorStatus.OFFLINE
        )
        assert not offline_sensor.is_online()
    
    def test_sensor_info_time_since_last_seen(self):
        """Testa cálculo de tempo desde última comunicação."""
        # Sensor que foi visto há 5 segundos
        past_time = datetime.now() - timedelta(seconds=5)
        sensor = SensorInfo(
            sensor_id="TIME_TEST",
            name="Sensor Teste",
            last_seen=past_time
        )
        
        time_since = sensor.time_since_last_seen()
        assert time_since is not None
        assert time_since >= 4.0  # Pelo menos 4 segundos (margem de erro)
        assert time_since <= 6.0  # No máximo 6 segundos
        
        # Sensor sem histórico
        never_seen_sensor = SensorInfo(
            sensor_id="NEVER_SEEN",
            name="Nunca Visto"
        )
        assert never_seen_sensor.time_since_last_seen() is None


class TestDataPacket:
    """Testes para a classe DataPacket."""
    
    def test_data_packet_creation(self):
        """Testa criação de pacote de dados."""
        readings = [
            StrainReading(
                timestamp=datetime.now(),
                strain_value=i * 10.0,
                raw_adc_value=i * 100,
                sensor_id="PACKET_TEST",
                battery_level=90 - i,
                temperature=20.0 + i
            )
            for i in range(3)
        ]
        
        packet = DataPacket(
            packet_id="PKT_001",
            sensor_id="PACKET_TEST",
            readings=readings,
            timestamp=datetime.now(),
            sequence_number=0,
            total_packets=1
        )
        
        assert packet.packet_id == "PKT_001"
        assert packet.sensor_id == "PACKET_TEST"
        assert len(packet.readings) == 3
        assert packet.sequence_number == 0
        assert packet.total_packets == 1
    
    def test_data_packet_auto_id(self):
        """Testa geração automática de ID."""
        packet = DataPacket(
            packet_id="",  # ID vazio deve ser gerado
            sensor_id="AUTO_ID_TEST",
            readings=[],
            timestamp=datetime.now()
        )
        
        assert packet.packet_id != ""
        assert len(packet.packet_id) == 8  # UUID truncado
    
    def test_data_packet_sequence_completion(self):
        """Testa verificação de sequência completa."""
        # Pacote único
        single_packet = DataPacket(
            packet_id="SINGLE",
            sensor_id="TEST",
            readings=[],
            timestamp=datetime.now(),
            sequence_number=0,
            total_packets=1
        )
        assert single_packet.is_complete_sequence()
        
        # Primeiro pacote de uma sequência
        first_packet = DataPacket(
            packet_id="FIRST",
            sensor_id="TEST",
            readings=[],
            timestamp=datetime.now(),
            sequence_number=0,
            total_packets=3
        )
        assert not first_packet.is_complete_sequence()
        
        # Último pacote de uma sequência
        last_packet = DataPacket(
            packet_id="LAST",
            sensor_id="TEST",
            readings=[],
            timestamp=datetime.now(),
            sequence_number=2,
            total_packets=3
        )
        assert last_packet.is_complete_sequence()
    
    def test_data_packet_size_estimation(self):
        """Testa estimativa de tamanho dos dados."""
        # Pacote vazio
        empty_packet = DataPacket(
            packet_id="EMPTY",
            sensor_id="TEST",
            readings=[],
            timestamp=datetime.now()
        )
        assert empty_packet.get_data_size() == 0
        
        # Pacote com 5 leituras
        readings = [
            StrainReading(
                timestamp=datetime.now(),
                strain_value=i,
                raw_adc_value=i * 100,
                sensor_id="SIZE_TEST",
                battery_level=90,
                temperature=25.0
            )
            for i in range(5)
        ]
        
        packet_with_data = DataPacket(
            packet_id="WITH_DATA",
            sensor_id="TEST",
            readings=readings,
            timestamp=datetime.now()
        )
        
        expected_size = 5 * 32  # 5 leituras * 32 bytes estimados
        assert packet_with_data.get_data_size() == expected_size


class TestEnums:
    """Testes para enumerações."""
    
    def test_sensor_status_values(self):
        """Testa valores de SensorStatus."""
        assert SensorStatus.OFFLINE.value == "offline"
        assert SensorStatus.CONNECTING.value == "connecting"
        assert SensorStatus.ONLINE.value == "online"
        assert SensorStatus.ERROR.value == "error"
        assert SensorStatus.LOW_BATTERY.value == "low_battery"
    
    def test_communication_protocol_values(self):
        """Testa valores de CommunicationProtocol."""
        assert CommunicationProtocol.BLE.value == "bluetooth_low_energy"
        assert CommunicationProtocol.WIFI.value == "wifi"


# Fixtures para testes
@pytest.fixture
def sample_strain_reading():
    """Fixture que retorna uma leitura de exemplo."""
    return StrainReading(
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        strain_value=100.0,
        raw_adc_value=2000,
        sensor_id="FIXTURE_TEST",
        battery_level=80,
        temperature=22.5
    )


@pytest.fixture
def sample_sensor_config():
    """Fixture que retorna uma configuração de exemplo."""
    return SensorConfiguration(
        sensor_id="FIXTURE_CONFIG",
        sampling_rate_ms=100,
        transmission_interval_s=2,
        calibration_factor=1.2,
        offset=5.0
    )


def test_integration_strain_reading_in_packet(sample_strain_reading):
    """Teste de integração: StrainReading dentro de DataPacket."""
    packet = DataPacket(
        packet_id="INTEGRATION_TEST",
        sensor_id=sample_strain_reading.sensor_id,
        readings=[sample_strain_reading],
        timestamp=datetime.now()
    )
    
    assert len(packet.readings) == 1
    assert packet.readings[0].sensor_id == sample_strain_reading.sensor_id
    assert packet.readings[0].is_valid()


if __name__ == "__main__":
    # Executa testes se arquivo for chamado diretamente
    pytest.main([__file__, "-v"])
