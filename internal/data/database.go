package data

import (
	"database/sql"
	"fmt"
	"time"

	"daq-system/internal/models"

	_ "modernc.org/sqlite"
)

// Database gerenciador do banco de dados SQLite
type Database struct {
	db   *sql.DB
	path string
}

// NewDatabase cria nova instância do banco de dados
func NewDatabase(dbPath string) *Database {
	db := &Database{path: dbPath}
	if err := db.connect(); err != nil {
		panic(fmt.Sprintf("Erro ao conectar banco: %v", err))
	}

	if err := db.initTables(); err != nil {
		panic(fmt.Sprintf("Erro ao inicializar tabelas: %v", err))
	}

	return db
}

// connect conecta ao banco de dados
func (d *Database) connect() error {
	var err error
	d.db, err = sql.Open("sqlite", d.path)
	if err != nil {
		return err
	}

	// Configura conexão
	d.db.SetMaxOpenConns(1)
	d.db.SetMaxIdleConns(1)

	return d.db.Ping()
}

// initTables cria as tabelas necessárias
func (d *Database) initTables() error {
	queries := []string{
		`CREATE TABLE IF NOT EXISTS strain_readings (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			timestamp INTEGER NOT NULL,
			strain_value REAL NOT NULL,
			raw_adc_value INTEGER NOT NULL,
			sensor_id TEXT NOT NULL,
			battery_level INTEGER NOT NULL,
			temperature REAL NOT NULL,
			checksum TEXT,
			created_at INTEGER DEFAULT (strftime('%s','now'))
		)`,

		`CREATE TABLE IF NOT EXISTS sensor_info (
			sensor_id TEXT PRIMARY KEY,
			name TEXT NOT NULL,
			status TEXT NOT NULL,
			last_seen INTEGER,
			protocol TEXT,
			signal_strength INTEGER,
			firmware_version TEXT,
			hardware_version TEXT,
			updated_at INTEGER DEFAULT (strftime('%s','now'))
		)`,

		`CREATE TABLE IF NOT EXISTS sensor_configs (
			sensor_id TEXT PRIMARY KEY,
			sampling_rate_ms INTEGER NOT NULL,
			transmission_interval_s INTEGER NOT NULL,
			calibration_factor REAL NOT NULL,
			offset_value REAL NOT NULL,
			deep_sleep_enabled BOOLEAN NOT NULL,
			wifi_ssid TEXT,
			wifi_password TEXT,
			updated_at INTEGER DEFAULT (strftime('%s','now'))
		)`,

		// Índices para performance
		`CREATE INDEX IF NOT EXISTS idx_readings_timestamp ON strain_readings(timestamp)`,
		`CREATE INDEX IF NOT EXISTS idx_readings_sensor ON strain_readings(sensor_id)`,
		`CREATE INDEX IF NOT EXISTS idx_readings_sensor_timestamp ON strain_readings(sensor_id, timestamp)`,
	}

	for _, query := range queries {
		if _, err := d.db.Exec(query); err != nil {
			return fmt.Errorf("erro ao executar query: %v", err)
		}
	}

	return nil
}

// StoreReading armazena uma leitura no banco
func (d *Database) StoreReading(reading *models.StrainReading) error {
	query := `INSERT INTO strain_readings 
		(timestamp, strain_value, raw_adc_value, sensor_id, battery_level, temperature, checksum)
		VALUES (?, ?, ?, ?, ?, ?, ?)`

	_, err := d.db.Exec(query,
		reading.Timestamp.Unix(),
		reading.StrainValue,
		reading.RawADCValue,
		reading.SensorID,
		reading.BatteryLevel,
		reading.Temperature,
		reading.Checksum,
	)

	return err
}

// StoreReadings armazena múltiplas leituras em lote
func (d *Database) StoreReadings(readings []*models.StrainReading) error {
	if len(readings) == 0 {
		return nil
	}

	tx, err := d.db.Begin()
	if err != nil {
		return err
	}
	defer tx.Rollback()

	query := `INSERT INTO strain_readings 
		(timestamp, strain_value, raw_adc_value, sensor_id, battery_level, temperature, checksum)
		VALUES (?, ?, ?, ?, ?, ?, ?)`

	stmt, err := tx.Prepare(query)
	if err != nil {
		return err
	}
	defer stmt.Close()

	for _, reading := range readings {
		_, err = stmt.Exec(
			reading.Timestamp.Unix(),
			reading.StrainValue,
			reading.RawADCValue,
			reading.SensorID,
			reading.BatteryLevel,
			reading.Temperature,
			reading.Checksum,
		)
		if err != nil {
			return err
		}
	}

	return tx.Commit()
}

// GetReadings recupera leituras do banco com filtros
func (d *Database) GetReadings(sensorID string, startTime, endTime *time.Time, limit int) ([]*models.StrainReading, error) {
	query := "SELECT timestamp, strain_value, raw_adc_value, sensor_id, battery_level, temperature, checksum FROM strain_readings WHERE 1=1"
	args := []interface{}{}

	if sensorID != "" {
		query += " AND sensor_id = ?"
		args = append(args, sensorID)
	}

	if startTime != nil {
		query += " AND timestamp >= ?"
		args = append(args, startTime.Unix())
	}

	if endTime != nil {
		query += " AND timestamp <= ?"
		args = append(args, endTime.Unix())
	}

	query += " ORDER BY timestamp DESC"

	if limit > 0 {
		query += " LIMIT ?"
		args = append(args, limit)
	}

	rows, err := d.db.Query(query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var readings []*models.StrainReading
	for rows.Next() {
		var timestamp int64
		reading := &models.StrainReading{}

		err = rows.Scan(
			&timestamp,
			&reading.StrainValue,
			&reading.RawADCValue,
			&reading.SensorID,
			&reading.BatteryLevel,
			&reading.Temperature,
			&reading.Checksum,
		)
		if err != nil {
			return nil, err
		}

		reading.Timestamp = time.Unix(timestamp, 0)
		readings = append(readings, reading)
	}

	return readings, rows.Err()
}

// StoreSensorInfo armazena informações de sensor
func (d *Database) StoreSensorInfo(info *models.SensorInfo) error {
	query := `INSERT OR REPLACE INTO sensor_info 
		(sensor_id, name, status, last_seen, protocol, signal_strength, firmware_version, hardware_version)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?)`

	var lastSeen *int64
	if info.LastSeen != nil {
		ts := info.LastSeen.Unix()
		lastSeen = &ts
	}

	var protocol *string
	if info.Protocol != nil {
		p := string(*info.Protocol)
		protocol = &p
	}

	_, err := d.db.Exec(query,
		info.SensorID,
		info.Name,
		string(info.Status),
		lastSeen,
		protocol,
		info.SignalStrength,
		info.FirmwareVersion,
		info.HardwareVersion,
	)

	return err
}

// StoreSensorConfig armazena configuração de sensor
func (d *Database) StoreSensorConfig(config *models.SensorConfiguration) error {
	query := `INSERT OR REPLACE INTO sensor_configs 
		(sensor_id, sampling_rate_ms, transmission_interval_s, calibration_factor, 
		 offset_value, deep_sleep_enabled, wifi_ssid, wifi_password)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?)`

	_, err := d.db.Exec(query,
		config.SensorID,
		config.SamplingRateMS,
		config.TransmissionIntervalS,
		config.CalibrationFactor,
		config.Offset,
		config.DeepSleepEnabled,
		config.WiFiSSID,
		config.WiFiPassword,
	)

	return err
}

// GetSensorConfig recupera configuração de sensor
func (d *Database) GetSensorConfig(sensorID string) (*models.SensorConfiguration, error) {
	query := `SELECT sensor_id, sampling_rate_ms, transmission_interval_s, 
		calibration_factor, offset_value, deep_sleep_enabled, wifi_ssid, wifi_password
		FROM sensor_configs WHERE sensor_id = ?`

	config := &models.SensorConfiguration{}
	err := d.db.QueryRow(query, sensorID).Scan(
		&config.SensorID,
		&config.SamplingRateMS,
		&config.TransmissionIntervalS,
		&config.CalibrationFactor,
		&config.Offset,
		&config.DeepSleepEnabled,
		&config.WiFiSSID,
		&config.WiFiPassword,
	)

	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}

	return config, nil
}

// CleanupOldData remove dados antigos do banco
func (d *Database) CleanupOldData(days int) (int64, error) {
	cutoffTime := time.Now().AddDate(0, 0, -days)

	result, err := d.db.Exec(
		"DELETE FROM strain_readings WHERE timestamp < ?",
		cutoffTime.Unix(),
	)
	if err != nil {
		return 0, err
	}

	return result.RowsAffected()
}

// GetDatabaseStats retorna estatísticas do banco
func (d *Database) GetDatabaseStats() (map[string]interface{}, error) {
	stats := make(map[string]interface{})

	// Conta total de leituras
	var totalReadings int64
	err := d.db.QueryRow("SELECT COUNT(*) FROM strain_readings").Scan(&totalReadings)
	if err != nil {
		return nil, err
	}
	stats["total_readings"] = totalReadings

	// Conta sensores únicos
	var uniqueSensors int64
	err = d.db.QueryRow("SELECT COUNT(DISTINCT sensor_id) FROM strain_readings").Scan(&uniqueSensors)
	if err != nil {
		return nil, err
	}
	stats["unique_sensors"] = uniqueSensors

	// Data da primeira e última leitura
	var firstReading, lastReading int64
	err = d.db.QueryRow("SELECT MIN(timestamp), MAX(timestamp) FROM strain_readings").Scan(&firstReading, &lastReading)
	if err != nil && err != sql.ErrNoRows {
		return nil, err
	}

	if err != sql.ErrNoRows {
		stats["first_reading"] = time.Unix(firstReading, 0).Format(time.RFC3339)
		stats["last_reading"] = time.Unix(lastReading, 0).Format(time.RFC3339)
	}

	return stats, nil
}

// Close fecha a conexão com o banco
func (d *Database) Close() error {
	if d.db != nil {
		return d.db.Close()
	}
	return nil
}
