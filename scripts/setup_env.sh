#!/usr/bin/env bash
set -euo pipefail

# Script para criar ambiente virtual e instalar dependências (Git Bash / WSL)
# Uso: bash scripts/setup_env.sh

if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
  echo "Python não encontrado. Por favor, instale o Python antes de rodar este script." >&2
  exit 2
fi

PY_CMD=python
if command -v python3 &> /dev/null; then
  PY_CMD=python3
fi

echo "Usando: $($PY_CMD --version)"

# Cria o venv
$PY_CMD -m venv venv

# Ativa o venv (Git Bash/MinGW/MSYS)
# shellcheck disable=SC1090
source venv/Scripts/activate || source venv/bin/activate || true

# Atualiza pip
$PY_CMD -m pip install --upgrade pip setuptools wheel

# Instala dependências
if [ -f requirements.txt ]; then
  pip install -r requirements.txt
else
  echo "Arquivo requirements.txt não encontrado. Pulei a instalação de dependências."
fi

echo "Ambiente preparado. Ative com: source venv/Scripts/activate (ou . venv/Scripts/activate)"
