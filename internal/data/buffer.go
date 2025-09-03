package data

import (
	"sync"
	"time"

	"daq-system/internal/models"
)

// Buffer buffer circular em memória para dados de sensores
type Buffer struct {
	readings      []*models.StrainReading
	maxSize       int
	flushInterval time.Duration
	lastFlush     time.Time
	mutex         sync.RWMutex
}

// NewBuffer cria novo buffer
func NewBuffer(maxSize int, flushInterval time.Duration) *Buffer {
	return &Buffer{
		readings:      make([]*models.StrainReading, 0, maxSize),
		maxSize:       maxSize,
		flushInterval: flushInterval,
		lastFlush:     time.Now(),
	}
}

// AddReading adiciona uma leitura ao buffer
func (b *Buffer) AddReading(reading *models.StrainReading) {
	b.mutex.Lock()
	defer b.mutex.Unlock()

	b.readings = append(b.readings, reading)

	// Remove dados antigos se buffer cheio
	if len(b.readings) > b.maxSize {
		// Remove o mais antigo
		b.readings = b.readings[1:]
	}
}

// GetAllReadings retorna todas as leituras do buffer
func (b *Buffer) GetAllReadings() []*models.StrainReading {
	b.mutex.RLock()
	defer b.mutex.RUnlock()

	// Retorna cópia para evitar race conditions
	readings := make([]*models.StrainReading, len(b.readings))
	copy(readings, b.readings)
	return readings
}

// Clear limpa todo o buffer
func (b *Buffer) Clear() {
	b.mutex.Lock()
	defer b.mutex.Unlock()

	b.readings = b.readings[:0]
}

// Size retorna tamanho atual do buffer
func (b *Buffer) Size() int {
	b.mutex.RLock()
	defer b.mutex.RUnlock()

	return len(b.readings)
}

// ShouldFlush verifica se é hora de fazer flush do buffer
func (b *Buffer) ShouldFlush() bool {
	b.mutex.RLock()
	defer b.mutex.RUnlock()

	return len(b.readings) >= b.maxSize ||
		time.Since(b.lastFlush) >= b.flushInterval
}

// MarkFlushed marca que o flush foi realizado
func (b *Buffer) MarkFlushed() {
	b.mutex.Lock()
	defer b.mutex.Unlock()

	b.lastFlush = time.Now()
}

// GetReadingsByTimeRange retorna leituras em um intervalo de tempo
func (b *Buffer) GetReadingsByTimeRange(start, end time.Time) []*models.StrainReading {
	b.mutex.RLock()
	defer b.mutex.RUnlock()

	var filtered []*models.StrainReading
	for _, reading := range b.readings {
		if reading.Timestamp.After(start) && reading.Timestamp.Before(end) {
			filtered = append(filtered, reading)
		}
	}

	return filtered
}

// GetReadingsBySensor retorna leituras de um sensor específico
func (b *Buffer) GetReadingsBySensor(sensorID string) []*models.StrainReading {
	b.mutex.RLock()
	defer b.mutex.RUnlock()

	var filtered []*models.StrainReading
	for _, reading := range b.readings {
		if reading.SensorID == sensorID {
			filtered = append(filtered, reading)
		}
	}

	return filtered
}

// GetLatestReading retorna a leitura mais recente
func (b *Buffer) GetLatestReading() *models.StrainReading {
	b.mutex.RLock()
	defer b.mutex.RUnlock()

	if len(b.readings) == 0 {
		return nil
	}

	return b.readings[len(b.readings)-1]
}

// GetLatestReadingBySensor retorna a leitura mais recente de um sensor
func (b *Buffer) GetLatestReadingBySensor(sensorID string) *models.StrainReading {
	b.mutex.RLock()
	defer b.mutex.RUnlock()

	// Busca de trás para frente para encontrar a mais recente
	for i := len(b.readings) - 1; i >= 0; i-- {
		if b.readings[i].SensorID == sensorID {
			return b.readings[i]
		}
	}

	return nil
}
