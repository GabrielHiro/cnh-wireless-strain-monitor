package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"strconv"
	"syscall"
	"time"

	"daq-system/internal/data"
	"daq-system/internal/models"
	"daq-system/internal/simulator"
	"daq-system/internal/websocket"

	"github.com/gorilla/mux"
	"github.com/rs/cors"
)

const (
	DefaultPort = "8080"
	Version     = "1.0.0"
)

type Config struct {
	ServerPort      string           `json:"server_port"`
	DatabasePath    string           `json:"database_path"`
	SampleRate      int              `json:"sample_rate"`
	BufferSize      int              `json:"buffer_size"`
	SimulatorConfig simulator.Config `json:"simulator_config"`
}

type Server struct {
	dataManager *data.Manager
	wsHub       *websocket.Hub
	simulator   *simulator.DAQSimulator
	httpServer  *http.Server
	config      *Config
}

func loadConfig() (*Config, error) {
	configPath := "config.json"
	if _, err := os.Stat(configPath); os.IsNotExist(err) {
		configPath = "config_example.json"
	}

	file, err := os.Open(configPath)
	if err != nil {
		return nil, fmt.Errorf("failed to open config file: %v", err)
	}
	defer file.Close()

	var config Config
	decoder := json.NewDecoder(file)
	if err := decoder.Decode(&config); err != nil {
		return nil, fmt.Errorf("failed to decode config: %v", err)
	}

	return &config, nil
}

func NewServer() (*Server, error) {
	config, err := loadConfig()
	if err != nil {
		return nil, fmt.Errorf("failed to load configuration: %v", err)
	}

	// Cria diretório para banco de dados se não existir
	dbDir := filepath.Dir(config.DatabasePath)
	if err := os.MkdirAll(dbDir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create database directory: %v", err)
	}

	// Inicializa data manager (usando constructor simples)
	dataManager := data.NewManager()

	wsHub := websocket.NewHub()
	sim := simulator.NewDAQSimulator()

	return &Server{
		dataManager: dataManager,
		wsHub:       wsHub,
		simulator:   sim,
		config:      config,
	}, nil
}

func (s *Server) setupRoutes() *mux.Router {
	r := mux.NewRouter()

	// API routes
	api := r.PathPrefix("/api/v1").Subrouter()

	// Health check
	api.HandleFunc("/health", s.healthHandler).Methods("GET")

	// Oscilloscope API
	oscilloscope := api.PathPrefix("/oscilloscope").Subrouter()
	oscilloscope.HandleFunc("/trace/{sensorId}", s.getTraceData).Methods("GET")
	oscilloscope.HandleFunc("/snapshot", s.getRealtimeSnapshot).Methods("GET")
	oscilloscope.HandleFunc("/streaming/{sensorId}", s.getStreamingData).Methods("GET")
	oscilloscope.HandleFunc("/metrics", s.getPerformanceMetrics).Methods("GET")

	// Sensor management
	sensors := api.PathPrefix("/sensors").Subrouter()
	sensors.HandleFunc("", s.listSensors).Methods("GET")
	sensors.HandleFunc("/{sensorId}", s.getSensor).Methods("GET")
	sensors.HandleFunc("/{sensorId}/config", s.configureSensor).Methods("POST")

	// Data export
	data := api.PathPrefix("/data").Subrouter()
	data.HandleFunc("/export/{format}", s.exportData).Methods("GET")

	// Simulator control
	sim := api.PathPrefix("/simulator").Subrouter()
	sim.HandleFunc("/start", s.startSimulator).Methods("POST")
	sim.HandleFunc("/stop", s.stopSimulator).Methods("POST")
	sim.HandleFunc("/status", s.getSimulatorStatus).Methods("GET")

	// WebSocket endpoint
	r.HandleFunc("/ws", s.wsHub.HandleWebSocket)

	// Static files
	r.PathPrefix("/").Handler(http.FileServer(http.Dir("./web/")))

	return r
}

func (s *Server) healthHandler(w http.ResponseWriter, r *http.Request) {
	response := map[string]interface{}{
		"status":    "healthy",
		"version":   Version,
		"timestamp": time.Now().Unix(),
		"uptime":    time.Since(time.Now()).Seconds(),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func (s *Server) getTraceData(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	sensorID := vars["sensorId"]

	// Parse query parameters
	decimationFactor := 1
	if df := r.URL.Query().Get("decimation"); df != "" {
		if parsed, err := strconv.Atoi(df); err == nil && parsed > 0 {
			decimationFactor = parsed
		}
	}

	maxPoints := 1000
	if mp := r.URL.Query().Get("maxPoints"); mp != "" {
		if parsed, err := strconv.Atoi(mp); err == nil && parsed > 0 {
			maxPoints = parsed
		}
	}

	traceData := s.dataManager.GetTraceData(sensorID, maxPoints, decimationFactor)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(traceData)
}

func (s *Server) getRealtimeSnapshot(w http.ResponseWriter, r *http.Request) {
	snapshot := s.dataManager.GetRealtimeSnapshot()

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(snapshot)
}

func (s *Server) getStreamingData(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	sensorID := vars["sensorId"]

	sinceTimestamp := int64(0)
	if since := r.URL.Query().Get("since"); since != "" {
		if parsed, err := strconv.ParseInt(since, 10, 64); err == nil {
			sinceTimestamp = parsed
		}
	}

	streamingData := s.dataManager.GetStreamingData(sensorID, sinceTimestamp)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(streamingData)
}

func (s *Server) getPerformanceMetrics(w http.ResponseWriter, r *http.Request) {
	metrics := s.dataManager.GetPerformanceMetrics()

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(metrics)
}

func (s *Server) listSensors(w http.ResponseWriter, r *http.Request) {
	sensors := s.dataManager.GetActiveSensors()

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(sensors)
}

func (s *Server) getSensor(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	sensorID := vars["sensorId"]

	sensor := s.dataManager.GetSensor(sensorID)
	if sensor == nil {
		http.Error(w, "Sensor not found", http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(sensor)
}

func (s *Server) configureSensor(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	sensorID := vars["sensorId"]

	var config models.SensorConfiguration
	if err := json.NewDecoder(r.Body).Decode(&config); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	config.SensorID = sensorID
	if err := s.dataManager.ConfigureSensor(&config); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "configured"})
}

func (s *Server) exportData(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	format := vars["format"]

	sensorID := r.URL.Query().Get("sensorId")
	startTime := r.URL.Query().Get("startTime")
	endTime := r.URL.Query().Get("endTime")

	data, contentType, filename, err := s.dataManager.ExportData(format, sensorID, startTime, endTime)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", contentType)
	w.Header().Set("Content-Disposition", fmt.Sprintf("attachment; filename=%s", filename))
	w.Write(data)
}

func (s *Server) startSimulator(w http.ResponseWriter, r *http.Request) {
	var config simulator.Config
	if err := json.NewDecoder(r.Body).Decode(&config); err != nil {
		// Use default config if no body provided
		config = simulator.DefaultConfig()
	}

	if err := s.simulator.Start(config); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "started"})
}

func (s *Server) stopSimulator(w http.ResponseWriter, r *http.Request) {
	s.simulator.Stop()

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "stopped"})
}

func (s *Server) getSimulatorStatus(w http.ResponseWriter, r *http.Request) {
	status := s.simulator.GetStatus()

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(status)
}

func (s *Server) Start(port string) error {
	router := s.setupRoutes()

	// Setup CORS
	c := cors.New(cors.Options{
		AllowedOrigins: []string{"*"},
		AllowedMethods: []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
		AllowedHeaders: []string{"*"},
	})

	handler := c.Handler(router)

	s.httpServer = &http.Server{
		Addr:    ":" + port,
		Handler: handler,
	}

	// Start WebSocket hub
	go s.wsHub.Run()

	// Start data manager background tasks
	go s.dataManager.Start()

	log.Printf("DAQ Server starting on port %s", port)
	log.Printf("WebSocket endpoint: ws://localhost:%s/ws", port)
	log.Printf("API documentation: http://localhost:%s/api/v1/health", port)

	return s.httpServer.ListenAndServe()
}

func (s *Server) Stop() error {
	log.Println("Shutting down server...")

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	// Stop components
	s.simulator.Stop()
	s.dataManager.Stop()
	s.wsHub.Stop()

	// Stop HTTP server
	if s.httpServer != nil {
		return s.httpServer.Shutdown(ctx)
	}

	return nil
}

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = DefaultPort
	}

	server, err := NewServer()
	if err != nil {
		log.Fatalf("Failed to create server: %v", err)
	}

	// Handle graceful shutdown
	c := make(chan os.Signal, 1)
	signal.Notify(c, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		<-c
		log.Println("Received shutdown signal")
		if err := server.Stop(); err != nil {
			log.Printf("Error during shutdown: %v", err)
		}
		os.Exit(0)
	}()

	// Start server
	if err := server.Start(server.config.ServerPort); err != nil && err != http.ErrServerClosed {
		log.Fatalf("Server failed to start: %v", err)
	}
}
