#include "hx711_simulator.h"
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

// Implementação das funções do simulador HX711

static uint64_t get_timestamp_us(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)(ts.tv_sec) * 1000000ULL + (uint64_t)(ts.tv_nsec) / 1000ULL;
}

static float generate_noise(float level) {
    // Gera ruído gaussiano simples
    static bool hasSpare = false;
    static float spare;
    
    if (hasSpare) {
        hasSpare = false;
        return spare * level;
    }
    
    hasSpare = true;
    float u = ((float)rand() / RAND_MAX) * 2.0f - 1.0f;
    float v = ((float)rand() / RAND_MAX) * 2.0f - 1.0f;
    float s = u * u + v * v;
    
    while (s >= 1.0f || s == 0.0f) {
        u = ((float)rand() / RAND_MAX) * 2.0f - 1.0f;
        v = ((float)rand() / RAND_MAX) * 2.0f - 1.0f;
        s = u * u + v * v;
    }
    
    float result = u * sqrtf(-2.0f * logf(s) / s);
    spare = v * sqrtf(-2.0f * logf(s) / s);
    
    return result * level;
}

bool hx711_init(hx711_simulator_t* hx711) {
    if (!hx711) return false;
    
    // Configuração padrão
    memset(hx711, 0, sizeof(hx711_simulator_t));
    
    hx711->config.gain = HX711_GAIN_128;
    hx711->config.calibration_factor = 1.0f;
    hx711->config.offset = 0.0f;
    hx711->config.noise_level = 0.01f; // 1% de ruído
    hx711->config.power_down = false;
    hx711->config.sample_count = 0;
    
    hx711->temperature = 25.0f; // Temperatura ambiente
    hx711->conversion_time_us = 100000; // 100ms típico para 10Hz
    hx711->initialized = true;
    
    // Seed do gerador de números aleatórios
    srand((unsigned int)time(NULL));
    
    return true;
}

bool hx711_set_gain(hx711_simulator_t* hx711, uint8_t gain) {
    if (!hx711 || !hx711->initialized) return false;
    
    if (gain != HX711_GAIN_128 && gain != HX711_GAIN_64 && gain != HX711_GAIN_32) {
        return false;
    }
    
    hx711->config.gain = gain;
    return true;
}

bool hx711_set_calibration(hx711_simulator_t* hx711, float factor, float offset) {
    if (!hx711 || !hx711->initialized) return false;
    
    hx711->config.calibration_factor = factor;
    hx711->config.offset = offset;
    return true;
}

void hx711_power_down(hx711_simulator_t* hx711) {
    if (hx711) {
        hx711->config.power_down = true;
    }
}

void hx711_power_up(hx711_simulator_t* hx711) {
    if (hx711) {
        hx711->config.power_down = false;
    }
}

bool hx711_is_ready(hx711_simulator_t* hx711) {
    if (!hx711 || !hx711->initialized || hx711->config.power_down) {
        return false;
    }
    
    // Simula tempo de conversão
    static uint64_t last_conversion = 0;
    uint64_t now = get_timestamp_us();
    
    if (now - last_conversion >= hx711->conversion_time_us) {
        last_conversion = now;
        return true;
    }
    
    return false;
}

int32_t hx711_read_raw(hx711_simulator_t* hx711) {
    if (!hx711 || !hx711->initialized || hx711->config.power_down) {
        return 0;
    }
    
    // Gera valor base (simula carga zero + offset)
    int32_t base_value = (int32_t)(hx711->config.offset * 1000.0f);
    
    // Adiciona ruído
    float noise = generate_noise(hx711->config.noise_level * 1000.0f);
    int32_t raw_value = base_value + (int32_t)noise;
    
    // Simula deriva térmica
    float thermal_drift = (hx711->temperature - 25.0f) * 10.0f;
    raw_value += (int32_t)thermal_drift;
    
    // Aplica ganho (simplificado)
    float gain_factor = (float)hx711->config.gain / 128.0f;
    raw_value = (int32_t)(raw_value * gain_factor);
    
    // Limita ao range do ADC de 24 bits
    if (raw_value > HX711_MAX_VALUE) raw_value = HX711_MAX_VALUE;
    if (raw_value < HX711_MIN_VALUE) raw_value = HX711_MIN_VALUE;
    
    // Atualiza dados
    hx711->last_reading.raw_value = raw_value;
    hx711->last_reading.timestamp_us = get_timestamp_us();
    hx711->last_reading.data_ready = true;
    hx711->config.sample_count++;
    
    return raw_value;
}

float hx711_read_strain(hx711_simulator_t* hx711) {
    int32_t raw = hx711_read_raw(hx711);
    return hx711_raw_to_strain(hx711, raw);
}

hx711_reading_t hx711_read_complete(hx711_simulator_t* hx711) {
    hx711_reading_t reading = {0};
    
    if (!hx711 || !hx711->initialized || hx711->config.power_down) {
        return reading;
    }
    
    reading.raw_value = hx711_read_raw(hx711);
    reading.strain_value = hx711_raw_to_strain(hx711, reading.raw_value);
    reading.timestamp_us = get_timestamp_us();
    reading.data_ready = true;
    
    hx711->last_reading = reading;
    
    return reading;
}

void hx711_simulate_load(hx711_simulator_t* hx711, float strain_microstrains) {
    if (!hx711 || !hx711->initialized) return;
    
    // Converte strain para valor ADC e armazena como "carga aplicada"
    // Isso será adicionado nas próximas leituras
    int32_t raw_equivalent = hx711_strain_to_raw(hx711, strain_microstrains);
    hx711->config.offset = (float)raw_equivalent / 1000.0f;
}

void hx711_simulate_noise(hx711_simulator_t* hx711, float noise_level) {
    if (!hx711 || !hx711->initialized) return;
    
    if (noise_level >= 0.0f && noise_level <= 1.0f) {
        hx711->config.noise_level = noise_level;
    }
}

void hx711_simulate_temperature_drift(hx711_simulator_t* hx711, float temperature) {
    if (!hx711 || !hx711->initialized) return;
    
    hx711->temperature = temperature;
}

float hx711_raw_to_strain(hx711_simulator_t* hx711, int32_t raw_value) {
    if (!hx711 || !hx711->initialized) return 0.0f;
    
    // Conversão simplificada: assume fator de calibração linear
    float strain = (float)raw_value * hx711->config.calibration_factor;
    strain -= hx711->config.offset;
    
    return strain;
}

int32_t hx711_strain_to_raw(hx711_simulator_t* hx711, float strain_value) {
    if (!hx711 || !hx711->initialized) return 0;
    
    // Conversão inversa
    float adjusted_strain = strain_value + hx711->config.offset;
    int32_t raw = (int32_t)(adjusted_strain / hx711->config.calibration_factor);
    
    // Limita ao range
    if (raw > HX711_MAX_VALUE) raw = HX711_MAX_VALUE;
    if (raw < HX711_MIN_VALUE) raw = HX711_MIN_VALUE;
    
    return raw;
}

uint32_t hx711_get_sample_rate(hx711_simulator_t* hx711) {
    if (!hx711 || !hx711->initialized) return 0;
    
    return 1000000 / hx711->conversion_time_us; // Hz
}

void hx711_reset(hx711_simulator_t* hx711) {
    if (!hx711) return;
    
    hx711->config.sample_count = 0;
    hx711->last_reading.data_ready = false;
    hx711->temperature = 25.0f;
}

bool hx711_self_test(hx711_simulator_t* hx711) {
    if (!hx711 || !hx711->initialized) return false;
    
    // Teste simples: tenta ler alguns valores
    for (int i = 0; i < 5; i++) {
        if (!hx711_is_ready(hx711)) continue;
        
        int32_t raw = hx711_read_raw(hx711);
        if (raw == 0) return false; // Falha na leitura
    }
    
    return true;
}

float hx711_get_temperature(hx711_simulator_t* hx711) {
    if (!hx711 || !hx711->initialized) return 0.0f;
    
    return hx711->temperature;
}

uint32_t hx711_get_sample_count(hx711_simulator_t* hx711) {
    if (!hx711 || !hx711->initialized) return 0;
    
    return hx711->config.sample_count;
}
