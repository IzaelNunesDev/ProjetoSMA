# Organizador de Arquivos com IA

Este projeto utiliza uma arquitetura baseada em agentes de IA para organizar arquivos em um diretório com base em um objetivo definido pelo usuário. A interação pode ser feita através de uma interface web.

## Funcionalidades

- **Análise de Diretório**: Um agente `scanner` analisa o conteúdo do diretório especificado e extrai metadados dos arquivos.
- **Planejamento Inteligente**: Um agente `planner` recebe os metadados e o objetivo do usuário para criar um plano de organização (ex: criar pastas, mover arquivos).
- **Execução Segura**: Um agente `executor` executa o plano aprovado, realizando as operações no sistema de arquivos.
- **Interface Web**: Uma interface web permite que o usuário inicie o processo de organização de forma interativa, visualizando os logs em tempo real.

## Como Instalar e Executar

Siga os passos abaixo para configurar e executar o projeto.

### 1. Pré-requisitos

- Python 3.9 ou superior
- Git

### 2. Instalação

1.  Clone o repositório:
    ```bash
    git clone <URL_DO_SEU_REPOSITORIO>
    cd ProjetoSMA/file-organizer
    ```

2.  Crie e ative um ambiente virtual:
    ```bash
    python -m venv venv
    .\venv\Scripts\activate  # No Windows, use `venv\Scripts\activate`
    ```

3.  Instale as dependências:
    ```bash
   pip install -r requirements.txt
    ```

4.  Configure as variáveis de ambiente. Crie um arquivo `.env` na raiz da pasta `file-organizer` e adicione sua chave da API do Google Gemini:
    ```
    GEMINI_API_KEY=SUA_CHAVE_API_AQUI
    ```

### 3. Execução

Para iniciar a aplicação com a interface web, execute o seguinte comando no terminal, a partir da pasta `file-organizer`:

```bash
uvicorn web_ui:app --reload
```

Isso iniciará um servidor local. Abra seu navegador e acesse [http://127.0.0.1:8000](http://127.0.0.1:8000).

Na interface, você deverá:

1.  Fornecer o **caminho absoluto** para o diretório que deseja organizar (ex: `C:\Users\Izael\Downloads` ou `C:\Users\Izael\Documents`).
2.  Descrever o **objetivo da organização** (ex: "Separar arquivos por tipo de documento" ou "Agrupar imagens por ano").
3.  Clicar em "Organizar".

Os logs do processo de organização serão exibidos em tempo real na tela.

## Estrutura do Projeto

-   `main_orchestrator.py`: Script principal para execução via linha de comando (CLI).
-   `web_ui.py`: Contém a lógica do servidor web (FastAPI) e a interface com o usuário.
-   `hub.py`: O hub central que orquestra os agentes e expõe a ferramenta `organize_directory`.
-   `agents/`: Contém os diferentes agentes:
    -   `scanner_agent.py`: Responsável por analisar os arquivos.
    -   `planner_agent.py`: Responsável por criar o plano de organização.
    -   `executor_agent.py`: Responsável por executar as ações no sistema de arquivos.
-   `templates/index.html`: O arquivo HTML para a interface web.
-   `requirements.txt`: Lista de dependências do Python.
-   `.env`: Arquivo para armazenar as chaves de API.
 