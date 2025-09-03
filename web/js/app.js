// Sistema DAQ - JavaScript Application
class DAQSystem {
    constructor() {
        this.websocket = null;
        this.isConnected = false;
        this.isPaused = false;
        this.selectedSensor = 'strain_gauge_1';
        this.dataBuffer = new Map();
        this.maxBufferSize = 1000;
        this.plotData = [];
        this.lastUpdate = Date.now();
        
        this.initializeElements();
        this.setupEventListeners();
        this.initializePlot();
        this.updateStatus();
        
        console.log('DAQ System initialized');
        this.addLogEntry('Sistema inicializado', 'success');
    }

    initializeElements() {
        // Status elements
        this.connectionStatus = document.getElementById('connection-status');
        this.simulatorStatus = document.getElementById('simulator-status');
        
        // Buttons
        this.connectBtn = document.getElementById('connect-btn');
        this.startSimBtn = document.getElementById('start-sim-btn');
        this.autoScaleBtn = document.getElementById('auto-scale-btn');
        this.pauseBtn = document.getElementById('pause-btn');
        this.clearBtn = document.getElementById('clear-btn');
        this.exportCsvBtn = document.getElementById('export-csv-btn');
        this.exportJsonBtn = document.getElementById('export-json-btn');
        
        // Controls
        this.sensorSelect = document.getElementById('sensor-select');
        this.sampleRateInput = document.getElementById('sample-rate-input');
        this.timebaseSelect = document.getElementById('timebase-select');
        this.triggerLevel = document.getElementById('trigger-level');
        
        // Metrics
        this.sampleRateDisplay = document.getElementById('sample-rate');
        this.currentStrain = document.getElementById('current-strain');
        this.minValue = document.getElementById('min-value');
        this.maxValue = document.getElementById('max-value');
        this.rmsValue = document.getElementById('rms-value');
        this.bufferUsage = document.getElementById('buffer-usage');
        
        // Other elements
        this.sensorsListElement = document.getElementById('sensors-list');
        this.systemLog = document.getElementById('system-log');
    }

    setupEventListeners() {
        // Connection controls
        this.connectBtn.addEventListener('click', () => this.toggleConnection());
        this.startSimBtn.addEventListener('click', () => this.toggleSimulator());
        
        // Plot controls
        this.sensorSelect.addEventListener('change', (e) => {
            this.selectedSensor = e.target.value;
            this.updatePlot();
        });
        this.autoScaleBtn.addEventListener('click', () => this.autoScale());
        this.pauseBtn.addEventListener('click', () => this.togglePause());
        this.clearBtn.addEventListener('click', () => this.clearPlot());
        
        // Export controls
        this.exportCsvBtn.addEventListener('click', () => this.exportData('csv'));
        this.exportJsonBtn.addEventListener('click', () => this.exportData('json'));
        
        // Settings
        this.timebaseSelect.addEventListener('change', () => this.updateTimebase());
    }

    initializePlot() {
        const layout = {
            title: 'Osciloscópio Virtual - Strain em Tempo Real',
            xaxis: {
                title: 'Tempo (s)',
                type: 'linear',
                autorange: true,
                showgrid: true
            },
            yaxis: {
                title: 'Strain (µε)',
                autorange: true,
                showgrid: true
            },
            margin: { t: 50, r: 50, b: 50, l: 80 },
            plot_bgcolor: '#fafafa',
            paper_bgcolor: 'white',
            font: { family: 'Segoe UI, sans-serif', size: 12 }
        };

        const config = {
            displayModeBar: true,
            modeBarButtonsToRemove: ['lasso2d', 'select2d'],
            displaylogo: false,
            responsive: true
        };

        this.plotData = [{
            x: [],
            y: [],
            type: 'scatter',
            mode: 'lines',
            name: 'Strain',
            line: { color: '#3498db', width: 2 }
        }];

        Plotly.newPlot('oscilloscope', this.plotData, layout, config);
    }

    toggleConnection() {
        if (this.isConnected) {
            this.disconnect();
        } else {
            this.connect();
        }
    }

    connect() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;
            
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                this.isConnected = true;
                this.updateStatus();
                this.addLogEntry('Conectado ao servidor WebSocket', 'success');
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleIncomingData(data);
                } catch (error) {
                    console.error('Erro ao processar dados:', error);
                    this.addLogEntry('Erro ao processar dados recebidos', 'error');
                }
            };
            
            this.websocket.onclose = () => {
                this.isConnected = false;
                this.updateStatus();
                this.addLogEntry('Conexão WebSocket fechada', 'warning');
            };
            
            this.websocket.onerror = (error) => {
                console.error('Erro WebSocket:', error);
                this.addLogEntry('Erro na conexão WebSocket', 'error');
            };
            
        } catch (error) {
            console.error('Erro ao conectar:', error);
            this.addLogEntry('Falha ao estabelecer conexão', 'error');
        }
    }

    disconnect() {
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
        this.isConnected = false;
        this.updateStatus();
        this.addLogEntry('Desconectado do servidor', 'warning');
    }

    async toggleSimulator() {
        try {
            const response = await fetch('/api/simulator/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    device_name: "DAQ_SIM_001",
                    sensor_count: 3,
                    sampling_rate_hz: parseFloat(this.sampleRateInput.value),
                    scenario: "field_work_light",
                    noise_level: 0.05,
                    enable_ble: true,
                    enable_wifi: false
                })
            });
            
            if (response.ok) {
                this.addLogEntry('Simulador iniciado', 'success');
                this.updateSimulatorStatus('running');
            } else {
                throw new Error(`HTTP ${response.status}`);
            }
        } catch (error) {
            console.error('Erro ao controlar simulador:', error);
            this.addLogEntry('Erro ao iniciar simulador', 'error');
        }
    }

    handleIncomingData(data) {
        if (!this.isPaused && data.sensor_id === this.selectedSensor) {
            // Adicionar dados ao buffer
            if (!this.dataBuffer.has(data.sensor_id)) {
                this.dataBuffer.set(data.sensor_id, []);
            }
            
            const buffer = this.dataBuffer.get(data.sensor_id);
            const timestamp = new Date(data.timestamp).getTime() / 1000;
            
            buffer.push({
                x: timestamp,
                y: data.value,
                timestamp: data.timestamp
            });
            
            // Limitar tamanho do buffer
            if (buffer.length > this.maxBufferSize) {
                buffer.shift();
            }
            
            this.updatePlot();
            this.updateMetrics(data);
        }
    }

    updatePlot() {
        if (!this.dataBuffer.has(this.selectedSensor)) return;
        
        const buffer = this.dataBuffer.get(this.selectedSensor);
        const timebase = parseInt(this.timebaseSelect.value) / 1000; // Convert to seconds
        const now = Date.now() / 1000;
        
        // Filter data based on timebase
        const filteredData = buffer.filter(point => (now - point.x) <= timebase * 10);
        
        const updateData = {
            x: [filteredData.map(point => point.x)],
            y: [filteredData.map(point => point.y)]
        };
        
        Plotly.restyle('oscilloscope', updateData, [0]);
    }

    updateMetrics(data) {
        if (!this.dataBuffer.has(data.sensor_id)) return;
        
        const buffer = this.dataBuffer.get(data.sensor_id);
        const values = buffer.map(point => point.y);
        
        if (values.length === 0) return;
        
        // Calculate metrics
        const min = Math.min(...values);
        const max = Math.max(...values);
        const mean = values.reduce((a, b) => a + b, 0) / values.length;
        const rms = Math.sqrt(values.reduce((a, b) => a + b * b, 0) / values.length);
        
        // Calculate sample rate
        const now = Date.now();
        const timeDiff = (now - this.lastUpdate) / 1000;
        const sampleRate = timeDiff > 0 ? (1 / timeDiff).toFixed(1) : '0';
        this.lastUpdate = now;
        
        // Update displays
        this.currentStrain.textContent = data.value.toFixed(2);
        this.minValue.textContent = min.toFixed(2);
        this.maxValue.textContent = max.toFixed(2);
        this.rmsValue.textContent = rms.toFixed(2);
        this.sampleRateDisplay.textContent = sampleRate;
        
        // Buffer usage
        const usage = ((buffer.length / this.maxBufferSize) * 100).toFixed(1);
        this.bufferUsage.textContent = `${usage}%`;
    }

    updateStatus() {
        // Connection status
        this.connectionStatus.textContent = this.isConnected ? 'Conectado' : 'Desconectado';
        this.connectionStatus.className = `status ${this.isConnected ? 'connected' : ''}`;
        this.connectBtn.textContent = this.isConnected ? 'Desconectar' : 'Conectar';
    }

    updateSimulatorStatus(status) {
        this.simulatorStatus.textContent = status === 'running' ? 'Executando' : 'Parado';
        this.simulatorStatus.className = `status ${status === 'running' ? 'running' : ''}`;
    }

    togglePause() {
        this.isPaused = !this.isPaused;
        this.pauseBtn.textContent = this.isPaused ? 'Retomar' : 'Pausar';
        this.addLogEntry(this.isPaused ? 'Aquisição pausada' : 'Aquisição retomada', 'info');
    }

    clearPlot() {
        this.dataBuffer.clear();
        this.plotData[0].x = [];
        this.plotData[0].y = [];
        Plotly.redraw('oscilloscope');
        this.addLogEntry('Plot limpo', 'info');
    }

    autoScale() {
        Plotly.relayout('oscilloscope', {
            'xaxis.autorange': true,
            'yaxis.autorange': true
        });
        this.addLogEntry('Auto-scale aplicado', 'info');
    }

    updateTimebase() {
        this.updatePlot();
        const timebase = this.timebaseSelect.value;
        this.addLogEntry(`Base de tempo alterada para ${timebase}ms/div`, 'info');
    }

    async exportData(format) {
        try {
            const response = await fetch(`/api/data/export/${format}?sensorId=${this.selectedSensor}`);
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = `daq_data_${this.selectedSensor}_${new Date().toISOString().split('T')[0]}.${format}`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                this.addLogEntry(`Dados exportados em formato ${format.toUpperCase()}`, 'success');
            } else {
                throw new Error(`HTTP ${response.status}`);
            }
        } catch (error) {
            console.error('Erro ao exportar dados:', error);
            this.addLogEntry('Erro ao exportar dados', 'error');
        }
    }

    addLogEntry(message, type = 'info') {
        const entry = document.createElement('div');
        entry.className = `log-entry ${type}`;
        entry.setAttribute('data-time', new Date().toLocaleTimeString());
        entry.textContent = message;
        
        this.systemLog.appendChild(entry);
        this.systemLog.scrollTop = this.systemLog.scrollHeight;
        
        // Limit log entries
        while (this.systemLog.children.length > 100) {
            this.systemLog.removeChild(this.systemLog.firstChild);
        }
    }

    // Fetch initial data
    async loadInitialData() {
        try {
            // Load sensors list
            const sensorsResponse = await fetch('/api/sensors');
            if (sensorsResponse.ok) {
                const sensors = await sensorsResponse.json();
                this.updateSensorsList(sensors);
            }
            
            // Load initial configuration
            const configResponse = await fetch('/api/config');
            if (configResponse.ok) {
                const config = await configResponse.json();
                this.applyConfiguration(config);
            }
        } catch (error) {
            console.error('Erro ao carregar dados iniciais:', error);
            this.addLogEntry('Erro ao carregar configuração inicial', 'error');
        }
    }

    updateSensorsList(sensors) {
        this.sensorsListElement.innerHTML = '';
        sensors.forEach(sensor => {
            const sensorElement = document.createElement('div');
            sensorElement.className = 'sensor-item';
            sensorElement.innerHTML = `
                <div>
                    <div class="sensor-name">${sensor.name}</div>
                    <div class="sensor-id">${sensor.id}</div>
                </div>
                <div>
                    <span class="sensor-value">--</span>
                    <span class="sensor-unit">${sensor.unit}</span>
                </div>
            `;
            this.sensorsListElement.appendChild(sensorElement);
        });
    }

    applyConfiguration(config) {
        if (config.sample_rate) {
            this.sampleRateInput.value = config.sample_rate;
        }
    }
}

// Initialize application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.daqSystem = new DAQSystem();
    window.daqSystem.loadInitialData();
});

// Handle page visibility changes
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        console.log('Page hidden - pausing updates');
    } else {
        console.log('Page visible - resuming updates');
    }
});
