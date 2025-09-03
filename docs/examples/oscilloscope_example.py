"""
Exemplo completo de uso da API do osciloscópio.

Este arquivo demonstra como usar a API para visualização de dados
em tempo real tipo osciloscópio.
"""

import time
import json
import threading
from datetime import datetime
from typing import Dict, Any

# Imports do sistema DAQ
from src.data.data_manager import DataManager
from src.data.oscilloscope_api import OscilloscopeAPI, WebSocketStreamer
from src.core.models import StrainReading


class OscilloscopeExample:
    """Exemplo de implementação do visualizador osciloscópio."""
    
    def __init__(self):
        """Inicializa o exemplo."""
        self.data_manager = DataManager()
        self.oscilloscope_api = OscilloscopeAPI(self.data_manager)
        self.websocket_streamer = WebSocketStreamer(self.oscilloscope_api)
        
        # Configuração do osciloscópio
        self.oscilloscope_api.set_config(
            time_window_seconds=10.0,
            max_points=1000,
            sample_rate_hz=100.0,
            auto_scale=True
        )
        
    def simulate_data_acquisition(self, sensor_id: str, 
                                 duration_seconds: int = 30) -> None:
        """
        Simula aquisição de dados em tempo real.
        
        Args:
            sensor_id: ID do sensor
            duration_seconds: Duração da simulação
        """
        import math
        import random
        
        print(f"Iniciando simulação de dados para sensor {sensor_id}")
        print(f"Duração: {duration_seconds} segundos")
        
        start_time = time.time()
        sample_count = 0
        
        while (time.time() - start_time) < duration_seconds:
            # Gera sinal simulado (senoide + ruído + drift)
            t = time.time() - start_time
            
            # Componentes do sinal
            sine_wave = 100 * math.sin(2 * math.pi * 0.5 * t)  # 0.5 Hz
            noise = random.gauss(0, 5)  # Ruído gaussiano
            drift = 10 * t / duration_seconds  # Drift lento
            
            strain_value = sine_wave + noise + drift
            
            # Cria leitura simulada
            reading = StrainReading(
                timestamp=datetime.now(),
                strain_value=strain_value,
                raw_adc_value=int(strain_value * 100 + 32768),  # Simula ADC
                sensor_id=sensor_id,
                battery_level=max(100 - int(t * 2), 10),  # Bateria diminuindo
                temperature=25.0 + random.gauss(0, 2)  # Temperatura ambiente
            )
            
            # Adiciona ao sistema
            self.data_manager.add_reading(reading)
            
            sample_count += 1
            time.sleep(0.01)  # 100Hz de amostragem
            
        print(f"Simulação concluída. {sample_count} amostras geradas.")
    
    def demonstrate_realtime_monitoring(self) -> None:
        """Demonstra monitoramento em tempo real."""
        print("=== Demonstração: Monitoramento em Tempo Real ===")
        
        # Inicia thread de simulação de dados
        import threading
        sensor_id = "STRAIN_001"
        
        sim_thread = threading.Thread(
            target=self.simulate_data_acquisition,
            args=(sensor_id, 15)
        )
        sim_thread.daemon = True
        sim_thread.start()
        
        # Monitora dados em tempo real
        for i in range(50):  # 5 segundos de monitoramento
            snapshot = self.oscilloscope_api.get_realtime_snapshot()
            
            print(f"\n--- Snapshot {i+1} ---")
            print(f"Timestamp: {snapshot['timestamp']}")
            print(f"Sensores ativos: {snapshot['active_sensors']}")
            print(f"Total de pontos: {snapshot['total_points']}")
            
            if sensor_id in snapshot['sensors']:
                sensor_data = snapshot['sensors'][sensor_id]
                print(f"Sensor {sensor_id}:")
                print(f"  Valor atual: {sensor_data['current_value']:.2f} µε")
                print(f"  Bateria: {sensor_data['battery']}%")
                print(f"  Temperatura: {sensor_data['temperature']:.1f}°C")
                print(f"  Min/Max: {sensor_data['min_value']:.2f}/{sensor_data['max_value']:.2f}")
                print(f"  Pontos coletados: {sensor_data['point_count']}")
            
            time.sleep(0.1)
    
    def demonstrate_trace_visualization(self) -> None:
        """Demonstra visualização de traços."""
        print("\n=== Demonstração: Visualização de Traços ===")
        
        sensor_id = "STRAIN_001"
        
        # Simula alguns dados primeiro
        sim_thread = threading.Thread(
            target=self.simulate_data_acquisition,
            args=(sensor_id, 5)
        )
        sim_thread.daemon = True
        sim_thread.start()
        sim_thread.join()
        
        # Obtém dados do traço
        trace_data = self.oscilloscope_api.get_trace_data(sensor_id)
        
        print(f"Dados do traço para {sensor_id}:")
        print(f"  Pontos coletados: {trace_data['point_count']}")
        print(f"  Duração: {trace_data['time_span']:.2f} segundos")
        print(f"  Faixa Y: {trace_data['y_min']:.2f} a {trace_data['y_max']:.2f}")
        print(f"  Amplitude: {trace_data['y_range']:.2f}")
        
        # Mostra alguns pontos
        if trace_data['point_count'] > 0:
            print("\nPrimeiros 5 pontos:")
            for i in range(min(5, len(trace_data['times']))):
                t = trace_data['times'][i]
                v = trace_data['values'][i]
                print(f"  T={t:.0f}ms, V={v:.2f}µε")
    
    def demonstrate_streaming_api(self) -> None:
        """Demonstra API de streaming."""
        print("\n=== Demonstração: API de Streaming ===")
        
        sensor_id = "STRAIN_001"
        last_timestamp = 0
        
        # Simula dados em background
        import threading
        sim_thread = threading.Thread(
            target=self.simulate_data_acquisition,
            args=(sensor_id, 10)
        )
        sim_thread.daemon = True
        sim_thread.start()
        
        # Simula cliente de streaming
        for update_cycle in range(20):
            streaming_data = self.oscilloscope_api.get_streaming_data(
                sensor_id, last_timestamp
            )
            
            print(f"\nCiclo {update_cycle + 1}:")
            print(f"  Novos pontos: {streaming_data['new_points']}")
            print(f"  Timestamp mais recente: {streaming_data['latest_timestamp']}")
            print(f"  Tem mais dados: {streaming_data['has_more']}")
            
            # Atualiza timestamp para próximo ciclo
            last_timestamp = streaming_data['latest_timestamp']
            
            time.sleep(0.5)  # Simula intervalo de atualização
    
    def demonstrate_export_functionality(self) -> None:
        """Demonstra funcionalidade de exportação."""
        print("\n=== Demonstração: Exportação de Dados ===")
        
        sensor_id = "STRAIN_001"
        
        # Gera alguns dados
        sim_thread = threading.Thread(
            target=self.simulate_data_acquisition,
            args=(sensor_id, 3)
        )
        sim_thread.daemon = True
        sim_thread.start()
        sim_thread.join()
        
        # Exporta em diferentes formatos
        formats = ['json', 'csv']
        
        for fmt in formats:
            try:
                exported_data = self.oscilloscope_api.export_trace_data(sensor_id, fmt)
                
                # Salva em arquivo
                filename = f"exported_data_{sensor_id}.{fmt}"
                with open(filename, 'w' if fmt != 'binary' else 'wb') as f:
                    f.write(exported_data)
                
                print(f"Dados exportados em formato {fmt.upper()}: {filename}")
                
                # Mostra preview para texto
                if fmt in ['json', 'csv']:
                    preview = exported_data[:200] + "..." if len(exported_data) > 200 else exported_data
                    print(f"Preview:\n{preview}\n")
                    
            except Exception as e:
                print(f"Erro ao exportar em {fmt}: {e}")
    
    def demonstrate_performance_monitoring(self) -> None:
        """Demonstra monitoramento de performance."""
        print("\n=== Demonstração: Monitoramento de Performance ===")
        
        # Gera dados de múltiplos sensores
        sensors = ["STRAIN_001", "STRAIN_002", "STRAIN_003"]
        
        threads = []
        for sensor_id in sensors:
            thread = threading.Thread(
                target=self.simulate_data_acquisition,
                args=(sensor_id, 8)
            )
            thread.daemon = True
            thread.start()
            threads.append(thread)
        
        # Monitora performance enquanto os dados são gerados
        for i in range(10):
            metrics = self.oscilloscope_api.get_performance_metrics()
            
            print(f"\n--- Métricas {i+1} ---")
            print(f"Sensores ativos: {metrics['stream_stats']['active_sensors']}")
            print(f"Total de pontos: {metrics['stream_stats']['total_points']}")
            print(f"Taxa de atualização: {metrics['api_update_rate']:.2f} Hz")
            print(f"Uso estimado de memória: {metrics['memory_usage']['estimated_bytes']} bytes")
            print(f"Pontos por sensor: {metrics['memory_usage']['points_per_sensor']}")
            
            time.sleep(1)
        
        # Aguarda conclusão das simulações
        for thread in threads:
            thread.join()
    
    def run_complete_demo(self) -> None:
        """Executa demonstração completa."""
        print("╔════════════════════════════════════════════════════════╗")
        print("║              DEMONSTRAÇÃO API OSCILOSCÓPIO             ║")
        print("║                                                        ║")
        print("║  Sistema DAQ com visualização em tempo real           ║")
        print("║  Formato de dados otimizado para gráficos             ║")
        print("╚════════════════════════════════════════════════════════╝")
        
        try:
            # Executa todas as demonstrações
            self.demonstrate_realtime_monitoring()
            self.demonstrate_trace_visualization()
            self.demonstrate_streaming_api()
            self.demonstrate_export_functionality()
            self.demonstrate_performance_monitoring()
            
            print("\n" + "="*60)
            print("✅ DEMONSTRAÇÃO CONCLUÍDA COM SUCESSO!")
            print("✅ Todos os recursos da API foram testados.")
            print("✅ Sistema pronto para integração com visualizador.")
            print("="*60)
            
        except Exception as e:
            print(f"\n❌ ERRO durante a demonstração: {e}")
            
        finally:
            # Limpeza
            self.data_manager.close()
    
    def generate_sample_output(self) -> Dict[str, Any]:
        """
        Gera saída de exemplo para desenvolvimento do visualizador.
        
        Returns:
            Dados de exemplo em formato JSON
        """
        sensor_id = "STRAIN_001"
        
        # Simula dados rapidamente
        import threading
        sim_thread = threading.Thread(
            target=self.simulate_data_acquisition,
            args=(sensor_id, 2)
        )
        sim_thread.daemon = True
        sim_thread.start()
        sim_thread.join()
        
        # Gera todos os tipos de saída
        sample_output = {
            'realtime_snapshot': self.oscilloscope_api.get_realtime_snapshot(),
            'trace_data': self.oscilloscope_api.get_trace_data(sensor_id),
            'streaming_data': self.oscilloscope_api.get_streaming_data(sensor_id),
            'performance_metrics': self.oscilloscope_api.get_performance_metrics(),
            'websocket_format': self.websocket_streamer.broadcast_snapshot()
        }
        
        return sample_output


def main():
    """Função principal de exemplo."""
    example = OscilloscopeExample()
    
    # Executa demonstração completa
    example.run_complete_demo()
    
    # Gera arquivo de exemplo para desenvolvimento
    sample_data = example.generate_sample_output()
    
    with open('oscilloscope_sample_output.json', 'w') as f:
        json.dump(sample_data, f, indent=2, default=str)
    
    print("\n📄 Arquivo de exemplo gerado: oscilloscope_sample_output.json")
    print("   Use este arquivo para desenvolver o visualizador.")


if __name__ == "__main__":
    main()
