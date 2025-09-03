"""
Aplicação principal do sistema DAQ.
Interface unificada para controle do sistema completo.
"""

import asyncio
import argparse
import sys
import signal
from pathlib import Path
from typing import Optional

# Adiciona diretório pai ao path
sys.path.append(str(Path(__file__).parent.parent))

from simulator import DAQSystemSimulator, SimulatorConfig
from src.data import DataManager
from src.communication import BLESimulator
from src.core.models import StrainReading, SensorInfo, SensorConfiguration


class DAQSystemApplication:
    """
    Aplicação principal do sistema DAQ.
    
    Integra simulador, comunicação e gerenciamento de dados
    em uma interface unificada de controle.
    """
    
    def __init__(self):
        """Inicializa a aplicação."""
        self.simulator: Optional[DAQSystemSimulator] = None
        self.data_manager = DataManager()
        self.ble_comm = BLESimulator()
        self._running = False
        self._shutdown_event = asyncio.Event()
        
        # Estatísticas de execução
        self.stats = {
            'readings_received': 0,
            'readings_stored': 0,
            'ble_connections': 0,
            'start_time': None
        }
        
    async def start(self, config: SimulatorConfig) -> None:
        """
        Inicia a aplicação completa.
        
        Args:
            config: Configuração do simulador
        """
        print(f"=== Sistema DAQ v1.0.0 ===")
        print(f"Dispositivo: {config.device_name}")
        print(f"Modo simulador: {'Habilitado' if config.auto_start else 'Manual'}")
        print("-" * 40)
        
        try:
            # Configura tratamento de sinais
            self._setup_signal_handlers()
            
            # Inicia componentes
            await self._start_components(config)
            
            # Loop principal
            await self._main_loop()
            
        except Exception as e:
            print(f"Erro na aplicação: {e}")
            raise
        finally:
            await self._cleanup()
    
    def _setup_signal_handlers(self) -> None:
        """Configura tratamento de sinais do sistema."""
        def signal_handler(signum, frame):
            print(f"\nSinal {signum} recebido, encerrando...")
            self._shutdown_event.set()
        
        # Tratamento para SIGINT (Ctrl+C) e SIGTERM
        signal.signal(signal.SIGINT, signal_handler)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, signal_handler)
    
    async def _start_components(self, config: SimulatorConfig) -> None:
        """Inicia todos os componentes do sistema."""
        import time
        self.stats['start_time'] = time.time()
        
        # 1. Inicia simulador
        if config.auto_start:
            print("Iniciando simulador...")
            self.simulator = DAQSystemSimulator(config)
            
            # Registra callbacks
            self.simulator.add_data_callback(self._on_data_received)
            self.simulator.add_status_callback(self._on_status_update)
            
            await self.simulator.start()
            print("✓ Simulador iniciado")
        
        # 2. Configura comunicação BLE
        if config.enable_ble:
            print("Configurando comunicação BLE...")
            self.ble_comm.add_connection_callback(self._on_ble_connection)
            self.ble_comm.add_data_callback(self._on_ble_data)
            await self.ble_comm.start_advertising()
            print("✓ BLE configurado")
        
        # 3. Aplicação pronta
        self._running = True
        print("✓ Sistema DAQ pronto!")
        print()
        
        # Mostra status inicial
        await self._show_system_status()
    
    async def _main_loop(self) -> None:
        """Loop principal da aplicação."""
        print("Sistema em execução. Pressione Ctrl+C para encerrar.")
        print()
        
        last_stats_time = 0
        
        while self._running and not self._shutdown_event.is_set():
            try:
                # Mostra estatísticas periodicamente (a cada 30 segundos)
                import time
                current_time = time.time()
                
                if current_time - last_stats_time > 30:
                    await self._show_periodic_stats()
                    last_stats_time = current_time
                
                # Verifica se deve encerrar
                try:
                    await asyncio.wait_for(self._shutdown_event.wait(), timeout=1.0)
                    break
                except asyncio.TimeoutError:
                    continue
                    
            except Exception as e:
                print(f"Erro no loop principal: {e}")
                await asyncio.sleep(1.0)
        
        self._running = False
    
    async def _show_system_status(self) -> None:
        """Mostra status inicial do sistema."""
        print("Status do Sistema:")
        
        if self.simulator:
            status = self.simulator.get_system_status()
            print(f"  Simulador: {status['simulator']['current_scenario']}")
            print(f"  Bateria: {status['esp32']['battery_level']:.1f}%")
            print(f"  BLE: {status['ble']['state']}")
        
        stats = self.data_manager.get_statistics()
        print(f"  Buffer: {stats.get('buffer_size', 0)} leituras")
        print()
    
    async def _show_periodic_stats(self) -> None:
        """Mostra estatísticas periódicas."""
        import time
        uptime = time.time() - self.stats['start_time']
        
        print(f"[{time.strftime('%H:%M:%S')}] Estatísticas:")
        print(f"  Uptime: {uptime/3600:.1f}h")
        print(f"  Leituras recebidas: {self.stats['readings_received']}")
        print(f"  Leituras armazenadas: {self.stats['readings_stored']}")
        print(f"  Conexões BLE: {self.stats['ble_connections']}")
        
        if self.simulator:
            sim_stats = self.simulator.get_statistics()
            if sim_stats['total_readings'] > 0:
                print(f"  Strain atual: {sim_stats['strain_stats']['current']:+7.2f} µε")
                print(f"  Bateria: {sim_stats['battery_level']:.1f}%")
        
        print()
    
    # Callbacks do sistema
    async def _on_data_received(self, reading: StrainReading) -> None:
        """
        Callback para dados recebidos do simulador.
        
        Args:
            reading: Leitura de strain recebida
        """
        # Incrementa contador
        self.stats['readings_received'] += 1
        
        # Armazena no gerenciador de dados
        try:
            self.data_manager.add_reading(reading)
            self.stats['readings_stored'] += 1
        except Exception as e:
            print(f"Erro ao armazenar leitura: {e}")
        
        # Log a cada 100 leituras
        if self.stats['readings_received'] % 100 == 0:
            print(f"[Data] {self.stats['readings_received']} leituras processadas")
    
    async def _on_status_update(self, sensor_info: SensorInfo) -> None:
        """
        Callback para atualizações de status.
        
        Args:
            sensor_info: Informações do sensor
        """
        # Armazena informações do sensor
        try:
            self.data_manager.database.store_sensor_info(sensor_info)
        except Exception as e:
            print(f"Erro ao armazenar status: {e}")
    
    async def _on_ble_connection(self, device, connected: bool) -> None:
        """
        Callback para eventos de conexão BLE.
        
        Args:
            device: Dispositivo BLE
            connected: Se conectado ou desconectado
        """
        if connected:
            self.stats['ble_connections'] += 1
            print(f"[BLE] Cliente conectado: {device.name}")
        else:
            print(f"[BLE] Cliente desconectado: {device.name}")
    
    async def _on_ble_data(self, address: str, data: bytes) -> None:
        """
        Callback para dados recebidos via BLE.
        
        Args:
            address: Endereço do dispositivo
            data: Dados recebidos
        """
        print(f"[BLE] Dados recebidos de {address}: {len(data)} bytes")
    
    # Controle do sistema
    async def set_scenario(self, scenario_name: str) -> bool:
        """
        Altera cenário de simulação.
        
        Args:
            scenario_name: Nome do cenário
            
        Returns:
            True se cenário alterado com sucesso
        """
        if self.simulator:
            return self.simulator.set_load_scenario(scenario_name)
        return False
    
    async def configure_sensor(self, config: SensorConfiguration) -> bool:
        """
        Configura parâmetros do sensor.
        
        Args:
            config: Nova configuração
            
        Returns:
            True se configuração aplicada
        """
        if self.simulator:
            return await self.simulator.configure_sensor(config)
        return False
    
    async def export_data(self, format_type: str, output_path: Path) -> bool:
        """
        Exporta dados coletados.
        
        Args:
            format_type: Formato de exportação
            output_path: Caminho do arquivo
            
        Returns:
            True se exportação bem-sucedida
        """
        try:
            self.data_manager.export_data(format_type, output_path)
            print(f"Dados exportados: {output_path}")
            return True
        except Exception as e:
            print(f"Erro na exportação: {e}")
            return False
    
    def get_system_statistics(self) -> dict:
        """Retorna estatísticas completas do sistema."""
        stats = {
            'application': self.stats.copy(),
            'data_manager': self.data_manager.get_statistics()
        }
        
        if self.simulator:
            stats['simulator'] = self.simulator.get_statistics()
            stats['system'] = self.simulator.get_system_status()
        
        return stats
    
    async def _cleanup(self) -> None:
        """Limpa recursos e encerra componentes."""
        print("\nEncerrando sistema...")
        
        # Para simulador
        if self.simulator:
            await self.simulator.stop()
            print("✓ Simulador parado")
        
        # Para comunicação BLE
        await self.ble_comm.stop_scan()
        print("✓ Comunicação BLE encerrada")
        
        # Fecha gerenciador de dados
        self.data_manager.close()
        print("✓ Dados persistidos")
        
        # Estatísticas finais
        import time
        total_time = time.time() - self.stats['start_time']
        print(f"\nResumo da sessão:")
        print(f"  Tempo de execução: {total_time/60:.1f} minutos")
        print(f"  Leituras processadas: {self.stats['readings_received']}")
        print(f"  Taxa média: {self.stats['readings_received']/total_time:.1f} leituras/s")


# Interface de linha de comando
async def main():
    """Função principal da aplicação."""
    parser = argparse.ArgumentParser(
        description="Sistema DAQ - Aquisição de Dados para Análise de Fadiga",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python main.py                           # Configuração padrão
  python main.py --name "Field_Test"       # Nome personalizado
  python main.py --speed 2.0 --scenario transport  # Simulação acelerada
  python main.py --no-ble --export csv     # Sem BLE, exporta CSV ao final
  python main.py --config sensor_config.json       # Configuração externa
        """
    )
    
    # Argumentos de configuração
    parser.add_argument(
        "--name", 
        default="DAQ_System", 
        help="Nome do dispositivo DAQ"
    )
    
    parser.add_argument(
        "--speed", 
        type=float, 
        default=1.0, 
        help="Velocidade da simulação (1.0 = tempo real)"
    )
    
    parser.add_argument(
        "--scenario", 
        default="idle", 
        choices=["idle", "transport", "field_work_light", "field_work_heavy", "harvest", "overload"],
        help="Cenário inicial de simulação"
    )
    
    parser.add_argument(
        "--no-ble", 
        action="store_true", 
        help="Desabilita comunicação BLE"
    )
    
    parser.add_argument(
        "--wifi", 
        action="store_true", 
        help="Habilita comunicação WiFi"
    )
    
    parser.add_argument(
        "--no-simulator", 
        action="store_true", 
        help="Inicia apenas como estação receptora"
    )
    
    parser.add_argument(
        "--export", 
        choices=["csv", "json", "excel"], 
        help="Exporta dados ao final da execução"
    )
    
    parser.add_argument(
        "--config", 
        type=Path,
        help="Arquivo de configuração JSON"
    )
    
    parser.add_argument(
        "--verbose", 
        action="store_true", 
        help="Saída detalhada"
    )
    
    args = parser.parse_args()
    
    # Configura logging se verbose
    if args.verbose:
        import logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Cria configuração
    config = SimulatorConfig(
        device_name=args.name,
        simulation_speed=args.speed,
        enable_ble=not args.no_ble,
        enable_wifi=args.wifi,
        auto_start=not args.no_simulator,
        realistic_loads=True
    )
    
    # Carrega configuração externa se especificada
    if args.config and args.config.exists():
        import json
        try:
            with open(args.config) as f:
                external_config = json.load(f)
            
            # Aplica configuração externa
            for key, value in external_config.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            
            print(f"Configuração carregada: {args.config}")
        
        except Exception as e:
            print(f"Erro ao carregar configuração: {e}")
            return 1
    
    # Cria e executa aplicação
    app = DAQSystemApplication()
    
    try:
        await app.start(config)
        
        # Exportação final se solicitada
        if args.export:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = Path(f"daq_data_{timestamp}.{args.export}")
            
            success = await app.export_data(args.export, output_path)
            if success:
                print(f"✓ Dados exportados: {output_path}")
        
        return 0
        
    except KeyboardInterrupt:
        print("\nExecução interrompida pelo usuário")
        return 0
    except Exception as e:
        print(f"Erro fatal: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    # Executa aplicação principal
    from datetime import datetime
    
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except Exception as e:
        print(f"Erro crítico: {e}")
        sys.exit(1)
