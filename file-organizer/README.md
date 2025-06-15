# Organizador de Arquivos com IA

Este projeto utiliza uma arquitetura moderna com agentes de IA para organizar arquivos em um diretório com base em um objetivo definido pelo usuário. A interação é feita através de uma interface web reativa construída com React, que se comunica em tempo real com um backend Python (FastAPI).

## Arquitetura

A aplicação é dividida em duas partes principais: um backend responsável pela lógica de IA e um frontend para a interação com o usuário.

-   **Backend (Python + FastAPI):**
    -   Serve uma API e um endpoint WebSocket para comunicação em tempo real.
    -   **Agentes de IA:**
        -   `ScannerAgent`: Analisa o conteúdo do diretório e extrai metadados.
        -   `PlannerAgent`: Cria um plano de organização com base no objetivo do usuário.
        -   `ExecutorAgent`: Executa o plano de forma segura.
        -   `SuggestionAgent`: Monitora um diretório e sugere ações de organização para novos arquivos.
    -   **Hub:** Orquestra a comunicação entre os agentes e o frontend.

-   **Frontend (React + TypeScript):**
    -   Interface de usuário moderna e reativa construída com Vite, React e Tailwind CSS.
    -   Recebe atualizações em tempo real do backend via WebSocket para exibir logs, status e sugestões.
    -   Permite ao usuário definir o diretório, o objetivo, aprovar planos e interagir com o sistema de forma intuitiva.

## Como Instalar e Executar

Siga os passos abaixo para configurar e executar o projeto em seu ambiente local.

### 1. Pré-requisitos

-   Python 3.9 ou superior
-   Node.js (v18 ou superior) e npm
-   Git

### 2. Instalação

**a. Clone o repositório:**

```bash
git clone <URL_DO_SEU_REPOSITORIO>
cd izaelnunesdev-projetosma/file-organizer
```

**b. Configure o Backend:**

1.  Navegue até a pasta do backend:
    ```bash
    cd backend
    ```
2.  Crie e ative um ambiente virtual:
    ```bash
    python -m venv venv
    # No Windows
    .\venv\Scripts\activate
    # No Linux/macOS
    source venv/bin/activate
    ```
3.  Instale as dependências do Python:
    ```bash
    pip install -r requirements.txt
    ```
4.  Configure suas credenciais. Copie o arquivo `.env.example` para `.env` e adicione sua chave da API do Google Gemini:
    ```bash
    cp .env.example .env
    # Edite o arquivo .env e adicione sua chave
    # GEMINI_API_KEY="SUA_CHAVE_API_REAL_AQUI"
    ```
    > **IMPORTANTE:** O arquivo `.env` já está no `.gitignore`. Nunca comite suas chaves de API.

**c. Configure o Frontend:**

1.  Navegue até a pasta do frontend (a partir da raiz `file-organizer`):
    ```bash
    cd ../frontend
    ```
2.  Instale as dependências do Node.js:
    ```bash
    npm install
    ```

### 3. Execução

Para rodar a aplicação, você precisará de dois terminais.

**a. Terminal 1: Iniciar o Backend**

```bash
# Navegue até a pasta do backend
cd file-organizer/backend

# Ative o ambiente virtual (se não estiver ativo)
.\venv\Scripts\activate

# Inicie o servidor FastAPI
python main.py
```
O backend estará rodando e aguardando conexões na porta 8000.

**b. Terminal 2: Iniciar o Frontend**

```bash
# Navegue até a pasta do frontend
cd file-organizer/frontend

# Inicie o servidor de desenvolvimento do Vite
npm run dev
```

**c. Acesse a Aplicação**

Abra seu navegador e acesse **[http://localhost:8080](http://localhost:8080)**.

## Estrutura do Projeto

```
file-organizer/
├── backend/
│   ├── agents/         # Módulos dos agentes de IA
│   ├── prompts/        # Templates de prompts para a IA
│   ├── .env.example    # Exemplo de arquivo de ambiente
│   ├── hub.py          # Orquestrador central dos agentes
│   ├── main.py         # Ponto de entrada do servidor FastAPI
│   ├── requirements.txt# Dependências do Python
│   └── watcher.py      # Monitoramento de diretórios
│
└── frontend/
    ├── public/         # Arquivos estáticos
    ├── src/
    │   ├── assets/     # Imagens e outros assets
    │   ├── components/ # Componentes React reutilizáveis
    │   ├── hooks/      # Hooks customizados (ex: useWebSocket)
    │   ├── pages/      # Páginas da aplicação
    │   ├── App.tsx     # Componente principal da aplicação
    │   └── main.tsx    # Ponto de entrada do React
    ├── package.json    # Dependências e scripts do Node.js
    └── vite.config.ts  # Configuração do Vite
```