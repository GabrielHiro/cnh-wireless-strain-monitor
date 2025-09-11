package models

import (
	"fmt"
	"time"
)

// SensorStatus representa o estado atual do sensor
type SensorStatus string

const (
	StatusOffline    SensorStatus = "offline"
	StatusConnecting SensorStatus = "connecting"
	StatusOnline     SensorStatus = "online"
	StatusError      SensorStatus = "error"
	StatusLowBattery SensorStatus = "low_battery"
)

// CommunicationProtocol define o protocolo de comunicação
type CommunicationProtocol string

const (
	ProtocolBLE  CommunicationProtocol = "bluetooth_low_energy"
	ProtocolWiFi CommunicationProtocol = "wifi"
)

// StrainReading representa uma leitura de deformação do strain gauge
type StrainReading struct {
	Timestamp    time.Time `json:"timestamp" db:"timestamp"`
	StrainValue  float64   `json:"strain_value" db:"strain_value"`   // microstrains (µε)
	RawADCValue  int32     `json:"raw_adc_value" db:"raw_adc_value"` // Valor bruto do ADC
	SensorID     string    `json:"sensor_id" db:"sensor_id"`
	BatteryLevel int       `json:"battery_level" db:"battery_level"` // 0-100%
	Temperature  float64   `json:"temperature" db:"temperature"`     // °C
	Checksum     string    `json:"checksum,omitempty" db:"checksum"`
}

// CalculateChecksum calcula um checksum simples para verificação de integridade
func (sr *StrainReading) CalculateChecksum() string {
	data := fmt.Sprintf("%d%.6f%d%d",
		sr.Timestamp.Unix(),
		sr.StrainValue,
		sr.RawADCValue,
		sr.BatteryLevel)

	// Simple hash
	hash := uint32(0)
	for _, c := range data {
		hash = hash*31 + uint32(c)
	}

	return fmt.Sprintf("%08x", hash)
}

// IsValid verifica se a leitura é válida
func (sr *StrainReading) IsValid() bool {
	if sr.Checksum == "" {
		sr.Checksum = sr.CalculateChecksum()
	}

	return sr.Checksum == sr.CalculateChecksum() &&
		sr.BatteryLevel >= 0 && sr.BatteryLevel <= 100 &&
		sr.Temperature >= -40 && sr.Temperature <= 85
}

// SensorConfiguration configuração do nó sensor
type SensorConfiguration struct {
	SensorID              string  `json:"sensor_id" db:"sensor_id"`
	SamplingRateMS        int     `json:"sampling_rate_ms" db:"sampling_rate_ms"`
	TransmissionIntervalS int     `json:"transmission_interval_s" db:"transmission_interval_s"`
	CalibrationFactor     float64 `json:"calibration_factor" db:"calibration_factor"`
	Offset                float64 `json:"offset" db:"offset"`
	DeepSleepEnabled      bool    `json:"deep_sleep_enabled" db:"deep_sleep_enabled"`
	WiFiSSID              string  `json:"wifi_ssid,omitempty" db:"wifi_ssid"`
	WiFiPassword          string  `json:"wifi_password,omitempty" db:"wifi_password"`
}

// DefaultSensorConfiguration retorna configuração padrão
func DefaultSensorConfiguration(sensorID string) *SensorConfiguration {
	return &SensorConfiguration{
		SensorID:              sensorID,
		SamplingRateMS:        100, // 10 Hz
		TransmissionIntervalS: 1,   // 1 segundo
		CalibrationFactor:     1.0,
		Offset:                0.0,
		DeepSleepEnabled:      true,
	}
}

// SensorInfo informações sobre um sensor conectado
type SensorInfo struct {
	SensorID        string                 `json:"sensor_id" db:"sensor_id"`
	Name            string                 `json:"name" db:"name"`
	Status          SensorStatus           `json:"status" db:"status"`
	LastSeen        *time.Time             `json:"last_seen,omitempty" db:"last_seen"`
	Protocol        *CommunicationProtocol `json:"protocol,omitempty" db:"protocol"`
	SignalStrength  *int                   `json:"signal_strength,omitempty" db:"signal_strength"` // dBm
	FirmwareVersion string                 `json:"firmware_version,omitempty" db:"firmware_version"`
	HardwareVersion string                 `json:"hardware_version,omitempty" db:"hardware_version"`
	Configuration   *SensorConfiguration   `json:"configuration,omitempty"`
}

// IsOnline verifica se o sensor está online
func (si *SensorInfo) IsOnline() bool {
	return si.Status == StatusOnline
}

// TimeSinceLastSeen retorna tempo em segundos desde a última comunicação
func (si *SensorInfo) TimeSinceLastSeen() *float64 {
	if si.LastSeen == nil {
		return nil
	}

	seconds := time.Since(*si.LastSeen).Seconds()
	return &seconds
}

// UpdateLastSeen atualiza o timestamp da última comunicação
func (si *SensorInfo) UpdateLastSeen() {
	now := time.Now()
	si.LastSeen = &now
}

// DataPacket pacote de dados transmitido pelo sensor
type DataPacket struct {
	PacketID       string          `json:"packet_id"`
	SensorID       string          `json:"sensor_id"`
	Readings       []StrainReading `json:"readings"`
	Timestamp      time.Time       `json:"timestamp"`
	SequenceNumber int             `json:"sequence_number"`
	TotalPackets   int             `json:"total_packets"`
}

// IsCompleteSequence verifica se é o último pacote da sequência
func (dp *DataPacket) IsCompleteSequence() bool {
	return dp.SequenceNumber >= dp.TotalPackets-1
}

// GetDataSize retorna tamanho estimado dos dados em bytes
func (dp *DataPacket) GetDataSize() int {
	return len(dp.Readings) * 32 // ~32 bytes por leitura
}

// OscilloscopeData estrutura otimizada para visualização
type OscilloscopeData struct {
	SensorID   string    `json:"sensor_id"`
	Times      []int64   `json:"times"`  // timestamps em ms
	Values     []float64 `json:"values"` // valores de strain
	PointCount int       `json:"point_count"`
	TimeSpan   float64   `json:"time_span"` // segundos
	YMin       float64   `json:"y_min"`
	YMax       float64   `json:"y_max"`
	YRange     float64   `json:"y_range"`
	LastUpdate int64     `json:"last_update"` // timestamp em ms
}

// RealtimeSnapshot snapshot em tempo real
type RealtimeSnapshot struct {
	Timestamp     int64                     `json:"timestamp"`
	ActiveSensors int                       `json:"active_sensors"`
	TotalPoints   int                       `json:"total_points"`
	Sensors       map[string]SensorSnapshot `json:"sensors"`
}

// SensorSnapshot dados instantâneos de um sensor
type SensorSnapshot struct {
	CurrentValue float64 `json:"current_value"`
	Timestamp    int64   `json:"timestamp"`
	Battery      int     `json:"battery"`
	Temperature  float64 `json:"temperature"`
	RawADC       int32   `json:"raw_adc"`
	MinValue     float64 `json:"min_value"`
	MaxValue     float64 `json:"max_value"`
	AvgValue     float64 `json:"avg_value"`
	PointCount   int     `json:"point_count"`
}

// StreamingData dados incrementais para streaming
type StreamingData struct {
	SensorID        string      `json:"sensor_id"`
	NewPoints       int         `json:"new_points"`
	Data            []DataPoint `json:"data"`
	LatestTimestamp int64       `json:"latest_timestamp"`
	HasMore         bool        `json:"has_more"`
}

// DataPoint ponto de dados otimizado
type DataPoint struct {
	T    int64   `json:"t"`    // timestamp ms
	V    float64 `json:"v"`    // valor strain
	R    int32   `json:"r"`    // raw ADC
	B    int     `json:"b"`    // battery
	Temp float64 `json:"temp"` // temperatura
}

// PerformanceMetrics métricas de performance do sistema
type PerformanceMetrics struct {
	StreamStats   StreamStats            `json:"stream_stats"`
	BufferStats   BufferStats            `json:"buffer_stats"`
	APIUpdateRate float64                `json:"api_update_rate"`
	MemoryUsage   MemoryUsage            `json:"memory_usage"`
	Config        map[string]interface{} `json:"config"`
}

// StreamStats estatísticas dos streams
type StreamStats struct {
	ActiveSensors int                          `json:"active_sensors"`
	TotalPoints   int                          `json:"total_points"`
	Sensors       map[string]SensorStreamStats `json:"sensors"`
}

// SensorStreamStats estatísticas por sensor
type SensorStreamStats struct {
	Points     int     `json:"points"`
	LatestTime int64   `json:"latest_time"`
	MinValue   float64 `json:"min_value"`
	MaxValue   float64 `json:"max_value"`
	AvgValue   float64 `json:"avg_value"`
}

// BufferStats estatísticas do buffer
type BufferStats struct {
	TotalReadings int        `json:"total_readings"`
	SensorsCount  int        `json:"sensors_count"`
	LatestReading *string    `json:"latest_reading"`
	StrainStats   *StatsInfo `json:"strain_stats"`
	BufferSize    int        `json:"buffer_size"`
}

// StatsInfo informações estatísticas
type StatsInfo struct {
	Min float64 `json:"min"`
	Max float64 `json:"max"`
	Avg float64 `json:"avg"`
}

// MemoryUsage uso de memória
type MemoryUsage struct {
	TotalPoints     int `json:"total_points"`
	EstimatedBytes  int `json:"estimated_bytes"`
	PointsPerSensor int `json:"points_per_sensor"`
	ActiveSensors   int `json:"active_sensors"`
}

// WebSocketMessage mensagem WebSocket
type WebSocketMessage struct {
	Type string      `json:"type"`
	Data interface{} `json:"data"`
}

// ErrorResponse resposta de erro padronizada
type ErrorResponse struct {
	Error   string `json:"error"`
	Code    int    `json:"code"`
	Message string `json:"message"`
}
