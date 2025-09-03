# PowerShell script para configurar ambiente virtual e instalar dependências
# Uso: PowerShell -ExecutionPolicy Bypass -File .\scripts\setup_env.ps1

param(
    [string]$PythonPath = "python"
)

if (-not (Get-Command $PythonPath -ErrorAction SilentlyContinue)) {
    Write-Error "Python não encontrado. Instale o Python 3.8+ e tente novamente."
    exit 2
}

$pyVersion = & $PythonPath --version
Write-Host "Usando: $pyVersion"

# Cria venv
& $PythonPath -m venv venv

# Ativa venv
$activate = Join-Path -Path (Get-Location) -ChildPath "venv\Scripts\Activate.ps1"
Write-Host "Ativar com: .\venv\Scripts\Activate.ps1"

# Atualiza pip
& $PythonPath -m pip install --upgrade pip setuptools wheel

# Instala dependências
if (Test-Path requirements.txt) {
    & $PythonPath -m pip install -r requirements.txt
} else {
    Write-Warning "requirements.txt não encontrado. Pulei a instalação de dependências."
}

Write-Host "Ambiente configurado com sucesso."
