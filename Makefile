# Makefile para o Sistema DAQ em Go/C
# Compatível com Windows/bash

.PHONY: help build run clean test deps install-deps format lint docker-build docker-run setup

# Variáveis
GO_MODULE := daq_system
APP_NAME := daq-server
VERSION := $(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")
BUILD_TIME := $(shell date -u '+%Y-%m-%d_%H:%M:%S')
LDFLAGS := -ldflags "-X main.Version=$(VERSION) -X main.BuildTime=$(BUILD_TIME)"

# Cores para output
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
NC := \033[0m # No Color

# Diretórios
BUILD_DIR := build
WEB_DIR := web
SIMULATOR_DIR := simulators
DATA_DIR := data

help: ## Mostra esta ajuda
	@echo "$(GREEN)Sistema DAQ - Comandos Disponíveis:$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""

setup: ## Configura o ambiente de desenvolvimento
	@echo "$(GREEN)Configurando ambiente...$(NC)"
	@mkdir -p $(BUILD_DIR) $(DATA_DIR) $(WEB_DIR)
	@echo "$(GREEN)✓ Diretórios criados$(NC)"

deps: ## Instala dependências Go
	@echo "$(GREEN)Instalando dependências Go...$(NC)"
	go mod tidy
	go mod download
	@echo "$(GREEN)✓ Dependências instaladas$(NC)"

install-deps: ## Instala ferramentas de desenvolvimento
	@echo "$(GREEN)Instalando ferramentas de desenvolvimento...$(NC)"
	go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest
	go install github.com/air-verse/air@latest
	@echo "$(GREEN)✓ Ferramentas instaladas$(NC)"

format: ## Formata o código Go
	@echo "$(GREEN)Formatando código...$(NC)"
	go fmt ./...
	@echo "$(GREEN)✓ Código formatado$(NC)"

lint: ## Executa linting no código
	@echo "$(GREEN)Executando lint...$(NC)"
	golangci-lint run --timeout=5m
	@echo "$(GREEN)✓ Lint concluído$(NC)"

build: setup deps ## Compila o projeto
	@echo "$(GREEN)Compilando servidor Go...$(NC)"
	go build $(LDFLAGS) -o $(BUILD_DIR)/$(APP_NAME) ./cmd/server
	@echo "$(GREEN)✓ Servidor compilado: $(BUILD_DIR)/$(APP_NAME)$(NC)"

build-simulators: ## Compila simuladores C
	@echo "$(GREEN)Compilando simuladores C...$(NC)"
	@cd $(SIMULATOR_DIR) && \
	gcc -c -fPIC hx711_simulator.c -o hx711_simulator.o && \
	gcc -shared -o libhx711_simulator.so hx711_simulator.o -lm && \
	echo "$(GREEN)✓ HX711 simulator compilado$(NC)" || echo "$(RED)✗ Erro na compilação do HX711$(NC)"

run: build ## Executa o servidor
	@echo "$(GREEN)Iniciando servidor DAQ...$(NC)"
	./$(BUILD_DIR)/$(APP_NAME)

run-dev: ## Executa em modo desenvolvimento (hot reload)
	@echo "$(GREEN)Iniciando modo desenvolvimento...$(NC)"
	air -c .air.toml

test: ## Executa testes
	@echo "$(GREEN)Executando testes...$(NC)"
	go test -v -race -coverprofile=coverage.out ./...
	go tool cover -html=coverage.out -o coverage.html
	@echo "$(GREEN)✓ Testes concluídos (ver coverage.html)$(NC)"

benchmark: ## Executa benchmarks
	@echo "$(GREEN)Executando benchmarks...$(NC)"
	go test -bench=. -benchmem ./...

clean: ## Limpa arquivos de build
	@echo "$(GREEN)Limpando arquivos...$(NC)"
	rm -rf $(BUILD_DIR)
	rm -f coverage.out coverage.html
	@cd $(SIMULATOR_DIR) && rm -f *.o *.so *.dll
	@echo "$(GREEN)✓ Limpeza concluída$(NC)"

init-web: ## Inicializa frontend web básico
	@echo "$(GREEN)Criando frontend web básico...$(NC)"
	@mkdir -p $(WEB_DIR)/css $(WEB_DIR)/js
	@echo "<!DOCTYPE html><html><head><title>DAQ System</title></head><body><h1>DAQ System Dashboard</h1><div id='app'></div></body></html>" > $(WEB_DIR)/index.html
	@echo "body { font-family: Arial, sans-serif; margin: 20px; }" > $(WEB_DIR)/css/style.css
	@echo "console.log('DAQ System Web Interface');" > $(WEB_DIR)/js/app.js
	@echo "$(GREEN)✓ Frontend básico criado em $(WEB_DIR)/$(NC)"

docker-build: ## Constrói imagem Docker
	@echo "$(GREEN)Construindo imagem Docker...$(NC)"
	docker build -t $(GO_MODULE):$(VERSION) .
	@echo "$(GREEN)✓ Imagem Docker criada: $(GO_MODULE):$(VERSION)$(NC)"

docker-run: ## Executa container Docker
	@echo "$(GREEN)Executando container Docker...$(NC)"
	docker run -p 8080:8080 -v $(PWD)/data:/app/data $(GO_MODULE):$(VERSION)

# Comandos de desenvolvimento
dev-install: setup deps install-deps init-web ## Configura ambiente completo de desenvolvimento
	@echo "$(GREEN)✓ Ambiente de desenvolvimento configurado!$(NC)"
	@echo "$(YELLOW)Próximos passos:$(NC)"
	@echo "  - Execute 'make run-dev' para desenvolvimento"
	@echo "  - Execute 'make build && make run' para produção"
	@echo "  - Execute 'make test' para testar"

status: ## Mostra status do projeto
	@echo "$(GREEN)Status do Projeto DAQ:$(NC)"
	@echo "  Versão: $(VERSION)"
	@echo "  Build Time: $(BUILD_TIME)"
	@echo "  Go Version: $(shell go version)"
	@if [ -f "$(BUILD_DIR)/$(APP_NAME)" ]; then \
		echo "  Status: $(GREEN)✓ Compilado$(NC)"; \
		echo "  Binário: $(BUILD_DIR)/$(APP_NAME)"; \
	else \
		echo "  Status: $(YELLOW)○ Não compilado$(NC)"; \
	fi
	@echo "  Configuração: $(shell if [ -f config.json ]; then echo "$(GREEN)✓ Disponível$(NC)"; else echo "$(YELLOW)○ Usando example$(NC)"; fi)"

# Comandos para simuladores
sim-test: build-simulators ## Testa simuladores C
	@echo "$(GREEN)Testando simuladores...$(NC)"
	@cd $(SIMULATOR_DIR) && \
	echo "#include \"hx711_simulator.h\"\n#include <stdio.h>\nint main() {\n  hx711_simulator_t sim;\n  if(hx711_init(&sim)) printf(\"HX711 OK\\n\");\n  return 0;\n}" > test.c && \
	gcc test.c -L. -lhx711_simulator -o test && \
	LD_LIBRARY_PATH=. ./test && \
	rm test.c test
	@echo "$(GREEN)✓ Simuladores testados$(NC)"

# Comandos de dados
backup-data: ## Faz backup dos dados
	@echo "$(GREEN)Fazendo backup dos dados...$(NC)"
	@if [ -d "$(DATA_DIR)" ]; then \
		tar -czf "backup_$(shell date +%Y%m%d_%H%M%S).tar.gz" $(DATA_DIR); \
		echo "$(GREEN)✓ Backup criado$(NC)"; \
	else \
		echo "$(YELLOW)○ Nenhum dado para backup$(NC)"; \
	fi

clean-data: ## Limpa dados antigos (CUIDADO!)
	@echo "$(RED)⚠ ATENÇÃO: Isso irá apagar todos os dados!$(NC)"
	@read -p "Tem certeza? Digite 'yes' para continuar: " confirm && [ "$$confirm" = "yes" ]
	@rm -rf $(DATA_DIR)/*
	@echo "$(GREEN)✓ Dados limpos$(NC)"

# Alias para comandos comuns
all: build ## Alias para build
server: run ## Alias para run
install: dev-install ## Alias para dev-install

# Para sistemas Windows específicos
windows-setup: ## Configuração específica para Windows
	@echo "$(GREEN)Configuração para Windows...$(NC)"
	@if ! command -v gcc >/dev/null 2>&1; then \
		echo "$(YELLOW)⚠ GCC não encontrado. Instale MinGW-w64 ou TDM-GCC$(NC)"; \
	fi
	@if ! command -v make >/dev/null 2>&1; then \
		echo "$(YELLOW)⚠ Make não encontrado. Use 'go run .\cmd\server' diretamente$(NC)"; \
	fi
