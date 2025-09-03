#!/usr/bin/env python3
"""
Script de inicialização do Sistema DAQ.
Fornece múltiplas opções de execução: CLI, GUI, ou apenas simulador.
"""

import sys
import argparse
import asyncio
from pathlib import Path

# Adiciona diretório do projeto ao path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))


def main():
    """Função principal do script de inicialização."""
    parser = argparse.ArgumentParser(
        description="Sistema DAQ - Aquisição de Dados para Análise de Fadiga",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modos de execução:
  gui         Interface gráfica completa (padrão)
  cli         Interface de linha de comando
  simulator   Apenas simulador independente

Exemplos:
  python run.py                    # Interface gráfica
  python run.py cli --name Field_Test  # CLI com nome personalizado
  python run.py simulator --scenario harvest  # Apenas simulador
  python run.py gui                # Interface gráfica explícita
        """
    )
    
    # Subcomandos
    subparsers = parser.add_subparsers(dest='mode', help='Modo de execução')
    
    # Modo GUI (padrão)
    gui_parser = subparsers.add_parser('gui', help='Interface gráfica')
    gui_parser.add_argument('--debug', action='store_true', help='Modo debug')
    
    # Modo CLI
    cli_parser = subparsers.add_parser('cli', help='Interface de linha de comando')
    cli_parser.add_argument('--name', default='DAQ_System', help='Nome do dispositivo')
    cli_parser.add_argument('--speed', type=float, default=1.0, help='Velocidade da simulação')
    cli_parser.add_argument('--scenario', default='idle', help='Cenário inicial')
    cli_parser.add_argument('--no-ble', action='store_true', help='Desabilita BLE')
    cli_parser.add_argument('--export', choices=['csv', 'json', 'excel'], help='Exporta ao final')
    cli_parser.add_argument('--verbose', action='store_true', help='Saída detalhada')
    
    # Modo simulador
    sim_parser = subparsers.add_parser('simulator', help='Apenas simulador')
    sim_parser.add_argument('--scenario', default='idle', help='Cenário de carga')
    sim_parser.add_argument('--duration', type=int, default=60, help='Duração em segundos')
    sim_parser.add_argument('--speed', type=float, default=1.0, help='Velocidade da simulação')
    sim_parser.add_argument('--output', help='Arquivo de saída')
    
    args = parser.parse_args()
    
    # Define modo padrão como GUI se nenhum especificado
    if not args.mode:
        args.mode = 'gui'
    
    # Executa modo selecionado
    try:
        if args.mode == 'gui':
            run_gui_mode(args)
        elif args.mode == 'cli':
            run_cli_mode(args)
        elif args.mode == 'simulator':
            run_simulator_mode(args)
        else:
            parser.error(f"Modo desconhecido: {args.mode}")
            
    except KeyboardInterrupt:
        print("\nExecução interrompida pelo usuário")
        sys.exit(0)
    except Exception as e:
        print(f"Erro: {e}")
        if hasattr(args, 'verbose') and args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def run_gui_mode(args):
    """Executa modo interface gráfica."""
    try:
        from gui import main_gui
        print("Iniciando interface gráfica...")
        asyncio.run(main_gui())
        
    except ImportError as e:
        print(f"Erro ao importar GUI: {e}")
        print("Certifique-se de que as dependências estão instaladas:")
        print("  pip install PyQt5 qasync matplotlib")
        sys.exit(1)


def run_cli_mode(args):
    """Executa modo linha de comando."""
    try:
        # Importa main do CLI
        sys.argv = ['main.py']  # Reset argv para evitar conflitos
        
        # Adiciona argumentos do CLI
        if args.name:
            sys.argv.extend(['--name', args.name])
        if args.speed != 1.0:
            sys.argv.extend(['--speed', str(args.speed)])
        if args.scenario != 'idle':
            sys.argv.extend(['--scenario', args.scenario])
        if args.no_ble:
            sys.argv.append('--no-ble')
        if args.export:
            sys.argv.extend(['--export', args.export])
        if args.verbose:
            sys.argv.append('--verbose')
        
        from main import main
        asyncio.run(main())
        
    except ImportError as e:
        print(f"Erro ao importar CLI: {e}")
        sys.exit(1)


def run_simulator_mode(args):
    """Executa apenas o simulador."""
    try:
        # Reset argv para simulador
        sys.argv = ['simulator/main.py']
        
        # Adiciona argumentos do simulador
        if args.scenario != 'idle':
            sys.argv.extend(['--scenario', args.scenario])
        if args.duration != 60:
            sys.argv.extend(['--duration', str(args.duration)])
        if args.speed != 1.0:
            sys.argv.extend(['--speed', str(args.speed)])
        if args.output:
            sys.argv.extend(['--output', args.output])
        
        from simulator.main import main
        asyncio.run(main())
        
    except ImportError as e:
        print(f"Erro ao importar simulador: {e}")
        sys.exit(1)


def check_dependencies():
    """Verifica se as dependências estão instaladas."""
    missing = []
    
    # Dependências obrigatórias
    required = ['pandas', 'numpy', 'pytest']
    
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    # Dependências opcionais
    optional = {
        'PyQt5': 'Interface gráfica',
        'matplotlib': 'Gráficos',
        'bleak': 'Comunicação BLE'
    }
    
    for package, description in optional.items():
        try:
            __import__(package)
        except ImportError:
            print(f"Aviso: {package} não instalado ({description})")
    
    if missing:
        print("Dependências obrigatórias faltando:")
        for package in missing:
            print(f"  - {package}")
        print("\nInstale com: pip install -r requirements.txt")
        return False
    
    return True


if __name__ == "__main__":
    # Verifica dependências básicas
    if not check_dependencies():
        sys.exit(1)
    
    # Executa aplicação
    main()
