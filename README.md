# Sistema DAQ - Aquisição de Dados para Análise de Fadiga

Sistema de aquisição de dados sem fio para análise de fadiga em máquinas agrícolas, desenvolvido como projeto de TCC. Inclui simulador completo para desenvolvimento e testes sem necessidade de hardware.

## 🚀 Características

- **Simulação Completa**: Simula ESP32, HX711, sensores de strain e cenários de carga
- **Interface Gráfica**: Interface PyQt5 com gráficos em tempo real
- **Comunicação**: Bluetooth LE e WiFi simulados
- **Análise de Dados**: Exportação para CSV, JSON e Excel
- **Modular**: Arquitetura bem estruturada e testada
- **Documentação**: Exemplos completos e documentação técnica

## 📋 Pré-requisitos

- Python 3.8+
- Sistema operacional: Windows, Linux ou macOS
- Memória RAM: 4GB mínimo
- Espaço em disco: 100MB

## 🔧 Instalação

### 1. Clone ou baixe o projeto
```bash
git clone <repositorio>
cd daq_system
```

### 2. Crie ambiente virtual (recomendado)
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### 3. Instale dependências
```bash
pip install -r requirements.txt
```

### 4. Verificação da instalação
```bash
python -m pytest tests/ -v
```

## 🖥️ Modos de Execução

### Interface Gráfica (Recomendado)
```bash
python run.py gui
```
Interface completa com:
- Gráficos em tempo real
- Controles de simulação
- Exportação de dados
- Monitor de status

### Linha de Comando
```bash
# Execução básica
python run.py cli

# Com parâmetros personalizados
python run.py cli --name "Campo_Teste" --scenario harvest --speed 2.0

# Exportação automática
python run.py cli --export csv --duration 300
```

### Apenas Simulador
```bash
# Simulação rápida
python run.py simulator --scenario field_work_heavy --duration 120

# Com saída personalizada
python run.py simulator --output dados_teste.json --speed 5.0
```

## 📊 Cenários de Simulação

| Cenário | Descrição | Strain Típico |
|---------|-----------|---------------|
| `idle` | Máquina parada | ±10 µε |
| `transport` | Transporte em estrada | ±50 µε |
| `field_work_light` | Trabalho leve no campo | ±200 µε |
| `field_work_heavy` | Trabalho pesado | ±500 µε |
| `harvest` | Operação de colheita | ±800 µε |
| `overload` | Sobrecarga crítica | ±1200 µε |

## 🏗️ Arquitetura do Sistema

```
daq_system/
├── src/                    # Código principal
│   ├── core/              # Modelos e configuração
│   ├── communication/     # Protocolos BLE/WiFi
│   └── data/              # Gerenciamento de dados
├── simulator/             # Simuladores de hardware
├── tests/                 # Testes unitários
├── docs/                  # Documentação técnica
└── examples/              # Exemplos de uso
```

## 📡 Comunicação

### Bluetooth LE
- **Service UUID**: `12345678-1234-5678-9ABC-123456789ABC`
- **Characteristic**: Leitura/escrita de dados
- **Protocolo**: Pacotes binários com timestamp

### WiFi (Simulado)
- **Protocolo**: HTTP REST API
- **Endpoints**: `/data`, `/status`, `/config`
- **Formato**: JSON

## 💾 Formato de Dados

### Leitura de Strain
```python
{
    "timestamp": "2024-01-15T10:30:45.123456",
    "strain": 245.67,           # µε (microstrains)
    "raw_adc": 2048,           # Valor ADC bruto
    "temperature": 23.4,        # °C
    "sensor_id": "HX711_001",
    "battery_level": 85.2       # %
}
```

### Exportação
- **CSV**: Dados tabulares para análise estatística
- **JSON**: Estrutura completa com metadados
- **Excel**: Múltiplas planilhas com gráficos

## 🧪 Testes

### Executar todos os testes
```bash
python -m pytest tests/ -v
```

### Testes específicos
```bash
# Apenas modelos
python -m pytest tests/test_models.py -v

# Apenas simuladores
python -m pytest tests/test_simulators.py -v

# Com cobertura
python -m pytest tests/ --cov=src --cov-report=html
```

## 📈 Exemplos de Uso

### Exemplo Básico
```python
from simulator import DAQSystemSimulator, SimulatorConfig

# Configuração
config = SimulatorConfig(
    device_name="Teste_Fadiga",
    simulation_speed=2.0,
    enable_ble=True
)

# Simulador
simulator = DAQSystemSimulator(config)
await simulator.start()

# Dados em tempo real
async for reading in simulator.data_stream():
    print(f"Strain: {reading.strain:+7.2f} µε")
```

### Análise de Dados
```python
from src.data import DataManager

# Carrega dados
manager = DataManager()
readings = manager.get_readings_by_timerange(
    start_time=datetime.now() - timedelta(hours=1)
)

# Estatísticas
stats = manager.calculate_statistics(readings)
print(f"Strain médio: {stats['mean']:.2f} µε")
print(f"Pico máximo: {stats['max']:.2f} µε")
```

### Configuração Avançada
```python
from src.core.models import SensorConfiguration

# Configuração personalizada
config = SensorConfiguration(
    sample_rate=100,           # Hz
    filter_enabled=True,
    filter_cutoff=10.0,        # Hz
    calibration_factor=1.234,
    gain=128,
    offset_compensation=True
)

await simulator.configure_sensor(config)
```

## 🔧 Troubleshooting

### Problemas Comuns

**Erro de importação PyQt5**
```bash
pip install PyQt5 PyQt5-tools
# ou no Ubuntu/Debian:
sudo apt-get install python3-pyqt5
```

**Erro de comunicação BLE**
```bash
pip install bleak
# Verificar se Bluetooth está habilitado
```

**Erro ao executar testes**
```bash
pip install pytest pytest-asyncio
python -m pytest --tb=short
```

### Logs e Debug

**Habilitar logs detalhados**
```bash
python run.py cli --verbose
```

**Logs do simulador**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 👥 Autores

- **Gabriel Hiro Furukawa**
- **Rafael Perassi Zanchetta**

## 🤝 Contribuição

### Estrutura de Desenvolvimento
1. **Fork** do repositório
2. **Clone** local
3. **Branch** para features: `git checkout -b feature/nova-funcionalidade`
4. **Commit** com mensagens descritivas
5. **Push** e **Pull Request**

### Padrões de Código
- **PEP 8** para formatação
- **Type hints** obrigatórios
- **Docstrings** em todas as funções
- **Testes** para novas funcionalidades

## 📄 Licença

Este projeto é desenvolvido como Trabalho de Conclusão de Curso (TCC) e está disponível para fins educacionais e de pesquisa.

## 📞 Contato e Suporte

- **Issues**: Use o sistema de issues do GitHub
- **Documentação**: Veja a pasta `docs/` para detalhes técnicos

---

## 🎯 Próximos Passos

- [ ] Interface web complementar
- [ ] Integração com hardware real
- [ ] Análise de fadiga avançada
- [ ] Machine Learning para predição
- [ ] API REST completa

## 📚 Referências

1. Norma ASTM E1049 - Práticas para análise de fadiga
2. IEEE 802.15.1 - Especificação Bluetooth
3. Documentação ESP32 - Espressif Systems
4. HX711 Datasheet - Avia Semiconductor
