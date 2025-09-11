#ifndef HX711_SIMULATOR_H
#define HX711_SIMULATOR_H

#include <stdint.h>
#include <stdbool.h>

// Configurações do HX711
#define HX711_GAIN_128 128
#define HX711_GAIN_64  64  
#define HX711_GAIN_32  32

#define HX711_RESOLUTION 24
#define HX711_MAX_VALUE  ((1 << (HX711_RESOLUTION - 1)) - 1)
#define HX711_MIN_VALUE  (-(1 << (HX711_RESOLUTION - 1)))

// Taxa de amostragem típica do HX711
#define HX711_SAMPLE_RATE_HZ 10

typedef struct {
    uint8_t gain;              // Ganho configurado (128, 64, 32)
    float calibration_factor;  // Fator de calibração
    float offset;              // Offset para zero
    float noise_level;         // Nível de ruído (0.0-1.0)
    bool power_down;           // Estado de power down
    uint32_t sample_count;     // Contador de amostras
} hx711_config_t;

typedef struct {
    int32_t raw_value;         // Valor bruto do ADC (24-bit signed)
    float strain_value;        // Valor de deformação em µε
    uint64_t timestamp_us;     // Timestamp em microssegundos
    bool data_ready;           // Flag de dados prontos
} hx711_reading_t;

// Estrutura principal do simulador HX711
typedef struct {
    hx711_config_t config;
    hx711_reading_t last_reading;
    float temperature;         // Temperatura do chip
    uint32_t conversion_time_us; // Tempo de conversão em us
    bool initialized;
} hx711_simulator_t;

// Funções de inicialização e configuração
bool hx711_init(hx711_simulator_t* hx711);
bool hx711_set_gain(hx711_simulator_t* hx711, uint8_t gain);
bool hx711_set_calibration(hx711_simulator_t* hx711, float factor, float offset);
void hx711_power_down(hx711_simulator_t* hx711);
void hx711_power_up(hx711_simulator_t* hx711);

// Funções de leitura
bool hx711_is_ready(hx711_simulator_t* hx711);
int32_t hx711_read_raw(hx711_simulator_t* hx711);
float hx711_read_strain(hx711_simulator_t* hx711);
hx711_reading_t hx711_read_complete(hx711_simulator_t* hx711);

// Funções de simulação
void hx711_simulate_load(hx711_simulator_t* hx711, float strain_microstrains);
void hx711_simulate_noise(hx711_simulator_t* hx711, float noise_level);
void hx711_simulate_temperature_drift(hx711_simulator_t* hx711, float temperature);

// Funções utilitárias
float hx711_raw_to_strain(hx711_simulator_t* hx711, int32_t raw_value);
int32_t hx711_strain_to_raw(hx711_simulator_t* hx711, float strain_value);
uint32_t hx711_get_sample_rate(hx711_simulator_t* hx711);
void hx711_reset(hx711_simulator_t* hx711);

// Funções de diagnóstico
bool hx711_self_test(hx711_simulator_t* hx711);
float hx711_get_temperature(hx711_simulator_t* hx711);
uint32_t hx711_get_sample_count(hx711_simulator_t* hx711);

#endif // HX711_SIMULATOR_H
