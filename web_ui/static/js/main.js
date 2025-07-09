const ws = new WebSocket(`ws://${window.location.host}/ws`);
const analyzeBtn = document.getElementById('analyzeBtn');
const directoryInput = document.getElementById('directoryInput');
const resultDiv = document.getElementById('result'); // Mudar para um div

ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    resultDiv.innerHTML = ''; // Limpa resultados anteriores

    if (msg.type === 'analysis_result' && msg.data) {
        if (msg.data.status === 'error') {
            resultDiv.innerHTML = `<p style="color: red;">Erro: ${msg.data.details || 'Ocorreu um erro.'}</p>`;
            return;
        }

        const analysisData = msg.data.result;
        const treeText = msg.data.tree;

        // 1. Análise
        const analysisHeader = document.createElement('h3');
        analysisHeader.textContent = 'Análise da Estrutura';
        const analysisP = document.createElement('p');
        analysisP.textContent = analysisData.analysis || "Nenhuma análise fornecida.";
        resultDiv.appendChild(analysisHeader);
        resultDiv.appendChild(analysisP);

        // 2. Sugestões
        const suggestionsHeader = document.createElement('h3');
        suggestionsHeader.textContent = 'Sugestões de Reorganização';
        resultDiv.appendChild(suggestionsHeader);
        
        if (analysisData.suggestions && analysisData.suggestions.length > 0) {
            const ul = document.createElement('ul');
            analysisData.suggestions.forEach(s => {
                const li = document.createElement('li');
                li.innerHTML = `Mover <code>${s.from}</code> para uma nova categoria: <strong>${s.to_category}</strong>`;
                ul.appendChild(li);
            });
            resultDiv.appendChild(ul);
        } else {
            const noSuggestionsP = document.createElement('p');
            noSuggestionsP.textContent = 'Nenhuma sugestão de reorganização necessária.';
            resultDiv.appendChild(noSuggestionsP);
        }
        
        // 3. Árvore de Diretórios
        const treeHeader = document.createElement('h3');
        treeHeader.textContent = 'Estrutura Analisada';
        const treePre = document.createElement('pre');
        treePre.textContent = treeText;
        resultDiv.appendChild(treeHeader);
        resultDiv.appendChild(treePre);

    } else if (msg.type === 'error') {
        resultDiv.innerHTML = `<p style="color: red;">Erro de comunicação: ${msg.message}</p>`;
    } else {
        // Log de status (ex: "Analisando...")
        resultDiv.textContent = JSON.stringify(msg, null, 2);
    }
};

analyzeBtn.onclick = () => {
    const directory = directoryInput.value.trim();
    if (!directory) {
        resultDiv.textContent = 'Informe um diretório válido.';
        return;
    }
    ws.send(JSON.stringify({ action: 'analyze_structure', directory }));
    resultDiv.textContent = 'Analisando...';
};