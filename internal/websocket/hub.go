package websocket

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"sync"
	"time"

	"daq-system/internal/models"

	"github.com/gorilla/websocket"
)

const (
	// Configurações WebSocket
	WriteWait      = 10 * time.Second
	PongWait       = 60 * time.Second
	PingPeriod     = (PongWait * 9) / 10
	MaxMessageSize = 512
	BufferSize     = 1024
)

var upgrader = websocket.Upgrader{
	ReadBufferSize:  BufferSize,
	WriteBufferSize: BufferSize,
	CheckOrigin: func(r *http.Request) bool {
		// Permite conexões de qualquer origem (para desenvolvimento)
		return true
	},
}

// Client representa um cliente WebSocket conectado
type Client struct {
	hub  *Hub
	conn *websocket.Conn
	send chan []byte
	id   string
}

// Hub mantém o conjunto de clientes ativos e broadcasts de mensagens
type Hub struct {
	clients    map[*Client]bool
	broadcast  chan []byte
	register   chan *Client
	unregister chan *Client
	mutex      sync.RWMutex
	running    bool
}

// NewHub cria um novo hub WebSocket
func NewHub() *Hub {
	return &Hub{
		clients:    make(map[*Client]bool),
		broadcast:  make(chan []byte, 256),
		register:   make(chan *Client),
		unregister: make(chan *Client),
	}
}

// Run inicia o hub WebSocket
func (h *Hub) Run() {
	h.mutex.Lock()
	h.running = true
	h.mutex.Unlock()

	for {
		select {
		case client := <-h.register:
			h.mutex.Lock()
			h.clients[client] = true
			h.mutex.Unlock()

			log.Printf("Cliente WebSocket conectado: %s", client.id)

			// Envia mensagem de boas-vindas
			welcomeMsg := models.WebSocketMessage{
				Type: "welcome",
				Data: map[string]interface{}{
					"client_id": client.id,
					"timestamp": time.Now().Unix(),
					"status":    "connected",
				},
			}
			client.sendMessage(welcomeMsg)

		case client := <-h.unregister:
			h.mutex.Lock()
			if _, ok := h.clients[client]; ok {
				delete(h.clients, client)
				close(client.send)
			}
			h.mutex.Unlock()

			log.Printf("Cliente WebSocket desconectado: %s", client.id)

		case message := <-h.broadcast:
			h.mutex.RLock()
			for client := range h.clients {
				select {
				case client.send <- message:
				default:
					delete(h.clients, client)
					close(client.send)
				}
			}
			h.mutex.RUnlock()
		}
	}
}

// Stop para o hub WebSocket
func (h *Hub) Stop() {
	h.mutex.Lock()
	if h.running {
		h.running = false

		// Fecha todas as conexões
		for client := range h.clients {
			close(client.send)
			client.conn.Close()
		}
		h.clients = make(map[*Client]bool)
	}
	h.mutex.Unlock()
}

// HandleWebSocket manipula upgrades de conexão WebSocket
func (h *Hub) HandleWebSocket(w http.ResponseWriter, r *http.Request) {
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Printf("Erro no upgrade WebSocket: %v", err)
		return
	}

	clientID := generateClientID()
	client := &Client{
		hub:  h,
		conn: conn,
		send: make(chan []byte, 256),
		id:   clientID,
	}

	client.hub.register <- client

	// Inicia goroutines para leitura e escrita
	go client.writePump()
	go client.readPump()
}

// BroadcastSnapshot envia snapshot para todos os clientes
func (h *Hub) BroadcastSnapshot(snapshot *models.RealtimeSnapshot) {
	message := models.WebSocketMessage{
		Type: "realtime_snapshot",
		Data: snapshot,
	}

	h.broadcastMessage(message)
}

// BroadcastTraceUpdate envia atualização de traço
func (h *Hub) BroadcastTraceUpdate(sensorID string, streamingData *models.StreamingData) {
	message := models.WebSocketMessage{
		Type: "trace_update",
		Data: map[string]interface{}{
			"sensor_id": sensorID,
			"data":      streamingData,
		},
	}

	h.broadcastMessage(message)
}

// BroadcastSensorStatus envia status de sensor
func (h *Hub) BroadcastSensorStatus(sensorInfo *models.SensorInfo) {
	message := models.WebSocketMessage{
		Type: "sensor_status",
		Data: sensorInfo,
	}

	h.broadcastMessage(message)
}

// GetConnectedClients retorna número de clientes conectados
func (h *Hub) GetConnectedClients() int {
	h.mutex.RLock()
	defer h.mutex.RUnlock()

	return len(h.clients)
}

// broadcastMessage envia mensagem para todos os clientes
func (h *Hub) broadcastMessage(message models.WebSocketMessage) {
	data, err := json.Marshal(message)
	if err != nil {
		log.Printf("Erro ao serializar mensagem WebSocket: %v", err)
		return
	}

	select {
	case h.broadcast <- data:
	default:
		log.Println("Canal de broadcast cheio, mensagem descartada")
	}
}

// Métodos do Client

// readPump bombeia mensagens da conexão WebSocket para o hub
func (c *Client) readPump() {
	defer func() {
		c.hub.unregister <- c
		c.conn.Close()
	}()

	c.conn.SetReadLimit(MaxMessageSize)
	c.conn.SetReadDeadline(time.Now().Add(PongWait))
	c.conn.SetPongHandler(func(string) error {
		c.conn.SetReadDeadline(time.Now().Add(PongWait))
		return nil
	})

	for {
		_, message, err := c.conn.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				log.Printf("Erro WebSocket: %v", err)
			}
			break
		}

		// Processa mensagens recebidas do cliente
		c.handleClientMessage(message)
	}
}

// writePump bombeia mensagens do hub para a conexão WebSocket
func (c *Client) writePump() {
	ticker := time.NewTicker(PingPeriod)
	defer func() {
		ticker.Stop()
		c.conn.Close()
	}()

	for {
		select {
		case message, ok := <-c.send:
			c.conn.SetWriteDeadline(time.Now().Add(WriteWait))
			if !ok {
				c.conn.WriteMessage(websocket.CloseMessage, []byte{})
				return
			}

			w, err := c.conn.NextWriter(websocket.TextMessage)
			if err != nil {
				return
			}
			w.Write(message)

			// Adiciona mensagens enfileiradas à mensagem atual
			n := len(c.send)
			for i := 0; i < n; i++ {
				w.Write([]byte{'\n'})
				w.Write(<-c.send)
			}

			if err := w.Close(); err != nil {
				return
			}

		case <-ticker.C:
			c.conn.SetWriteDeadline(time.Now().Add(WriteWait))
			if err := c.conn.WriteMessage(websocket.PingMessage, nil); err != nil {
				return
			}
		}
	}
}

// sendMessage envia mensagem para este cliente específico
func (c *Client) sendMessage(message models.WebSocketMessage) {
	data, err := json.Marshal(message)
	if err != nil {
		log.Printf("Erro ao serializar mensagem: %v", err)
		return
	}

	select {
	case c.send <- data:
	default:
		close(c.send)
		delete(c.hub.clients, c)
	}
}

// handleClientMessage processa mensagens recebidas do cliente
func (c *Client) handleClientMessage(message []byte) {
	var msg models.WebSocketMessage
	if err := json.Unmarshal(message, &msg); err != nil {
		log.Printf("Erro ao deserializar mensagem do cliente %s: %v", c.id, err)
		return
	}

	switch msg.Type {
	case "ping":
		// Responde com pong
		pongMsg := models.WebSocketMessage{
			Type: "pong",
			Data: map[string]interface{}{
				"timestamp": time.Now().Unix(),
			},
		}
		c.sendMessage(pongMsg)

	case "subscribe":
		// Cliente quer se inscrever em atualizações específicas
		log.Printf("Cliente %s se inscreveu: %+v", c.id, msg.Data)

	case "unsubscribe":
		// Cliente quer cancelar inscrição
		log.Printf("Cliente %s cancelou inscrição: %+v", c.id, msg.Data)

	default:
		log.Printf("Tipo de mensagem desconhecido do cliente %s: %s", c.id, msg.Type)
	}
}

// generateClientID gera ID único para cliente
func generateClientID() string {
	return fmt.Sprintf("client_%d", time.Now().UnixNano())
}
