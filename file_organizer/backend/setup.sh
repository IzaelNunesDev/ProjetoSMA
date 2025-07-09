#!/bin/bash

echo "🚀 Configurando ambiente do File Organizer..."

# Verificar se Python 3 está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 não encontrado. Instale o Python 3 primeiro."
    exit 1
fi

# Verificar versão do Python
python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "📦 Python $python_version detectado"

# Criar ambiente virtual se não existir
if [ ! -d "venv" ]; then
    echo "🔧 Criando ambiente virtual..."
    python3 -m venv venv
fi

# Ativar ambiente virtual
echo "🔧 Ativando ambiente virtual..."
source venv/bin/activate

# Atualizar pip
echo "📦 Atualizando pip..."
pip install --upgrade pip

# Instalar dependências
echo "📦 Instalando dependências..."
pip install -r requirements.txt

# Verificar instalação
echo "✅ Verificando instalação..."
python -c "import fastapi, fastmcp, uvicorn; print('✅ Todas as dependências instaladas com sucesso!')"

echo "🎉 Setup concluído! Para executar o projeto:"
echo "   source venv/bin/activate"
echo "   python main.py" 