"""
Exemplo de uso completo do sistema DAQ.
Demonstra integração entre simulador, comunicação e gerenciamento de dados.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Adiciona diretório pai ao path
sys.path.append(str(Path(__file__).parent.parent))

from simulator import DAQSystemSimulator, SimulatorConfig
from src.data import DataManager
from src.communication import BLESimulator, MessageProtocol, MessageType
from src.core.models import StrainReading, SensorConfiguration


class DAQSystemExample:
    """Exemplo completo de uso do sistema DAQ."""
    
    def __init__(self):
        """Inicializa o exemplo."""
        self.simulator = None
        self.data_manager = DataManager()
        self.ble_comm = BLESimulator()
        self.received_readings = []
        
    async def run_complete_example(self):
        """Executa exemplo completo do sistema."""
        print("=== Exemplo Sistema DAQ Completo ===\n")
        
        # 1. Configuração inicial
        await self._setup_system()
        
        # 2. Demonstração de cenários
        await self._demonstrate_scenarios()
        
        # 3. Teste de comunicação
        await self._test_communication()
        
        # 4. Coleta e análise de dados
        await self._collect_and_analyze_data()
        
        # 5. Exportação de dados
        await self._export_data()
        
        # 6. Limpeza
        await self._cleanup()
        
        print("\n=== Exemplo concluído com sucesso! ===")
    
    async def _setup_system(self):
        """Configura o sistema inicial."""
        print("1. Configurando sistema...")
        
        # Configuração do simulador
        config = SimulatorConfig(
            device_name="DAQ_Example",
            simulation_speed=5.0,  # 5x mais rápido para exemplo
            enable_ble=True,
            realistic_loads=True
        )
        
        # Cria simulador
        self.simulator = DAQSystemSimulator(config)
        
        # Registra callbacks
        self.simulator.add_data_callback(self._on_data_received)
        self.simulator.add_status_callback(self._on_status_update)
        
        # Configura parâmetros do sensor
        sensor_config = SensorConfiguration(
            sensor_id="EXAMPLE_001",
            sampling_rate_ms=50,  # Mais rápido para exemplo
            transmission_interval_s=1,
            calibration_factor=1.2,
            offset=0.0,
            deep_sleep_enabled=False  # Desabilitado para exemplo
        )
        
        await self.simulator.configure_sensor(sensor_config)
        
        # Inicia simulador
        await self.simulator.start()
        
        print(f"   ✓ Simulador iniciado: {config.device_name}")
        print(f"   ✓ Configuração aplicada: {sensor_config.sensor_id}")
        print()
    
    async def _demonstrate_scenarios(self):
        """Demonstra diferentes cenários de carga."""
        print("2. Demonstrando cenários de carga...")
        
        scenarios = [
            ("idle", 3),
            ("transport", 5),
            ("field_work_light", 4),
            ("field_work_heavy", 3),
            ("harvest", 4)
        ]
        
        for scenario_name, duration in scenarios:
            print(f"   Cenário: {scenario_name} ({duration}s)")
            
            # Altera cenário
            self.simulator.set_load_scenario(scenario_name)
            
            # Coleta dados por alguns segundos
            start_time = datetime.now()
            scenario_readings = []
            
            while (datetime.now() - start_time).seconds < duration:
                await asyncio.sleep(0.1)
                
                # Coleta dados recentes
                recent = self.data_manager.get_recent_readings(
                    sensor_id="EXAMPLE_001",
                    minutes=1,
                    max_count=10
                )
                scenario_readings.extend(recent)
            
            # Mostra estatísticas do cenário
            if scenario_readings:
                strains = [r.strain_value for r in scenario_readings[-20:]]  # Últimas 20
                avg_strain = sum(strains) / len(strains)
                min_strain = min(strains)
                max_strain = max(strains)
                
                print(f"      Strain médio: {avg_strain:+7.2f} µε")
                print(f"      Faixa: {min_strain:+7.2f} a {max_strain:+7.2f} µε")
        
        print()
    
    async def _test_communication(self):
        """Testa comunicação BLE."""
        print("3. Testando comunicação BLE...")
        
        # Registra callbacks de comunicação
        self.ble_comm.add_data_callback(self._on_ble_data)
        self.ble_comm.add_connection_callback(self._on_ble_connection)
        
        # Inicia descoberta
        print("   Iniciando descoberta de dispositivos...")
        await self.ble_comm.start_scan(timeout=3.0)
        
        devices = self.ble_comm.discovered_devices
        print(f"   ✓ Dispositivos encontrados: {len(devices)}")
        
        if devices:
            # Conecta ao primeiro dispositivo DAQ
            daq_devices = [
                addr for addr, dev in devices.items() 
                if "DAQ" in dev.name
            ]
            
            if daq_devices:
                target_address = daq_devices[0]
                device = devices[target_address]
                
                print(f"   Conectando a: {device.name} ({target_address})")
                success = await self.ble_comm.connect(target_address)
                
                if success:
                    print("   ✓ Conexão estabelecida")
                    
                    # Testa comandos
                    await self._test_ble_commands(target_address)
                    
                    # Desconecta
                    await self.ble_comm.disconnect(target_address)
                    print("   ✓ Desconectado")
                else:
                    print("   ✗ Falha na conexão")
        
        await self.ble_comm.stop_scan()
        print()
    
    async def _test_ble_commands(self, address: str):
        """Testa comandos via BLE."""
        print("   Testando comandos BLE...")
        
        # Comando PING
        ping_msg = MessageProtocol.create_message(MessageType.PING, {})
        success = await self.ble_comm.send_data(address, ping_msg)
        if success:
            print("      ✓ PING enviado")
        
        # Aguarda resposta
        await asyncio.sleep(0.5)
        
        # Solicitação de status
        status_msg = MessageProtocol.create_message(MessageType.STATUS_REQUEST, {})
        success = await self.ble_comm.send_data(address, status_msg)
        if success:
            print("      ✓ Status solicitado")
        
        # Aguarda resposta
        await asyncio.sleep(0.5)
    
    async def _collect_and_analyze_data(self):
        """Coleta e analisa dados."""
        print("4. Coletando e analisando dados...")
        
        # Aplica carga dinâmica por alguns segundos
        self.simulator.set_load_scenario("field_work_heavy")
        
        print("   Coletando dados por 10 segundos...")
        start_time = datetime.now()
        
        while (datetime.now() - start_time).seconds < 10:
            await asyncio.sleep(0.1)
        
        # Analisa dados coletados
        recent_data = self.data_manager.get_recent_readings(
            sensor_id="EXAMPLE_001",
            minutes=1
        )
        
        if recent_data:
            print(f"   ✓ Dados coletados: {len(recent_data)} leituras")
            
            # Estatísticas
            strains = [r.strain_value for r in recent_data]
            batteries = [r.battery_level for r in recent_data]
            temperatures = [r.temperature for r in recent_data]
            
            print(f"   Strain - Média: {sum(strains)/len(strains):+7.2f} µε")
            print(f"   Strain - Min/Max: {min(strains):+7.2f} / {max(strains):+7.2f} µε")
            print(f"   Bateria - Média: {sum(batteries)/len(batteries):.1f}%")
            print(f"   Temperatura - Média: {sum(temperatures)/len(temperatures):.1f}°C")
            
            # Detecta picos de deformação
            threshold = 200.0  # µε
            peaks = [r for r in recent_data if abs(r.strain_value) > threshold]
            
            if peaks:
                print(f"   ⚠ Picos detectados: {len(peaks)} acima de ±{threshold} µε")
                max_peak = max(peaks, key=lambda r: abs(r.strain_value))
                print(f"      Pico máximo: {max_peak.strain_value:+7.2f} µε em {max_peak.timestamp.strftime('%H:%M:%S')}")
        
        print()
    
    async def _export_data(self):
        """Exporta dados coletados."""
        print("5. Exportando dados...")
        
        # Define período de exportação
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=5)  # Últimos 5 minutos
        
        # Exporta em diferentes formatos
        formats = [
            ("csv", "example_data.csv"),
            ("json", "example_data.json")
        ]
        
        for format_type, filename in formats:
            try:
                output_path = Path(__file__).parent / filename
                
                self.data_manager.export_data(
                    format_type=format_type,
                    output_path=output_path,
                    sensor_id="EXAMPLE_001",
                    start_time=start_time,
                    end_time=end_time
                )
                
                print(f"   ✓ Exportado {format_type.upper()}: {filename}")
                
            except Exception as e:
                print(f"   ✗ Erro ao exportar {format_type}: {e}")
        
        # Mostra estatísticas gerais
        stats = self.data_manager.get_statistics(sensor_id="EXAMPLE_001")
        print(f"   Total de leituras no sistema: {stats['total_readings']}")
        
        print()
    
    async def _cleanup(self):
        """Limpa recursos."""
        print("6. Finalizando...")
        
        # Para simulador
        if self.simulator:
            await self.simulator.stop()
            print("   ✓ Simulador parado")
        
        # Fecha gerenciador de dados
        self.data_manager.close()
        print("   ✓ Dados persistidos")
        
        # Para comunicação BLE
        await self.ble_comm.stop_scan()
        print("   ✓ Comunicação BLE encerrada")
    
    # Callbacks
    async def _on_data_received(self, reading: StrainReading):
        """Callback para dados recebidos do simulador."""
        # Adiciona ao gerenciador de dados
        self.data_manager.add_reading(reading)
        self.received_readings.append(reading)
        
        # Log periódico (a cada 50 leituras)
        if len(self.received_readings) % 50 == 0:
            print(f"   [Data] {len(self.received_readings)} leituras recebidas")
    
    async def _on_status_update(self, sensor_info):
        """Callback para atualizações de status."""
        # Log ocasional de status
        pass
    
    async def _on_ble_data(self, address: str, data: bytes):
        """Callback para dados BLE."""
        try:
            message = MessageProtocol.parse_message(data)
            msg_type = message['type']
            
            if msg_type == MessageType.PONG:
                print("      ✓ PONG recebido")
            elif msg_type == MessageType.STATUS_RESPONSE:
                print("      ✓ Status recebido")
            elif msg_type == MessageType.DATA_SINGLE:
                print("      ✓ Dados de strain recebidos")
        
        except Exception as e:
            print(f"      ✗ Erro ao processar dados BLE: {e}")
    
    async def _on_ble_connection(self, device, connected: bool):
        """Callback para eventos de conexão BLE."""
        status = "conectado" if connected else "desconectado"
        print(f"   Dispositivo {device.name}: {status}")


# Exemplo de uso específico
async def example_custom_scenario():
    """Exemplo de cenário customizado."""
    print("\n=== Exemplo: Cenário Customizado ===")
    
    config = SimulatorConfig(
        device_name="Custom_Test",
        simulation_speed=2.0,
        realistic_loads=False  # Usar carga manual
    )
    
    simulator = DAQSystemSimulator(config)
    data_collected = []
    
    async def collect_data(reading):
        data_collected.append(reading)
    
    simulator.add_data_callback(collect_data)
    await simulator.start()
    
    # Sequência de cargas customizadas
    load_sequence = [0, 50, 100, 150, 200, 100, 0, -50, 0]
    
    print("Aplicando sequência de cargas:")
    for i, load in enumerate(load_sequence):
        print(f"  Passo {i+1}: {load:+4.0f} µε")
        simulator.apply_custom_load(load)
        await asyncio.sleep(2)  # 2 segundos por passo
    
    await simulator.stop()
    
    print(f"Dados coletados: {len(data_collected)} leituras")
    
    if data_collected:
        final_strains = [r.strain_value for r in data_collected[-10:]]
        print(f"Últimas leituras: {[f'{s:+6.1f}' for s in final_strains]} µε")


async def main():
    """Função principal dos exemplos."""
    try:
        # Exemplo completo
        example = DAQSystemExample()
        await example.run_complete_example()
        
        # Exemplo de cenário customizado
        await example_custom_scenario()
        
    except KeyboardInterrupt:
        print("\nExemplo interrompido pelo usuário")
    except Exception as e:
        print(f"Erro no exemplo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Executa os exemplos
    asyncio.run(main())
