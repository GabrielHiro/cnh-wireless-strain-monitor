# Estrutura de Saída de Dados para Visualizador Osciloscópio

## Visão Geral

O sistema DAQ foi projetado para fornecer dados otimizados especificamente para visualização em tempo real tipo osciloscópio. Os dados são estruturados para máxima performance em gráficos, sem necessidade de processamento adicional.

## Formatos de Saída

### 1. Dados de Traço (Trace Data)

**Endpoint:** `oscilloscope_api.get_trace_data(sensor_id)`

```json
{
  "sensor_id": "STRAIN_001",
  "times": [1623456789123, 1623456789133, 1623456789143, ...],
  "values": [125.45, 127.32, 124.88, ...],
  "point_count": 1000,
  "time_span": 10.0,
  "y_min": 98.12,
  "y_max": 156.78,
  "y_range": 58.66,
  "last_update": 1623456789999
}
```

**Características:**
- `times`: Array de timestamps em milissegundos (formato Unix)
- `values`: Array de valores de deformação em microstrains (µε)
- Arrays sincronizados: `times[i]` corresponde a `values[i]`
- Otimizado para plotagem direta (sem parsing adicional)

### 2. Snapshot em Tempo Real

**Endpoint:** `oscilloscope_api.get_realtime_snapshot()`

```json
{
  "timestamp": 1623456789999,
  "active_sensors": 3,
  "total_points": 2847,
  "sensors": {
    "STRAIN_001": {
      "current_value": 125.45,
      "timestamp": 1623456789123,
      "battery": 87,
      "temperature": 24.5,
      "raw_adc": 32890,
      "min_value": 98.12,
      "max_value": 156.78,
      "avg_value": 127.35,
      "point_count": 1000
    },
    "STRAIN_002": {
      // ... dados similares
    }
  }
}
```

### 3. Dados de Streaming Incremental

**Endpoint:** `oscilloscope_api.get_streaming_data(sensor_id, since_timestamp)`

```json
{
  "sensor_id": "STRAIN_001",
  "new_points": 5,
  "data": [
    {"t": 1623456789123, "v": 125.45, "r": 32890, "b": 87, "temp": 24.5},
    {"t": 1623456789133, "v": 127.32, "r": 32910, "b": 87, "temp": 24.5},
    // ... mais pontos
  ],
  "latest_timestamp": 1623456789183,
  "has_more": true
}
```

**Estrutura dos pontos:**
- `t`: Timestamp em milissegundos
- `v`: Valor de deformação (µε)
- `r`: Valor bruto do ADC
- `b`: Nível da bateria (%)
- `temp`: Temperatura (°C)

### 4. Formato WebSocket

**Para aplicações web em tempo real:**

```json
{
  "type": "realtime_snapshot",
  "data": {
    // ... dados do snapshot
  },
  "client_count": 2
}
```

```json
{
  "type": "trace_update", 
  "sensor_id": "STRAIN_001",
  "data": {
    // ... dados incrementais
  }
}
```

## Especificações Técnicas

### Frequência de Atualização
- **Dados brutos:** 100 Hz por sensor
- **Streaming:** Até 50 Hz (configurável)
- **WebSocket:** 10-30 Hz (otimizado para web)

### Capacidade de Buffer
- **Memória:** 1000 pontos por sensor (10 segundos a 100Hz)
- **Persistência:** Ilimitada (banco SQLite)
- **Decimação:** Automática para visualização

### Formatos de Exportação

#### CSV (Para análise)
```csv
timestamp_ms,strain_value
1623456789123,125.45
1623456789133,127.32
...
```

#### JSON (Para integração)
```json
{
  "metadata": {
    "exported_at": "2023-06-12T10:30:00Z",
    "total_readings": 1000,
    "system": "Sistema DAQ"
  },
  "readings": [...]
}
```

#### Binário (Para performance)
- Formato: Float64 (timestamp_ms, value) por ponto
- 16 bytes por ponto de dados
- Ideal para aplicações de alta performance

## Implementação no Visualizador

### Estrutura Recomendada

```javascript
// Exemplo JavaScript para aplicação web
class OscilloscopeVisualizer {
  constructor(apiEndpoint) {
    this.apiEndpoint = apiEndpoint;
    this.traces = new Map();
    this.lastTimestamp = 0;
  }
  
  async updateTrace(sensorId) {
    const response = await fetch(
      `${this.apiEndpoint}/streaming/${sensorId}?since=${this.lastTimestamp}`
    );
    const data = await response.json();
    
    if (data.new_points > 0) {
      this.addPointsToTrace(sensorId, data.data);
      this.lastTimestamp = data.latest_timestamp;
    }
  }
  
  addPointsToTrace(sensorId, points) {
    // points já estão no formato otimizado
    const times = points.map(p => p.t);
    const values = points.map(p => p.v);
    
    // Adiciona diretamente ao gráfico
    this.plotly.extendTraces('chart', {
      x: [times],
      y: [values]
    }, [sensorId]);
  }
}
```

### Integração com Chart.js

```javascript
// Configuração otimizada para Chart.js
const chartConfig = {
  type: 'line',
  data: {
    datasets: [{
      label: 'Strain (µε)',
      data: [], // Preenchido com [{x: timestamp, y: value}, ...]
      borderColor: 'rgb(75, 192, 192)',
      tension: 0.1
    }]
  },
  options: {
    responsive: true,
    animation: false, // Importante para tempo real
    scales: {
      x: {
        type: 'linear',
        position: 'bottom',
        title: { display: true, text: 'Tempo (ms)' }
      },
      y: {
        title: { display: true, text: 'Deformação (µε)' }
      }
    },
    plugins: {
      streaming: {
        duration: 10000, // 10 segundos
        refresh: 100,    // 100ms
        delay: 0
      }
    }
  }
};
```

### Integração com Plotly.js

```javascript
// Configuração para Plotly.js
const plotlyConfig = {
  data: [{
    x: [], // timestamps
    y: [], // valores
    type: 'scatter',
    mode: 'lines',
    name: 'Strain'
  }],
  layout: {
    title: 'Deformação em Tempo Real',
    xaxis: { title: 'Tempo (ms)' },
    yaxis: { title: 'Deformação (µε)' },
    showlegend: true
  },
  config: {
    responsive: true,
    displayModeBar: false
  }
};

// Atualização em tempo real
setInterval(() => {
  fetch('/api/oscilloscope/streaming/STRAIN_001')
    .then(response => response.json())
    .then(data => {
      if (data.new_points > 0) {
        const times = data.data.map(p => p.t);
        const values = data.data.map(p => p.v);
        
        Plotly.extendTraces('chart', {
          x: [times],
          y: [values]
        }, [0]);
      }
    });
}, 100); // Atualização a cada 100ms
```

## Considerações de Performance

### Para Aplicações Desktop
- Use formato binário para máxima performance
- Implemente decimação no cliente se necessário
- Cache dados localmente para zoom/pan

### Para Aplicações Web
- Use WebSocket para streaming contínuo
- Limite pontos visíveis (1000-2000 máximo)
- Implemente throttling de atualizações

### Para Análise Offline
- Use exportação CSV/JSON
- Processe lotes grandes via API de database
- Implemente paginação para datasets grandes

## Exemplo de Integração Completa

```python
# Servidor lado Python
from src.data import DataManager, OscilloscopeAPI

# Inicialização
data_manager = DataManager()
osc_api = OscilloscopeAPI(data_manager)

# Configuração
osc_api.set_config(
    time_window_seconds=10.0,
    max_points=1000,
    sample_rate_hz=100.0
)

# Endpoint Flask de exemplo
@app.route('/api/oscilloscope/trace/<sensor_id>')
def get_trace(sensor_id):
    trace_data = osc_api.get_trace_data(sensor_id)
    return jsonify(trace_data)

@app.route('/api/oscilloscope/streaming/<sensor_id>')
def get_streaming(sensor_id):
    since = request.args.get('since', 0, type=float)
    streaming_data = osc_api.get_streaming_data(sensor_id, since)
    return jsonify(streaming_data)
```

Esta estrutura garante que:
1. ✅ Dados estão otimizados para gráficos
2. ✅ Não há necessidade de processamento adicional
3. ✅ Performance máxima para visualização em tempo real
4. ✅ Flexibilidade para diferentes tipos de visualizadores
5. ✅ Compatibilidade com bibliotecas gráficas populares
