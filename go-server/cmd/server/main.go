package main

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"daq-system/internal/api"
	"daq-system/internal/config"
	"daq-system/internal/database"
	"daq-system/internal/oscilloscope"
	"daq-system/internal/protocol"
	"daq-system/internal/websocket"

	"github.com/rs/zerolog"
)

func main() {
	// Setup logging
	zerolog.TimeFieldFormat = time.RFC3339
	logger := zerolog.New(os.Stdout).With().Timestamp().Logger()

	// Load configuration
	cfg, err := config.Load("config.yaml")
	if err != nil {
		logger.Fatal().Err(err).Msg("Failed to load configuration")
	}

	// Initialize database
	db, err := database.New(cfg.Database)
	if err != nil {
		logger.Fatal().Err(err).Msg("Failed to initialize database")
	}
	defer db.Close()

	// Initialize protocol handler
	protocolHandler := protocol.NewHandler(logger)

	// Initialize oscilloscope streamer
	oscStreamer := oscilloscope.NewStreamer(cfg.Oscilloscope, logger)

	// Initialize WebSocket hub
	wsHub := websocket.NewHub(logger)
	go wsHub.Run()

	// Initialize API server
	apiServer := api.NewServer(cfg.API, db, oscStreamer, wsHub, logger)

	// Setup HTTP server
	srv := &http.Server{
		Addr:         fmt.Sprintf(":%d", cfg.Server.Port),
		Handler:      apiServer.Router(),
		ReadTimeout:  time.Duration(cfg.Server.ReadTimeout) * time.Second,
		WriteTimeout: time.Duration(cfg.Server.WriteTimeout) * time.Second,
		IdleTimeout:  time.Duration(cfg.Server.IdleTimeout) * time.Second,
	}

	// Start server in goroutine
	go func() {
		logger.Info().
			Int("port", cfg.Server.Port).
			Msg("Starting DAQ server")

		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Fatal().Err(err).Msg("Server failed to start")
		}
	}()

	// Start protocol listener for hardware communication
	go func() {
		if err := protocolHandler.StartListener(cfg.Protocol.Port); err != nil {
			logger.Error().Err(err).Msg("Failed to start protocol listener")
		}
	}()

	// Wait for interrupt signal
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	logger.Info().Msg("Shutting down server...")

	// Graceful shutdown with timeout
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		logger.Fatal().Err(err).Msg("Server forced to shutdown")
	}

	logger.Info().Msg("Server exited")
}
