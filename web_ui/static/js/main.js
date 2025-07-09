const ws = new WebSocket(`ws://${window.location.host}/ws`);
const analyzeBtn = document.getElementById('analyzeBtn');
const directoryInput = document.getElementById('directoryInput');
const resultPre = document.getElementById('result');

ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.type === 'analysis_result') {
        resultPre.textContent = JSON.stringify(msg.data, null, 2);
    } else if (msg.type === 'error') {
        resultPre.textContent = 'Erro: ' + msg.message;
    }
};

analyzeBtn.onclick = () => {
    const directory = directoryInput.value.trim();
    if (!directory) {
        resultPre.textContent = 'Informe um diretório válido.';
        return;
    }
    ws.send(JSON.stringify({ action: 'analyze_structure', directory }));
    resultPre.textContent = 'Analisando...';
}; 