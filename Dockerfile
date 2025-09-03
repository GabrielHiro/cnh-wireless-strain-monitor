# Dockerfile para Sistema DAQ Go/C
# Build stage
FROM golang:1.21-alpine AS builder

# Instalar dependências para compilação C
RUN apk add --no-cache gcc musl-dev make

# Configurar diretório de trabalho
WORKDIR /app

# Copiar go mod files
COPY go.mod go.sum ./

# Download dependências
RUN go mod download

# Copiar código fonte
COPY . .

# Compilar simuladores C
WORKDIR /app/simulators
RUN gcc -c -fPIC hx711_simulator.c -o hx711_simulator.o && \
    gcc -shared -o libhx711_simulator.so hx711_simulator.o -lm

# Compilar aplicação Go
WORKDIR /app
RUN CGO_ENABLED=1 GOOS=linux go build -a -installsuffix cgo -o daq-server ./cmd/server

# Runtime stage
FROM alpine:latest

# Instalar runtime dependencies
RUN apk --no-cache add ca-certificates libc6-compat

# Criar usuário não-root
RUN addgroup -g 1001 -S daq && \
    adduser -S daq -u 1001 -G daq

# Criar diretórios necessários
RUN mkdir -p /app/data /app/web /app/simulators && \
    chown -R daq:daq /app

WORKDIR /app

# Copiar binários e arquivos necessários
COPY --from=builder /app/daq-server .
COPY --from=builder /app/simulators/libhx711_simulator.so ./simulators/
COPY --from=builder /app/config_example.json ./config.json
COPY --from=builder /app/web ./web

# Configurar usuário
USER daq

# Expor porta
EXPOSE 8080

# Variáveis de ambiente
ENV PORT=8080
ENV DATABASE_PATH=/app/data/daq.db
ENV LD_LIBRARY_PATH=/app/simulators

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:${PORT}/api/health || exit 1

# Volume para dados persistentes
VOLUME ["/app/data"]

# Comando padrão
CMD ["./daq-server"]
