document.addEventListener('DOMContentLoaded', () => {
    const messages = document.getElementById('messages');
    const form = document.getElementById('form');
    const actionSelect = document.getElementById('action_select');
    
    // Input groups
    const organizeInputs = document.getElementById('organize_inputs');
    const indexInputs = document.getElementById('index_inputs');
    const queryInputs = document.getElementById('query_inputs');
    const watchInputs = document.getElementById('watch_inputs');
    const maintenanceInputs = document.getElementById('maintenance_inputs');

    // Inputs individuais
    const dirInputOrganize = document.getElementById('dir_input_organize');
    const goalInput = document.getElementById('goal_input');
    const dirInputIndex = document.getElementById('dir_input_index');
    const queryInput = document.getElementById('query_input');
    const dirInputWatch = document.getElementById('dir_input_watch');
    const maintenanceActionSelect = document.getElementById('maintenance_action_select');
    const dirInputMaintenance = document.getElementById('dir_input_maintenance');
    const submitButton = document.getElementById('submit_button');
    const dryRunCheckbox = document.getElementById('dry_run_checkbox');

    let watchedDirectory = ''; // Armazena o diretório monitorado

    const ws = new WebSocket(`ws://${window.location.host}/ws`);

    function addMessageToChat(type, content, level = 'info', contentType = 'text') {
        const messagesContainer = messages;
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', type === 'user' ? 'user' : 'agent');

        const contentDiv = document.createElement('div');
        contentDiv.classList.add('content');

        if (contentType === 'html') {
            contentDiv.innerHTML = content.data;
            messageDiv.appendChild(contentDiv);
            messagesContainer.appendChild(messageDiv);
        } else if (type === 'log') {
            const logDiv = document.createElement('div');
            logDiv.classList.add('log-message');
            logDiv.textContent = content;
            logDiv.style.color = level === 'error' ? '#ff6b6b' : (level === 'warning' ? '#f9ca24' : '#aaa');
            messagesContainer.appendChild(logDiv);
        } else if (type === 'query_result') {
             contentDiv.innerHTML = `<strong>Resposta:</strong><p>${content.answer}</p><p><small>Fontes: ${content.source_files.join(', ') || 'N/A'}</small></p>`;
             messageDiv.appendChild(contentDiv);
             messagesContainer.appendChild(messageDiv);
        } else if (type === 'agent' && typeof content === 'object' && content.data) {
            contentDiv.innerHTML = `<p>${content.message}</p><pre style="background-color: #2a2a2a; padding: 10px; border-radius: 5px; white-space: pre-wrap; word-wrap: break-word;">${JSON.stringify(content.data, null, 2)}</pre>`;
            messageDiv.appendChild(contentDiv);
            messagesContainer.appendChild(messageDiv);
        } else {
            contentDiv.textContent = content;
            messageDiv.appendChild(contentDiv);
            messagesContainer.appendChild(messageDiv);
        }
        
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

function displaySuggestion(suggestion) {
    const suggestionId = `suggestion-${Date.now()}`;
    const card = document.createElement('div');
    card.classList.add('suggestion-card');
    card.id = suggestionId;

    card.innerHTML = `
        <div class="suggestion-header">✨ Nova Sugestão de Organização</div>
        <div class="suggestion-body">
            <p><strong>Motivo:</strong> ${suggestion.reason}</p>
            <p><strong>Mover de:</strong> <code>${suggestion.from}</code></p>
            <p><strong>Para:</strong> <code>${suggestion.to}</code></p>
        </div>
        <div class="suggestion-actions">
            <button class="approve-btn">Aprovar</button>
            <button class="decline-btn">Recusar</button>
        </div>
    `;

    messages.appendChild(card);
    messages.scrollTop = messages.scrollHeight;

    card.querySelector('.approve-btn').addEventListener('click', () => {
        // Envia a aprovação de volta para o servidor
        ws.send(JSON.stringify({
            action: 'approve_suggestion',
            suggestion: suggestion 
        }));
        addMessageToChat('user', `Aprovada sugestão para mover ${suggestion.from.split('\\').pop()}.`);
        card.remove();
    });

    card.querySelector('.decline-btn').addEventListener('click', () => {
        addMessageToChat('user', `Recusada sugestão para ${suggestion.from.split('\\').pop()}.`);
        card.remove();
    });
}

function displayPlanForApproval(plan) {
    const planId = `plan-${Date.now()}`;
    const card = document.createElement('div');
    card.classList.add('suggestion-card'); // Reutilizar o estilo do card
    card.id = planId;

    let stepsHtml = plan.steps.map(step => 
        `<li><strong>${step.action}:</strong> <code>${step.path || step.from}</code> ${step.to ? '<strong>→</strong> <code>' + step.to + '</code>' : ''}</li>`
    ).join('');

    card.innerHTML = `
        <div class="suggestion-header">📋 Plano de Organização Proposto</div>
        <div class="suggestion-body">
            <p><strong>Objetivo:</strong> ${plan.objective}</p>
            <p><strong>Ações Propostas:</strong></p>
            <ul style="max-height: 200px; overflow-y: auto; background: #1a1a1a; padding: 10px; border-radius: 4px;">${stepsHtml}</ul>
        </div>
        <div class="suggestion-actions">
            <button class="approve-btn">Executar Plano</button>
            <button class="decline-btn">Cancelar</button>
        </div>
    `;
    messages.appendChild(card);
    messages.scrollTop = messages.scrollHeight;

    card.querySelector('.approve-btn').addEventListener('click', () => {
        ws.send(JSON.stringify({
            action: 'execute_plan',
            plan: plan
        }));
        addMessageToChat('user', `Aprovado plano de organização.`);
        card.remove();
        setFormEnabled(false); // Desabilitar form enquanto executa
    });

    card.querySelector('.decline-btn').addEventListener('click', () => {
        addMessageToChat('user', 'Plano de organização cancelado.');
        card.remove();
        setFormEnabled(true); // Reabilitar o form
    });
}

    ws.onmessage = function(event) {
        const data = JSON.parse(event.data);
        console.log("Received data:", data);

        // Reabilita o formulário ao receber resultado final, erro ou query
        if (data.type === 'result' || data.type === 'query_result' || data.type === 'error' || data.type === 'plan_result') {
            setFormEnabled(true);
        }

        if (data.type === 'log') {
            addMessageToChat('log', data.message, data.level);
        } else if (data.type === 'result') {
            // Formatação amigável para organização
            if (data.data.summary && Array.isArray(data.data.summary)) {
                let formattedResult = '<strong>Resumo da Organização:</strong><ul style="list-style-type: none; padding-left: 0;">';
                data.data.summary.forEach(item => {
                    if (item.status === 'success') {
                        formattedResult += `<li>✔️ [${item.action||''}] ${item.path || item.from} movido/criado com sucesso.</li>`;
                    } else {
                        formattedResult += `<li style="color: #ff6b6b;">❌ [${item.action||''}] Falha: ${item.details}</li>`;
                    }
                });
                formattedResult += '</ul>';
                addMessageToChat('agent', { message: '✅ Operação concluída!', data: formattedResult }, 'info', 'html');
            } else {
                // Fallback para outros resultados
                addMessageToChat('agent', {message: '✅ Operação concluída!', data: data.data});
            }
        } else if (data.type === 'query_result') {
            addMessageToChat('query_result', data.data);
        } else if (data.type === 'suggestion') {
            displaySuggestion(data.data);
        } else if (data.type === 'error') {
            addMessageToChat('agent', `❌ Erro: ${data.message}`);
        } else if (data.type === 'plan_result') {
            displayPlanForApproval(data.data);
        }
    };

    actionSelect.addEventListener('change', () => {
        const selectedAction = actionSelect.value;
        organizeInputs.classList.toggle('hidden', selectedAction !== 'organize');
        indexInputs.classList.toggle('hidden', selectedAction !== 'index');
        queryInputs.classList.toggle('hidden', selectedAction !== 'query');
        watchInputs.classList.toggle('hidden', selectedAction !== 'start_watching');
        maintenanceInputs.classList.toggle('hidden', selectedAction !== 'maintenance');
        
        let buttonText = 'Executar';
        if (selectedAction === 'query') buttonText = 'Perguntar';
        if (selectedAction === 'start_watching') buttonText = 'Iniciar Monitoramento';
        if (selectedAction === 'maintenance') buttonText = 'Executar Manutenção';
        submitButton.textContent = buttonText;
    });

    // --- Controle de estado do formulário ---
    const formInputs = document.querySelectorAll('#form input, #form select, #form button');
    function setFormEnabled(enabled) {
        formInputs.forEach(input => input.disabled = !enabled);
        submitButton.style.cursor = enabled ? 'pointer' : 'not-allowed';
        submitButton.style.backgroundColor = enabled ? '#007bff' : '#555';
    }

    form.addEventListener('submit', function(event) {
        event.preventDefault();
        setFormEnabled(false); // Desabilita ao submeter
        const action = actionSelect.value;
        let payload = { action };
        let userMessage = '';

        if (action === 'organize') {
            payload.directory = dirInputOrganize.value;
            payload.goal = goalInput.value;
            payload.dry_run = dryRunCheckbox.checked; // Adicionar o novo parâmetro
            if (!payload.directory || !payload.goal) {
                alert('Por favor, preencha o caminho do diretório e o objetivo.');
                return;
            }
            userMessage = `${payload.dry_run ? 'Simular Organização' : 'Organizar'}: "${payload.directory}"\nObjetivo: "${payload.goal}"`;
        } else if (action === 'index') {
            payload.directory = dirInputIndex.value;
            if (!payload.directory) {
                alert('Por favor, preencha o caminho do diretório.');
                return;
            }
            userMessage = `Indexar diretório: "${payload.directory}"`;
        } else if (action === 'query') {
            payload.query = queryInput.value;
            if (!payload.query) {
                alert('Por favor, insira sua pergunta.');
                return;
            }
            userMessage = `Consultar: "${payload.query}"`;
        } else if (action === 'start_watching') { // Novo
            payload.directory = dirInputWatch.value;
            if (!payload.directory) {
                alert('Por favor, preencha o caminho do diretório para monitorar.');
                return;
            }
            watchedDirectory = payload.directory; // Armazena o diretório
            userMessage = `Iniciar monitoramento em: "${payload.directory}"`;
        } else if (action === 'maintenance') {
            payload.sub_action = maintenanceActionSelect.value;
            payload.directory = dirInputMaintenance.value;
            if (!payload.directory) {
                alert('Por favor, preencha o caminho do diretório para a manutenção.');
                return;
            }
            userMessage = `Manutenção: ${maintenanceActionSelect.options[maintenanceActionSelect.selectedIndex].text} em "${payload.directory}"`;
        }
        
        ws.send(JSON.stringify(payload));
        addMessageToChat('user', userMessage);
    });

    addMessageToChat('agent', 'Olá! Sou seu agente de arquivos. Escolha uma ação, preencha os campos e clique para começar.');

    // Aciona o evento change para garantir que o estado inicial está correto
    actionSelect.dispatchEvent(new Event('change'));
});
