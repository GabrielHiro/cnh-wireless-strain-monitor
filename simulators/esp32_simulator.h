#ifndef ESP32_SIMULATOR_H
#define ESP32_SIMULATOR_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

// Configurações do ESP32
#define ESP32_MAX_GPIOS         48
#define ESP32_MAX_ADC_CHANNELS  20
#define ESP32_ADC_RESOLUTION    4096  // 12-bit ADC
#define ESP32_DAC_RESOLUTION    256   // 8-bit DAC
#define ESP32_WIFI_MAX_SSID     32
#define ESP32_BLE_MAX_NAME      32

// Modos de operação dos pinos
typedef enum {
    ESP32_GPIO_INPUT = 0,
    ESP32_GPIO_OUTPUT,
    ESP32_GPIO_INPUT_PULLUP,
    ESP32_GPIO_INPUT_PULLDOWN,
    ESP32_GPIO_ANALOG
} esp32_gpio_mode_t;

// Estados dos pinos
typedef enum {
    ESP32_GPIO_LOW = 0,
    ESP32_GPIO_HIGH = 1
} esp32_gpio_state_t;

// Configuração WiFi
typedef struct {
    char ssid[ESP32_WIFI_MAX_SSID];
    char password[64];
    bool enabled;
    int8_t rssi;
    uint8_t channel;
    bool connected;
    uint32_t ip_address;
    uint32_t gateway;
    uint32_t subnet;
} esp32_wifi_config_t;

// Configuração BLE
typedef struct {
    char device_name[ESP32_BLE_MAX_NAME];
    bool enabled;
    bool advertising;
    bool connected;
    uint8_t client_count;
    uint16_t service_uuid;
    uint16_t characteristic_uuid;
} esp32_ble_config_t;

// Configuração de pino GPIO
typedef struct {
    uint8_t pin;
    esp32_gpio_mode_t mode;
    esp32_gpio_state_t state;
    uint16_t analog_value;
    bool interrupt_enabled;
    bool pullup_enabled;
    bool pulldown_enabled;
} esp32_gpio_config_t;

// Configuração ADC
typedef struct {
    uint8_t channel;
    uint16_t resolution;
    uint8_t attenuation;
    uint16_t raw_value;
    float voltage;
    bool enabled;
} esp32_adc_config_t;

// Configuração DAC
typedef struct {
    uint8_t channel;
    uint8_t value;
    float voltage;
    bool enabled;
} esp32_dac_config_t;

// Configuração de timer
typedef struct {
    uint8_t timer_id;
    uint32_t period_us;
    bool enabled;
    bool auto_reload;
    uint64_t last_trigger;
    uint32_t trigger_count;
} esp32_timer_config_t;

// Simulador principal do ESP32
typedef struct {
    // Estado geral
    bool initialized;
    uint64_t uptime_us;
    float cpu_frequency_mhz;
    uint32_t free_heap;
    uint32_t total_heap;
    float temperature;
    
    // Configurações de comunicação
    esp32_wifi_config_t wifi;
    esp32_ble_config_t ble;
    
    // GPIOs
    esp32_gpio_config_t gpios[ESP32_MAX_GPIOS];
    
    // ADCs
    esp32_adc_config_t adcs[ESP32_MAX_ADC_CHANNELS];
    
    // DACs (ESP32 tem 2 canais DAC)
    esp32_dac_config_t dacs[2];
    
    // Timers
    esp32_timer_config_t timers[4];
    
    // Watchdog
    bool watchdog_enabled;
    uint32_t watchdog_timeout_ms;
    uint64_t last_watchdog_feed;
    
    // Sleep mode
    bool sleep_enabled;
    uint32_t sleep_duration_us;
    
} esp32_simulator_t;

// Funções de inicialização
bool esp32_init(esp32_simulator_t* esp32);
void esp32_reset(esp32_simulator_t* esp32);
void esp32_deep_sleep(esp32_simulator_t* esp32, uint32_t duration_us);
void esp32_light_sleep(esp32_simulator_t* esp32, uint32_t duration_us);

// Funções GPIO
bool esp32_gpio_set_mode(esp32_simulator_t* esp32, uint8_t pin, esp32_gpio_mode_t mode);
bool esp32_gpio_write(esp32_simulator_t* esp32, uint8_t pin, esp32_gpio_state_t state);
esp32_gpio_state_t esp32_gpio_read(esp32_simulator_t* esp32, uint8_t pin);
bool esp32_gpio_enable_pullup(esp32_simulator_t* esp32, uint8_t pin, bool enable);
bool esp32_gpio_enable_pulldown(esp32_simulator_t* esp32, uint8_t pin, bool enable);

// Funções ADC
bool esp32_adc_init(esp32_simulator_t* esp32, uint8_t channel);
uint16_t esp32_adc_read_raw(esp32_simulator_t* esp32, uint8_t channel);
float esp32_adc_read_voltage(esp32_simulator_t* esp32, uint8_t channel);
void esp32_adc_simulate_input(esp32_simulator_t* esp32, uint8_t channel, float voltage);

// Funções DAC
bool esp32_dac_init(esp32_simulator_t* esp32, uint8_t channel);
bool esp32_dac_write(esp32_simulator_t* esp32, uint8_t channel, uint8_t value);
bool esp32_dac_write_voltage(esp32_simulator_t* esp32, uint8_t channel, float voltage);

// Funções WiFi
bool esp32_wifi_init(esp32_simulator_t* esp32, const char* ssid, const char* password);
bool esp32_wifi_connect(esp32_simulator_t* esp32);
bool esp32_wifi_disconnect(esp32_simulator_t* esp32);
bool esp32_wifi_is_connected(esp32_simulator_t* esp32);
int8_t esp32_wifi_get_rssi(esp32_simulator_t* esp32);
uint32_t esp32_wifi_get_ip(esp32_simulator_t* esp32);

// Funções BLE
bool esp32_ble_init(esp32_simulator_t* esp32, const char* device_name);
bool esp32_ble_start_advertising(esp32_simulator_t* esp32);
bool esp32_ble_stop_advertising(esp32_simulator_t* esp32);
bool esp32_ble_send_data(esp32_simulator_t* esp32, const uint8_t* data, size_t length);
bool esp32_ble_is_connected(esp32_simulator_t* esp32);

// Funções de timer
bool esp32_timer_init(esp32_simulator_t* esp32, uint8_t timer_id, uint32_t period_us);
bool esp32_timer_start(esp32_simulator_t* esp32, uint8_t timer_id);
bool esp32_timer_stop(esp32_simulator_t* esp32, uint8_t timer_id);
bool esp32_timer_check_trigger(esp32_simulator_t* esp32, uint8_t timer_id);

// Funções de watchdog
bool esp32_watchdog_init(esp32_simulator_t* esp32, uint32_t timeout_ms);
void esp32_watchdog_feed(esp32_simulator_t* esp32);
bool esp32_watchdog_check_timeout(esp32_simulator_t* esp32);

// Funções de sistema
uint64_t esp32_get_uptime_us(esp32_simulator_t* esp32);
uint32_t esp32_get_free_heap(esp32_simulator_t* esp32);
float esp32_get_temperature(esp32_simulator_t* esp32);
void esp32_simulate_temperature(esp32_simulator_t* esp32, float temperature);

// Funções de simulação
void esp32_simulate_heap_usage(esp32_simulator_t* esp32, uint32_t used_bytes);
void esp32_simulate_wifi_signal(esp32_simulator_t* esp32, int8_t rssi);
void esp32_simulate_noise(esp32_simulator_t* esp32, float noise_level);

// Funções de debug e teste
bool esp32_self_test(esp32_simulator_t* esp32);
void esp32_print_status(esp32_simulator_t* esp32);

#ifdef __cplusplus
}
#endif

#endif // ESP32_SIMULATOR_H
