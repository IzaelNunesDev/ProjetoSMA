# File Organizer - Backend

Sistema inteligente de organização de arquivos com interface web.

## 🚀 Instalação Rápida

### Pré-requisitos
- Python 3.8 ou superior
- Git

### Setup Automático
```bash
# Clone o repositório (se ainda não fez)
git clone <seu-repositorio>
cd file-organizer/backend

# Execute o script de setup
./setup.sh
```

### Setup Manual
```bash
# 1. Criar ambiente virtual
python3 -m venv venv

# 2. Ativar ambiente virtual
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# 3. Instalar dependências
pip install -r requirements.txt
```

## 🏃‍♂️ Execução

```bash
# Ativar ambiente virtual (se não estiver ativo)
source venv/bin/activate

# Executar o servidor
python main.py
```

O servidor estará disponível em: http://127.0.0.1:8000

## 🔧 Configuração do IDE

### VS Code
1. Abra o projeto no VS Code
2. Pressione `Ctrl+Shift+P` (ou `Cmd+Shift+P` no Mac)
3. Digite "Python: Select Interpreter"
4. Selecione o interpretador do ambiente virtual: `./venv/bin/python`

### PyCharm
1. Vá em `File > Settings > Project > Python Interpreter`
2. Clique em "Add Interpreter"
3. Selecione "Existing Environment"
4. Aponte para `./venv/bin/python`

## 🐛 Solução de Problemas

### Erro: "Module not found"
- Certifique-se de que o ambiente virtual está ativado
- Reinstale as dependências: `pip install -r requirements.txt`

### Erro: "Port already in use"
- Mude a porta no arquivo `main.py` ou mate o processo:
  ```bash
  lsof -ti:8000 | xargs kill -9
  ```

### Warnings de Depreciação
- Os warnings são normais e não afetam a funcionalidade
- Eles foram suprimidos no código para melhor experiência

## 📁 Estrutura do Projeto

```
backend/
├── agents/           # Agentes de IA
├── templates/        # Templates HTML
├── static/          # Arquivos estáticos (CSS, JS)
├── prompts/         # Prompts para IA
├── chroma_db/       # Banco de dados vetorial
├── web_ui.py        # Interface web principal
├── hub.py           # Hub de ferramentas
├── main.py          # Ponto de entrada
└── requirements.txt # Dependências
```

## 🔍 Funcionalidades

- **Organização Inteligente**: Organiza arquivos usando IA
- **Monitoramento Proativo**: Detecta novos arquivos automaticamente
- **Sistema de Memória**: Lembra de organizações anteriores
- **Interface Web**: Interface amigável para interação
- **Checkpoints**: Sistema de backup e restauração

## 📝 Licença

Este projeto está sob a licença MIT. 