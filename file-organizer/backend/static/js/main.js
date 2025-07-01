document.addEventListener('DOMContentLoaded', () => {
    const messages = document.getElementById('messages');
    const form = document.getElementById('form');
    const actionSelect = document.getElementById('action_select');
    
    // Input groups
    const organizeInputs = document.getElementById('organize_inputs');
    const organizeExperimentalInputs = document.getElementById('organize_experimental_inputs'); 
    const indexInputs = document.getElementById('index_inputs');
    const queryInputs = document.getElementById('query_inputs');
    const watchInputs = document.getElementById('watch_inputs');
    const maintenanceInputs = document.getElementById('maintenance_inputs');

    // Inputs individuais
    const dirInputOrganize = document.getElementById('dir_input_organize');
    const dirInputOrganizeExperimental = document.getElementById('dir_input_organize_experimental'); 
    const goalInput = document.getElementById('goal_input');
    const dirInputIndex = document.getElementById('dir_input_index');
    const queryInput = document.getElementById('query_input');
    const dirInputWatch = document.getElementById('dir_input_watch');
    const maintenanceActionSelect = document.getElementById('maintenance_action_select');
    const dirInputMaintenance = document.getElementById('dir_input_maintenance');
    const submitButton = document.getElementById('submit_button');
    const dryRunCheckbox = document.getElementById('dry_run_checkbox');

    let watchedDirectory = ''; 

    const ws = new WebSocket(`ws://${window.location.host}/ws`);

    // Funções de display e addMessageToChat (sem mudanças)...
    function addMessageToChat(type, content, level = 'info', contentType = 'text') {
        const messagesContainer = messages;
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', type === 'user' ? 'user' : 'agent');
        const contentDiv = document.createElement('div');
        contentDiv.classList.add('content');
        if (contentType === 'html') {
            contentDiv.innerHTML = content.data;
        } else if (type === 'log') {
            const logDiv = document.createElement('div');
            logDiv.classList.add('log-message');
            logDiv.textContent = content;
            logDiv.style.color = level === 'error' ? '#ff6b6b' : (level === 'warning' ? '#f9ca24' : '#aaa');
            messagesContainer.appendChild(logDiv);
            messageDiv.appendChild(logDiv);
            return;
        } else if (type === 'query_result') {
             contentDiv.innerHTML = `<strong>Resposta:</strong><p>${content.answer}</p><p><small>Fontes: ${content.source_files.join(', ') || 'N/A'}</small></p>`;
        } else if (type === 'agent' && typeof content === 'object' && content.data) {
            contentDiv.innerHTML = `<p>${content.message}</p><pre style="background-color: #2a2a2a; padding: 10px; border-radius: 5px; white-space: pre-wrap; word-wrap: break-word;">${JSON.stringify(content.data, null, 2)}</pre>`;
        } else {
            contentDiv.textContent = content;
        }
        messageDiv.appendChild(contentDiv);
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    function displayPlanForApproval(plan) {
        const planId = `plan-${Date.now()}`;
        const card = document.createElement('div');
        card.classList.add('suggestion-card');
        card.id = planId;
        let stepsHtml = plan.steps.map(step => `<li><strong>${step.action}:</strong> <code>${step.path || step.from}</code> ${step.to ? '<strong>→</strong> <code>' + step.to + '</code>' : ''}</li>`).join('');
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
            ws.send(JSON.stringify({ action: 'execute_plan', plan: plan }));
            addMessageToChat('user', 'Aprovado plano de organização.');
            card.remove();
            setFormEnabled(false);
        });
        card.querySelector('.decline-btn').addEventListener('click', () => {
            addMessageToChat('user', 'Plano de organização cancelado.');
            card.remove();
            setFormEnabled(true);
        });
    }

    ws.onmessage = function(event) {
        const data = JSON.parse(event.data);
        console.log("Received data:", data);

        if (['result', 'query_result', 'error', 'plan_result', 'experimental_result'].includes(data.type)) {
            setFormEnabled(true);
        }

        if (data.type === 'log') {
            addMessageToChat('log', data.message, data.level);
        } else if (data.type === 'experimental_result') { 
            // Primeiro, verifica se o backend retornou um erro
            if (data.data.status === 'error') {
                addMessageToChat('agent', `❌ Erro na análise experimental: ${data.data.details}`, 'error');
                return;
            }

            const result = data.data.result;
            const tree = data.data.tree;

            // Verifica se o 'result' existe antes de tentar ler 'analysis'
            if (!result) {
                addMessageToChat('agent', `❌ Erro: A resposta da análise está mal formatada.`, 'error');
                return;
            }
            
            let html = `<strong>Análise da Estrutura:</strong><p>${result.analysis}</p>`;
            if (result.suggestions && result.suggestions.length > 0) {
                html += '<strong>Sugestões de Reorganização:</strong><ul>';
                result.suggestions.forEach(s => {
                    html += `<li>Mover <code>${s.from}</code> para uma nova categoria: <strong>${s.to_category}</strong></li>`;
                });
                html += '</ul>';
            } else {
                html += '<p>Nenhuma sugestão de reorganização necessária.</p>';
            }
            html += '<strong>Estrutura Analisada:</strong><pre style="background-color: #2a2a2a; padding: 10px; border-radius: 5px; white-space: pre-wrap; word-wrap: break-word;">' + tree + '</pre>';
            addMessageToChat('agent', { message: '✅ Análise Experimental Concluída', data: html }, 'info', 'html');
        } else if (data.type === 'plan_result') {
            displayPlanForApproval(data.data);
        } else if (data.type === 'error') {
            addMessageToChat('agent', `❌ Erro: ${data.message}`, 'error'); 
        } else if (data.data && data.data.summary) { // Resposta do organize padrão
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
             addMessageToChat('agent', { message: '✅ Operação concluída!', data: data.data });
        }
    };

    actionSelect.addEventListener('change', () => {
        const selectedAction = actionSelect.value;
        organizeInputs.classList.toggle('hidden', selectedAction !== 'organize');
        organizeExperimentalInputs.classList.toggle('hidden', selectedAction !== 'organize_experimental'); 
        indexInputs.classList.toggle('hidden', selectedAction !== 'index');
        queryInputs.classList.toggle('hidden', selectedAction !== 'query');
        watchInputs.classList.toggle('hidden', selectedAction !== 'start_watching');
        maintenanceInputs.classList.toggle('hidden', selectedAction !== 'maintenance');
        
        let buttonText = 'Executar';
        if (selectedAction === 'query') buttonText = 'Perguntar';
        if (selectedAction === 'start_watching') buttonText = 'Iniciar Monitoramento';
        if (selectedAction === 'maintenance') buttonText = 'Executar Manutenção';
        if (selectedAction === 'organize_experimental') buttonText = 'Analisar Estrutura'; 
        submitButton.textContent = buttonText;
    });

    const formInputs = document.querySelectorAll('#form input, #form select, #form button');
    function setFormEnabled(enabled) {
        formInputs.forEach(input => input.disabled = !enabled);
        submitButton.style.cursor = enabled ? 'pointer' : 'not-allowed';
        submitButton.style.backgroundColor = enabled ? '#007bff' : '#555';
    }

    form.addEventListener('submit', function(event) {
        event.preventDefault();
        setFormEnabled(false);
        const action = actionSelect.value;
        let payload = { action };
        let userMessage = '';

        if (action === 'organize') {
            payload.directory = dirInputOrganize.value;
            payload.goal = goalInput.value;
            payload.dry_run = dryRunCheckbox.checked;
            if (!payload.directory || !payload.goal) {
                alert('Por favor, preencha o caminho do diretório e o objetivo.');
                setFormEnabled(true); return;
            }
            userMessage = `${payload.dry_run ? 'Simular Organização' : 'Organizar'}: "${payload.directory}"\nObjetivo: "${payload.goal}"`;
        } else if (action === 'organize_experimental') { 
            payload.directory = dirInputOrganizeExperimental.value;
            if (!payload.directory) {
                alert('Por favor, preencha o caminho do diretório para analisar.');
                setFormEnabled(true); return;
            }
            userMessage = `Análise Experimental em: "${payload.directory}"`;
        } else if (action === 'index') {
            payload.directory = dirInputIndex.value;
            if (!payload.directory) {
                alert('Por favor, preencha o caminho do diretório.');
                setFormEnabled(true); return;
            }
            userMessage = `Indexar diretório: "${payload.directory}"`;
        } else if (action === 'query') {
            payload.query = queryInput.value;
            if (!payload.query) {
                alert('Por favor, insira sua pergunta.');
                setFormEnabled(true); return;
            }
            userMessage = `Consultar: "${payload.query}"`;
        } else if (action === 'start_watching') {
            payload.directory = dirInputWatch.value;
            if (!payload.directory) {
                alert('Por favor, preencha o caminho do diretório para monitorar.');
                setFormEnabled(true); return;
            }
            userMessage = `Iniciar monitoramento em: "${payload.directory}"`;
        } else if (action === 'maintenance') {
            payload.sub_action = maintenanceActionSelect.value;
            payload.directory = dirInputMaintenance.value;
            if (!payload.directory) {
                alert('Por favor, preencha o caminho do diretório para a manutenção.');
                setFormEnabled(true); return;
            }
            userMessage = `Manutenção: ${maintenanceActionSelect.options[maintenanceActionSelect.selectedIndex].text} em "${payload.directory}"`;
        }
        
        ws.send(JSON.stringify(payload));
        addMessageToChat('user', userMessage);
    });

    addMessageToChat('agent', 'Olá! Sou seu agente de arquivos. Escolha uma ação, preencha os campos e clique para começar.');

    actionSelect.dispatchEvent(new Event('change'));

    // --- RESTAURAÇÃO DE CHECKPOINTS ---
    const restoreBtn = document.getElementById('restore-btn');
    const restoreModal = document.getElementById('restore-modal');
    const closeRestoreModal = document.getElementById('close-restore-modal');
    const checkpointList = document.getElementById('checkpoint-list');

    restoreBtn.addEventListener('click', async () => {
        const dir = dirInputOrganize.value;
        if (!dir) {
            alert('Preencha o caminho do diretório para ver os checkpoints.');
            return;
        }
        
        // Mostrar modal e indicar carregamento
        restoreModal.classList.remove('hidden');
        checkpointList.innerHTML = '<div style="text-align: center; padding: 20px; color: #f9ca24;">🔄 Carregando checkpoints...</div>';
        
        try {
            const resp = await fetch('/api/checkpoints/list', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ directory: dir })
            });
            
            const data = await resp.json();
            
            if (data.status === 'success' && data.checkpoints && data.checkpoints.length > 0) {
                checkpointList.innerHTML = data.checkpoints.map(cp =>
                    `<div style='margin-bottom: 12px; padding: 10px; background: #181818; border-radius: 4px;'>
                        <div><b>Commit:</b> <code>${cp.hash.slice(0,8)}</code></div>
                        <div><b>Data:</b> ${new Date(cp.date).toLocaleString()}</div>
                        <div><b>Mensagem:</b> ${cp.msg}</div>
                        <button class='restore-checkpoint-btn' data-hash='${cp.hash}' style='margin-top: 8px; background: #f9ca24; color: #222; border: none; padding: 6px 14px; border-radius: 4px; cursor: pointer;'>Restaurar</button>
                    </div>`
                ).join('');
                
                // Adicionar event listeners aos botões de restaurar
                document.querySelectorAll('.restore-checkpoint-btn').forEach(btn => {
                    btn.addEventListener('click', async (e) => {
                        if (!confirm('Tem certeza que deseja restaurar este checkpoint? Isso irá sobrescrever os arquivos atuais.')) return;
                        
                        const hash = btn.getAttribute('data-hash');
                        btn.disabled = true;
                        btn.textContent = 'Restaurando...';
                        
                        try {
                            const resp = await fetch(`/api/checkpoints/restore/${hash}`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ directory: dir })
                            });
                            const result = await resp.json();
                            
                            if (result.status === 'success') {
                                alert('Checkpoint restaurado com sucesso!');
                                restoreModal.classList.add('hidden');
                            } else {
                                alert('Erro ao restaurar checkpoint: ' + (result.message || 'Erro desconhecido'));
                                btn.disabled = false;
                                btn.textContent = 'Restaurar';
                            }
                        } catch (err) {
                            console.error('Erro ao restaurar checkpoint:', err);
                            alert('Erro ao restaurar checkpoint: ' + err.message);
                            btn.disabled = false;
                            btn.textContent = 'Restaurar';
                        }
                    });
                });
            } else {
                checkpointList.innerHTML = `
                    <div style="text-align: center; padding: 20px; color: #f9ca24;">
                        📁 Nenhum checkpoint encontrado para este diretório.
                        <br><br>
                        <small style="color: #888;">Os checkpoints são criados automaticamente quando você organiza arquivos.</small>
                    </div>
                `;
            }
        } catch (err) {
            console.error('Erro ao buscar checkpoints:', err);
            checkpointList.innerHTML = `
                <div style="text-align: center; padding: 20px; color: #ff6b6b;">
                    ❌ Erro ao buscar checkpoints: ${err.message}
                    <br><br>
                    <button onclick="location.reload()" style="background: #333; color: #fff; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">Tentar Novamente</button>
                </div>
            `;
        }
    });
    
    // Fechar modal quando clicar no botão fechar
    closeRestoreModal.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        restoreModal.classList.add('hidden');
        checkpointList.innerHTML = 'Carregando...';
    });
    
    // Fechar modal quando clicar fora dele
    restoreModal.addEventListener('click', (e) => {
        if (e.target === restoreModal) {
            restoreModal.classList.add('hidden');
            checkpointList.innerHTML = 'Carregando...';
        }
    });
    
    // Fechar modal com ESC
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !restoreModal.classList.contains('hidden')) {
            restoreModal.classList.add('hidden');
            checkpointList.innerHTML = 'Carregando...';
        }
    });
});