const VERSION = '3.15';
        const endpoints = [
            {
                method: 'GET',
                path: '/status',
                description: 'Retorna o status da API e o total de registros carregados.',
                sample: '{\\n  "message": "API de Busca de Clientes Ativa",\\n  "total_registros": 42860\\n}',
                action: { type: 'request', label: 'Testar', endpoint: '/status', responseId: 'r-status' }
            },
            {
                method: 'GET',
                path: '/config/status',
                description: 'Mostra se tokens, painel, cache e arquivos principais estao configurados.',
                sample: '{\\n  "tokens": { "painel_best": true, "maxplayer_panel": true }\\n}',
                action: { type: 'request', label: 'Ver configuracao', endpoint: '/config/status', responseId: 'r-config-status' }
            },
            {
                method: 'GET',
                path: '/historico/acoes',
                description: 'Lista as ultimas acoes sensiveis executadas pelo painel.',
                sample: 'Retorna criacoes e trocas de dominio do MaxPlayer com dados sensiveis mascarados.',
                action: { type: 'request', label: 'Ver historico', endpoint: '/historico/acoes', responseId: 'r-action-history' }
            },
            {
                method: 'POST',
                path: '/buscar',
                description: 'Busca um cliente em todas as colunas pelo termo informado.',
                sample: 'Body: { "termo": "+5551999999999" }\\n\\nRetorna o primeiro cliente encontrado.',
                field: { id: 'buscarTermo', label: 'Termo de busca', placeholder: 'Telefone, nome ou ID' },
                action: { type: 'postTerm', label: 'Buscar', endpoint: '/buscar', inputId: 'buscarTermo', responseId: 'r-buscar' }
            },
            {
                method: 'POST',
                path: '/filtrar',
                description: 'Retorna uma lista com todos os clientes encontrados. Bom para busca por data.',
                sample: 'Body: { "termo": "19/08/2025" }\\n\\nRetorna: [ { ... }, { ... } ]',
                field: { id: 'filtrarTermo', label: 'Filtro', placeholder: 'Data, nome, telefone ou termo' },
                action: { type: 'postTerm', label: 'Filtrar', endpoint: '/filtrar', inputId: 'filtrarTermo', responseId: 'r-filtrar' }
            },
            {
                method: 'POST',
                path: '/cliente/consulta',
                description: 'Consulta revendas, link de pagamento, linhas e MaxPlayer em uma unica pesquisa.',
                sample: 'Body: { "termo": "5521999999999" }\\n\\nRetorna: revenda, linha e maxplayer.',
                field: { id: 'consultaUnificadaTermo', label: 'Termo', placeholder: 'Telefone, usuario, ID ou email' },
                action: { type: 'postTerm', label: 'Consultar tudo', endpoint: '/cliente/consulta', inputId: 'consultaUnificadaTermo', responseId: 'r-consulta-unificada' }
            },
            {
                method: 'GET',
                path: '/reload',
                description: 'Recarrega os dados do Excel sem reiniciar o servidor.',
                sample: '{\\n  "message": "Dados recarregados.",\\n  "total_registros": 42860\\n}',
                action: { type: 'request', label: 'Recarregar', endpoint: '/reload', responseId: 'r-reload' }
            },
            {
                method: 'POST',
                path: '/atualizar',
                description: 'Executa o script update_all_revendas.py para atualizar todos os dados.',
                sample: '{\\n  "message": "Atualizacao iniciada em segundo plano",\\n  "status_url": "/atualizar/status"\\n}',
                action: { type: 'update', label: 'Atualizar dados', responseId: 'r-atualizar' }
            },
            {
                method: 'GET',
                path: '/atualizar/status',
                description: 'Consulta o andamento da atualizacao em segundo plano.',
                sample: '{\\n  "running": false,\\n  "status": "success",\\n  "message": "Atualizado com sucesso"\\n}',
                action: { type: 'request', label: 'Ver status', endpoint: '/atualizar/status', responseId: 'r-atualizar-status' }
            },
            {
                method: 'GET',
                path: '/revenda/adicionar',
                description: 'Mostra a documentacao para adicionar uma nova revenda.',
                sample: 'Retorna instrucoes de uso do POST /revenda/adicionar.',
                action: { type: 'request', label: 'Ver instrucoes', endpoint: '/revenda/adicionar', responseId: 'r-add-doc' }
            },
            {
                method: 'POST',
                path: '/revenda/adicionar',
                description: 'Adiciona uma nova revenda ao arquivo de logins.',
                sample: 'Body: {\\n  "nome": "Revenda XYZ",\\n  "email": "revenda@email.com",\\n  "password": "senha123",\\n  "filename": "opcional.json"\\n}',
                action: { type: 'manual', label: 'Usar via API', responseId: 'r-add' }
            },
            {
                method: 'POST',
                path: '/ (alias)',
                description: 'Alias para /buscar. Busca cliente pelo termo enviado.',
                sample: 'Body: { "termo": "valor" }\\n\\nRetorna o cliente encontrado.',
                field: { id: 'aliasTermo', label: 'Termo', placeholder: 'Digite o termo de busca' },
                action: { type: 'postTerm', label: 'Testar alias', endpoint: '/', inputId: 'aliasTermo', responseId: 'r-alias' }
            },
            {
                method: 'GET',
                path: '/consultar-linha/{telefone}',
                description: 'Consulta API externa de linhas pelo numero de telefone.',
                sample: 'Exemplo: /consultar-linha/5511999999999\\n\\nRetorna dados da linha na API externa.',
                field: { id: 'linhaTelefone', label: 'Telefone', placeholder: 'Telefone com DDD' },
                action: { type: 'phone', label: 'Consultar linha', inputId: 'linhaTelefone', responseId: 'r-linha' }
            },
            {
                method: 'POST',
                path: '/maxplayer/usuario',
                description: 'Pesquisa se um usuario existe na base do MaxPlayer.',
                sample: 'Body: { "termo": "5521999999999" }\\n\\nBusca por usuario, ID, email ou usuario IPTV vinculado.',
                field: { id: 'maxplayerUsuario', label: 'Usuario MaxPlayer', placeholder: 'Usuario, telefone, ID ou email' },
                action: { type: 'postTerm', label: 'Pesquisar MaxPlayer', endpoint: '/maxplayer/usuario', inputId: 'maxplayerUsuario', responseId: 'r-maxplayer' }
            },
            {
                method: 'POST',
                path: '/maxplayer/usuario/prevalidar',
                description: 'Valida se ha dados suficientes para criar um usuario MaxPlayer.',
                sample: 'Body: { "termo": "5521999999999" }\\n\\nRetorna se pode criar e quais dados serao usados.',
                field: { id: 'prevalidarMaxplayer', label: 'Termo', placeholder: 'Telefone ou usuario' },
                action: { type: 'postTerm', label: 'Prevalidar', endpoint: '/maxplayer/usuario/prevalidar', inputId: 'prevalidarMaxplayer', responseId: 'r-max-prevalidar' }
            },
            {
                method: 'GET',
                path: '/maxplayer/domains',
                description: 'Lista os dominios configurados no MaxPlayer.',
                sample: 'Retorna: { "domains": [ { "id": "...", "domain": "..." } ] }',
                action: { type: 'request', label: 'Listar dominios', endpoint: '/maxplayer/domains', responseId: 'r-max-domains' }
            },
            {
                method: 'POST',
                path: '/maxplayer-free/usuario',
                description: 'Pesquisa se um usuario existe no MaxPlayer Free.',
                sample: 'Body: { "termo": "5521999999999" }\\n\\nBusca por usuario, line_id, senha ou dominio.',
                field: { id: 'maxplayerFreeUsuario', label: 'Usuario MaxPlayer Free', placeholder: 'Usuario, telefone ou line_id' },
                action: { type: 'postTerm', label: 'Pesquisar Free', endpoint: '/maxplayer-free/usuario', inputId: 'maxplayerFreeUsuario', responseId: 'r-maxplayer-free' }
            },
            {
                method: 'GET',
                path: '/maxplayer-free/domains',
                description: 'Lista os dominios disponiveis do MaxPlayer Free.',
                sample: 'Retorna: [ { "id": "...", "label": "ROTA PRINCIPAL" } ]',
                action: { type: 'request', label: 'Listar dominios Free', endpoint: '/maxplayer-free/domains', responseId: 'r-max-free-domains' }
            },
            {
                method: 'POST',
                path: '/maxplayer-free/usuario/criar',
                description: 'Cria um usuario no MaxPlayer Free usando line_id e dominio.',
                sample: 'Body: { "line_id": 123, "domain_id": "..." }',
                action: { type: 'manual', label: 'Usar pela busca', responseId: 'r-max-free-create' }
            },
            {
                method: 'POST',
                path: '/maxplayer/lista/dominio',
                description: 'Troca o dominio de uma lista MaxPlayer.',
                sample: 'Body: { "list_id": "...", "domain_id": "...", "new_list_name": "List 1", "iptv_username": "...", "iptv_password": "..." }',
                action: { type: 'manual', label: 'Usar pela busca', responseId: 'r-max-edit-domain' }
            },
            {
                method: 'GET',
                path: '/revenda/listar',
                description: 'Lista todas as revendas cadastradas com total de clientes.',
                sample: '{\\n  "total": 5,\\n  "revendas": [\\n    { "nome": "...", "email": "...", "total_clientes": 150 }\\n  ]\\n}',
                action: { type: 'request', label: 'Listar revendas', endpoint: '/revenda/listar', responseId: 'r-listar' }
            },
            {
                method: 'DELETE',
                path: '/revenda/excluir',
                description: 'Exclui uma revenda pelo email e remove o arquivo JSON relacionado.',
                sample: 'Body: { "email": "revenda@email.com" }\\n\\nAtencao: esta acao nao pode ser desfeita.',
                field: { id: 'deleteEmail', label: 'Email da revenda', placeholder: 'revenda@email.com', type: 'email' },
                action: { type: 'delete', label: 'Excluir revenda', inputId: 'deleteEmail', responseId: 'r-delete' }
            }
        ];

        let activeFilter = 'all';
        let updateTimer = null;
        let lastUnifiedData = null;
        let pendingMessageType = '';
        let maxplayerDomains = [];
        let maxplayerFreeDomains = [];

        const endpointList = document.getElementById('endpointList');
        const emptyState = document.getElementById('emptyState');
        const searchInput = document.getElementById('searchInput');

        function escapeHtml(value) {
            return String(value)
                .replaceAll('&', '&amp;')
                .replaceAll('<', '&lt;')
                .replaceAll('>', '&gt;')
                .replaceAll('"', '&quot;')
                .replaceAll("'", '&#039;');
        }

        function setResponse(id, state, message) {
            const el = document.getElementById(id);
            if (!el) return;
            el.className = 'response show ' + state;
            el.textContent = message;
        }

        async function requestJson(endpoint, options = {}) {
            const separator = endpoint.includes('?') ? '&' : '?';
            const response = await fetch(endpoint + separator + 'v=' + VERSION, {
                cache: 'no-store',
                credentials: 'same-origin',
                ...options
            });
            const text = await response.text();
            let data;
            try {
                data = text ? JSON.parse(text) : {};
            } catch (error) {
                data = { detail: text || 'Resposta vazia da API.' };
            }
            if (!response.ok) {
                throw new Error(JSON.stringify(data, null, 2));
            }
            return data;
        }

        function pretty(data) {
            return JSON.stringify(data, null, 2);
        }

        function normalizeStatus(status) {
            if (status === 'sucesso') return { label: 'Encontrado', className: 'ok' };
            if (status === 'erro') return { label: 'Erro', className: 'err' };
            if (status === 'ignorado') return { label: 'Ignorado', className: 'warn' };
            return { label: 'Nao encontrado', className: 'warn' };
        }

        function emptyValue(value) {
            return value === undefined || value === null || value === '' ? 'N/A' : value;
        }

        function formatTrialValue(value) {
            const normalized = String(value || '').toLowerCase();
            return normalized.includes('sim') ? 'Teste' : 'Cliente';
        }

        function copyIcon(label = 'Copiar link') {
            return `
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                    stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <rect width="14" height="14" x="8" y="8" rx="2"></rect>
                    <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"></path>
                </svg>
                <span class="sr-only">${escapeHtml(label)}</span>`;
        }

        function checkIcon() {
            return `
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"
                    stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <path d="M20 6 9 17l-5-5"></path>
                </svg>
                <span class="sr-only">Copiado</span>`;
        }

        async function copyText(value) {
            if (navigator.clipboard && window.isSecureContext) {
                await navigator.clipboard.writeText(value);
                return;
            }

            const area = document.createElement('textarea');
            area.value = value;
            area.setAttribute('readonly', '');
            area.style.position = 'fixed';
            area.style.left = '-9999px';
            area.style.top = '0';
            document.body.appendChild(area);
            area.focus();
            area.select();
            const ok = document.execCommand('copy');
            area.remove();
            if (!ok) {
                throw new Error('copy_failed');
            }
        }

        function registeredPhone(value) {
            const text = emptyValue(value);
            if (text === 'N/A') return text;
            return String(text).split('@')[0];
        }

        function formatValidUntil(value) {
            const text = emptyValue(value);
            if (text === 'N/A') return text;
            if (text.includes(' as ')) return text.replace(' as ', ' às ');
            if (text.includes(' às ')) return text;

            const date = new Date(text);
            if (!Number.isNaN(date.getTime())) {
                const day = date.toLocaleDateString('pt-BR');
                const hour = date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
                return `${day} às ${hour}`;
            }

            return text;
        }

        function formatDisplayDate(value) {
            const text = emptyValue(value);
            if (text === 'N/A') return text;

            if (/^\d{10}$/.test(text)) {
                return new Date(Number(text) * 1000).toLocaleDateString('pt-BR');
            }

            if (/^\d{13}$/.test(text)) {
                return new Date(Number(text)).toLocaleDateString('pt-BR');
            }

            return text;
        }

        function buildAccessMessage(data) {
            return [
                'AQUI ESTÃO SEUS DADOS DE ACESSO 📺',
                `👤 Usuário: ${emptyValue(data.usuario)}`,
                `🔑 Senha: ${emptyValue(data.senha)}`,
                `🖥️ Número de telas: ${emptyValue(data.telas || 1)}`,
                `📱 Telefone cadastrado: ${registeredPhone(data.telefone || data.usuario)}`,
                '',
                `📅 Válido até: ${formatValidUntil(data.vencimento)}`
            ].join('\n');
        }

        function expirationLine(dateValue, daysValue) {
            const days = Number(daysValue);
            if (!Number.isNaN(days)) {
                if (days <= 0) return 'Ja esta expirado.';
                if (days === 1) return 'Falta 1 dia para expirar.';
                return `Faltam ${days} dias para expirar.`;
            }

            const text = emptyValue(dateValue);
            if (text === 'N/A') return '';
            const match = text.match(/^(\d{2})\/(\d{2})\/(\d{4})/);
            if (!match) return '';

            const target = new Date(Number(match[3]), Number(match[2]) - 1, Number(match[1]));
            const today = new Date();
            target.setHours(0, 0, 0, 0);
            today.setHours(0, 0, 0, 0);
            const diff = Math.ceil((target - today) / 86400000);
            if (diff <= 0) return 'Ja esta expirado.';
            if (diff === 1) return 'Falta 1 dia para expirar.';
            return `Faltam ${diff} dias para expirar.`;
        }

        function clientName(data) {
            const detalhe = data.linha?.linha || {};
            const revenda = data.revenda || {};
            return usefulValue(revenda.nome, detalhe.usuario, data.termo_buscado, 'cliente');
        }

        function paymentMessage(data) {
            const revenda = data.revenda || {};
            const detalhe = data.linha?.linha || {};
            const vencimento = formatDisplayDate(revenda.data_expiracao);
            return [
                `Oi, ${clientName(data)}`,
                '',
                `Seu plano ${emptyValue(revenda.plano)}`,
                `com vencimento ${emptyValue(vencimento)}`,
                expirationLine(vencimento),
                '',
                'Caso queira efetuar o pagamento, esse e o link:',
                emptyValue(revenda.Link)
            ].filter((line) => line !== '').join('\n');
        }

        function theBestMessage(data) {
            const detalhe = data.linha?.linha || {};
            return [
                `Oi, ${clientName(data)}`,
                '',
                'Seguem seus dados de acesso:',
                `Usuario: ${emptyValue(detalhe.usuario)}`,
                `Senha: ${emptyValue(detalhe.senha)}`,
                `Telas: ${emptyValue(detalhe.telas || 1)}`,
                `Vencimento: ${emptyValue(detalhe.vencimento)}`,
                expirationLine(detalhe.vencimento, detalhe.dias_restantes)
            ].filter((line) => line !== '').join('\n');
        }

        function maxplayerMessage(data) {
            const maxplayer = data.maxplayer || {};
            const user = (maxplayer.usuarios || [])[0] || {};
            const list = (user.listas || [])[0] || {};
            const iptv = list.iptv || {};
            const vencimento = user.vencimento || list.vencimento || data.linha?.linha?.vencimento || '';
            return [
                `Oi, ${clientName(data)}`,
                '',
                'Seguem seus dados do MaxPlayer:',
                `Usuario: ${emptyValue(iptv.usuario || user.usuario)}`,
                `Senha: ${emptyValue(iptv.senha)}`,
                `Dominio: ${emptyValue(iptv.fqdn)}`,
                `Porta: ${emptyValue(iptv.porta)}`,
                `Vencimento: ${emptyValue(vencimento)}`,
                expirationLine(vencimento, data.linha?.linha?.dias_restantes)
            ].filter((line) => line !== '').join('\n');
        }

        function maxplayerFreeMessage(data) {
            const maxplayerFree = data.maxplayer_free || {};
            const user = (maxplayerFree.usuarios || [])[0] || {};
            const freeLine = (data.maxplayer_free_linhas?.linhas || [])[0] || {};
            const source = user.usuario ? user : freeLine;
            return [
                `Oi, ${clientName(data)}`,
                '',
                'Seguem seus dados do MaxPlayer Free:',
                `Usuario: ${emptyValue(source.usuario)}`,
                `Senha: ${emptyValue(source.senha)}`,
                `Dominio: ${emptyValue(source.dominio)}`,
                `Vencimento: ${emptyValue(source.vencimento)}`,
                expirationLine(source.vencimento)
            ].filter((line) => line !== '').join('\n');
        }

        function buildClientMessage(type, data) {
            if (type === 'payment') return paymentMessage(data);
            if (type === 'maxplayer') return maxplayerMessage(data);
            if (type === 'maxplayer-free') return maxplayerFreeMessage(data);
            return theBestMessage(data);
        }

        function buildBotConversaPayload(data, mensagem, tipo) {
            const detalhe = data.linha?.linha || {};
            const revenda = data.revenda || {};

            return {
                mensagem,
                dados: {
                    tipo_mensagem: tipo || '',
                    termo: data.termo_buscado || '',
                    cliente: revenda.nome || detalhe.usuario || '',
                    telefone: detalhe.telefone || revenda.telefone || data.telefone_normalizado || '',
                    usuario: detalhe.usuario || '',
                    senha: detalhe.senha || '',
                    telas: detalhe.telas || 1,
                    vencimento: detalhe.vencimento || '',
                    vencimento_completo: detalhe.vencimento_completo || '',
                    status_the_best: detalhe.status_interno || detalhe.status_conta || '',
                    revenda_the_best: detalhe.revenda || '',
                    link_pagamento: revenda.Link || '',
                    m3u: detalhe.url_m3u || '',
                    m3u_plus: detalhe.url_m3u_plus || ''
                }
            };
        }

        function renderDataValue(row) {
            const value = emptyValue(row[1]);
            if (row[2] === 'copy-button' && row[1] && row[1] !== 'N/A') {
                return `
                    <button class="btn secondary copy-action-btn" type="button" data-copy-value="${escapeHtml(row[1])}">
                        Copiar ${escapeHtml(row[0])}
                    </button>`;
            }

            if (row[2] === 'link' && row[1] && row[1] !== 'nao_encontrado') {
                return `
                    <div class="link-actions">
                        <a class="value-link" href="${escapeHtml(row[1])}" target="_blank" rel="noopener">Abrir link</a>
                        <button class="copy-link" type="button" data-copy-value="${escapeHtml(row[1])}" title="Copiar link" aria-label="Copiar link">${copyIcon()}</button>
                    </div>`;
            }

            if (row[2] === 'copy' && row[1] && row[1] !== 'N/A') {
                return `
                    <div class="copy-value">
                        <span>${escapeHtml(value)}</span>
                        <button class="copy-link" type="button" data-copy-value="${escapeHtml(row[1])}" title="Copiar ${escapeHtml(row[0])}" aria-label="Copiar ${escapeHtml(row[0])}">${copyIcon('Copiar ' + row[0])}</button>
                    </div>`;
            }

            return escapeHtml(value);
        }

        function dataRows(rows) {
            return `
                <div class="data-grid">
                    ${rows.map((row) => `
                        <div class="data-row">
                            <div class="data-label">${escapeHtml(row[0])}</div>
                            <div class="data-value">${renderDataValue(row)}</div>
                        </div>
                    `).join('')}
                </div>`;
        }

        function accessSelectButton(message) {
            if (!message) return '';
            return `
                <button class="btn secondary select-data-btn" type="button" data-copy-value="${escapeHtml(message)}">
                    Selecionar dados
                </button>`;
        }

        function sendClientButton(type) {
            return `
                <button class="btn secondary send-client-btn" type="button" data-open-message-modal="${escapeHtml(type)}">
                    Enviar para cliente
                </button>`;
        }

        function renderResultCard(targetId, title, status, rows, emptyMessage, rawData) {
            const target = document.getElementById(targetId);
            const badge = normalizeStatus(status);
            const rawId = targetId + '-raw';
            target.innerHTML = `
                <div class="result-head">
                    <h3 class="result-title">${escapeHtml(title)}</h3>
                    <span class="badge ${badge.className}">${escapeHtml(badge.label)}</span>
                </div>
                ${rows.length ? dataRows(rows) : `<p class="empty-result">${escapeHtml(emptyMessage)}</p>`}
                <button class="raw-toggle" type="button" data-raw-target="${rawId}">Ver JSON</button>
                <pre class="raw-output" id="${rawId}">${escapeHtml(pretty(rawData))}</pre>
            `;
        }

        function statusPill(label, state) {
            return `<span class="summary-pill ${state}">${escapeHtml(label)}</span>`;
        }

        function foundStatus(value) {
            return value === 'sucesso';
        }

        function usefulValue(...values) {
            for (const value of values) {
                const text = emptyValue(value);
                if (text !== 'N/A' && text !== 'nao_encontrado' && text !== 'não encontrado') {
                    return text;
                }
            }
            return 'Cliente';
        }

        function buildSummary(data) {
            const revenda = data.revenda || {};
            const linha = data.linha || {};
            const detalhe = linha.linha || {};
            const maxplayer = data.maxplayer || {};
            const lineOk = foundStatus(linha.status);
            const paymentOk = foundStatus(revenda.status);
            const maxOk = foundStatus(maxplayer.status);
            const cliente = usefulValue(revenda.nome, detalhe.usuario, data.termo_buscado);
            const usuario = usefulValue(detalhe.usuario, data.termo_buscado);
            const vencimento = usefulValue(detalhe.vencimento, formatDisplayDate(revenda.data_expiracao), 'N/A');
            const statusLinha = usefulValue(detalhe.status_interno, detalhe.status_conta, 'N/A');
            const headline = lineOk
                ? `${cliente} | Usuario: ${usuario} | Vencimento: ${vencimento} | The Best: ${statusLinha}`
                : `${cliente} | The Best nao encontrado`;

            const alerts = [];
            const days = Number(detalhe.dias_restantes);
            if (lineOk && (detalhe.status_interno === 'expired' || days <= 0)) {
                alerts.push(statusPill('Vence hoje ou ja venceu', 'warn'));
            }
            if (paymentOk && lineOk && revenda.telefone && detalhe.telefone && registeredPhone(revenda.telefone) !== registeredPhone(detalhe.telefone)) {
                alerts.push(statusPill('Telefones diferentes', 'warn'));
            }
            if (paymentOk && !lineOk) alerts.push(statusPill('Tem pagamento, sem The Best', 'warn'));
            if (lineOk && !maxOk) alerts.push(statusPill('Tem The Best, sem MaxPlayer', 'warn'));

            return `
                <p class="summary-line">${escapeHtml(headline)}</p>
                <div class="summary-statuses">
                    ${statusPill(`The Best: ${lineOk ? 'encontrado' : 'nao encontrado'}`, lineOk ? 'ok' : 'warn')}
                    ${statusPill(`Pagamentos: ${paymentOk ? 'encontrado' : 'nao encontrado'}`, paymentOk ? 'ok' : 'warn')}
                    ${statusPill(`MaxPlayer: ${maxOk ? 'encontrado' : 'nao encontrado'}`, maxOk ? 'ok' : 'warn')}
                </div>
                ${alerts.length ? `<div class="summary-alerts">${alerts.join('')}</div>` : ''}
            `;
        }

        function renderSummary(data) {
            const summary = document.getElementById('clientSummary');
            summary.innerHTML = buildSummary(data);
            summary.hidden = false;
        }

        function shouldShowMaxplayerFree(data) {
            const revenda = String(data?.linha?.linha?.revenda || '').trim().toLowerCase();
            return revenda === 'tdscr7milgols';
        }

        function domainOptions(selectedId = '') {
            if (!maxplayerDomains.length) {
                return '<option value="">Carregando dominios...</option>';
            }

            return [
                '<option value="">Selecione um dominio</option>',
                ...maxplayerDomains.map((domain) => {
                    const label = `${domain.domain}${domain.label ? ' - ' + domain.label : ''} (${domain.https ? 'HTTPS' : 'HTTP'}:${domain.port || '80'})`;
                    const selected = String(domain.id) === String(selectedId) ? ' selected' : '';
                    return `<option value="${escapeHtml(domain.id)}"${selected}>${escapeHtml(label)}</option>`;
                })
            ].join('');
        }

        function freeDomainOptions(selectedId = '') {
            if (!maxplayerFreeDomains.length) {
                return '<option value="">Carregando dominios Free...</option>';
            }

            return [
                '<option value="">Selecione um dominio Free</option>',
                ...maxplayerFreeDomains.map((domain) => {
                    const label = domain.label || domain.domain || domain.id;
                    const selected = String(domain.id) === String(selectedId) ? ' selected' : '';
                    return `<option value="${escapeHtml(domain.id)}"${selected}>${escapeHtml(label)}</option>`;
                })
            ].join('');
        }

        async function loadMaxplayerDomains() {
            try {
                const data = await requestJson('/maxplayer/domains');
                maxplayerDomains = data.domains || [];
                document.querySelectorAll('select[data-domain-select]').forEach((select) => {
                    const selected = select.dataset.selected || select.value;
                    select.innerHTML = domainOptions(selected);
                    select.value = selected;
                });
            } catch (error) {
                maxplayerDomains = [];
                document.querySelectorAll('select[data-domain-select]').forEach((select) => {
                    select.innerHTML = '<option value="">Erro ao carregar dominios</option>';
                });
            }
        }

        async function loadMaxplayerFreeDomains() {
            try {
                const data = await requestJson('/maxplayer-free/domains');
                maxplayerFreeDomains = data.domains || [];
                document.querySelectorAll('select[data-free-domain-select]').forEach((select) => {
                    const selected = select.dataset.selected || select.value;
                    select.innerHTML = freeDomainOptions(selected);
                    select.value = selected;
                });
            } catch (error) {
                maxplayerFreeDomains = [];
                document.querySelectorAll('select[data-free-domain-select]').forEach((select) => {
                    select.innerHTML = '<option value="">Erro ao carregar dominios Free</option>';
                });
            }
        }

        function maxplayerCreateForm(data) {
            const linha = data.linha?.linha || {};
            const termo = data.telefone_normalizado || data.termo_buscado || '';
            const iptvUser = linha.usuario && linha.usuario !== 'N/A' ? linha.usuario : termo;
            const iptvPass = linha.senha && linha.senha !== 'N/A' ? linha.senha : '';
            const disabled = iptvUser && iptvPass ? '' : ' disabled';
            const hint = iptvUser && iptvPass ? '' : '<p class="empty-result">Para criar, preciso encontrar usuario e senha na base de linhas.</p>';

            return `
                <div class="inline-form">
                    <label for="createMaxDomain">Dominio para criar</label>
                    <select id="createMaxDomain" data-domain-select>${domainOptions('')}</select>
                    <input id="createMaxUser" value="${escapeHtml(iptvUser)}" placeholder="Usuario IPTV">
                    <input id="createMaxPass" value="${escapeHtml(iptvPass)}" placeholder="Senha IPTV">
                    ${hint}
                    <button class="btn primary" type="button" data-create-maxplayer${disabled}>Criar no MaxPlayer</button>
                </div>`;
        }

        function maxplayerDomainForm(user) {
            const list = (user.listas || [])[0] || {};
            const iptv = list.iptv || {};
            if (!list.id || !iptv.usuario || !iptv.senha) {
                return '';
            }

            return `
                <div class="inline-form">
                    <label for="editMaxDomain">Trocar dominio</label>
                    <select id="editMaxDomain" data-domain-select data-selected="${escapeHtml(list.dominio_id || '')}">${domainOptions(list.dominio_id || '')}</select>
                    <button class="btn primary" type="button"
                        data-edit-max-domain
                        data-list-id="${escapeHtml(list.id)}"
                        data-list-name="${escapeHtml(list.nome || 'List 1')}"
                        data-iptv-user="${escapeHtml(iptv.usuario)}"
                        data-iptv-pass="${escapeHtml(iptv.senha)}">
                        Salvar dominio
                    </button>
                </div>`;
        }

        function maxplayerFreeCreateForm(data) {
            const freeLine = (data.maxplayer_free_linhas?.linhas || [])[0] || {};
            if (!freeLine.id) {
                return '<p class="empty-result">Para criar no Free, preciso encontrar a linha no Painel Apps.</p>';
            }

            return `
                <div class="inline-form">
                    <label for="createMaxFreeDomain">Dominio Free</label>
                    <select id="createMaxFreeDomain" data-free-domain-select>${freeDomainOptions('')}</select>
                    <div class="data-grid">
                        <div class="data-row">
                            <div class="data-label">Line ID</div>
                            <div class="data-value">${escapeHtml(freeLine.id)}</div>
                        </div>
                        <div class="data-row">
                            <div class="data-label">Linha</div>
                            <div class="data-value">${escapeHtml(freeLine.usuario || 'N/A')}</div>
                        </div>
                    </div>
                    <button class="btn primary" type="button" data-create-maxplayer-free data-line-id="${escapeHtml(freeLine.id)}">Criar no Free</button>
                </div>`;
        }

        function renderResellerResult(data) {
            const revenda = data.revenda || {};
            const rows = revenda.status === 'sucesso' ? [
                ['Cliente', revenda.nome],
                ['Telefone', revenda.telefone],
                ['Revenda', revenda.Revenda],
                ['Plano', revenda.plano],
                ['Vencimento', formatDisplayDate(revenda.data_expiracao)],
                ['ID cliente', revenda.Id_client],
                ['DT Row', revenda.DT_RowId],
                ['Pagamento', revenda.Link, 'link']
            ] : [];

            renderResultCard(
                'resellerResult',
                'Pagamentos',
                revenda.status,
                rows,
                revenda.mensagem || 'Nenhum cadastro encontrado na base das revendas.',
                revenda
            );

            if (revenda.status === 'sucesso') {
                document.getElementById('resellerResult').insertAdjacentHTML('beforeend', sendClientButton('payment'));
            }
        }

        function renderLineResult(data) {
            const linha = data.linha || {};
            const detalhe = linha.linha || {};
            const accessMessage = buildAccessMessage({
                usuario: detalhe.usuario,
                senha: detalhe.senha,
                telas: detalhe.telas || 1,
                telefone: detalhe.telefone || data.telefone_normalizado || detalhe.usuario,
                vencimento: detalhe.vencimento_completo || detalhe.vencimento
            });
            const rows = linha.status === 'sucesso' ? [
                ['ID linha', detalhe.id],
                ['Telefone', detalhe.telefone],
                ['Usuario', detalhe.usuario],
                ['Senha', detalhe.senha],
                ['Vencimento', detalhe.vencimento],
                ['Dias restantes', detalhe.dias_restantes],
                ['Status', detalhe.status_conta],
                ['Status interno', detalhe.status_interno],
                ['Tipo', formatTrialValue(detalhe.e_teste)],
                ['DNS', detalhe.dns],
                ['Revenda', detalhe.revenda],
                ['Criado em', detalhe.criado_em],
                ['Atualizado em', detalhe.atualizado_em],
                ['M3U Plus', detalhe.url_m3u_plus, 'copy-button'],
                ['M3U', detalhe.url_m3u, 'copy-button']
            ] : [];

            renderResultCard(
                'lineResult',
                'The Best',
                linha.status,
                rows,
                linha.mensagem || 'Nenhuma linha encontrada no The Best.',
                linha
            );

            if (linha.status === 'sucesso') {
                document.getElementById('lineResult').insertAdjacentHTML('beforeend', accessSelectButton(accessMessage));
                document.getElementById('lineResult').insertAdjacentHTML('beforeend', sendClientButton('the-best'));
            }
        }

        function renderMaxplayerResult(data) {
            const maxplayer = data.maxplayer || {};
            const user = (maxplayer.usuarios || [])[0] || {};
            const list = (user.listas || [])[0] || {};
            const iptv = list.iptv || {};
            const accessMessage = buildAccessMessage({
                usuario: iptv.usuario || user.usuario,
                senha: iptv.senha,
                telas: user.telas || list.telas || 1,
                telefone: iptv.usuario || data.telefone_normalizado || user.usuario,
                vencimento: user.vencimento || list.vencimento || data.linha?.linha?.vencimento_completo || data.linha?.linha?.vencimento
            });
            const rows = maxplayer.status === 'sucesso' ? [
                ['Usuario', user.usuario],
                ['ID', user.id],
                ['Email', user.email],
                ['Lista', list.nome],
                ['Dominio', iptv.fqdn],
                ['Porta', iptv.porta],
                ['Usuario IPTV', iptv.usuario],
                ['Senha IPTV', iptv.senha],
                ['Encontrados', maxplayer.total_encontrado],
                ['Cache', maxplayer.cache]
            ] : [];

            renderResultCard(
                'maxplayerResult',
                'MaxPlayer',
                maxplayer.status,
                rows,
                maxplayer.mensagem || 'Nenhum usuario encontrado no MaxPlayer.',
                maxplayer
            );

            if (maxplayer.status === 'sucesso') {
                document.getElementById('maxplayerResult').insertAdjacentHTML('beforeend', accessSelectButton(accessMessage));
                document.getElementById('maxplayerResult').insertAdjacentHTML('beforeend', sendClientButton('maxplayer'));
                document.getElementById('maxplayerResult').insertAdjacentHTML('beforeend', maxplayerDomainForm(user));
            } else {
                document.getElementById('maxplayerResult').insertAdjacentHTML('beforeend', maxplayerCreateForm(data));
            }
        }

        function renderMaxplayerFreeResult(data) {
            const maxplayerFree = data.maxplayer_free || {};
            const user = (maxplayerFree.usuarios || [])[0] || {};
            const freeLine = (data.maxplayer_free_linhas?.linhas || [])[0] || {};
            const userAccessMessage = buildAccessMessage({
                usuario: user.usuario,
                senha: user.senha,
                telas: user.telas || 1,
                telefone: user.usuario,
                vencimento: user.vencimento
            });
            const lineAccessMessage = buildAccessMessage({
                usuario: freeLine.usuario,
                senha: freeLine.senha,
                telas: freeLine.telas || 1,
                telefone: freeLine.usuario,
                vencimento: freeLine.vencimento
            });
            const rows = maxplayerFree.status === 'sucesso' ? [
                ['Usuario', user.usuario],
                ['ID', user.id],
                ['Line ID', user.line_id],
                ['Senha', user.senha],
                ['Vencimento', user.vencimento],
                ['Dominio', user.dominio],
                ['Tipo', formatTrialValue(user.e_teste)],
                ['Encontrados', maxplayerFree.total_encontrado],
                ['Cache', maxplayerFree.cache]
            ] : freeLine.id ? [
                ['Linha encontrada', freeLine.usuario],
                ['Line ID', freeLine.id],
                ['Senha linha', freeLine.senha],
                ['Vencimento', freeLine.vencimento],
                ['Tipo', formatTrialValue(freeLine.e_teste)]
            ] : [];

            renderResultCard(
                'maxplayerFreeResult',
                'MaxPlayer Free',
                maxplayerFree.status === 'sucesso' ? 'sucesso' : (freeLine.id ? 'ignorado' : maxplayerFree.status),
                rows,
                maxplayerFree.mensagem || 'Nenhum usuario encontrado no MaxPlayer Free.',
                {
                    usuario: maxplayerFree,
                    linha: data.maxplayer_free_linhas
                }
            );

            if (maxplayerFree.status !== 'sucesso') {
                if (freeLine.id) {
                    document.getElementById('maxplayerFreeResult').insertAdjacentHTML('beforeend', accessSelectButton(lineAccessMessage));
                    document.getElementById('maxplayerFreeResult').insertAdjacentHTML('beforeend', sendClientButton('maxplayer-free'));
                }
                document.getElementById('maxplayerFreeResult').insertAdjacentHTML('beforeend', maxplayerFreeCreateForm(data));
            } else {
                document.getElementById('maxplayerFreeResult').insertAdjacentHTML('beforeend', accessSelectButton(userAccessMessage));
                document.getElementById('maxplayerFreeResult').insertAdjacentHTML('beforeend', sendClientButton('maxplayer-free'));
            }
        }

        async function loadMaxplayerFreeLine(data, term) {
            if (!shouldShowMaxplayerFree(data)) {
                document.getElementById('maxplayerFreeResult').hidden = true;
                return;
            }

            document.getElementById('maxplayerFreeResult').hidden = false;
            renderResultCard('maxplayerFreeResult', 'MaxPlayer Free', 'ignorado', [], 'Consultando Free em segundo plano...', {});
            try {
                const freeLine = await requestJson('/maxplayer-free/linha', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ termo: term })
                });
                const nextData = {
                    ...data,
                    maxplayer_free_linhas: freeLine
                };
                lastUnifiedData = nextData;
                renderMaxplayerFreeResult(nextData);
                loadMaxplayerFreeDomains();
            } catch (error) {
                const nextData = {
                    ...data,
                    maxplayer_free_linhas: {
                        status: 'erro',
                        mensagem: error.message,
                        linhas: []
                    }
                };
                renderMaxplayerFreeResult(nextData);
            }
        }

        async function runUnifiedSearch(term) {
            const button = document.getElementById('clientSearchButton');
            const results = document.getElementById('clientResults');
            const summary = document.getElementById('clientSummary');

            button.disabled = true;
            button.textContent = 'Pesquisando...';
            summary.hidden = true;
            summary.innerHTML = '';
            results.classList.add('show');
            renderResultCard('lineResult', 'The Best', 'ignorado', [], 'Consultando The Best...', {});
            renderResultCard('resellerResult', 'Pagamentos', 'ignorado', [], 'Consultando pagamentos...', {});
            renderResultCard('maxplayerResult', 'MaxPlayer', 'ignorado', [], 'Consultando MaxPlayer...', {});
            document.getElementById('maxplayerFreeResult').hidden = true;

            try {
                const data = await requestJson('/cliente/consulta', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ termo: term })
                });
                lastUnifiedData = data;
                renderLineResult(data);
                renderResellerResult(data);
                renderMaxplayerResult(data);
                renderSummary(data);
                loadMaxplayerDomains();
                loadMaxplayerFreeLine(data, term);
            } catch (error) {
                renderResultCard('lineResult', 'The Best', 'erro', [], error.message, {});
                renderResultCard('resellerResult', 'Pagamentos', 'erro', [], error.message, {});
                renderResultCard('maxplayerResult', 'MaxPlayer', 'erro', [], error.message, {});
                document.getElementById('maxplayerFreeResult').hidden = true;
            } finally {
                button.disabled = false;
                button.textContent = 'Pesquisar';
            }
        }

        function openMessageModal(type) {
            if (!lastUnifiedData) {
                alert('Consulte um cliente antes de enviar.');
                return;
            }

            pendingMessageType = type;
            const modal = document.getElementById('messageModal');
            const textarea = document.getElementById('messageText');
            textarea.value = buildClientMessage(type, lastUnifiedData);
            modal.hidden = false;
            textarea.focus();
            textarea.select();
        }

        function closeMessageModal() {
            document.getElementById('messageModal').hidden = true;
            pendingMessageType = '';
        }

        async function sendEditedMessage() {
            if (!lastUnifiedData || !pendingMessageType) {
                alert('Consulte um cliente antes de enviar.');
                return;
            }

            const button = document.getElementById('sendMessageBtn');
            const textarea = document.getElementById('messageText');
            const mensagem = textarea.value.trim();
            if (!mensagem) {
                alert('A mensagem esta vazia.');
                textarea.focus();
                return;
            }

            button.disabled = true;
            button.textContent = 'Enviando...';
            try {
                await requestJson('/botconversa/enviar', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(buildBotConversaPayload(lastUnifiedData, mensagem, pendingMessageType))
                });
                closeMessageModal();
                alert('Mensagem enviada para o BotConversa.');
            } catch (error) {
                alert(error.message);
            } finally {
                button.disabled = false;
                button.textContent = 'Enviar';
            }
        }

        async function runRequest(action, method = 'GET') {
            setResponse(action.responseId, 'loading', 'Carregando...');
            try {
                const data = await requestJson(action.endpoint, { method });
                setResponse(action.responseId, 'success', pretty(data));
                if (action.endpoint === '/status' || action.endpoint === '/reload') {
                    await loadStats();
                }
            } catch (error) {
                setResponse(action.responseId, 'error', error.message);
            }
        }

        async function runPostTerm(action) {
            const value = document.getElementById(action.inputId).value.trim();
            if (!value) {
                setResponse(action.responseId, 'error', 'Digite um termo para continuar.');
                return;
            }
            setResponse(action.responseId, 'loading', 'Buscando...');
            try {
                const data = await requestJson(action.endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ termo: value })
                });
                setResponse(action.responseId, 'success', pretty(data));
            } catch (error) {
                setResponse(action.responseId, 'error', error.message);
            }
        }

        async function runPhone(action) {
            const value = document.getElementById(action.inputId).value.trim();
            const phone = value.replace(/\\D/g, '');
            if (!phone) {
                setResponse(action.responseId, 'error', 'Digite um telefone para continuar.');
                return;
            }
            setResponse(action.responseId, 'loading', 'Consultando linha...');
            try {
                const data = await requestJson('/consultar-linha/' + phone);
                setResponse(action.responseId, 'success', pretty(data));
            } catch (error) {
                setResponse(action.responseId, 'error', error.message);
            }
        }

        async function runDelete(action) {
            const email = document.getElementById(action.inputId).value.trim();
            if (!email) {
                setResponse(action.responseId, 'error', 'Digite o email da revenda.');
                return;
            }
            if (!confirm('Tem certeza que deseja excluir a revenda ' + email + '?\\n\\nEsta acao nao pode ser desfeita.')) {
                return;
            }
            setResponse(action.responseId, 'loading', 'Excluindo revenda...');
            try {
                const data = await requestJson('/revenda/excluir', {
                    method: 'DELETE',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email })
                });
                setResponse(action.responseId, data.status === 'sucesso' ? 'success' : 'error', pretty(data));
                if (data.status === 'sucesso') {
                    document.getElementById(action.inputId).value = '';
                }
            } catch (error) {
                setResponse(action.responseId, 'error', error.message);
            }
        }

        async function runUpdate(action) {
            setResponse(action.responseId, 'loading', 'Iniciando atualizacao...');
            try {
                const data = await requestJson('/atualizar', { method: 'POST' });
                setResponse(action.responseId, 'success', pretty(data));
                document.getElementById('updateLog').textContent = pretty(data);
                await pollUpdateStatus(true);
            } catch (error) {
                setResponse(action.responseId, 'error', error.message);
                await pollUpdateStatus(false);
            }
        }

        function runManual(action) {
            setResponse(action.responseId, 'loading', 'Este endpoint precisa de nome, email, senha e filename opcional. Use um cliente HTTP para enviar o JSON completo.');
        }

        async function handleAction(action) {
            if (action.type === 'request') return runRequest(action);
            if (action.type === 'postTerm') return runPostTerm(action);
            if (action.type === 'phone') return runPhone(action);
            if (action.type === 'delete') return runDelete(action);
            if (action.type === 'update') return runUpdate(action);
            return runManual(action);
        }

        function renderEndpoints() {
            const term = searchInput.value.trim().toLowerCase();
            const visible = endpoints.filter((item) => {
                const matchesFilter = activeFilter === 'all' || item.method === activeFilter;
                const content = (item.method + ' ' + item.path + ' ' + item.description).toLowerCase();
                return matchesFilter && content.includes(term);
            });

            endpointList.innerHTML = visible.map((item, index) => {
                const field = item.field ? `
                    <div class="field">
                        <label for="${item.field.id}">${escapeHtml(item.field.label)}</label>
                        <input id="${item.field.id}" type="${item.field.type || 'text'}" placeholder="${escapeHtml(item.field.placeholder)}">
                    </div>` : '';
                return `
                    <article class="endpoint-card" data-index="${endpoints.indexOf(item)}">
                        <div class="endpoint-main">
                            <span class="method ${item.method.toLowerCase()}">${item.method}</span>
                            <div>
                                <h3 class="endpoint-path">${escapeHtml(item.path)}</h3>
                                <p class="endpoint-desc">${escapeHtml(item.description)}</p>
                            </div>
                            <button class="btn" data-toggle="${index}">Detalhes</button>
                        </div>
                        <div class="endpoint-body">
                            <pre>${escapeHtml(item.sample)}</pre>
                            ${field}
                            <div class="actions">
                                <button class="btn ${item.method === 'DELETE' ? 'danger' : 'primary'}" data-action-index="${endpoints.indexOf(item)}">${escapeHtml(item.action.label)}</button>
                            </div>
                            <div class="response" id="${item.action.responseId}"></div>
                        </div>
                    </article>`;
            }).join('');

            emptyState.hidden = visible.length !== 0;
            document.getElementById('endpointTotal').textContent = endpoints.length;
        }

        function updateCounts() {
            document.getElementById('countAll').textContent = endpoints.length;
            document.getElementById('countGet').textContent = endpoints.filter((item) => item.method === 'GET').length;
            document.getElementById('countPost').textContent = endpoints.filter((item) => item.method === 'POST').length;
            document.getElementById('countDelete').textContent = endpoints.filter((item) => item.method === 'DELETE').length;
        }

        async function loadStats() {
            try {
                const data = await requestJson('/status');
                document.getElementById('totalRegs').textContent = Number(data.total_registros || 0).toLocaleString('pt-BR');
                document.getElementById('apiState').textContent = 'Online';
                document.getElementById('apiMessage').textContent = data.message || 'API respondendo';
            } catch (error) {
                document.getElementById('totalRegs').textContent = '?';
                document.getElementById('apiState').textContent = 'Erro';
                document.getElementById('apiMessage').textContent = 'Nao foi possivel consultar /status';
            }
        }

        async function pollUpdateStatus(keepPolling) {
            try {
                const data = await requestJson('/atualizar/status');
                document.getElementById('updateState').textContent = data.running ? 'Rodando' : (data.status || 'Idle');
                document.getElementById('updateMessage').textContent = data.message || 'Sem detalhes';
                document.getElementById('updateLog').textContent = pretty(data);

                if (data.running || keepPolling) {
                    window.clearTimeout(updateTimer);
                    updateTimer = window.setTimeout(() => pollUpdateStatus(false), 2500);
                } else if (data.status === 'success') {
                    await loadStats();
                }
            } catch (error) {
                document.getElementById('updateState').textContent = 'Erro';
                document.getElementById('updateMessage').textContent = 'Falha ao consultar status';
                document.getElementById('updateLog').textContent = error.message;
            }
        }

        document.getElementById('navFilters').addEventListener('click', (event) => {
            const button = event.target.closest('button[data-filter]');
            if (!button) return;
            activeFilter = button.dataset.filter;
            document.querySelectorAll('#navFilters button').forEach((item) => item.classList.toggle('active', item === button));
            renderEndpoints();
        });

        document.getElementById('clientSearchForm').addEventListener('submit', async (event) => {
            event.preventDefault();
            const term = document.getElementById('clientSearchInput').value.trim();
            if (!term) {
                document.getElementById('clientSearchInput').focus();
                return;
            }
            await runUnifiedSearch(term);
        });

        document.getElementById('themeToggleBtn').addEventListener('click', () => {
            const isDark = document.body.classList.toggle('theme-dark');
            localStorage.setItem('painel-theme', isDark ? 'dark' : 'light');
            document.getElementById('themeToggleBtn').textContent = isDark ? 'Modo claro' : 'Modo escuro';
        });

        document.getElementById('toggleEndpointsBtn').addEventListener('click', () => {
            const workspace = document.querySelector('.workspace');
            const isOpen = workspace.classList.toggle('show');
            document.getElementById('toggleEndpointsBtn').textContent = isOpen ? 'Ocultar endpoints' : 'Endpoints';
            if (isOpen) {
                workspace.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });

        document.getElementById('sendMessageBtn').addEventListener('click', sendEditedMessage);

        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && !document.getElementById('messageModal').hidden) {
                closeMessageModal();
            }
        });

        document.addEventListener('click', (event) => {
            const copyButton = event.target.closest('button[data-copy-value]');
            if (copyButton) {
                const value = copyButton.dataset.copyValue;
                copyText(value).then(() => {
                    const original = copyButton.innerHTML;
                    const isTextButton = copyButton.classList.contains('select-data-btn');
                    if (isTextButton) {
                        copyButton.textContent = 'Dados copiados';
                    } else {
                        copyButton.innerHTML = checkIcon();
                    }
                    copyButton.classList.add('copied');
                    window.setTimeout(() => {
                        if (isTextButton) {
                            copyButton.textContent = 'Selecionar dados';
                        } else {
                            copyButton.innerHTML = original;
                        }
                        copyButton.classList.remove('copied');
                    }, 1400);
                }).catch(() => {
                    alert('Nao foi possivel copiar automaticamente. Valor: ' + value);
                });
                return;
            }

            const messageButton = event.target.closest('button[data-open-message-modal]');
            if (messageButton) {
                openMessageModal(messageButton.dataset.openMessageModal);
                return;
            }

            if (event.target.closest('[data-close-message-modal]')) {
                closeMessageModal();
                return;
            }

            const createButton = event.target.closest('button[data-create-maxplayer]');
            if (createButton) {
                const domainId = document.getElementById('createMaxDomain')?.value;
                const iptvUser = document.getElementById('createMaxUser')?.value.trim();
                const iptvPass = document.getElementById('createMaxPass')?.value.trim();
                if (!domainId || !iptvUser || !iptvPass) {
                    alert('Selecione um dominio e confirme usuario/senha IPTV.');
                    return;
                }
                if (!confirm('Criar este usuario no MaxPlayer com o dominio selecionado?')) {
                    return;
                }
                createButton.disabled = true;
                createButton.textContent = 'Criando...';
                requestJson('/maxplayer/usuario/criar', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        domain_id: domainId,
                        iptv_user: iptvUser,
                        iptv_pass: iptvPass,
                        username: iptvUser,
                        user_password: iptvPass
                    })
                }).then(() => {
                    return runUnifiedSearch(document.getElementById('clientSearchInput').value.trim() || iptvUser);
                }).catch((error) => {
                    alert(error.message);
                }).finally(() => {
                    createButton.disabled = false;
                    createButton.textContent = 'Criar no MaxPlayer';
                });
                return;
            }

            const editButton = event.target.closest('button[data-edit-max-domain]');
            if (editButton) {
                const domainId = document.getElementById('editMaxDomain')?.value;
                if (!domainId) {
                    alert('Selecione um dominio.');
                    return;
                }
                if (!confirm('Trocar o dominio desta lista no MaxPlayer?')) {
                    return;
                }
                editButton.disabled = true;
                editButton.textContent = 'Salvando...';
                requestJson('/maxplayer/lista/dominio', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        list_id: editButton.dataset.listId,
                        domain_id: domainId,
                        new_list_name: editButton.dataset.listName || 'List 1',
                        iptv_username: editButton.dataset.iptvUser,
                        iptv_password: editButton.dataset.iptvPass
                    })
                }).then(() => {
                    return runUnifiedSearch(document.getElementById('clientSearchInput').value.trim() || editButton.dataset.iptvUser);
                }).catch((error) => {
                    alert(error.message);
                }).finally(() => {
                    editButton.disabled = false;
                    editButton.textContent = 'Salvar dominio';
                });
                return;
            }

            const createFreeButton = event.target.closest('button[data-create-maxplayer-free]');
            if (createFreeButton) {
                const domainId = document.getElementById('createMaxFreeDomain')?.value;
                const lineId = Number(createFreeButton.dataset.lineId);
                if (!domainId || !lineId) {
                    alert('Selecione um dominio Free e confirme a linha.');
                    return;
                }
                if (!confirm('Criar este usuario no MaxPlayer Free com o dominio selecionado?')) {
                    return;
                }
                createFreeButton.disabled = true;
                createFreeButton.textContent = 'Criando...';
                requestJson('/maxplayer-free/usuario/criar', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        line_id: lineId,
                        domain_id: domainId
                    })
                }).then(() => {
                    return runUnifiedSearch(document.getElementById('clientSearchInput').value.trim());
                }).catch((error) => {
                    alert(error.message);
                }).finally(() => {
                    createFreeButton.disabled = false;
                    createFreeButton.textContent = 'Criar no Free';
                });
                return;
            }

            const rawButton = event.target.closest('button[data-raw-target]');
            if (!rawButton) return;
            const target = document.getElementById(rawButton.dataset.rawTarget);
            if (!target) return;
            const isOpen = target.classList.toggle('show');
            rawButton.textContent = isOpen ? 'Ocultar JSON' : 'Ver JSON';
        });

        endpointList.addEventListener('click', async (event) => {
            const toggle = event.target.closest('button[data-toggle]');
            if (toggle) {
                const card = toggle.closest('.endpoint-card');
                const open = card.classList.toggle('open');
                toggle.textContent = open ? 'Ocultar' : 'Detalhes';
                return;
            }

            const actionButton = event.target.closest('button[data-action-index]');
            if (actionButton) {
                const endpoint = endpoints[Number(actionButton.dataset.actionIndex)];
                await handleAction(endpoint.action);
            }
        });

        searchInput.addEventListener('input', renderEndpoints);
        document.getElementById('refreshStatusBtn').addEventListener('click', async () => {
            await loadStats();
            await pollUpdateStatus(false);
        });
        document.getElementById('runUpdateBtn').addEventListener('click', () => {
            const action = endpoints.find((item) => item.path === '/atualizar').action;
            const card = document.querySelector(`[data-index="${endpoints.findIndex((item) => item.path === '/atualizar')}"]`);
            if (card && !card.classList.contains('open')) {
                card.classList.add('open');
                card.querySelector('button[data-toggle]').textContent = 'Ocultar';
            }
            handleAction(action);
        });

        updateCounts();
        renderEndpoints();
        if (localStorage.getItem('painel-theme') === 'dark') {
            document.body.classList.add('theme-dark');
            document.getElementById('themeToggleBtn').textContent = 'Modo claro';
        }
        loadStats();
        pollUpdateStatus(false);
