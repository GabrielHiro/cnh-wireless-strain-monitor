# Documentação Técnica - Sistema DAQ

## Visão Geral

O Sistema DAQ (Data Acquisition) é uma solução completa para aquisição de dados de deformação (*strain*) em máquinas agrícolas, desenvolvida como parte do TCC para CNH Industrial.

## Arquitetura do Sistema

### Componentes Principais

1. **Nó Sensor (Hardware/Simulado)**
   - ESP32: Microcontrolador principal
   - HX711: Conversor ADC para strain gauges
   - Bateria LiPo com gerenciamento de energia
   - Comunicação BLE/WiFi

2. **Estação Receptora (Software)**
   - Interface para descoberta e conexão de sensores
   - Coleta e armazenamento de dados
   - Exportação para análise
   - Interface gráfica de monitoramento

3. **Simulador Completo**
   - Simula comportamento realístico sem hardware
   - Múltiplos cenários de carga
   - Testes automatizados

## Especificações Técnicas

### Hardware Simulado

#### ESP32 Simulator
- **CPU**: 240 MHz (simulado)
- **Conectividade**: WiFi 802.11 b/g/n + BLE 4.2
- **Modos de Energia**:
  - Ativo: 240 mA
  - WiFi TX: +170 mA
  - BLE TX: +12 mA
  - Deep Sleep: 5 µA
- **Bateria**: LiPo 3.7V, 2000 mAh simulado

#### HX711 Simulator
- **Resolução**: 24 bits
- **Taxa de Amostragem**: Configurável (padrão: 100ms)
- **Faixa ADC**: -8,388,608 a +8,388,607
- **Ruído Simulado**: 0.1% do valor lido
- **Deriva Térmica**: 0.02%/°C

### Protocolo de Comunicação

#### Formato da Mensagem
```
[HEADER 8 bytes][PAYLOAD variável]

HEADER:
- Magic Number (2 bytes): 0xDACC
- Message Type (1 byte): Tipo da mensagem
- Compression (1 byte): Tipo de compressão
- Payload Length (2 bytes): Tamanho do payload
- Checksum (2 bytes): CRC16 do payload
```

#### Tipos de Mensagem
- `0x01`: PING
- `0x02`: PONG
- `0x10`: CONNECT/DISCONNECT
- `0x20-0x22`: Configuração
- `0x30-0x32`: Dados
- `0x40-0x41`: Status
- `0x50`: Erro

### Estrutura de Dados

#### StrainReading
```python
@dataclass
class StrainReading:
    timestamp: datetime
    strain_value: float        # microstrains (µε)
    raw_adc_value: int
    sensor_id: str
    battery_level: int         # 0-100%
    temperature: float         # °C
    checksum: str             # Verificação integridade
```

#### SensorConfiguration
```python
@dataclass
class SensorConfiguration:
    sensor_id: str
    sampling_rate_ms: int      # Taxa de amostragem
    transmission_interval_s: int
    calibration_factor: float
    offset: float
    deep_sleep_enabled: bool
    wifi_ssid: Optional[str]
    wifi_password: Optional[str]
```

## Cenários de Simulação

### Cenários Pré-definidos

1. **idle**: Máquina parada
   - Strain base: 0 µε
   - Amplitude: ±5 µε
   - Frequência: 0.1 Hz

2. **transport**: Transporte em estrada
   - Strain base: 10 µε
   - Amplitude: ±30 µε
   - Frequência: 2.0 Hz

3. **field_work_light**: Trabalho leve
   - Strain base: 50 µε
   - Amplitude: ±100 µε
   - Frequência: 1.5 Hz

4. **field_work_heavy**: Trabalho pesado
   - Strain base: 200 µε
   - Amplitude: ±300 µε
   - Frequência: 3.0 Hz

5. **harvest**: Operação de colheita
   - Strain base: 150 µε
   - Amplitude: ±250 µε
   - Frequência: 4.0 Hz

6. **overload**: Sobrecarga
   - Strain base: 400 µε
   - Amplitude: ±200 µε
   - Frequência: 1.0 Hz

## API de Uso

### Simulador Principal

```python
from simulator import DAQSystemSimulator, SimulatorConfig

# Configuração
config = SimulatorConfig(
    device_name="Meu_DAQ",
    simulation_speed=2.0,    # 2x mais rápido
    enable_ble=True,
    realistic_loads=True
)

# Inicialização
simulator = DAQSystemSimulator(config)

# Callbacks
async def on_data(reading):
    print(f"Strain: {reading.strain_value:.2f} µε")

simulator.add_data_callback(on_data)

# Execução
await simulator.start()

# Controle de cenários
simulator.set_load_scenario("field_work_heavy")
simulator.apply_custom_load(250.0)  # µε

await simulator.stop()
```

### Gerenciamento de Dados

```python
from src.data import DataManager

# Inicialização
data_mgr = DataManager()

# Adicionar dados
data_mgr.add_reading(strain_reading)

# Buscar dados recentes
recent_data = data_mgr.get_recent_readings(
    sensor_id="DAQ_001",
    minutes=60,
    max_count=1000
)

# Exportar dados
data_mgr.export_data(
    format_type="csv",
    output_path=Path("strain_data.csv"),
    sensor_id="DAQ_001"
)

# Estatísticas
stats = data_mgr.get_statistics()
print(f"Total de leituras: {stats['total_readings']}")
```

### Comunicação BLE

```python
from src.communication import BLESimulator

ble = BLESimulator()

# Callbacks
def on_device_found(device):
    print(f"Dispositivo encontrado: {device.name}")

def on_data_received(address, data):
    print(f"Dados de {address}: {len(data)} bytes")

ble.add_scan_callback(on_device_found)
ble.add_data_callback(on_data_received)

# Descoberta
await ble.start_scan(timeout=10.0)

# Conexão
devices = ble.discovered_devices
if devices:
    address = list(devices.keys())[0]
    success = await ble.connect(address)
    
    if success:
        # Enviar comando
        ping_msg = create_ping_message()
        await ble.send_data(address, ping_msg)
```

## Configuração e Execução

### Pré-requisitos

```bash
# Python 3.8+
pip install -r requirements.txt
```

### Dependências Principais
- `asyncio`: Programação assíncrona
- `sqlite3`: Banco de dados
- `dataclasses`: Estruturas de dados
- `json`: Serialização
- `struct`: Protocolo binário

### Dependências Opcionais
- `pytest`: Testes automatizados
- `pandas`: Exportação Excel
- `matplotlib`: Visualização
- `PyQt5`: Interface gráfica

### Execução do Simulador

```bash
# Simulador básico
python -m simulator.main

# Com parâmetros
python -m simulator.main --name "DAQ_Field_Test" --speed 1.5 --scenario transport

# Sem BLE
python -m simulator.main --no-ble

# Com WiFi
python -m simulator.main --wifi
```

### Testes

```bash
# Todos os testes
pytest tests/ -v

# Testes específicos
pytest tests/test_models.py -v
pytest tests/test_simulators.py -v

# Com cobertura
pytest tests/ --cov=src --cov=simulator --cov-report=html
```

## Calibração e Validação

### Calibração de Strain Gauges

1. **Tara (Zero)**:
   ```python
   hx711.tare()  # Remove offset atual
   ```

2. **Aplicação de Carga Conhecida**:
   ```python
   # Aplicar peso/força conhecida
   # Medir valor ADC resultante
   known_strain = 1000.0  # µε
   adc_reading = hx711.read_adc_raw()
   
   # Calcular fator de calibração
   calibration_factor = known_strain / adc_reading
   hx711.set_calibration_factor(calibration_factor)
   ```

3. **Validação**:
   ```python
   # Verificar linearidade com múltiplas cargas
   test_loads = [0, 500, 1000, 1500, 2000]  # µε
   for load in test_loads:
       apply_physical_load(load)
       measured = hx711.read_strain_microstrains()
       error = abs(measured - load) / load * 100
       print(f"Carga: {load} µε, Medido: {measured:.2f} µε, Erro: {error:.2f}%")
   ```

### Validação do Sistema

1. **Teste de Comunicação**:
   - Verificar alcance BLE/WiFi
   - Medir latência de transmissão
   - Validar integridade dos pacotes

2. **Teste de Autonomia**:
   - Monitorar consumo de bateria
   - Verificar funcionamento do deep sleep
   - Testar recuperação após descarga

3. **Teste de Campo**:
   - Comparar com instrumentação cabeada
   - Verificar resistência a interferências
   - Validar em condições ambientais reais

## Troubleshooting

### Problemas Comuns

1. **Leituras Instáveis**:
   - Verificar conexões do strain gauge
   - Ajustar filtros de ruído
   - Verificar aterramento

2. **Perda de Comunicação**:
   - Verificar alcance do sinal
   - Verificar interferências
   - Verificar nível da bateria

3. **Deriva de Valores**:
   - Verificar temperatura ambiente
   - Verificar fixação do sensor
   - Executar nova calibração

4. **Falhas de Sincronização**:
   - Verificar sincronização de tempo
   - Verificar sequência de pacotes
   - Verificar buffer de dados

### Logs e Diagnóstico

```python
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Habilitar logs detalhados
logger = logging.getLogger('daq_system')
logger.setLevel(logging.DEBUG)
```

## Limitações e Considerações

### Limitações Atuais

1. **Simulador**:
   - Não simula interferências reais
   - Ruído simplificado
   - Não simula falhas de hardware

2. **Comunicação**:
   - Implementação BLE básica
   - Sem criptografia
   - Sem redundância de dados

3. **Armazenamento**:
   - SQLite para prototipagem
   - Sem backup automático
   - Retenção limitada por espaço

### Melhorias Futuras

1. **Hardware Real**:
   - Integração com ESP32 físico
   - Calibração automática
   - Proteção contra sobretensão

2. **Comunicação Avançada**:
   - Protocolo seguro (TLS)
   - Múltiplos canais
   - Mesh networking

3. **Análise de Dados**:
   - Detecção automática de fadiga
   - Predição de falhas
   - Análise espectral

4. **Interface de Usuário**:
   - Dashboard web
   - Aplicativo móvel
   - Alertas em tempo real

## Referências

- ESP32 Technical Reference Manual
- HX711 Datasheet  
- Bluetooth Low Energy Specification
- IEEE 802.11 WiFi Standards
- Strain Gauge Measurement Guidelines
- CNH Industrial Engineering Standards
