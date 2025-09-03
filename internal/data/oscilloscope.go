package data

import (
	"sort"
	"sync"
	"time"

	"daq-system/internal/models"
)

// OscilloscopeStreamer streamer otimizado para visualização tipo osciloscópio
type OscilloscopeStreamer struct {
	dataStreams map[string][]*models.DataPoint
	maxPoints   int
	mutex       sync.RWMutex
}

// NewOscilloscopeStreamer cria novo streamer de osciloscópio
func NewOscilloscopeStreamer(maxPoints int) *OscilloscopeStreamer {
	return &OscilloscopeStreamer{
		dataStreams: make(map[string][]*models.DataPoint),
		maxPoints:   maxPoints,
	}
}

// AddReading adiciona leitura ao stream de osciloscópio
func (os *OscilloscopeStreamer) AddReading(reading *models.StrainReading) {
	os.mutex.Lock()
	defer os.mutex.Unlock()

	// Inicializa stream do sensor se não existir
	if _, exists := os.dataStreams[reading.SensorID]; !exists {
		os.dataStreams[reading.SensorID] = make([]*models.DataPoint, 0, os.maxPoints)
	}

	// Converte para formato otimizado
	dataPoint := &models.DataPoint{
		T:    reading.Timestamp.UnixMilli(),
		V:    reading.StrainValue,
		R:    reading.RawADCValue,
		B:    reading.BatteryLevel,
		Temp: reading.Temperature,
	}

	stream := os.dataStreams[reading.SensorID]
	stream = append(stream, dataPoint)

	// Mantém apenas os últimos N pontos
	if len(stream) > os.maxPoints {
		// Remove os pontos mais antigos
		copy(stream, stream[len(stream)-os.maxPoints:])
		stream = stream[:os.maxPoints]
	}

	os.dataStreams[reading.SensorID] = stream
}

// GetTraceData retorna dados formatados para traço de osciloscópio
func (os *OscilloscopeStreamer) GetTraceData(sensorID string, maxPoints, decimationFactor int) *models.OscilloscopeData {
	os.mutex.RLock()
	defer os.mutex.RUnlock()

	stream, exists := os.dataStreams[sensorID]
	if !exists || len(stream) == 0 {
		return os.emptyTraceData(sensorID)
	}

	// Aplica decimação se necessário
	if decimationFactor > 1 {
		decimatedStream := make([]*models.DataPoint, 0, len(stream)/decimationFactor)
		for i := 0; i < len(stream); i += decimationFactor {
			decimatedStream = append(decimatedStream, stream[i])
		}
		stream = decimatedStream
	}

	// Limita número de pontos
	if maxPoints > 0 && len(stream) > maxPoints {
		stream = stream[len(stream)-maxPoints:]
	}

	// Extrai arrays para plotagem
	times := make([]int64, len(stream))
	values := make([]float64, len(stream))

	for i, point := range stream {
		times[i] = point.T
		values[i] = point.V
	}

	// Calcula estatísticas
	yMin, yMax := values[0], values[0]
	for _, v := range values {
		if v < yMin {
			yMin = v
		}
		if v > yMax {
			yMax = v
		}
	}

	yRange := yMax - yMin
	if yRange == 0 {
		yRange = 1.0
	}

	timeSpan := 0.0
	if len(times) > 1 {
		timeSpan = float64(times[len(times)-1]-times[0]) / 1000.0
	}

	return &models.OscilloscopeData{
		SensorID:   sensorID,
		Times:      times,
		Values:     values,
		PointCount: len(times),
		TimeSpan:   timeSpan,
		YMin:       yMin,
		YMax:       yMax,
		YRange:     yRange,
		LastUpdate: time.Now().UnixMilli(),
	}
}

// GetLatestValues retorna os valores mais recentes de todos os sensores
func (os *OscilloscopeStreamer) GetLatestValues() map[string]*models.DataPoint {
	os.mutex.RLock()
	defer os.mutex.RUnlock()

	latest := make(map[string]*models.DataPoint)
	for sensorID, stream := range os.dataStreams {
		if len(stream) > 0 {
			// Copia o último ponto
			lastPoint := stream[len(stream)-1]
			latest[sensorID] = &models.DataPoint{
				T:    lastPoint.T,
				V:    lastPoint.V,
				R:    lastPoint.R,
				B:    lastPoint.B,
				Temp: lastPoint.Temp,
			}
		}
	}

	return latest
}

// GetStreamingData retorna dados incrementais para streaming
func (os *OscilloscopeStreamer) GetStreamingData(sensorID string, sinceTimestamp int64) *models.StreamingData {
	os.mutex.RLock()
	defer os.mutex.RUnlock()

	stream, exists := os.dataStreams[sensorID]
	if !exists {
		return os.emptyStreamingData(sensorID, sinceTimestamp)
	}

	// Filtra pontos novos
	var newPoints []*models.DataPoint
	for _, point := range stream {
		if point.T > sinceTimestamp {
			newPoints = append(newPoints, point)
		}
	}

	latestTimestamp := sinceTimestamp
	if len(newPoints) > 0 {
		latestTimestamp = newPoints[len(newPoints)-1].T
	}

	// Converte para formato de resposta
	data := make([]models.DataPoint, len(newPoints))
	for i, point := range newPoints {
		data[i] = *point
	}

	return &models.StreamingData{
		SensorID:        sensorID,
		NewPoints:       len(newPoints),
		Data:            data,
		LatestTimestamp: latestTimestamp,
		HasMore:         len(newPoints) > 0,
	}
}

// GetStreamStats retorna estatísticas dos streams ativos
func (os *OscilloscopeStreamer) GetStreamStats() models.StreamStats {
	os.mutex.RLock()
	defer os.mutex.RUnlock()

	totalPoints := 0
	sensors := make(map[string]models.SensorStreamStats)

	for sensorID, stream := range os.dataStreams {
		if len(stream) == 0 {
			continue
		}

		totalPoints += len(stream)

		// Calcula estatísticas do sensor
		values := make([]float64, len(stream))
		for i, point := range stream {
			values[i] = point.V
		}

		sort.Float64s(values)
		sum := 0.0
		for _, v := range values {
			sum += v
		}

		sensors[sensorID] = models.SensorStreamStats{
			Points:     len(stream),
			LatestTime: stream[len(stream)-1].T,
			MinValue:   values[0],
			MaxValue:   values[len(values)-1],
			AvgValue:   sum / float64(len(values)),
		}
	}

	return models.StreamStats{
		ActiveSensors: len(os.dataStreams),
		TotalPoints:   totalPoints,
		Sensors:       sensors,
	}
}

// ClearStream limpa stream de um sensor específico
func (os *OscilloscopeStreamer) ClearStream(sensorID string) {
	os.mutex.Lock()
	defer os.mutex.Unlock()

	if _, exists := os.dataStreams[sensorID]; exists {
		os.dataStreams[sensorID] = os.dataStreams[sensorID][:0]
	}
}

// ClearAllStreams limpa todos os streams
func (os *OscilloscopeStreamer) ClearAllStreams() {
	os.mutex.Lock()
	defer os.mutex.Unlock()

	for sensorID := range os.dataStreams {
		os.dataStreams[sensorID] = os.dataStreams[sensorID][:0]
	}
}

// GetActiveSensors retorna lista de sensores ativos
func (os *OscilloscopeStreamer) GetActiveSensors() []string {
	os.mutex.RLock()
	defer os.mutex.RUnlock()

	sensors := make([]string, 0, len(os.dataStreams))
	for sensorID, stream := range os.dataStreams {
		if len(stream) > 0 {
			sensors = append(sensors, sensorID)
		}
	}

	return sensors
}

// Métodos auxiliares privados

func (os *OscilloscopeStreamer) emptyTraceData(sensorID string) *models.OscilloscopeData {
	return &models.OscilloscopeData{
		SensorID:   sensorID,
		Times:      []int64{},
		Values:     []float64{},
		PointCount: 0,
		TimeSpan:   0,
		YMin:       0,
		YMax:       0,
		YRange:     0,
		LastUpdate: time.Now().UnixMilli(),
	}
}

func (os *OscilloscopeStreamer) emptyStreamingData(sensorID string, timestamp int64) *models.StreamingData {
	return &models.StreamingData{
		SensorID:        sensorID,
		NewPoints:       0,
		Data:            []models.DataPoint{},
		LatestTimestamp: timestamp,
		HasMore:         false,
	}
}
