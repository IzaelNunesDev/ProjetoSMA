document.addEventListener('DOMContentLoaded', () => {
    const ws = new WebSocket(`ws://${window.location.host}/ws`);

    const generatePlanBtn = document.getElementById('generatePlanBtn');
    const summarizeBtn = document.getElementById('summarizeBtn');
    const directoryInput = document.getElementById('directoryInput');
    const goalInput = document.getElementById('goalInput');
    const resultContainer = document.getElementById('result-container');

    const setFormDisabled = (disabled) => {
        generatePlanBtn.disabled = disabled;
        summarizeBtn.disabled = disabled;
        directoryInput.disabled = disabled;
        goalInput.disabled = disabled;
        generatePlanBtn.textContent = disabled ? 'Gerando...' : 'Gerar Plano';
    };

    ws.onopen = () => console.log('WebSocket conectado.');
    ws.onclose = () => console.log('WebSocket desconectado.');
    ws.onerror = (error) => console.error('WebSocket Error:', error);

    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        console.log('Mensagem recebida:', msg);

        if (msg.type === 'plan_result') {
            setFormDisabled(false);
            const data = msg.data;
            if (data.status === 'plan_generated' && data.plan) {
                displayPlan(data.plan);
            } else {
                resultContainer.innerHTML = `<div class="plan-container" style="color: #ff6b6b;"><strong>Erro:</strong> ${data.message || 'Não foi possível gerar o plano.'}</div>`;
            }
        } else if (msg.type === 'log') {
            const logPanel = document.querySelector('.log-panel');
            if(logPanel) {
                const logEntry = document.createElement('div');
                logEntry.className = `log-message ${msg.level}`;
                logEntry.textContent = `[${msg.level.toUpperCase()}] ${msg.message}`;
                logPanel.appendChild(logEntry);
                logPanel.scrollTop = logPanel.scrollHeight;
            }
        } else if (msg.type === 'error') {
            setFormDisabled(false);
            resultContainer.innerHTML = `<div class="plan-container" style="color: #ff6b6b;"><strong>Erro no Servidor:</strong> ${msg.message}</div>`;
        }
    };

    function displayPlan(plan) {
        let stepsHtml = '';
        if (plan.steps && plan.steps.length > 0) {
            stepsHtml = plan.steps.map(step => {
                const fromPath = step.from ? `<code>${step.from}</code>` : '';
                const toPath = step.to ? `<strong> → </strong><code>${step.to}</code>` : `<code>${step.path}</code>`;
                return `<div class="plan-step"><span class="action">${step.action}</span>: ${fromPath}${toPath}</div>`;
            }).join('');
        } else {
            stepsHtml = '<p>Nenhuma ação necessária para este plano.</p>';
        }

        resultContainer.innerHTML = `
            <div class="plan-container">
                <h3>Plano de Organização Sugerido</h3>
                <p><strong>Objetivo:</strong> ${plan.objective}</p>
                <hr>
                ${stepsHtml}
            </div>
            <div class="plan-container">
                <h3>Logs do Agente</h3>
                <div class="log-panel"></div>
            </div>
        `;
    }

    generatePlanBtn.addEventListener('click', () => {
        const directory = directoryInput.value.trim();
        const goal = goalInput.value.trim();
        if (!directory || !goal) {
            alert('Por favor, preencha o diretório e o objetivo.');
            return;
        }
        setFormDisabled(true);
        resultContainer.innerHTML = `
            <div class="plan-container">
                <h3>Gerando Plano...</h3>
                <p>O agente está analisando o diretório. Logs aparecerão abaixo.</p>
                <div class="log-panel">
                   <div class="log-message info">[INFO] Solicitação enviada ao agente...</div>
                </div>
            </div>`;
        ws.send(JSON.stringify({ action: 'generate_plan', directory, goal }));
    });

    summarizeBtn.addEventListener('click', () => {
        alert('Enviando solicitação para o SummarizerAgent. Ele irá processar as últimas entradas do feed em segundo plano. Verifique a página do feed para ver o resultado.');
        ws.send(JSON.stringify({ action: 'process_feed' }));
    });
});