document.addEventListener('DOMContentLoaded', function() {
    const ws = new WebSocket(`ws://${window.location.host}/ws`);
    const chat = document.getElementById('chat');
    const form = document.getElementById('action-form');
    const actionSelect = document.getElementById('action');
    const dirInput = document.getElementById('dir_input');
    const queryInput = document.getElementById('query_input');
    const organizeExperimentalInputs = document.getElementById('organize_experimental_inputs');
    const dirInputOrganizeExperimental = document.getElementById('dir_input_organize_experimental');

    // Show/hide inputs based on selected action
    actionSelect.addEventListener('change', () => {
        const selectedAction = actionSelect.value;
        document.getElementById('organize_inputs').classList.toggle('hidden', selectedAction !== 'organize');
        document.getElementById('query_inputs').classList.toggle('hidden', selectedAction !== 'query');
        organizeExperimentalInputs.classList.toggle('hidden', selectedAction !== 'organize_experimental');
    });

    // Handle form submission
    form.addEventListener('submit', function(event) {
        event.preventDefault();
        setFormEnabled(false);

        const action = actionSelect.value;
        let payload = { action };
        let userMessage = '';

        if (action === 'organize') {
            payload.directory = dirInput.value;
            if (!payload.directory) {
                alert('Por favor, preencha o caminho do diretório.');
                setFormEnabled(true);
                return;
            }
            userMessage = `Organizando: "${payload.directory}"`;
        } else if (action === 'query') {
            payload.query = queryInput.value;
            if (!payload.query) {
                alert('Por favor, preencha sua consulta.');
                setFormEnabled(true);
                return;
            }
            userMessage = `Consultando: "${payload.query}"`;
        } else if (action === 'organize_experimental') {
            payload.directory = dirInputOrganizeExperimental.value;
            if (!payload.directory) {
                alert('Por favor, preencha o caminho do diretório.');
                setFormEnabled(true);
                return;
            }
            userMessage = `Análise Experimental em: "${payload.directory}"`;
        }

        addMessageToChat('user', { message: userMessage }, 'info');
        ws.send(JSON.stringify(payload));
    });

    // Handle WebSocket messages
    ws.onmessage = function(event) {
        const data = JSON.parse(event.data);

        if (data.type === 'log') {
            addMessageToChat('agent', { message: data.message }, data.level);
        } else if (data.type === 'plan_result') {
            // ... existing plan result handling
        } else if (data.type === 'query_result') {
            // ... existing query result handling
        } else if (data.type === 'experimental_result') {
            const result = data.data.result;
            const tree = data.data.tree;
            
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
        }
    };

    function setFormEnabled(enabled) {
        Array.from(form.elements).forEach(element => {
            element.disabled = !enabled;
        });
    }

    function addMessageToChat(sender, content, level = 'info', contentType = 'text') {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender} ${level}`;
        
        if (contentType === 'html') {
            messageDiv.innerHTML = `<strong>${content.message}</strong><br>${content.data}`;
        } else {
            messageDiv.textContent = content.message;
        }
        
        chat.appendChild(messageDiv);
        chat.scrollTop = chat.scrollHeight;
    }
});
