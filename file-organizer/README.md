Organizador de Arquivos com IA
Este projeto utiliza uma arquitetura baseada em agentes de IA para organizar arquivos em um diretório com base em um objetivo definido pelo usuário. A interação pode ser feita através de uma interface web.
Funcionalidades
Análise de Diretório: Um agente scanner analisa o conteúdo do diretório especificado e extrai metadados dos arquivos.
Planejamento Inteligente: Um agente planner recebe os metadados e o objetivo do usuário para criar um plano de organização (ex: criar pastas, mover arquivos).
Execução Segura: Um agente executor executa o plano aprovado, realizando as operações no sistema de arquivos.
Monitoramento Proativo: Um watcher monitora um diretório e, ao detectar um novo arquivo, usa um suggestion_agent para propor uma ação de organização baseada na memória do sistema.
Interface Web: Uma interface web permite que o usuário inicie o processo de organização de forma interativa, visualizando os logs em tempo real e aprovando sugestões.
Como Instalar e Executar
Siga os passos abaixo para configurar e executar o projeto.
1. Pré-requisitos
Python 3.9 ou superior
Git
2. Instalação
Clone o repositório:
git clone <URL_DO_SEU_REPOSITORIO>
cd izaelnunesdev-projetosma/file-organizer
Use code with caution.
Bash
Crie e ative um ambiente virtual:
python -m venv venv
source venv/bin/activate  # No Linux/macOS
# ou
.\venv\Scripts\activate  # No Windows
Use code with caution.
Bash
Instale as dependências:
pip install -r requirements.txt
Use code with caution.
Bash
Configure as variáveis de ambiente. Copie o arquivo .env.example para um novo arquivo chamado .env.
cp .env.example .env
Use code with caution.
Bash
Em seguida, edite o arquivo .env e adicione sua chave da API do Google Gemini.
# .env
GEMINI_API_KEY="SUA_CHAVE_API_REAL_AQUI"
Use code with caution.
IMPORTANTE: O arquivo .env contém informações sensíveis e já está no .gitignore para não ser enviado ao seu repositório Git. Nunca comite suas chaves de API! Se você clonou o repositório com uma chave exposta, revogue-a imediatamente no seu painel do Google Cloud.
3. Execução
Para iniciar a aplicação com a interface web, execute o seguinte comando no terminal, a partir da pasta file-organizer:
python main.py
Use code with caution.
Bash
Isso iniciará um servidor local. Abra seu navegador e acesse http://127.0.0.1:8000.
Na interface, você poderá:
Fornecer o caminho absoluto para o diretório que deseja organizar.
Descrever o objetivo da organização.
Indexar um diretório para criar uma memória.
Consultar a memória com perguntas em linguagem natural.
Iniciar o monitoramento proativo de um diretório.
Clicar no botão de ação para executar a tarefa selecionada.
Os logs do processo de organização serão exibidos em tempo real na tela.
Estrutura do Projeto
main.py: Ponto de entrada que inicia o servidor web.
web_ui.py: Contém a lógica do servidor web (FastAPI) e a interface com o usuário.
hub.py: O hub central que orquestra os agentes e expõe as ferramentas como organize_directory e suggest_file_move.
agents/: Contém os diferentes agentes (scanner, planner, executor, memory, suggestion).
prompts/: Diretório para gerenciamento de templates de prompts.
watcher.py: Módulo que implementa o monitoramento de diretórios em segundo plano.
templates/: Contém os arquivos HTML para a interface web.
requirements.txt: Lista de dependências do Python.
.env: Arquivo para armazenar as chaves de API (ignorado pelo Git).
.env.example: Arquivo de exemplo para as variáveis de ambiente.
.gitignore: Especifica arquivos e pastas a serem ignorados pelo Git.