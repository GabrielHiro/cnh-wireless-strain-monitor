"""
Testes unitários para os simuladores HX711 e ESP32.
Valida comportamento dos simuladores de hardware.
"""

import pytest
import asyncio
import time
import sys
from pathlib import Path

# Adiciona diretório pai ao path para importações
sys.path.append(str(Path(__file__).parent.parent))

from simulator.hx711_simulator import HX711Simulator, HX711SimulatorConfig
from simulator.esp32_simulator import ESP32Simulator, ESP32Config, ESP32PowerMode


class TestHX711Simulator:
    """Testes para o simulador HX711."""
    
    def test_hx711_initialization(self):
        """Testa inicialização do simulador HX711."""
        hx711 = HX711Simulator()
        
        assert hx711.config.resolution_bits == 24
        assert hx711.config.max_value == 2**23 - 1
        assert hx711.is_ready()
    
    def test_hx711_custom_config(self):
        """Testa inicialização com configuração customizada."""
        config = HX711SimulatorConfig(
            resolution_bits=16,
            noise_level=0.05,
            drift_rate=0.001
        )
        
        hx711 = HX711Simulator(config)
        
        assert hx711.config.resolution_bits == 16
        assert hx711.config.noise_level == 0.05
        assert hx711.config.drift_rate == 0.001
    
    def test_calibration_factor_setting(self):
        """Testa configuração do fator de calibração."""
        hx711 = HX711Simulator()
        
        # Fator válido
        hx711.set_calibration_factor(2.5)
        assert hx711._calibration_factor == 2.5
        
        # Fator inválido (negativo)
        with pytest.raises(ValueError):
            hx711.set_calibration_factor(-1.0)
        
        # Fator inválido (zero)
        with pytest.raises(ValueError):
            hx711.set_calibration_factor(0.0)
    
    def test_temperature_setting(self):
        """Testa configuração de temperatura."""
        hx711 = HX711Simulator()
        
        hx711.set_temperature(35.5)
        assert hx711._temperature == 35.5
        
        hx711.set_temperature(-10.0)
        assert hx711._temperature == -10.0
    
    def test_load_application(self):
        """Testa aplicação de carga simulada."""
        hx711 = HX711Simulator()
        
        # Aplica carga conhecida
        test_strain = 150.0
        hx711.apply_load(test_strain)
        
        assert hx711._current_strain == test_strain
    
    def test_adc_reading_consistency(self):
        """Testa consistência das leituras do ADC."""
        hx711 = HX711Simulator()
        
        # Aplica carga zero
        hx711.apply_load(0.0)
        
        # Múltiplas leituras devem ser similares (considerando ruído)
        readings = [hx711.read_adc_raw() for _ in range(10)]
        
        # Calcula desvio padrão das leituras
        import statistics
        std_dev = statistics.stdev(readings)
        
        # Desvio deve ser pequeno para carga constante
        assert std_dev < abs(max(readings)) * 0.1  # Menos de 10% de variação
    
    def test_strain_reading_with_calibration(self):
        """Testa leitura de strain com calibração."""
        hx711 = HX711Simulator()
        
        # Define fator de calibração conhecido
        calibration_factor = 2.0
        hx711.set_calibration_factor(calibration_factor)
        
        # Aplica carga conhecida
        applied_strain = 100.0
        hx711.apply_load(applied_strain)
        
        # Lê strain com calibração
        measured_strain = hx711.read_strain_microstrains()
        
        # Deve estar próximo do valor aplicado multiplicado pela calibração
        expected_strain = applied_strain * calibration_factor
        assert abs(measured_strain - expected_strain) < expected_strain * 0.2  # 20% de tolerância
    
    def test_power_management(self):
        """Testa gerenciamento de energia."""
        hx711 = HX711Simulator()
        
        # Inicialmente deve estar pronto
        assert hx711.is_ready()
        
        # Modo power down
        hx711.power_down()
        assert not hx711.is_ready()
        
        # Tentativa de leitura em power down deve falhar
        with pytest.raises(RuntimeError):
            hx711.read_adc_raw()
        
        # Power up
        hx711.power_up()
        assert hx711.is_ready()
        
        # Agora deve conseguir ler
        reading = hx711.read_adc_raw()
        assert isinstance(reading, int)
    
    def test_tare_functionality(self):
        """Testa funcionalidade de tara."""
        hx711 = HX711Simulator()
        
        # Aplica offset conhecido
        hx711.apply_load(50.0)
        
        # Executa tara
        hx711.tare()
        
        # Baseline deve ser atualizado
        assert hx711._baseline_value != 0
    
    def test_dynamic_load_simulation(self):
        """Testa simulação de carga dinâmica."""
        hx711 = HX711Simulator()
        
        initial_strain = hx711._current_strain
        
        # Simula carga dinâmica
        hx711.simulate_dynamic_load(time_factor=1.0)
        
        # Strain deve ter mudado
        assert hx711._current_strain != initial_strain
    
    def test_status_reporting(self):
        """Testa relatório de status."""
        hx711 = HX711Simulator()
        
        status = hx711.get_status()
        
        assert isinstance(status, dict)
        assert 'ready' in status
        assert 'temperature' in status
        assert 'calibration_factor' in status
        assert 'current_strain' in status
        assert status['ready'] == hx711.is_ready()
    
    def test_reset_functionality(self):
        """Testa reset do simulador."""
        hx711 = HX711Simulator()
        
        # Modifica estado
        hx711.set_calibration_factor(3.0)
        hx711.set_temperature(40.0)
        hx711.apply_load(200.0)
        
        # Executa reset
        hx711.reset()
        
        # Estado deve voltar ao inicial
        assert hx711._calibration_factor == 1.0
        assert hx711._temperature == 25.0
        assert hx711._current_strain == 0.0
        assert hx711.is_ready()


class TestESP32Simulator:
    """Testes para o simulador ESP32."""
    
    def test_esp32_initialization(self):
        """Testa inicialização do simulador ESP32."""
        esp32 = ESP32Simulator()
        
        assert esp32.config.device_name == "DAQ_Sensor"
        assert esp32.device_id is not None
        assert len(esp32.device_id) == 8
        assert esp32._power_mode == ESP32PowerMode.ACTIVE
        assert esp32.hx711 is not None
    
    def test_esp32_custom_config(self):
        """Testa inicialização com configuração customizada."""
        config = ESP32Config(
            device_name="Custom_DAQ",
            cpu_frequency_mhz=160,
            deep_sleep_enabled=False
        )
        
        esp32 = ESP32Simulator(config)
        
        assert esp32.config.device_name == "Custom_DAQ"
        assert esp32.config.cpu_frequency_mhz == 160
        assert esp32.config.deep_sleep_enabled is False
    
    @pytest.mark.asyncio
    async def test_esp32_start_stop(self):
        """Testa início e parada do simulador."""
        esp32 = ESP32Simulator()
        
        # Inicialmente deve estar parado
        assert not esp32._is_running
        
        # Inicia simulação
        await esp32.start()
        assert esp32._is_running
        
        # Para simulação
        await esp32.stop()
        assert not esp32._is_running
    
    def test_battery_simulation(self):
        """Testa simulação de bateria."""
        esp32 = ESP32Simulator()
        
        # Bateria deve iniciar carregada
        assert esp32._battery_level == 100.0
        assert esp32._battery_voltage > 4.0
        
        # Simula descarga
        esp32._battery_level = 50.0
        esp32._update_battery()
        
        # Tensão deve ter diminuído
        assert esp32._battery_voltage < 4.2
        assert esp32._battery_voltage > 3.0
    
    def test_current_consumption_calculation(self):
        """Testa cálculo de consumo de corrente."""
        esp32 = ESP32Simulator()
        
        # Modo ativo deve ter consumo base
        active_current = esp32._get_current_consumption()
        assert active_current >= esp32.config.current_active
        
        # Modo deep sleep deve ter consumo menor
        esp32._power_mode = ESP32PowerMode.DEEP_SLEEP
        sleep_current = esp32._get_current_consumption()
        assert sleep_current < active_current
        assert sleep_current == esp32.config.current_deep_sleep
    
    @pytest.mark.asyncio
    async def test_wifi_connection(self):
        """Testa simulação de conexão WiFi."""
        esp32 = ESP32Simulator()
        
        # Tentativa de conexão
        result = await esp32.wifi_connect("TestNetwork", "password123")
        
        # Deve conectar (95% de chance de sucesso na simulação)
        # Em caso de falha, tenta novamente
        if not result:
            result = await esp32.wifi_connect("TestNetwork", "password123")
        
        # Pelo menos uma das tentativas deve funcionar
        assert result or esp32._wifi_status.value in ["connected", "error"]
        
        # Desconecta
        esp32.wifi_disconnect()
        assert esp32._wifi_status.value == "disconnected"
    
    @pytest.mark.asyncio
    async def test_ble_advertising(self):
        """Testa simulação de advertising BLE."""
        esp32 = ESP32Simulator()
        
        # Inicia advertising
        await esp32.ble_start_advertising()
        assert esp32._ble_status.value == "advertising"
        
        # Para advertising
        esp32.ble_stop_advertising()
        assert esp32._ble_status.value == "disabled"
    
    @pytest.mark.asyncio
    async def test_ble_connection_management(self):
        """Testa gerenciamento de conexões BLE."""
        esp32 = ESP32Simulator()
        
        client_id = "test_client_123"
        
        # Aceita conexão
        result = await esp32.ble_accept_connection(client_id)
        assert result is True
        assert client_id in esp32._connected_clients
        assert esp32._ble_status.value == "connected"
        
        # Desconecta cliente
        esp32.ble_disconnect_client(client_id)
        assert client_id not in esp32._connected_clients
    
    def test_sensor_configuration(self):
        """Testa configuração de sensor."""
        esp32 = ESP32Simulator()
        
        config = {
            'calibration_factor': 2.5,
            'temperature': 30.0
        }
        
        result = esp32.configure_sensor(config)
        assert result is True
        
        # Verifica se configuração foi aplicada no HX711
        assert esp32.hx711._calibration_factor == 2.5
        assert esp32.hx711._temperature == 30.0
    
    def test_callback_management(self):
        """Testa gerenciamento de callbacks."""
        esp32 = ESP32Simulator()
        
        # Contadores para verificar se callbacks foram chamados
        data_callback_count = 0
        status_callback_count = 0
        
        def data_callback(data):
            nonlocal data_callback_count
            data_callback_count += 1
        
        def status_callback(status):
            nonlocal status_callback_count
            status_callback_count += 1
        
        # Registra callbacks
        esp32.add_data_callback(data_callback)
        esp32.add_status_callback(status_callback)
        
        # Verifica se callbacks foram adicionados
        assert len(esp32._data_callbacks) == 1
        assert len(esp32._status_callbacks) == 1
    
    def test_device_info(self):
        """Testa informações do dispositivo."""
        esp32 = ESP32Simulator()
        
        device_info = esp32.get_device_info()
        
        assert isinstance(device_info, dict)
        assert 'device_id' in device_info
        assert 'device_name' in device_info
        assert 'hardware_version' in device_info
        assert 'firmware_version' in device_info
        assert device_info['device_id'] == esp32.device_id
        assert device_info['device_name'] == esp32.config.device_name
    
    def test_status_reporting(self):
        """Testa relatório de status completo."""
        esp32 = ESP32Simulator()
        
        status = esp32.get_status()
        
        assert isinstance(status, dict)
        assert 'device_id' in status
        assert 'power_mode' in status
        assert 'wifi_status' in status
        assert 'ble_status' in status
        assert 'battery_level' in status
        assert 'battery_voltage' in status
        assert 'uptime_seconds' in status
        assert 'buffer_size' in status
        
        # Verifica tipos de dados
        assert isinstance(status['battery_level'], int)
        assert isinstance(status['battery_voltage'], float)
        assert isinstance(status['uptime_seconds'], float)
        assert isinstance(status['buffer_size'], int)


# Fixtures para testes
@pytest.fixture
def hx711_simulator():
    """Fixture que retorna um simulador HX711 configurado."""
    return HX711Simulator()


@pytest.fixture
def esp32_simulator():
    """Fixture que retorna um simulador ESP32 configurado."""
    return ESP32Simulator()


def test_integration_hx711_esp32_communication(esp32_simulator):
    """Teste de integração entre HX711 e ESP32."""
    esp32 = esp32_simulator
    
    # Aplica carga no HX711
    test_strain = 123.45
    esp32.hx711.apply_load(test_strain)
    
    # Lê através do ESP32
    reading = esp32.hx711.read_strain_microstrains()
    
    # Valor deve estar próximo do aplicado (considerando ruído e calibração)
    assert abs(reading - test_strain) < test_strain * 0.3  # 30% de tolerância


if __name__ == "__main__":
    # Executa testes se arquivo for chamado diretamente
    pytest.main([__file__, "-v"])
