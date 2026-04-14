from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import pandas as pd
import os
import json
import re
import unicodedata
import subprocess
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
        <title>Painel Revendas</title>
        <style>
            body {
                font-family: Arial;
                background: #0f172a;
                color: white;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
            }
            .box {
                background: #1e293b;
                padding: 30px;
                border-radius: 16px;
                text-align: center;
                width: 320px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.4);
            }
            button {
                background: #22c55e;
                border: none;
                padding: 12px;
                border-radius: 10px;
                width: 100%;
                font-size: 16px;
                cursor: pointer;
                color: white;
            }
            button:hover {
                opacity: 0.9;
            }
            #status {
                margin-top: 15px;
                font-size: 14px;
            }
        </style>
    </head>
    <body>
        <div class="box">
            <h2>🚀 Atualizar Revendas</h2>
            <p>Clique para atualizar os dados</p>
            <button onclick="atualizar()">Atualizar</button>
            <div id="status"></div>
        </div>

        <script>
            async function atualizar() {
                const status = document.getElementById("status");
                status.innerText = "⏳ Atualizando... aguarde";

                try {
                    const res = await fetch("/atualizar", {
                        method: "POST"
                    });

                    const data = await res.json();

                    if (res.ok) {
                        status.innerText = "✅ Atualizado! Total: " + data.total;
                    } else {
                        status.innerText = "❌ Erro: " + (data.detail || "falha");
                    }
                } catch (e) {
                    status.innerText = "❌ Erro de conexão";
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
        "data_expiracao": "nao_encontrado"
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

if __name__ == "__main__":
    import uvicorn
    # Executa o servidor na porta 8080
    uvicorn.run(app, host="0.0.0.0", port=8080)
