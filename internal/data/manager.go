package data

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"sort"
	"strings"
	"sync"
	"time"

	"daq-system/internal/models"
)

const (
	MaxBufferSize         = 10000
	BufferFlushInterval   = 60 * time.Second
	MaxOscilloscopePoints = 1000
)

// Manager gerenciador principal de dados
type Manager struct {
	buffer         *Buffer
	database       *Database
	oscilloscope   *OscilloscopeStreamer
	mutex          sync.RWMutex
	running        bool
	stopChan       chan struct{}
	lastUpdateTime time.Time
}

// NewManager cria novo gerenciador de dados
func NewManager() *Manager {
	buffer := NewBuffer(MaxBufferSize, BufferFlushInterval)
	db := NewDatabase("daq_data.db")
	oscilloscope := NewOscilloscopeStreamer(MaxOscilloscopePoints)

	return &Manager{
		buffer:       buffer,
		database:     db,
		oscilloscope: oscilloscope,
		stopChan:     make(chan struct{}),
	}
}

// Start inicia as tarefas em background
func (m *Manager) Start() {
	m.mutex.Lock()
	m.running = true
	m.mutex.Unlock()

	// Goroutine para flush automático do buffer
	go m.autoFlushLoop()
}

// Stop para todas as tarefas
func (m *Manager) Stop() {
	m.mutex.Lock()
	if m.running {
		m.running = false
		close(m.stopChan)
	}
	m.mutex.Unlock()

	// Flush final
	m.flushBuffer()
	m.database.Close()
}

// AddReading adiciona uma leitura ao sistema
func (m *Manager) AddReading(reading *models.StrainReading) {
	if !reading.IsValid() {
		return
	}

	// Adiciona ao buffer
	m.buffer.AddReading(reading)

	// Adiciona ao streamer de osciloscópio
	m.oscilloscope.AddReading(reading)

	// Flush se necessário
	if m.buffer.ShouldFlush() {
		go m.flushBuffer()
	}
}

// AddReadings adiciona múltiplas leituras
func (m *Manager) AddReadings(readings []*models.StrainReading) {
	for _, reading := range readings {
		if reading.IsValid() {
			m.buffer.AddReading(reading)
			m.oscilloscope.AddReading(reading)
		}
	}

	if m.buffer.ShouldFlush() {
		go m.flushBuffer()
	}
}

// GetTraceData retorna dados formatados para traço de osciloscópio
func (m *Manager) GetTraceData(sensorID string, maxPoints, decimationFactor int) *models.OscilloscopeData {
	return m.oscilloscope.GetTraceData(sensorID, maxPoints, decimationFactor)
}

// GetRealtimeSnapshot retorna snapshot em tempo real
func (m *Manager) GetRealtimeSnapshot() *models.RealtimeSnapshot {
	latestValues := m.oscilloscope.GetLatestValues()
	stats := m.oscilloscope.GetStreamStats()

	snapshot := &models.RealtimeSnapshot{
		Timestamp:     time.Now().UnixMilli(),
		ActiveSensors: stats.ActiveSensors,
		TotalPoints:   stats.TotalPoints,
		Sensors:       make(map[string]models.SensorSnapshot),
	}

	for sensorID, latest := range latestValues {
		sensorStats, exists := stats.Sensors[sensorID]
		if !exists {
			continue
		}

		snapshot.Sensors[sensorID] = models.SensorSnapshot{
			CurrentValue: latest.V,
			Timestamp:    latest.T,
			Battery:      latest.B,
			Temperature:  latest.Temp,
			RawADC:       latest.R,
			MinValue:     sensorStats.MinValue,
			MaxValue:     sensorStats.MaxValue,
			AvgValue:     sensorStats.AvgValue,
			PointCount:   sensorStats.Points,
		}
	}

	return snapshot
}

// GetStreamingData retorna dados incrementais para streaming
func (m *Manager) GetStreamingData(sensorID string, sinceTimestamp int64) *models.StreamingData {
	return m.oscilloscope.GetStreamingData(sensorID, sinceTimestamp)
}

// GetPerformanceMetrics retorna métricas de performance
func (m *Manager) GetPerformanceMetrics() *models.PerformanceMetrics {
	streamStats := m.oscilloscope.GetStreamStats()
	bufferStats := m.getBufferStats()

	return &models.PerformanceMetrics{
		StreamStats:   streamStats,
		BufferStats:   bufferStats,
		APIUpdateRate: m.calculateUpdateRate(),
		MemoryUsage:   m.estimateMemoryUsage(streamStats),
		Config: map[string]interface{}{
			"max_buffer_size":         MaxBufferSize,
			"oscilloscope_max_points": MaxOscilloscopePoints,
			"flush_interval_seconds":  BufferFlushInterval.Seconds(),
		},
	}
}

// GetActiveSensors retorna lista de sensores ativos
func (m *Manager) GetActiveSensors() []*models.SensorInfo {
	// Implementação simplificada - busca sensores com atividade recente
	sensors := make([]*models.SensorInfo, 0)

	stats := m.oscilloscope.GetStreamStats()
	for sensorID := range stats.Sensors {
		sensor := &models.SensorInfo{
			SensorID: sensorID,
			Name:     fmt.Sprintf("Sensor %s", sensorID),
			Status:   models.StatusOnline,
		}
		now := time.Now()
		sensor.LastSeen = &now
		sensors = append(sensors, sensor)
	}

	return sensors
}

// GetSensor retorna informações de um sensor específico
func (m *Manager) GetSensor(sensorID string) *models.SensorInfo {
	sensors := m.GetActiveSensors()
	for _, sensor := range sensors {
		if sensor.SensorID == sensorID {
			return sensor
		}
	}
	return nil
}

// ConfigureSensor configura um sensor
func (m *Manager) ConfigureSensor(config *models.SensorConfiguration) error {
	// Por enquanto apenas armazena a configuração
	// Em uma implementação real, enviaria para o sensor via BLE/WiFi
	return m.database.StoreSensorConfig(config)
}

// ExportData exporta dados em formato específico
func (m *Manager) ExportData(format, sensorID, startTime, endTime string) ([]byte, string, string, error) {
	// Parse timestamps se fornecidos
	var start, end *time.Time
	if startTime != "" {
		if t, err := time.Parse(time.RFC3339, startTime); err == nil {
			start = &t
		}
	}
	if endTime != "" {
		if t, err := time.Parse(time.RFC3339, endTime); err == nil {
			end = &t
		}
	}

	// Busca dados
	readings, err := m.database.GetReadings(sensorID, start, end, 0)
	if err != nil {
		return nil, "", "", err
	}

	switch strings.ToLower(format) {
	case "csv":
		return m.exportCSV(readings, sensorID)
	case "json":
		return m.exportJSON(readings, sensorID)
	default:
		return nil, "", "", fmt.Errorf("formato não suportado: %s", format)
	}
}

// Métodos privados

func (m *Manager) autoFlushLoop() {
	ticker := time.NewTicker(BufferFlushInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			if m.buffer.ShouldFlush() {
				m.flushBuffer()
			}
		case <-m.stopChan:
			return
		}
	}
}

func (m *Manager) flushBuffer() {
	readings := m.buffer.GetAllReadings()
	if len(readings) > 0 {
		if err := m.database.StoreReadings(readings); err == nil {
			m.buffer.Clear()
			m.buffer.MarkFlushed()
		}
	}
}

func (m *Manager) getBufferStats() models.BufferStats {
	readings := m.buffer.GetAllReadings()

	stats := models.BufferStats{
		TotalReadings: len(readings),
		BufferSize:    m.buffer.Size(),
	}

	if len(readings) > 0 {
		// Conta sensores únicos
		sensors := make(map[string]bool)
		values := make([]float64, 0, len(readings))

		for _, reading := range readings {
			sensors[reading.SensorID] = true
			values = append(values, reading.StrainValue)
		}

		stats.SensorsCount = len(sensors)
		latest := readings[len(readings)-1].Timestamp.Format(time.RFC3339)
		stats.LatestReading = &latest

		// Calcula estatísticas dos valores
		if len(values) > 0 {
			sort.Float64s(values)
			sum := 0.0
			for _, v := range values {
				sum += v
			}

			stats.StrainStats = &models.StatsInfo{
				Min: values[0],
				Max: values[len(values)-1],
				Avg: sum / float64(len(values)),
			}
		}
	}

	return stats
}

func (m *Manager) calculateUpdateRate() float64 {
	now := time.Now()
	if !m.lastUpdateTime.IsZero() {
		rate := 1.0 / now.Sub(m.lastUpdateTime).Seconds()
		m.lastUpdateTime = now
		return rate
	}

	m.lastUpdateTime = now
	return 0.0
}

func (m *Manager) estimateMemoryUsage(stats models.StreamStats) models.MemoryUsage {
	pointsPerSensor := 0
	if stats.ActiveSensors > 0 {
		pointsPerSensor = stats.TotalPoints / stats.ActiveSensors
	}

	bytesPerPoint := 32 // Estimativa
	estimatedBytes := stats.TotalPoints * bytesPerPoint

	return models.MemoryUsage{
		TotalPoints:     stats.TotalPoints,
		EstimatedBytes:  estimatedBytes,
		PointsPerSensor: pointsPerSensor,
		ActiveSensors:   stats.ActiveSensors,
	}
}

func (m *Manager) exportCSV(readings []*models.StrainReading, sensorID string) ([]byte, string, string, error) {
	var buf strings.Builder
	writer := csv.NewWriter(&buf)

	// Cabeçalho
	writer.Write([]string{
		"timestamp",
		"strain_value_microstrains",
		"raw_adc_value",
		"sensor_id",
		"battery_level_percent",
		"temperature_celsius",
		"checksum",
	})

	// Dados
	for _, reading := range readings {
		writer.Write([]string{
			reading.Timestamp.Format(time.RFC3339),
			fmt.Sprintf("%.6f", reading.StrainValue),
			fmt.Sprintf("%d", reading.RawADCValue),
			reading.SensorID,
			fmt.Sprintf("%d", reading.BatteryLevel),
			fmt.Sprintf("%.2f", reading.Temperature),
			reading.Checksum,
		})
	}

	writer.Flush()

	filename := fmt.Sprintf("daq_data_%s_%s.csv",
		sensorID,
		time.Now().Format("20060102_150405"))

	return []byte(buf.String()), "text/csv", filename, nil
}

func (m *Manager) exportJSON(readings []*models.StrainReading, sensorID string) ([]byte, string, string, error) {
	data := map[string]interface{}{
		"metadata": map[string]interface{}{
			"exported_at":    time.Now().Format(time.RFC3339),
			"total_readings": len(readings),
			"sensor_id":      sensorID,
			"system":         "DAQ System Go",
		},
		"readings": readings,
	}

	jsonData, err := json.MarshalIndent(data, "", "  ")
	if err != nil {
		return nil, "", "", err
	}

	filename := fmt.Sprintf("daq_data_%s_%s.json",
		sensorID,
		time.Now().Format("20060102_150405"))

	return jsonData, "application/json", filename, nil
}
