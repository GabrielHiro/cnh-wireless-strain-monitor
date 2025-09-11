package simulator

import (
	"fmt"
	"math"
	"math/rand"
	"sync"
	"time"

	"daq-system/internal/models"
)

// Config configuração do simulador
type Config struct {
	DeviceName       string        `json:"device_name"`
	SensorCount      int           `json:"sensor_count"`
	SamplingRateHz   float64       `json:"sampling_rate_hz"`
	Scenario         string        `json:"scenario"`
	NoiseLevel       float64       `json:"noise_level"`
	EnableBLE        bool          `json:"enable_ble"`
	EnableWiFi       bool          `json:"enable_wifi"`
	BatteryDrainRate float64       `json:"battery_drain_rate"`
	Duration         time.Duration `json:"duration"`
}

// DefaultConfig retorna configuração padrão
func DefaultConfig() Config {
	return Config{
		DeviceName:       "DAQ_SIM_001",
		SensorCount:      1,
		SamplingRateHz:   10.0,
		Scenario:         "field_work_light",
		NoiseLevel:       0.05,
		EnableBLE:        true,
		EnableWiFi:       false,
		BatteryDrainRate: 0.001,
		Duration:         0, // Infinito
	}
}

// Scenario define um cenário de simulação
type Scenario struct {
	Name        string
	BaseStrain  float64 // µε
	Amplitude   float64 // µε
	Frequency   float64 // Hz
	Description string
}

// Cenários predefinidos
var scenarios = map[string]Scenario{
	"idle": {
		Name:        "idle",
		BaseStrain:  0,
		Amplitude:   10,
		Frequency:   0.1,
		Description: "Máquina parada",
	},
	"transport": {
		Name:        "transport",
		BaseStrain:  20,
		Amplitude:   50,
		Frequency:   2.0,
		Description: "Transporte em estrada",
	},
	"field_work_light": {
		Name:        "field_work_light",
		BaseStrain:  100,
		Amplitude:   200,
		Frequency:   1.5,
		Description: "Trabalho leve no campo",
	},
	"field_work_heavy": {
		Name:        "field_work_heavy",
		BaseStrain:  300,
		Amplitude:   500,
		Frequency:   3.0,
		Description: "Trabalho pesado",
	},
	"harvest": {
		Name:        "harvest",
		BaseStrain:  400,
		Amplitude:   800,
		Frequency:   4.0,
		Description: "Operação de colheita",
	},
	"overload": {
		Name:        "overload",
		BaseStrain:  800,
		Amplitude:   1200,
		Frequency:   5.0,
		Description: "Sobrecarga crítica",
	},
}

// DAQSimulator simulador principal do sistema DAQ
type DAQSimulator struct {
	config    Config
	running   bool
	sensors   []*SensorSimulator
	mutex     sync.RWMutex
	stopChan  chan struct{}
	startTime time.Time
}

// SensorSimulator simula um sensor individual
type SensorSimulator struct {
	id           string
	scenario     Scenario
	noiseLevel   float64
	batteryLevel float64
	temperature  float64
	samplingRate float64
	startTime    time.Time
	sequence     int64
}

// NewDAQSimulator cria novo simulador DAQ
func NewDAQSimulator() *DAQSimulator {
	return &DAQSimulator{
		sensors:  make([]*SensorSimulator, 0),
		stopChan: make(chan struct{}),
	}
}

// Start inicia o simulador com a configuração especificada
func (ds *DAQSimulator) Start(config Config) error {
	ds.mutex.Lock()
	defer ds.mutex.Unlock()

	if ds.running {
		return fmt.Errorf("simulador já está executando")
	}

	ds.config = config
	ds.running = true
	ds.startTime = time.Now()

	// Cria sensores
	ds.sensors = make([]*SensorSimulator, config.SensorCount)
	for i := 0; i < config.SensorCount; i++ {
		sensorID := fmt.Sprintf("%s_SENSOR_%03d", config.DeviceName, i+1)

		scenario, exists := scenarios[config.Scenario]
		if !exists {
			scenario = scenarios["field_work_light"]
		}

		ds.sensors[i] = &SensorSimulator{
			id:           sensorID,
			scenario:     scenario,
			noiseLevel:   config.NoiseLevel,
			batteryLevel: 100.0,
			temperature:  25.0 + rand.Float64()*10 - 5, // 20-30°C
			samplingRate: config.SamplingRateHz,
			startTime:    time.Now(),
			sequence:     0,
		}
	}

	return nil
}

// Stop para o simulador
func (ds *DAQSimulator) Stop() {
	ds.mutex.Lock()
	defer ds.mutex.Unlock()

	if ds.running {
		ds.running = false
		close(ds.stopChan)
	}
}

// StreamData inicia stream de dados para um callback
func (ds *DAQSimulator) StreamData(callback func(*models.StrainReading)) {
	if !ds.IsRunning() {
		return
	}

	// Calcula intervalo de amostragem
	interval := time.Duration(float64(time.Second) / ds.config.SamplingRateHz)
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			if !ds.IsRunning() {
				return
			}

			// Gera leituras para todos os sensores
			for _, sensor := range ds.sensors {
				reading := sensor.GenerateReading()
				callback(reading)
			}

			// Para se atingiu duração especificada
			if ds.config.Duration > 0 && time.Since(ds.startTime) >= ds.config.Duration {
				ds.Stop()
				return
			}

		case <-ds.stopChan:
			return
		}
	}
}

// IsRunning verifica se o simulador está executando
func (ds *DAQSimulator) IsRunning() bool {
	ds.mutex.RLock()
	defer ds.mutex.RUnlock()
	return ds.running
}

// GetStatus retorna status atual do simulador
func (ds *DAQSimulator) GetStatus() map[string]interface{} {
	ds.mutex.RLock()
	defer ds.mutex.RUnlock()

	status := map[string]interface{}{
		"running":      ds.running,
		"sensor_count": len(ds.sensors),
		"config":       ds.config,
	}

	if ds.running {
		status["uptime_seconds"] = time.Since(ds.startTime).Seconds()

		// Status dos sensores
		sensorStatus := make([]map[string]interface{}, len(ds.sensors))
		for i, sensor := range ds.sensors {
			sensorStatus[i] = map[string]interface{}{
				"id":            sensor.id,
				"battery_level": sensor.batteryLevel,
				"temperature":   sensor.temperature,
				"sequence":      sensor.sequence,
				"scenario":      sensor.scenario.Name,
			}
		}
		status["sensors"] = sensorStatus
	}

	return status
}

// GetScenarios retorna lista de cenários disponíveis
func (ds *DAQSimulator) GetScenarios() map[string]Scenario {
	return scenarios
}

// Métodos do SensorSimulator

// GenerateReading gera uma leitura simulada
func (ss *SensorSimulator) GenerateReading() *models.StrainReading {
	now := time.Now()
	elapsed := now.Sub(ss.startTime).Seconds()

	// Gera valor de strain baseado no cenário
	strainValue := ss.generateStrainValue(elapsed)

	// Simula valor ADC (baseado no HX711)
	// Assume fator de conversão aproximado
	rawADC := int32(strainValue*100 + 32768 + rand.Float64()*200 - 100)

	// Atualiza estado do sensor
	ss.updateSensorState(elapsed)
	ss.sequence++

	reading := &models.StrainReading{
		Timestamp:    now,
		StrainValue:  strainValue,
		RawADCValue:  rawADC,
		SensorID:     ss.id,
		BatteryLevel: int(ss.batteryLevel),
		Temperature:  ss.temperature,
	}

	// Calcula checksum
	reading.Checksum = reading.CalculateChecksum()

	return reading
}

// generateStrainValue gera valor de deformação baseado no cenário
func (ss *SensorSimulator) generateStrainValue(elapsed float64) float64 {
	scenario := ss.scenario

	// Componente principal (senoide)
	mainSignal := scenario.BaseStrain +
		scenario.Amplitude*math.Sin(2*math.Pi*scenario.Frequency*elapsed)

	// Ruído gaussiano
	noise := rand.NormFloat64() * ss.noiseLevel * scenario.Amplitude

	// Componente aleatória adicional para simular irregularidades
	randomComponent := rand.Float64()*20 - 10

	// Deriva lenta (simula mudanças graduais)
	drift := math.Sin(2*math.Pi*0.01*elapsed) * 5

	return mainSignal + noise + randomComponent + drift
}

// updateSensorState atualiza estado interno do sensor
func (ss *SensorSimulator) updateSensorState(elapsed float64) {
	// Drena bateria gradualmente
	drainRate := 0.001 // % por segundo
	if ss.scenario.Name == "overload" {
		drainRate *= 2 // Drena mais rápido sob carga pesada
	}

	ss.batteryLevel -= drainRate
	if ss.batteryLevel < 0 {
		ss.batteryLevel = 0
	}

	// Simula variação de temperatura
	baseTemp := 25.0
	tempVariation := math.Sin(2*math.Pi*0.001*elapsed) * 3 // Variação lenta
	workingHeat := 0.0

	// Aquecimento durante trabalho pesado
	if ss.scenario.Name == "field_work_heavy" || ss.scenario.Name == "harvest" {
		workingHeat = 5.0
	} else if ss.scenario.Name == "overload" {
		workingHeat = 10.0
	}

	ss.temperature = baseTemp + tempVariation + workingHeat + rand.Float64()*2 - 1
}

// GetCurrentReading retorna leitura atual sem avançar sequência
func (ss *SensorSimulator) GetCurrentReading() *models.StrainReading {
	now := time.Now()
	elapsed := now.Sub(ss.startTime).Seconds()
	strainValue := ss.generateStrainValue(elapsed)
	rawADC := int32(strainValue*100 + 32768)

	reading := &models.StrainReading{
		Timestamp:    now,
		StrainValue:  strainValue,
		RawADCValue:  rawADC,
		SensorID:     ss.id,
		BatteryLevel: int(ss.batteryLevel),
		Temperature:  ss.temperature,
	}

	reading.Checksum = reading.CalculateChecksum()
	return reading
}
