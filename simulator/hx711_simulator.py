"""
Simulador do HX711 - Conversor ADC para strain gauges.
Simula o comportamento do conversor analógico-digital de 24 bits.
"""

import random
import time
import math
from typing import Optional
from dataclasses import dataclass


@dataclass
class HX711SimulatorConfig:
    """Configuração do simulador HX711."""
    resolution_bits: int = 24
    max_value: int = 2**23 - 1  # Valor máximo para 24 bits signed
    noise_level: float = 0.001  # Nível de ruído (% do valor)
    drift_rate: float = 0.0001  # Taxa de deriva por segundo
    temperature_coefficient: float = 0.02  # % por °C


class HX711Simulator:
    """
    Simulador do conversor ADC HX711.
    
    Simula a leitura de strain gauges com ruído realístico,
    deriva temporal e efeitos de temperatura.
    """
    
    def __init__(self, config: Optional[HX711SimulatorConfig] = None):
        """
        Inicializa o simulador HX711.
        
        Args:
            config: Configuração do simulador
        """
        self.config = config or HX711SimulatorConfig()
        self._baseline_value = 0  # Valor de referência (zero strain)
        self._current_strain = 0.0  # Deformação atual em microstrains
        self._temperature = 25.0  # Temperatura atual em °C
        self._drift_accumulator = 0.0  # Acumulador de deriva
        self._last_reading_time = time.time()
        self._calibration_factor = 1.0  # Fator de calibração
        self._is_ready = True
        
        # Simula variações típicas de uma aplicação real
        self._base_frequency = 0.1  # Hz - frequência base da simulação
        self._amplitude_factor = 100.0  # microstrains
        
    def set_calibration_factor(self, factor: float) -> None:
        """
        Define o fator de calibração do strain gauge.
        
        Args:
            factor: Fator de calibração (tipicamente entre 0.1 e 10.0)
        """
        if factor <= 0:
            raise ValueError("Fator de calibração deve ser positivo")
        self._calibration_factor = factor
    
    def set_temperature(self, temperature: float) -> None:
        """
        Define a temperatura ambiente para simulação de deriva térmica.
        
        Args:
            temperature: Temperatura em graus Celsius
        """
        self._temperature = temperature
    
    def apply_load(self, strain_microstrains: float) -> None:
        """
        Aplica uma deformação simulada ao strain gauge.
        
        Args:
            strain_microstrains: Deformação em microstrains (µε)
        """
        self._current_strain = strain_microstrains
    
    def simulate_dynamic_load(self, time_factor: float = 1.0) -> None:
        """
        Simula uma carga dinâmica variável (ex: vibração de máquina).
        
        Args:
            time_factor: Fator de velocidade da simulação
        """
        current_time = time.time() * time_factor
        
        # Simula diferentes componentes de frequência
        base_component = math.sin(2 * math.pi * self._base_frequency * current_time)
        high_freq_component = 0.3 * math.sin(2 * math.pi * self._base_frequency * 5 * current_time)
        random_component = 0.1 * (random.random() - 0.5)
        
        # Combina componentes para criar um sinal realístico
        total_strain = (
            self._amplitude_factor * 
            (base_component + high_freq_component + random_component)
        )
        
        self._current_strain = total_strain
    
    def read_adc_raw(self) -> int:
        """
        Lê o valor bruto do ADC (simulado).
        
        Returns:
            Valor ADC de 24 bits (-8388608 a 8388607)
        """
        if not self._is_ready:
            raise RuntimeError("ADC não está pronto para leitura")
        
        current_time = time.time()
        time_delta = current_time - self._last_reading_time
        self._last_reading_time = current_time
        
        # Calcula deriva temporal
        self._drift_accumulator += self.config.drift_rate * time_delta
        
        # Efeito da temperatura
        temp_effect = (self._temperature - 25.0) * self.config.temperature_coefficient / 100
        
        # Converte strain para valor ADC
        # Assumindo que strain gauge de 350Ω com bridge voltage de 5V
        # Sensibilidade típica: 2mV/V por 1000 microstrains
        strain_voltage = (self._current_strain / 1000.0) * 0.002  # 2mV/V
        
        # Converte tensão para valor ADC (assumindo ganho 128 do HX711)
        adc_value = int((strain_voltage * 128 / 5.0) * self.config.max_value)
        
        # Adiciona deriva e efeito de temperatura
        adc_value += int(self._drift_accumulator * self.config.max_value)
        adc_value += int(temp_effect * adc_value)
        
        # Adiciona ruído
        noise = random.gauss(0, self.config.noise_level * abs(adc_value))
        adc_value += int(noise)
        
        # Limita aos valores válidos do ADC
        adc_value = max(-self.config.max_value, min(self.config.max_value, adc_value))
        
        return adc_value
    
    def read_strain_microstrains(self) -> float:
        """
        Lê a deformação em microstrains (com calibração aplicada).
        
        Returns:
            Deformação em microstrains (µε)
        """
        raw_value = self.read_adc_raw()
        
        # Converte valor ADC para microstrains usando calibração
        # Fórmula inversa da conversão em read_adc_raw()
        voltage_ratio = (raw_value / self.config.max_value) * (5.0 / 128)
        strain_microstrains = (voltage_ratio / 0.002) * 1000.0
        
        return strain_microstrains * self._calibration_factor
    
    def is_ready(self) -> bool:
        """
        Verifica se o ADC está pronto para leitura.
        
        Returns:
            True se pronto, False caso contrário
        """
        return self._is_ready
    
    def power_down(self) -> None:
        """Simula modo de baixo consumo."""
        self._is_ready = False
    
    def power_up(self) -> None:
        """Sai do modo de baixo consumo."""
        self._is_ready = True
        # Simula tempo de estabilização
        time.sleep(0.001)  # 1ms
    
    def tare(self) -> None:
        """
        Executa tara (zera a leitura atual).
        Remove offset atual definindo como baseline.
        """
        current_raw = self.read_adc_raw()
        self._baseline_value = current_raw
        
    def get_status(self) -> dict:
        """
        Retorna status atual do simulador.
        
        Returns:
            Dicionário com informações de status
        """
        return {
            'ready': self._is_ready,
            'temperature': self._temperature,
            'calibration_factor': self._calibration_factor,
            'current_strain': self._current_strain,
            'drift_accumulator': self._drift_accumulator,
            'baseline_value': self._baseline_value
        }
    
    def reset(self) -> None:
        """Reseta o simulador para estado inicial."""
        self._baseline_value = 0
        self._current_strain = 0.0
        self._drift_accumulator = 0.0
        self._last_reading_time = time.time()
        self._calibration_factor = 1.0
        self._temperature = 25.0
        self._is_ready = True
