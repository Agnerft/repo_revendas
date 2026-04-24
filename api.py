from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
import pandas as pd
import os
import json
import re
import unicodedata
import subprocess
import requests
from typing import Optional

app = FastAPI(title="Serviço de Busca de Revendas")

EXCEL_FILE = "revendas_consolidadas.xlsx"
df = None

class SearchRequest(BaseModel):
    termo: str

class RevendaRequest(BaseModel):
    nome: str
    email: str
    password: str
    filename: Optional[str] = None

def load_data():
    global df
    if os.path.exists(EXCEL_FILE):
        try:
            print(f"Carregando {EXCEL_FILE}...")
            # Lê todas as colunas como string para facilitar a busca
            df = pd.read_excel(EXCEL_FILE, dtype=str)
            # Preenche NaN com string vazia
            df = df.fillna("")
            print(f"Colunas carregadas: {df.columns.tolist()}")
            print(f"Dados carregados: {len(df)} registros.")
        except Exception as e:
            print(f"Erro ao carregar Excel: {e}")
            df = pd.DataFrame()
    else:
        print(f"Arquivo {EXCEL_FILE} não encontrado.")
        df = pd.DataFrame()

# Carrega os dados na inicialização
load_data()

@app.get("/")
def read_root():
    return RedirectResponse(url="/painel")

@app.get("/status")
def status():
    return {
        "message": "API de Busca de Clientes Ativa",
        "total_registros": len(df) if df is not None else 0,
        "uso_post": "POST /buscar com body {'termo': 'valor'}"
    }

@app.get("/painel", response_class=HTMLResponse)
def painel():
    return """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
        <meta http-equiv="Pragma" content="no-cache">
        <meta http-equiv="Expires" content="0">
        <title>Painel API - Revendas</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
                color: #e2e8f0;
                min-height: 100vh;
                padding: 40px 20px;
            }
            .container { max-width: 1200px; margin: 0 auto; }
            h1 {
                text-align: center;
                margin-bottom: 10px;
                font-size: 2.5rem;
                background: linear-gradient(90deg, #22c55e, #3b82f6);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            .subtitle { text-align: center; color: #94a3b8; margin-bottom: 40px; }
            .grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
                gap: 20px;
            }
            .card {
                background: #1e293b;
                border-radius: 16px;
                padding: 24px;
                border: 1px solid #334155;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            .card:hover { transform: translateY(-4px); box-shadow: 0 20px 40px rgba(0,0,0,0.3); }
            .method {
                display: inline-block;
                padding: 4px 12px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                text-transform: uppercase;
                margin-bottom: 12px;
            }
            .get { background: #22c55e; color: #fff; }
            .post { background: #3b82f6; color: #fff; }
            .endpoint {
                font-family: 'Courier New', monospace;
                font-size: 16px;
                color: #f8fafc;
                margin-bottom: 12px;
                word-break: break-all;
            }
            .description { color: #94a3b8; font-size: 14px; line-height: 1.5; margin-bottom: 16px; }
            .code-block {
                background: #0f172a;
                border-radius: 8px;
                padding: 16px;
                font-family: 'Courier New', monospace;
                font-size: 13px;
                overflow-x: auto;
                border-left: 3px solid #22c55e;
            }
            .code-block pre { margin: 0; color: #e2e8f0; }
            .status-bar {
                background: #0f172a;
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 30px;
                display: flex;
                justify-content: space-around;
                flex-wrap: wrap;
                gap: 20px;
                border: 1px solid #334155;
            }
            .stat { text-align: center; }
            .stat-value { font-size: 2rem; font-weight: bold; color: #22c55e; }
            .stat-label { color: #64748b; font-size: 14px; }
            .test-btn {
                background: #22c55e;
                border: none;
                padding: 10px 20px;
                border-radius: 8px;
                color: white;
                cursor: pointer;
                font-size: 14px;
                margin-top: 12px;
                transition: opacity 0.2s;
            }
            .test-btn:hover { opacity: 0.9; }
            .response {
                margin-top: 12px;
                padding: 12px;
                border-radius: 8px;
                font-size: 13px;
                display: none;
                white-space: pre-wrap;
                word-break: break-word;
            }
            .response.show { display: block; }
            .response.success { background: #064e3b; color: #6ee7b7; }
            .response.error { background: #450a0a; color: #fca5a5; }
            .input-group { margin-top: 12px; }
            .input-group input {
                width: 100%;
                padding: 10px;
                border-radius: 6px;
                border: 1px solid #475569;
                background: #0f172a;
                color: #e2e8f0;
                font-size: 14px;
            }
            .input-group input:focus { outline: none; border-color: #22c55e; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 API de Revendas</h1>
            <p class="subtitle">Documentação completa dos endpoints disponíveis</p>
            
            <div class="status-bar">
                <div class="stat">
                    <div class="stat-value" id="totalRegs">-</div>
                    <div class="stat-label">Total de Registros</div>
                </div>
                <div class="stat">
                    <div class="stat-value">11</div>
                    <div class="stat-label">Endpoints</div>
                </div>
                <div class="stat">
                    <div class="stat-value">✅</div>
                    <div class="stat-label">Status</div>
                </div>
            </div>

            <div class="grid">
                <!-- GET /status -->
                <div class="card">
                    <span class="method get">GET</span>
                    <div class="endpoint">/status</div>
                    <div class="description">Retorna status da API e total de registros carregados</div>
                    <div class="code-block"><pre>{
  "message": "API de Busca de Clientes Ativa",
  "total_registros": 42860
}</pre></div>
                    <button class="test-btn" onclick="testGet('/status', 'r1')">Testar</button>
                    <div class="response" id="r1"></div>
                </div>

                <!-- POST /buscar -->
                <div class="card">
                    <span class="method post">POST</span>
                    <div class="endpoint">/buscar</div>
                    <div class="description">Busca um cliente em todas as colunas pelo termo. Suporta comandos especiais como "atualizar"</div>
                    <div class="code-block"><pre>Body: { "termo": "+5551999999999" }

Retorna: {
  "Revenda": "Nome",
  "nome": "Cliente",
  "telefone": "+55...",
  "data_expiracao": "..."
}</pre></div>
                    <div class="input-group">
                        <input type="text" id="in1" placeholder="Telefone, nome ou ID...">
                    </div>
                    <button class="test-btn" onclick="testPost('/buscar', 'in1', 'r2')">Testar</button>
                    <div class="response" id="r2"></div>
                </div>

                <!-- POST /filtrar -->
                <div class="card">
                    <span class="method post">POST</span>
                    <div class="endpoint">/filtrar</div>
                    <div class="description">Retorna LISTA com todos os clientes encontrados. Ideal para buscar por data</div>
                    <div class="code-block"><pre>Body: { "termo": "19/08/2025" }

Retorna: [ { ... }, { ... } ] // array</pre></div>
                    <div class="input-group">
                        <input type="text" id="in2" placeholder="Data ou termo...">
                    </div>
                    <button class="test-btn" onclick="testPost('/filtrar', 'in2', 'r3')">Testar</button>
                    <div class="response" id="r3"></div>
                </div>

                <!-- GET /reload -->
                <div class="card">
                    <span class="method get">GET</span>
                    <div class="endpoint">/reload</div>
                    <div class="description">Recarrega os dados do Excel sem reiniciar o servidor</div>
                    <div class="code-block"><pre>Retorna: {
  "message": "Dados recarregados.",
  "total_registros": 42860
}</pre></div>
                    <button class="test-btn" onclick="testGet('/reload', 'r4')">Recarregar</button>
                    <div class="response" id="r4"></div>
                </div>

                <!-- POST /atualizar -->
                <div class="card">
                    <span class="method post">POST</span>
                    <div class="endpoint">/atualizar</div>
                    <div class="description">Executa o script update_all_revendas.py para atualizar todos os dados (pode demorar)</div>
                    <div class="code-block"><pre>Retorna: {
  "message": "Atualizado com sucesso",
  "total": 42860
}</pre></div>
                    <button class="test-btn" onclick="testGet('/atualizar', 'r5', 'POST')">Atualizar Dados</button>
                    <div class="response" id="r5"></div>
                </div>

                <!-- GET /revenda/adicionar -->
                <div class="card">
                    <span class="method get">GET</span>
                    <div class="endpoint">/revenda/adicionar</div>
                    <div class="description">Documentação do endpoint para adicionar revenda</div>
                    <div class="code-block"><pre>Retorna: instruções de uso do POST</pre></div>
                    <button class="test-btn" onclick="testGet('/revenda/adicionar', 'r6')">Ver</button>
                    <div class="response" id="r6"></div>
                </div>

                <!-- POST /revenda/adicionar -->
                <div class="card">
                    <span class="method post">POST</span>
                    <div class="endpoint">/revenda/adicionar</div>
                    <div class="description">Adiciona uma nova revenda ao arquivo de logins</div>
                    <div class="code-block"><pre>Body: {
  "nome": "Revenda XYZ",
  "email": "revenda@email.com",
  "password": "senha123",
  "filename": "opcional.json"
}</pre></div>
                    <button class="test-btn" onclick="alert('Use Postman ou curl para testar este endpoint')">Adicionar Revenda</button>
                </div>

                <!-- POST / (alias) -->
                <div class="card">
                    <span class="method post">POST</span>
                    <div class="endpoint">/ (alias)</div>
                    <div class="description">Alias para /buscar. Busca cliente pelo termo enviado</div>
                    <div class="code-block"><pre>Body: { "termo": "valor" }

Retorna: objeto do cliente encontrado</pre></div>
                    <div class="input-group">
                        <input type="text" id="in3" placeholder="Digite o termo de busca...">
                    </div>
                    <button class="test-btn" onclick="testPost('/', 'in3', 'r7')">Testar</button>
                    <div class="response" id="r7"></div>
                </div>

                <!-- GET /consultar-linha/{telefone} -->
                <div class="card">
                    <span class="method get">GET</span>
                    <div class="endpoint">/consultar-linha/{telefone}</div>
                    <div class="description">Consulta API externa de linhas pelo número de telefone</div>
                    <div class="code-block"><pre>Ex: /consultar-linha/5511999999999

Headers: Api-Key: ***
Retorna: dados da linha na API externa</pre></div>
                    <div class="input-group">
                        <input type="text" id="in4" placeholder="Telefone com DDD...">
                    </div>
                    <button class="test-btn" onclick="testConsultarLinha()">Consultar</button>
                    <div class="response" id="r8"></div>
                </div>

                <!-- GET /revenda/listar -->
                <div class="card">
                    <span class="method get">GET</span>
                    <div class="endpoint">/revenda/listar</div>
                    <div class="description">Lista todas as revendas cadastradas com total de clientes</div>
                    <div class="code-block"><pre>Retorna: {
  "total": 5,
  "revendas": [
    { "nome": "...", "email": "...", "total_clientes": 150 }
  ]
}</pre></div>
                    <button class="test-btn" onclick="testGet('/revenda/listar', 'r9')">Listar Revendas</button>
                    <div class="response" id="r9"></div>
                </div>

                <!-- DELETE /revenda/excluir -->
                <div class="card">
                    <span class="method" style="background: #ef4444; color: #fff;">DELETE</span>
                    <div class="endpoint">/revenda/excluir</div>
                    <div class="description">Exclui uma revenda pelo email</div>
                    <div class="code-block"><pre>Body: { "email": "revenda@email.com" }

⚠️ Atenção: Remove também o arquivo JSON</pre></div>
                    <div class="input-group">
                        <input type="email" id="in5" placeholder="Email da revenda...">
                    </div>
                    <button class="test-btn" onclick="testDeleteRevenda()" style="background: #ef4444;">🗑️ Excluir Revenda</button>
                    <div class="response" id="r10"></div>
                </div>
            </div>
        </div>

        <script>
            // Carrega total de registros ao iniciar
            async function loadStats() {
                try {
                    const res = await fetch('/status');
                    const data = await res.json();
                    document.getElementById('totalRegs').textContent = data.total_registros;
                } catch (e) {
                    document.getElementById('totalRegs').textContent = '?';
                }
            }
            loadStats();

            async function testGet(endpoint, respId, method) {
                const respDiv = document.getElementById(respId);
                respDiv.className = 'response show';
                respDiv.textContent = '⏳ Carregando...';
                
                try {
                    const res = await fetch(endpoint, { method: method || 'GET' });
                    const data = await res.json();
                    respDiv.className = 'response show success';
                    respDiv.textContent = '✅ ' + JSON.stringify(data, null, 2);
                } catch (e) {
                    respDiv.className = 'response show error';
                    respDiv.textContent = '❌ Erro: ' + e.message;
                }
            }

            async function testPost(endpoint, inputId, respId) {
                const termo = document.getElementById(inputId).value;
                const respDiv = document.getElementById(respId);
                
                if (!termo) {
                    respDiv.className = 'response show error';
                    respDiv.textContent = '❌ Digite um termo de busca';
                    return;
                }
                
                respDiv.className = 'response show';
                respDiv.textContent = '⏳ Buscando...';
                
                try {
                    const res = await fetch(endpoint, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ termo })
                    });
                    const data = await res.json();
                    respDiv.className = 'response show success';
                    respDiv.textContent = '✅ ' + JSON.stringify(data, null, 2);
                } catch (e) {
                    respDiv.className = 'response show error';
                    respDiv.textContent = '❌ Erro: ' + e.message;
                }
            }

            async function testConsultarLinha() {
                const telefone = document.getElementById('in4').value.trim();
                const respDiv = document.getElementById('r8');
                
                if (!telefone) {
                    respDiv.className = 'response show error';
                    respDiv.textContent = '❌ Digite um telefone';
                    return;
                }
                
                // Remove caracteres não numéricos
                const telefoneLimpo = telefone.replace(/\D/g, '');
                
                respDiv.className = 'response show';
                respDiv.textContent = '⏳ Consultando API externa...';
                
                try {
                    const res = await fetch('/consultar-linha/' + telefoneLimpo);
                    const data = await res.json();
                    respDiv.className = 'response show success';
                    respDiv.textContent = '✅ ' + JSON.stringify(data, null, 2);
                } catch (e) {
                    respDiv.className = 'response show error';
                    respDiv.textContent = '❌ Erro: ' + e.message;
                }
            }

            async function testDeleteRevenda() {
                const email = document.getElementById('in5').value.trim();
                const respDiv = document.getElementById('r10');
                
                if (!email) {
                    respDiv.className = 'response show error';
                    respDiv.textContent = '❌ Digite o email da revenda';
                    return;
                }
                
                // Confirmação antes de excluir
                if (!confirm('⚠️ Tem certeza que deseja excluir a revenda: ' + email + '?\n\nEsta ação não pode ser desfeita!')) {
                    return;
                }
                
                respDiv.className = 'response show';
                respDiv.textContent = '⏳ Excluindo revenda...';
                
                try {
                    const res = await fetch('/revenda/excluir', {
                        method: 'DELETE',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ email: email })
                    });
                    const data = await res.json();
                    
                    if (data.status === 'sucesso') {
                        respDiv.className = 'response show success';
                        respDiv.textContent = '✅ ' + JSON.stringify(data, null, 2);
                        document.getElementById('in5').value = ''; // Limpa o campo
                    } else {
                        respDiv.className = 'response show error';
                        respDiv.textContent = '❌ ' + JSON.stringify(data, null, 2);
                    }
                } catch (e) {
                    respDiv.className = 'response show error';
                    respDiv.textContent = '❌ Erro: ' + e.message;
                }
            }
        </script>
    </body>
    </html>
    """



@app.post("/atualizar")
def atualizar():
    try:
        result = subprocess.run(
            ["python", "update_all_revendas.py"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            load_data()
            return JSONResponse({
                "message": "Atualizado com sucesso",
                "total": len(df)
            })
        else:
            return JSONResponse(
                status_code=500,
                content={"detail": result.stderr}
            )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": str(e)}
        )




@app.post("/")
def read_root_post(request: SearchRequest):
    """
    Alias para /buscar. Permite POST na raiz.
    """
    return buscar_cliente(request)

@app.post("/buscar")
def buscar_cliente(request: SearchRequest):
    """
    Busca um cliente em todas as colunas pelo termo enviado no corpo da requisição.
    Body: { "termo": "valor da busca" }
    """
    print(f"Recebida busca: {request.termo}")
    if df is None or df.empty:
        raise HTTPException(status_code=503, detail="Dados não carregados ou vazios.")
    
    q = request.termo
    if not q:
        return {"resultados": [], "total": 0}
    
    termo = q.lower().strip()
    
    # --- COMANDO INTERNO DE ATUALIZAÇÃO ---
    if termo == "atualizar":
        import subprocess
        print("Recebido comando de atualização. Executando update_all_revendas.py...")
        
        # Executa o script de atualização
        # Usamos subprocess para rodar o script independentemente
        try:
            # Roda o script e espera terminar (pode demorar alguns minutos)
            # Como é uma requisição HTTP, o cliente vai esperar.
            # Se demorar muito, pode dar timeout no cliente.
            result = subprocess.run(["python", "update_all_revendas.py"], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("Atualização concluída. Recarregando dados...")
                load_data()
                return {
                    "Revenda": "SISTEMA",
                    "DT_RowId": "CMD_OK",
                    "Id_client": "00000",
                    "nome": "Atualização Concluída",
                    "telefone": f"Total: {len(df)} registros",
                    "data_expiracao": "Atualizado agora"
                }
            else:
                print(f"Erro na atualização: {result.stderr}")
                return {
                    "Revenda": "ERRO",
                    "DT_RowId": "CMD_FAIL",
                    "Id_client": "",
                    "nome": "Erro na atualização",
                    "telefone": "",
                    "data_expiracao": "Verifique logs"
                }
        except Exception as e:
            print(f"Exceção ao rodar atualização: {e}")
            return {
                "Revenda": "ERRO",
                "DT_RowId": "CMD_EXCEPT",
                "Id_client": "",
                "nome": f"Erro: {str(e)}",
                "telefone": "",
                "data_expiracao": ""
            }

    # Remove o sinal de '+' se existir (ex: '+55...' -> '55...')
    # ATENÇÃO: Como agora os dados no Excel têm '+', não devemos remover o '+' da busca se o usuário mandar
    # Se o usuário mandar +55... e no banco está +55..., deve casar.
    # Se o usuário mandar 55... e no banco está +55..., o contains não vai casar direto se for exato,
    # mas '55...' está contido em '+55...', então contains funciona.
    # O problema é se removermos o '+' da busca (+55 -> 55), e no banco é +55.
    # 55 está em +55? Sim.
    # Mas se a lógica anterior removia, por que falhava?
    # Talvez o usuário mande +555185216088.
    # Código remove + -> 555185216088.
    # Banco tem +555185216088 (se foi atualizado corretamente).
    # '555185216088' está em '+555185216088'? Sim.
    # Então deveria funcionar.
    # Mas vamos garantir que a busca seja mais flexível: buscar com e sem o +
    
    # Se o termo tem +, vamos tentar buscar exatamente como veio primeiro
    # Se não encontrar, tentamos sem o +
    
    mask = df.apply(lambda x: x.astype(str).str.lower().str.contains(termo, regex=False, na=False)).any(axis=1)
    
    # Se não achou e tem +, tenta sem o +
    if not mask.any() and "+" in termo:
        termo_sem_plus = termo.replace("+", "")
        mask = df.apply(lambda x: x.astype(str).str.lower().str.contains(termo_sem_plus, regex=False, na=False)).any(axis=1)
    
    # Se não achou e NÃO tem +, tenta COM o + (caso o usuário mande sem e no banco tenha)
    if not mask.any() and "+" not in termo and termo.isdigit():
         termo_com_plus = "+" + termo
         mask = df.apply(lambda x: x.astype(str).str.lower().str.contains(termo_com_plus, regex=False, na=False)).any(axis=1)
         
    # Se ainda não achou, e o termo começa com 55 (DDI Brasil), tenta sem o 55
    # Ex: Busca +5551... mas no banco está +51...
    if not mask.any() and "55" in termo:
        # Tenta remover +55 ou apenas 55 do início
        termo_sem_ddi = termo.replace("+55", "").replace("55", "", 1)
        # Se ficou vazio ou muito curto, ignora
        if len(termo_sem_ddi) > 4:
             mask = df.apply(lambda x: x.astype(str).str.lower().str.contains(termo_sem_ddi, regex=False, na=False)).any(axis=1)

    # BUSCA ROBUSTA POR SUFIXO (ÚLTIMA TENTATIVA)
    # Se ainda não encontrou, vamos comparar apenas os DÍGITOS.
    # Se o usuário mandou um número com pelo menos 8 dígitos,
    # verificamos se esses dígitos finais existem em algum telefone do banco.
    if not mask.any():
        import re
        # Extrai apenas dígitos da busca
        digits_busca = re.sub(r'[^\d]', '', termo)
        
        # Só aplica se tiver pelo menos 8 dígitos (evitar match falso em números curtos)
        if len(digits_busca) >= 8:
            # Pega os últimos 8 dígitos (suficiente para identificar unicamente na maioria dos casos)
            sufixo = digits_busca[-8:]
            
            # Função auxiliar para verificar se o telefone da linha contém esse sufixo
            def check_suffix(val):
                val_str = str(val)
                # Extrai dígitos do valor da célula
                val_digits = re.sub(r'[^\d]', '', val_str)
                return sufixo in val_digits
            
            # Aplica apenas na coluna 'telefone' (mais eficiente e preciso)
            if 'telefone' in df.columns:
                mask = df['telefone'].apply(check_suffix)
            else:
                # Se não tiver coluna telefone explícita, tenta em todas (mais lento)
                mask = df.apply(lambda row: row.astype(str).apply(lambda x: sufixo in re.sub(r'[^\d]', '', x)).any(), axis=1)

    resultados = df[mask]
    
    # Converte para lista de dicionários
    lista_resultados = resultados.to_dict(orient="records")
    
    if lista_resultados:
        # Pega o primeiro resultado
        item = lista_resultados[0]
        
        # Limpeza extra no telefone da resposta (garantir apenas números e adicionar +)
        if "telefone" in item:
            import re
            phone = str(item["telefone"])
            digits = re.sub(r'[^\d]', '', phone)
            item["telefone"] = f"+{digits}" if digits else phone
        
        # Adiciona o link de pagamento
        dt_row_id = item.get("DT_RowId", "")
        if dt_row_id and dt_row_id != "nao_encontrado":
            item["Link"] = f"https://pagueaqui.top/{dt_row_id}"
        else:
            item["Link"] = "nao_encontrado"
            
        return item
    
    # Se não encontrar nada, retorna objeto vazio com campos preenchidos com "nao_encontrado"
    # para evitar erro de mapeamento no BotConversa
    return {
        "Revenda": "nao_encontrado",
        "DT_RowId": "nao_encontrado",
        "Id_client": "nao_encontrado",
        "nome": "nao_encontrado",
        "telefone": "nao_encontrado",
        "plano": "nao_encontrado",
        "data_expiracao": "nao_encontrado",
        "Link": "nao_encontrado"
    }

@app.get("/revenda/adicionar")
def adicionar_revenda_get():
    return {"message": "Para adicionar uma revenda, use o método POST enviando o JSON no corpo da requisição."}

@app.post("/revenda/adicionar")
def adicionar_revenda(request: RevendaRequest):
    """
    Adiciona uma nova revenda ao arquivo de logins.
    """
    LOGINS_FILE = "revendas_logins.json"
    
    if not os.path.exists(LOGINS_FILE):
        logins = []
    else:
        try:
            with open(LOGINS_FILE, 'r', encoding='utf-8') as f:
                logins = json.load(f)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao ler arquivo de logins: {e}")
    
    # Verifica se já existe
    if any(l['email'] == request.email for l in logins):
        return {"status": "erro", "mensagem": "Revenda com este e-mail já existe."}
    
    # Gera filename se não fornecido
    filename = request.filename
    if not filename:
        # Normaliza o nome para ser usado no nome do arquivo
        clean_name = unicodedata.normalize('NFKD', request.nome).encode('ASCII', 'ignore').decode('ASCII')
        clean_name = re.sub(r'[^a-zA-Z0-9]', '', clean_name).lower()
        filename = f"revenda{clean_name}.json"
    
    new_revenda = {
        "nome": request.nome,
        "email": request.email,
        "password": request.password,
        "filename": filename
    }
    
    logins.append(new_revenda)
    
    try:
        with open(LOGINS_FILE, 'w', encoding='utf-8') as f:
            json.dump(logins, f, indent=4, ensure_ascii=False)
        return {"status": "sucesso", "mensagem": f"Revenda {request.nome} adicionada com sucesso.", "revenda": new_revenda}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar arquivo de logins: {e}")

class DeleteRevendaRequest(BaseModel):
    email: str

@app.delete("/revenda/excluir")
def excluir_revenda(request: DeleteRevendaRequest):
    """
    Exclui uma revenda do arquivo de logins pelo email.
    Body: { "email": "revenda@email.com" }
    """
    LOGINS_FILE = "revendas_logins.json"
    
    if not os.path.exists(LOGINS_FILE):
        return {"status": "erro", "mensagem": "Arquivo de logins não encontrado."}
    
    try:
        with open(LOGINS_FILE, 'r', encoding='utf-8') as f:
            logins = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao ler arquivo de logins: {e}")
    
    # Procura a revenda pelo email
    revenda_encontrada = None
    for i, revenda in enumerate(logins):
        if revenda['email'] == request.email:
            revenda_encontrada = logins.pop(i)
            break
    
    if not revenda_encontrada:
        return {"status": "erro", "mensagem": f"Revenda com email {request.email} não encontrada."}
    
    # Salva o arquivo atualizado
    try:
        with open(LOGINS_FILE, 'w', encoding='utf-8') as f:
            json.dump(logins, f, indent=4, ensure_ascii=False)
        
        # Também remove o arquivo JSON da revenda se existir
        filename = revenda_encontrada.get('filename')
        if filename and os.path.exists(filename):
            os.remove(filename)
        
        return {
            "status": "sucesso", 
            "mensagem": f"Revenda {revenda_encontrada['nome']} excluída com sucesso.",
            "revenda_removida": revenda_encontrada
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar arquivo de logins: {e}")

@app.get("/revenda/listar")
def listar_revendas():
    """
    Lista todas as revendas cadastradas com quantidade de clientes.
    """
    LOGINS_FILE = "revendas_logins.json"
    
    if not os.path.exists(LOGINS_FILE):
        return {"status": "sucesso", "total": 0, "revendas": []}
    
    try:
        with open(LOGINS_FILE, 'r', encoding='utf-8') as f:
            logins = json.load(f)
        
        # Retorna nome, email, filename e quantidade de clientes
        revendas_lista = []
        for r in logins:
            revenda_info = {
                "nome": r["nome"], 
                "email": r["email"], 
                "filename": r["filename"],
                "total_clientes": 0
            }
            
            # Conta clientes no arquivo JSON da revenda
            filename = r.get('filename')
            if filename and os.path.exists(filename):
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        clientes = json.load(f)
                        revenda_info["total_clientes"] = len(clientes)
                except:
                    pass
            
            revendas_lista.append(revenda_info)
        
        return {
            "status": "sucesso",
            "total": len(revendas_lista),
            "revendas": revendas_lista
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao ler arquivo de logins: {e}")

@app.post("/filtrar")
def filtrar_clientes(request: SearchRequest):
    """
    Retorna uma LISTA com todos os clientes encontrados pelo termo.
    Ideal para buscar por data (ex: '19/08/2025').
    """
    if df is None or df.empty:
        raise HTTPException(status_code=503, detail="Dados não carregados ou vazios.")
    
    q = request.termo
    if not q:
        return []
    
    termo = q.lower().strip()
    
    # Busca exata ou parcial (neste caso, parcial funciona bem para datas)
    mask = df.apply(lambda x: x.astype(str).str.lower().str.contains(termo, regex=False, na=False)).any(axis=1)
    
    resultados = df[mask]
    
    return resultados.to_dict(orient="records")

@app.get("/reload")
def reload_data():
    """Recarrega os dados do Excel sem reiniciar o servidor."""
    load_data()
    return {"message": "Dados recarregados.", "total_registros": len(df)}

# =============================================================================
# API EXTERNA - Consulta de Linhas
# =============================================================================

API_KEY_EXTERNA = "klxMbmr6pWOGO48GNvG746SWnQk_BMl3In4c_9IDpD4"
API_BASE_URL = "https://api.painel.best/lines/"  # Ajuste para a URL real da API

@app.post("/consultar-linha")
def consultar_linha_externa(request: SearchRequest):
    """
    Consulta a API externa buscando por número de telefone.
    Body: { "termo": "5511999999999" }
    """
    telefone = request.termo.strip()
    
    if not telefone:
        raise HTTPException(status_code=400, detail="Telefone não informado")
    
    # Remove caracteres não numéricos para a busca
    telefone_limpo = re.sub(r'[^\d]', '', telefone)
    
    headers = {
        'Api-Key': API_KEY_EXTERNA
    }
    
    params = {
        'search': telefone_limpo,
        'page': 1,
        'per_page': 100
    }
    
    try:
        response = requests.get(API_BASE_URL, headers=headers, params=params, timeout=30)
        
        # Debug - log do que foi retornado
        print(f"API Externa - Status: {response.status_code}")
        print(f"API Externa - URL: {response.url}")
        print(f"API Externa - Resposta (primeiros 500 chars): {response.text[:500]}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                # Formata a resposta de forma apresentável
                if data.get('results') and len(data['results']) > 0:
                    linha = data['results'][0]
                    
                    # Converte timestamps para datas legíveis
                    from datetime import datetime
                    exp_date = datetime.fromtimestamp(linha.get('exp_date', 0)).strftime('%d/%m/%Y') if linha.get('exp_date') else 'N/A'
                    created_at = datetime.fromtimestamp(linha.get('created_at', 0)).strftime('%d/%m/%Y') if linha.get('created_at') else 'N/A'
                    
                    resultado_formatado = {
                        "status": "✅ ENCONTRADO",
                        "telefone": linha.get('phone', 'N/A'),
                        "usuario": linha.get('username', 'N/A'),
                        "senha": linha.get('password', 'N/A'),
                        "vencimento": exp_date,
                        "dias_restantes": linha.get('countdown_exp_days', 'N/A'),
                        "status_conta": "Ativa" if linha.get('is_enabled') else "Desativada",
                        "e_teste": "Sim" if linha.get('is_trial') else "Não",
                        "criado_em": created_at,
                        "notas": linha.get('notes', ''),
                        "revenda": linha.get('user_username', 'N/A')
                    }
                    
                    return {
                        "status": "sucesso",
                        "telefone_buscado": telefone,
                        "total_encontrado": data.get('count', 0),
                        "linha": resultado_formatado
                    }
                else:
                    return {
                        "status": "nao_encontrado",
                        "telefone_buscado": telefone,
                        "mensagem": "Nenhuma linha encontrada com este telefone"
                    }
                    
            except json.JSONDecodeError:
                return {
                    "status": "erro",
                    "telefone_buscado": telefone,
                    "erro": "Resposta não é JSON válido",
                    "resposta_raw": response.text[:500]
                }
        else:
            return {
                "status": "erro",
                "telefone_buscado": telefone,
                "http_code": response.status_code,
                "resposta": response.text[:500]
            }
            
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Erro na API externa: {str(e)}")

@app.get("/consultar-linha/{telefone}")
def consultar_linha_externa_get(telefone: str):
    """
    Consulta a API externa passando o telefone na URL.
    Exemplo: /consultar-linha/5511999999999
    """
    if not telefone:
        raise HTTPException(status_code=400, detail="Telefone não informado")
    
    # Remove caracteres não numéricos
    telefone_limpo = re.sub(r'[^\d]', '', telefone)
    
    headers = {
        'Api-Key': API_KEY_EXTERNA
    }
    
    params = {
        'search': telefone_limpo,
        'page': 1,
        'per_page': 100
    }
    
    try:
        response = requests.get(API_BASE_URL, headers=headers, params=params, timeout=30)
        
        # Debug - log do que foi retornado
        print(f"API Externa GET - Status: {response.status_code}")
        print(f"API Externa GET - URL: {response.url}")
        print(f"API Externa GET - Resposta (primeiros 500 chars): {response.text[:500]}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                # Formata a resposta de forma apresentável
                if data.get('results') and len(data['results']) > 0:
                    linha = data['results'][0]
                    
                    # Converte timestamps para datas legíveis
                    from datetime import datetime
                    exp_date = datetime.fromtimestamp(linha.get('exp_date', 0)).strftime('%d/%m/%Y') if linha.get('exp_date') else 'N/A'
                    created_at = datetime.fromtimestamp(linha.get('created_at', 0)).strftime('%d/%m/%Y') if linha.get('created_at') else 'N/A'
                    
                    resultado_formatado = {
                        "status": "✅ ENCONTRADO",
                        "telefone": linha.get('phone', 'N/A'),
                        "usuario": linha.get('username', 'N/A'),
                        "senha": linha.get('password', 'N/A'),
                        "vencimento": exp_date,
                        "dias_restantes": linha.get('countdown_exp_days', 'N/A'),
                        "status_conta": "Ativa" if linha.get('is_enabled') else "Desativada",
                        "e_teste": "Sim" if linha.get('is_trial') else "Não",
                        "criado_em": created_at,
                        "notas": linha.get('notes', ''),
                        "revenda": linha.get('user_username', 'N/A')
                    }
                    
                    return {
                        "status": "sucesso",
                        "telefone_buscado": telefone,
                        "total_encontrado": data.get('count', 0),
                        "linha": resultado_formatado
                    }
                else:
                    return {
                        "status": "nao_encontrado",
                        "telefone_buscado": telefone,
                        "mensagem": "Nenhuma linha encontrada com este telefone"
                    }
                    
            except json.JSONDecodeError:
                return {
                    "status": "erro",
                    "telefone_buscado": telefone,
                    "erro": "Resposta não é JSON válido",
                    "resposta_raw": response.text[:500]
                }
        else:
            return {
                "status": "erro",
                "telefone_buscado": telefone,
                "http_code": response.status_code,
                "resposta": response.text[:500]
            }
            
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Erro na API externa: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    # Executa o servidor na porta 8080
    uvicorn.run(app, host="0.0.0.0", port=8080)
