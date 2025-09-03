#!/usr/bin/env python3
"""
Script de demonstração prática da API do osciloscópio.

Este script mostra como integrar e usar a API de osciloscópio
de forma prática em diferentes cenários.
"""

import sys
import time
import json
import asyncio
from pathlib import Path

# Adiciona o diretório src ao path para imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from data import DataManager, OscilloscopeAPI
from core.models import StrainReading
from datetime import datetime


class PracticalOscilloscopeDemo:
    """Demonstração prática da API do osciloscópio."""
    
    def __init__(self):
        """Inicializa a demonstração."""
        print("🔧 Inicializando sistema DAQ...")
        
        self.data_manager = DataManager()
        self.oscilloscope_api = OscilloscopeAPI(self.data_manager)
        
        # Configuração para demonstração
        self.oscilloscope_api.set_config(
            time_window_seconds=5.0,
            max_points=500,
            sample_rate_hz=100.0,
            auto_scale=True
        )
        
        print("✅ Sistema inicializado com sucesso!")
        print(f"   Janela de tempo: {self.oscilloscope_api.config.time_window_seconds}s")
        print(f"   Máximo de pontos: {self.oscilloscope_api.config.max_points}")
        print(f"   Taxa de amostragem: {self.oscilloscope_api.config.sample_rate_hz}Hz\n")
    
    def generate_test_data(self, sensor_id: str, duration: float = 3.0):
        """
        Gera dados de teste simulando um sensor real.
        
        Args:
            sensor_id: ID do sensor
            duration: Duração em segundos
        """
        import math
        import random
        
        print(f"📊 Gerando dados para sensor {sensor_id} por {duration}s...")
        
        start_time = time.time()
        points_generated = 0
        
        while (time.time() - start_time) < duration:
            # Simula sinal real: senoide + ruído + componente DC
            t = time.time() - start_time
            
            # Sinal principal (simulando deformação estrutural)
            base_signal = 50 * math.sin(2 * math.pi * 1.0 * t)  # 1Hz
            noise = random.gauss(0, 2)  # Ruído
            dc_offset = 100  # Offset DC
            
            strain_value = base_signal + noise + dc_offset
            
            # Cria leitura
            reading = StrainReading(
                timestamp=datetime.now(),
                strain_value=strain_value,
                raw_adc_value=int(strain_value * 100 + 32768),
                sensor_id=sensor_id,
                battery_level=random.randint(80, 100),
                temperature=25.0 + random.gauss(0, 1)
            )
            
            # Adiciona ao sistema
            self.data_manager.add_reading(reading)
            points_generated += 1
            
            time.sleep(0.01)  # 100Hz
        
        print(f"✅ {points_generated} pontos gerados para {sensor_id}\n")
    
    def demonstrate_realtime_access(self):
        """Demonstra acesso aos dados em tempo real."""
        print("🔄 DEMONSTRAÇÃO: Acesso aos Dados em Tempo Real")
        print("=" * 50)
        
        sensor_id = "DEMO_SENSOR_001"
        
        # Gera dados em background
        import threading
        data_thread = threading.Thread(
            target=self.generate_test_data,
            args=(sensor_id, 5.0)
        )
        data_thread.daemon = True
        data_thread.start()
        
        # Monitora em tempo real
        for i in range(10):
            # Busca snapshot atual
            snapshot = self.oscilloscope_api.get_realtime_snapshot()
            
            print(f"📸 Snapshot {i+1}:")
            print(f"   Timestamp: {snapshot['timestamp']}")
            print(f"   Sensores ativos: {snapshot['active_sensors']}")
            
            if sensor_id in snapshot['sensors']:
                sensor_data = snapshot['sensors'][sensor_id]
                print(f"   {sensor_id}:")
                print(f"     Valor atual: {sensor_data['current_value']:.2f} µε")
                print(f"     Bateria: {sensor_data['battery']}%")
                print(f"     Temperatura: {sensor_data['temperature']:.1f}°C")
                print(f"     Faixa: {sensor_data['min_value']:.1f} a {sensor_data['max_value']:.1f}")
            
            print()
            time.sleep(0.5)
        
        data_thread.join()
    
    def demonstrate_trace_extraction(self):
        """Demonstra extração de dados de traço."""
        print("📈 DEMONSTRAÇÃO: Extração de Dados de Traço")
        print("=" * 50)
        
        sensor_id = "DEMO_SENSOR_002"
        
        # Gera dados primeiro
        self.generate_test_data(sensor_id, 2.0)
        
        # Extrai traço completo
        trace_data = self.oscilloscope_api.get_trace_data(sensor_id)
        
        print(f"📊 Dados de traço para {sensor_id}:")
        print(f"   Total de pontos: {trace_data['point_count']}")
        print(f"   Duração: {trace_data['time_span']:.2f}s")
        print(f"   Valor mínimo: {trace_data['y_min']:.2f} µε")
        print(f"   Valor máximo: {trace_data['y_max']:.2f} µε")
        print(f"   Amplitude: {trace_data['y_range']:.2f} µε")
        
        # Mostra primeiros e últimos pontos
        if trace_data['point_count'] > 0:
            times = trace_data['times']
            values = trace_data['values']
            
            print(f"\n   Primeiros 3 pontos:")
            for i in range(min(3, len(times))):
                print(f"     T={times[i]:.0f}ms, V={values[i]:.2f}µε")
            
            print(f"   Últimos 3 pontos:")
            for i in range(max(0, len(times)-3), len(times)):
                print(f"     T={times[i]:.0f}ms, V={values[i]:.2f}µε")
        
        print()
    
    def demonstrate_streaming_updates(self):
        """Demonstra atualizações incrementais."""
        print("🌊 DEMONSTRAÇÃO: Streaming Incremental")
        print("=" * 50)
        
        sensor_id = "DEMO_SENSOR_003"
        
        # Gera dados em background continuamente
        import threading
        
        def continuous_data_generation():
            for _ in range(50):  # 5 segundos a 10Hz
                self.generate_test_data(sensor_id, 0.1)
                time.sleep(0.1)
        
        data_thread = threading.Thread(target=continuous_data_generation)
        data_thread.daemon = True
        data_thread.start()
        
        # Simula cliente de streaming
        last_timestamp = 0
        
        for update in range(15):
            # Busca dados novos
            streaming_data = self.oscilloscope_api.get_streaming_data(
                sensor_id, last_timestamp
            )
            
            print(f"🔄 Update {update+1}:")
            print(f"   Novos pontos: {streaming_data['new_points']}")
            print(f"   Timestamp mais recente: {streaming_data['latest_timestamp']}")
            print(f"   Tem mais dados: {streaming_data['has_more']}")
            
            if streaming_data['new_points'] > 0:
                # Mostra último ponto recebido
                last_point = streaming_data['data'][-1]
                print(f"   Último valor: {last_point['v']:.2f} µε")
            
            # Atualiza timestamp para próxima iteração
            last_timestamp = streaming_data['latest_timestamp']
            
            time.sleep(0.3)
        
        data_thread.join()
        print()
    
    def demonstrate_export_capabilities(self):
        """Demonstra capacidades de exportação."""
        print("💾 DEMONSTRAÇÃO: Exportação de Dados")
        print("=" * 50)
        
        sensor_id = "DEMO_SENSOR_004"
        
        # Gera dados para exportação
        self.generate_test_data(sensor_id, 1.5)
        
        # Testa diferentes formatos de exportação
        formats = ['json', 'csv']
        
        for fmt in formats:
            try:
                exported_data = self.oscilloscope_api.export_trace_data(sensor_id, fmt)
                
                # Salva arquivo
                filename = f"demo_export_{sensor_id}.{fmt}"
                with open(filename, 'w') as f:
                    f.write(exported_data)
                
                print(f"✅ Exportado em {fmt.upper()}: {filename}")
                
                # Preview dos dados
                if len(exported_data) > 200:
                    preview = exported_data[:200] + "..."
                else:
                    preview = exported_data
                
                print(f"   Preview: {preview[:100]}...")
                
            except Exception as e:
                print(f"❌ Erro ao exportar em {fmt}: {e}")
        
        print()
    
    def demonstrate_performance_monitoring(self):
        """Demonstra monitoramento de performance."""
        print("⚡ DEMONSTRAÇÃO: Monitoramento de Performance")
        print("=" * 50)
        
        # Gera carga de trabalho com múltiplos sensores
        sensors = ["PERF_01", "PERF_02", "PERF_03"]
        
        import threading
        threads = []
        
        for sensor_id in sensors:
            thread = threading.Thread(
                target=self.generate_test_data,
                args=(sensor_id, 3.0)
            )
            thread.daemon = True
            thread.start()
            threads.append(thread)
        
        # Monitora performance
        for i in range(6):
            metrics = self.oscilloscope_api.get_performance_metrics()
            
            print(f"📊 Métricas {i+1}:")
            print(f"   Sensores ativos: {metrics['stream_stats']['active_sensors']}")
            print(f"   Total de pontos: {metrics['stream_stats']['total_points']}")
            print(f"   Taxa de atualização API: {metrics['api_update_rate']:.2f} Hz")
            
            memory = metrics['memory_usage']
            print(f"   Uso de memória:")
            print(f"     Pontos totais: {memory['total_points']}")
            print(f"     Bytes estimados: {memory['estimated_bytes']:,}")
            print(f"     Pontos por sensor: {memory['points_per_sensor']}")
            
            print()
            time.sleep(0.5)
        
        # Aguarda conclusão
        for thread in threads:
            thread.join()
    
    def create_integration_example(self):
        """Cria exemplo de integração para desenvolvedores."""
        print("🔧 CRIANDO: Exemplo de Integração")
        print("=" * 50)
        
        # Gera dados de exemplo
        sensor_id = "INTEGRATION_EXAMPLE"
        self.generate_test_data(sensor_id, 2.0)
        
        # Cria estrutura de exemplo completa
        integration_example = {
            'metadata': {
                'description': 'Exemplo de integração com API de Osciloscópio',
                'timestamp': datetime.now().isoformat(),
                'sensor_id': sensor_id,
                'api_version': '1.0'
            },
            'realtime_snapshot': self.oscilloscope_api.get_realtime_snapshot(),
            'trace_data': self.oscilloscope_api.get_trace_data(sensor_id),
            'streaming_sample': self.oscilloscope_api.get_streaming_data(sensor_id),
            'performance_metrics': self.oscilloscope_api.get_performance_metrics(),
            'usage_examples': {
                'javascript_fetch': '''
fetch('/api/oscilloscope/trace/SENSOR_ID')
  .then(response => response.json())
  .then(data => {
    // data.times e data.values prontos para plotagem
    chart.update(data.times, data.values);
  });
''',
                'python_requests': '''
import requests
response = requests.get('/api/oscilloscope/trace/SENSOR_ID')
data = response.json()
# Arrays prontos: data['times'], data['values']
''',
                'websocket_client': '''
const ws = new WebSocket('ws://localhost:8080/oscilloscope');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'realtime_snapshot') {
    updateDisplay(data.data);
  }
};
'''
            }
        }
        
        # Salva exemplo
        filename = 'oscilloscope_integration_example.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(integration_example, f, indent=2, default=str)
        
        print(f"✅ Exemplo criado: {filename}")
        print(f"   Use este arquivo para desenvolvimento do visualizador")
        print(f"   Contém todos os formatos de dados da API")
        print()
    
    def run_complete_demonstration(self):
        """Executa demonstração completa."""
        print("╔" + "="*58 + "╗")
        print("║" + " "*58 + "║")
        print("║" + "  DEMONSTRAÇÃO PRÁTICA - API OSCILOSCÓPIO DAQ".center(58) + "║")
        print("║" + " "*58 + "║")
        print("║" + "  Dados otimizados para visualização em tempo real".center(58) + "║")
        print("║" + " "*58 + "║")
        print("╚" + "="*58 + "╝")
        print()
        
        try:
            # Executa todas as demonstrações
            self.demonstrate_realtime_access()
            self.demonstrate_trace_extraction()
            self.demonstrate_streaming_updates()
            self.demonstrate_export_capabilities()
            self.demonstrate_performance_monitoring()
            self.create_integration_example()
            
            print("🎉 DEMONSTRAÇÃO CONCLUÍDA COM SUCESSO! 🎉")
            print()
            print("📋 RESUMO:")
            print("   ✅ Acesso em tempo real - Funcionando")
            print("   ✅ Extração de traços - Funcionando")
            print("   ✅ Streaming incremental - Funcionando")
            print("   ✅ Exportação de dados - Funcionando")
            print("   ✅ Monitoramento de performance - Funcionando")
            print("   ✅ Exemplo de integração - Criado")
            print()
            print("🚀 PRÓXIMOS PASSOS:")
            print("   1. Use oscilloscope_integration_example.json para desenvolvimento")
            print("   2. Implemente visualizador usando os formatos demonstrados")
            print("   3. Teste com dados reais do seu sistema DAQ")
            print("   4. Otimize conforme necessário")
            print()
            print("📖 DOCUMENTAÇÃO:")
            print("   - Formatos de dados: docs/DATA_OUTPUT_FORMAT.md")
            print("   - Exemplos: docs/examples/oscilloscope_example.py")
            print("   - API: src/data/oscilloscope_api.py")
            
        except Exception as e:
            print(f"❌ ERRO durante demonstração: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            # Limpeza
            print("\n🧹 Limpando recursos...")
            self.data_manager.close()
            print("✅ Limpeza concluída")


def main():
    """Função principal."""
    demo = PracticalOscilloscopeDemo()
    demo.run_complete_demonstration()


if __name__ == "__main__":
    main()
