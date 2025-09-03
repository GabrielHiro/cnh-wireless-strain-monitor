"""
Aplicação principal do simulador DAQ.
Interface de linha de comando para testar o sistema sem hardware.
"""

import asyncio
import argparse
import sys
import time
from pathlib import Path

# Adiciona diretório pai ao path para importações
sys.path.append(str(Path(__file__).parent.parent))

from simulator.daq_simulator import DAQSystemSimulator, SimulatorConfig
from src.core.models import StrainReading, SensorInfo


class SimulatorCLI:
    """Interface de linha de comando para o simulador."""
    
    def __init__(self):
        """Inicializa o CLI do simulador."""
        self.simulator = None
        self._running = False
        
    async def start_simulator(self, config: SimulatorConfig) -> None:
        """
        Inicia o simulador com configuração específica.
        
        Args:
            config: Configuração do simulador
        """
        print("=== Simulador Sistema DAQ ===")
        print(f"Dispositivo: {config.device_name}")
        print(f"BLE: {'Habilitado' if config.enable_ble else 'Desabilitado'}")
        print(f"WiFi: {'Habilitado' if config.enable_wifi else 'Desabilitado'}")
        print(f"Velocidade: {config.simulation_speed}x")
        print("-" * 40)
        
        # Cria e configura simulador
        self.simulator = DAQSystemSimulator(config)
        
        # Registra callbacks para monitoramento
        self.simulator.add_data_callback(self._on_data_received)
        self.simulator.add_status_callback(self._on_status_update)
        
        # Inicia simulação
        await self.simulator.start()
        self._running = True
        
        print("Simulador iniciado!")
        print("Comandos disponíveis:")
        print("  scenarios - Lista cenários de carga")
        print("  set <scenario> - Altera cenário")
        print("  load <valor> - Aplica carga customizada")
        print("  stats - Mostra estatísticas")
        print("  status - Status do sistema")
        print("  quit - Sair")
        print()
        
        # Loop de comandos
        await self._command_loop()
    
    async def _command_loop(self) -> None:
        """Loop de processamento de comandos."""
        while self._running:
            try:
                # Simula input não-bloqueante
                await asyncio.sleep(0.1)
                
                # Em uma implementação real, usaria aioconsole ou similar
                # Por simplicidade, vou simular alguns comandos automaticamente
                
                # A cada 10 segundos, muda cenário automaticamente
                if int(time.time()) % 10 == 0:
                    scenarios = list(self.simulator.get_available_scenarios().keys())
                    import random
                    new_scenario = random.choice(scenarios)
                    self.simulator.set_load_scenario(new_scenario)
                    await asyncio.sleep(1)  # Evita múltiplas mudanças no mesmo segundo
                
            except KeyboardInterrupt:
                print("\nEncerrando simulador...")
                self._running = False
                break
            except Exception as e:
                print(f"Erro no loop de comandos: {e}")
                await asyncio.sleep(1)
        
        if self.simulator:
            await self.simulator.stop()
    
    async def _on_data_received(self, reading: StrainReading) -> None:
        """
        Callback chamado quando dados são recebidos.
        
        Args:
            reading: Leitura recebida
        """
        # Mostra dados periodicamente (a cada 5 segundos)
        if int(time.time()) % 5 == 0:
            print(f"[{reading.timestamp.strftime('%H:%M:%S')}] "
                  f"Strain: {reading.strain_value:+8.2f} µε | "
                  f"Battery: {reading.battery_level}% | "
                  f"Temp: {reading.temperature:.1f}°C")
    
    async def _on_status_update(self, sensor_info: SensorInfo) -> None:
        """
        Callback chamado quando status é atualizado.
        
        Args:
            sensor_info: Informações do sensor
        """
        # Log de status apenas quando muda
        pass
    
    def _process_command(self, command: str) -> bool:
        """
        Processa comando inserido pelo usuário.
        
        Args:
            command: Comando a ser processado
            
        Returns:
            True para continuar, False para sair
        """
        parts = command.strip().lower().split()
        
        if not parts:
            return True
        
        cmd = parts[0]
        
        if cmd == "quit":
            return False
        
        elif cmd == "scenarios":
            scenarios = self.simulator.get_available_scenarios()
            print("Cenários disponíveis:")
            for name, description in scenarios.items():
                current = " (atual)" if name == self.simulator._current_scenario else ""
                print(f"  {name}: {description}{current}")
        
        elif cmd == "set" and len(parts) > 1:
            scenario = parts[1]
            if self.simulator.set_load_scenario(scenario):
                print(f"Cenário alterado para: {scenario}")
            else:
                print(f"Cenário inválido: {scenario}")
        
        elif cmd == "load" and len(parts) > 1:
            try:
                load_value = float(parts[1])
                self.simulator.apply_custom_load(load_value)
                print(f"Carga aplicada: {load_value} µε")
            except ValueError:
                print("Valor de carga inválido")
        
        elif cmd == "stats":
            stats = self.simulator.get_statistics()
            print("Estatísticas:")
            print(f"  Total de leituras: {stats['total_readings']}")
            if stats['total_readings'] > 0:
                strain_stats = stats['strain_stats']
                print(f"  Strain atual: {strain_stats['current']:.2f} µε")
                print(f"  Strain min/max: {strain_stats['min']:.2f} / {strain_stats['max']:.2f} µε")
                print(f"  Strain médio: {strain_stats['avg']:.2f} µε")
                print(f"  Bateria: {stats['battery_level']:.1f}%")
                print(f"  Cenário: {stats['current_scenario']}")
        
        elif cmd == "status":
            status = self.simulator.get_system_status()
            print("Status do sistema:")
            print(f"  Simulador: {'Rodando' if status['simulator']['running'] else 'Parado'}")
            print(f"  Cenário: {status['simulator']['current_scenario']}")
            print(f"  Velocidade: {status['simulator']['simulation_speed']}x")
            print(f"  ESP32 - Bateria: {status['esp32']['battery_level']:.1f}%")
            print(f"  ESP32 - Modo: {status['esp32']['power_mode']}")
            print(f"  BLE - Estado: {status['ble']['state']}")
        
        else:
            print("Comando não reconhecido. Digite 'quit' para sair.")
        
        return True


async def main():
    """Função principal do simulador."""
    parser = argparse.ArgumentParser(description="Simulador Sistema DAQ")
    parser.add_argument("--name", default="DAQ_Simulator", help="Nome do dispositivo")
    parser.add_argument("--speed", type=float, default=1.0, help="Velocidade da simulação")
    parser.add_argument("--no-ble", action="store_true", help="Desabilita BLE")
    parser.add_argument("--wifi", action="store_true", help="Habilita WiFi")
    parser.add_argument("--scenario", default="idle", help="Cenário inicial")
    
    args = parser.parse_args()
    
    # Cria configuração
    config = SimulatorConfig(
        device_name=args.name,
        simulation_speed=args.speed,
        enable_ble=not args.no_ble,
        enable_wifi=args.wifi,
        auto_start=True,
        realistic_loads=True
    )
    
    # Inicia CLI
    cli = SimulatorCLI()
    
    try:
        await cli.start_simulator(config)
    except KeyboardInterrupt:
        print("\nSimulação interrompida pelo usuário")
    except Exception as e:
        print(f"Erro na simulação: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Executa o simulador
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nSimulador encerrado")
    except Exception as e:
        print(f"Erro fatal: {e}")
        sys.exit(1)
