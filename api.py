from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import pandas as pd
import os
import json
import base64
import re
import unicodedata
import subprocess
import sys
import threading
import time
import secrets
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Optional

app = FastAPI(title="ServiÃ§o de Busca de Revendas")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, ".env")

def load_env_file(path=ENV_FILE):
    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip().lstrip("\ufeff")
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)

load_env_file()

EXCEL_FILE = os.path.join(BASE_DIR, "revendas_consolidadas.xlsx")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
LOG_DIR = os.path.join(BASE_DIR, "logs")
ACTION_HISTORY_FILE = os.path.join(LOG_DIR, "action_history.json")
MAXPLAYER_CACHE_FILE = os.path.join(LOG_DIR, "maxplayer_users_cache.json")
PAINEL_TEMPLATE = os.path.join(TEMPLATES_DIR, "painel.html")
PANEL_USERNAME = os.getenv("PANEL_USERNAME", "")
PANEL_PASSWORD = os.getenv("PANEL_PASSWORD", "")
PANEL_PASSWORD_ENABLED = bool(PANEL_PASSWORD)
df = None
df_search_text = None
df_phone_digits = None
update_lock = threading.Lock()
update_status = {
    "running": False,
    "status": "idle",
    "message": "Nenhuma atualizacao em andamento.",
    "total": None,
    "returncode": None
}
update_process = None
UPDATE_LOG_FILE = os.path.join(BASE_DIR, "update_all_revendas.log")
GESTOR_LOGIN_PAGE_URL = "https://app.gestorinove.com.br/login"
GESTOR_LOGIN_URL = "https://app.gestorinove.com.br/valida"
BOTCONVERSA_WEBHOOK_URL = os.getenv("BOTCONVERSA_WEBHOOK_URL", "")
security = HTTPBasic(auto_error=False)

if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

def require_panel_auth(credentials: Optional[HTTPBasicCredentials] = Depends(security)):
    if not PANEL_PASSWORD_ENABLED:
        return True

    valid_username = not PANEL_USERNAME or (
        credentials is not None and secrets.compare_digest(credentials.username, PANEL_USERNAME)
    )
    valid_password = credentials is not None and secrets.compare_digest(credentials.password, PANEL_PASSWORD)

    if not valid_username or not valid_password:
        raise HTTPException(
            status_code=401,
            detail="Autenticacao necessaria.",
            headers={"WWW-Authenticate": "Basic"}
        )

    return True

def require_setting(value, name):
    if not value:
        raise HTTPException(status_code=500, detail=f"{name} nao configurado no .env.")
    return value

def ensure_log_dir():
    os.makedirs(LOG_DIR, exist_ok=True)

def mask_secret(value):
    if value is None:
        return None

    text = str(value)
    if len(text) <= 6:
        return "***"
    return f"{text[:3]}***{text[-3:]}"

def sanitize_action_details(value):
    if isinstance(value, dict):
        sanitized = {}
        for key, item in value.items():
            if any(secret_key in key.lower() for secret_key in ["password", "senha", "token", "pass"]):
                sanitized[key] = mask_secret(item)
            else:
                sanitized[key] = sanitize_action_details(item)
        return sanitized

    if isinstance(value, list):
        return [sanitize_action_details(item) for item in value]

    return value

def log_action(action, status, details=None):
    ensure_log_dir()
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "status": status,
        "details": sanitize_action_details(details or {})
    }

    history = []
    if os.path.exists(ACTION_HISTORY_FILE):
        try:
            with open(ACTION_HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []

    history.append(entry)
    history = history[-500:]

    with open(ACTION_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    return entry


class SearchRequest(BaseModel):
    termo: str

class RevendaRequest(BaseModel):
    nome: str
    email: str
    password: str
    filename: Optional[str] = None

class CredenciaisRevendaRequest(BaseModel):
    email_atual: str
    novo_email: str
    nova_senha: Optional[str] = None

class MaxplayerCreateRequest(BaseModel):
    domain_id: str
    iptv_user: str
    iptv_pass: str
    username: Optional[str] = None
    user_password: Optional[str] = None
    user_email: Optional[str] = None
    fullname: Optional[str] = None

class MaxplayerEditListRequest(BaseModel):
    list_id: str
    domain_id: str
    new_list_name: str = "List 1"
    iptv_username: str
    iptv_password: str

class MaxplayerFreeCreateRequest(BaseModel):
    line_id: int
    domain_id: str

class BotConversaWebhookRequest(BaseModel):
    mensagem: str
    dados: Optional[dict] = None

def testar_login_gestor(email, password):
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })

    try:
        session.get(GESTOR_LOGIN_PAGE_URL, timeout=30)
        response = session.post(
            GESTOR_LOGIN_URL,
            data={"email": email, "senha": password, "redir": ""},
            timeout=30
        )

        if response.url == "https://app.gestorinove.com.br/painel" or "painel" in response.url:
            return True, "Login validado com sucesso."

        if "GESTOR_SESSION" in session.cookies:
            return True, "Login validado por cookie de sessao."

        response_text = unicodedata.normalize("NFKD", response.text).encode("ASCII", "ignore").decode("ASCII")
        response_text = response_text.lower()
        if "erro" in response_text or "invalido" in response_text:
            return False, "Credenciais invalidas no Gestor."

        return False, "Nao foi possivel confirmar o login no Gestor."
    except requests.exceptions.RequestException as e:
        return False, f"Erro ao conectar no Gestor: {e}"
    finally:
        session.close()

def load_data():
    global df, df_search_text, df_phone_digits
    if os.path.exists(EXCEL_FILE):
        try:
            print(f"Carregando {EXCEL_FILE}...")
            # LÃª todas as colunas como string para facilitar a busca
            df = pd.read_excel(EXCEL_FILE, dtype=str)
            # Preenche NaN com string vazia
            df = df.fillna("")
            df_search_text = df.astype(str).agg(" ".join, axis=1).str.lower()
            if "telefone" in df.columns:
                df_phone_digits = df["telefone"].astype(str).str.replace(r"[^\d]", "", regex=True)
            else:
                df_phone_digits = df.astype(str).agg(" ".join, axis=1).str.replace(r"[^\d]", "", regex=True)
            print(f"Colunas carregadas: {df.columns.tolist()}")
            print(f"Dados carregados: {len(df)} registros.")
        except Exception as e:
            print(f"Erro ao carregar Excel: {e}")
            df = pd.DataFrame()
            df_search_text = pd.Series(dtype=str)
            df_phone_digits = pd.Series(dtype=str)
    else:
        print(f"Arquivo {EXCEL_FILE} nÃ£o encontrado.")
        df = pd.DataFrame()
        df_search_text = pd.Series(dtype=str)
        df_phone_digits = pd.Series(dtype=str)

# Carrega os dados na inicializaÃ§Ã£o
def start_update_process():
    """Inicia o atualizador sem bloquear o processo da API."""
    global update_process

    script_path = os.path.join(BASE_DIR, "update_all_revendas.py")
    log_file = open(UPDATE_LOG_FILE, "w", encoding="utf-8")
    update_process = subprocess.Popen(
        [sys.executable, script_path],
        cwd=BASE_DIR,
        text=True,
        stdout=log_file,
        stderr=subprocess.STDOUT
    )
    return update_process

def get_update_log_tail():
    if not os.path.exists(UPDATE_LOG_FILE):
        return ""

    try:
        with open(UPDATE_LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return "".join(lines[-40:]).strip()
    except Exception as e:
        return f"Erro ao ler log: {e}"

def refresh_update_status():
    global update_process

    with update_lock:
        if update_process is None or not update_status["running"]:
            return update_status

        returncode = update_process.poll()
        if returncode is None:
            return update_status

        update_process = None
        update_status["running"] = False
        update_status["returncode"] = returncode

    if returncode == 0:
        load_data()
        update_status.update({
            "status": "success",
            "message": "Atualizado com sucesso",
            "total": len(df)
        })
    else:
        update_status.update({
            "status": "error",
            "message": get_update_log_tail() or "Falha ao executar update_all_revendas.py"
        })

    return update_status

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

@app.get("/config/status")
def config_status(_authenticated: bool = Depends(require_panel_auth)):
    panel = decode_maxplayer_panel_token() if MAXPLAYER_PANEL_TOKEN else {"group": None, "id": None}
    return {
        "status": "ok",
        "painel_protegido": PANEL_PASSWORD_ENABLED,
        "tokens": {
            "painel_best": bool(API_KEY_EXTERNA),
            "maxplayer_public": bool(MAXPLAYER_API_TOKEN),
            "maxplayer_panel": bool(MAXPLAYER_PANEL_TOKEN),
            "painel_apps": bool(PAINEL_APPS_USERNAME and PAINEL_APPS_PASSWORD),
            "botconversa_webhook": bool(BOTCONVERSA_WEBHOOK_URL)
        },
        "maxplayer": {
            "group": panel.get("group"),
            "id": panel.get("id"),
            "cache_seconds": MAXPLAYER_CACHE_SECONDS,
            "cache_file": os.path.exists(MAXPLAYER_CACHE_FILE)
        },
        "arquivos": {
            "template": os.path.exists(PAINEL_TEMPLATE),
            "static": os.path.isdir(STATIC_DIR),
            "historico": os.path.exists(ACTION_HISTORY_FILE)
        }
    }

@app.get("/historico/acoes")
def historico_acoes(limit: int = 50, _authenticated: bool = Depends(require_panel_auth)):
    if not os.path.exists(ACTION_HISTORY_FILE):
        return {"total": 0, "acoes": []}

    try:
        with open(ACTION_HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao ler historico: {e}")

    return {
        "total": len(history),
        "acoes": history[-max(1, min(limit, 200)):]
    }

@app.post("/botconversa/enviar")
def enviar_botconversa(request: BotConversaWebhookRequest, _authenticated: bool = Depends(require_panel_auth)):
    webhook_url = require_setting(BOTCONVERSA_WEBHOOK_URL, "BOTCONVERSA_WEBHOOK_URL")
    payload = {
        "mensagem": request.mensagem,
        "message": request.mensagem,
        **(request.dados or {})
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=20)
    except requests.exceptions.RequestException as e:
        log_action("botconversa_webhook", "erro", {"error": str(e), "payload": payload})
        raise HTTPException(status_code=503, detail=f"Erro ao enviar webhook BotConversa: {e}")

    if response.status_code >= 400:
        detail = response.text[:500]
        log_action("botconversa_webhook", "erro", {"http_code": response.status_code, "response": detail, "payload": payload})
        raise HTTPException(status_code=response.status_code, detail=f"BotConversa retornou HTTP {response.status_code}: {detail}")

    log_action("botconversa_webhook", "sucesso", {"http_code": response.status_code, "payload": payload})
    return {
        "status": "sucesso",
        "message": "Webhook enviado para o BotConversa.",
        "http_code": response.status_code
    }

@app.get("/painel", response_class=HTMLResponse)
def painel(_authenticated: bool = Depends(require_panel_auth)):
    with open(PAINEL_TEMPLATE, "r", encoding="utf-8") as template_file:
        return template_file.read()

@app.post("/atualizar")
def atualizar():
    refresh_update_status()

    with update_lock:
        if update_status["running"]:
            return JSONResponse(
                status_code=409,
                content={
                    "message": "Atualizacao ja esta em andamento.",
                    "status": update_status
                }
            )

        update_status.update({
            "running": True,
            "status": "running",
            "message": "Atualizacao iniciada.",
            "total": len(df) if df is not None else 0,
            "returncode": None
        })
        start_update_process()

    return JSONResponse(
        status_code=202,
        content={
            "message": "Atualizacao iniciada em background.",
            "status_url": "/atualizar/status",
            "status": update_status
        }
    )

@app.get("/atualizar/status")
def atualizar_status():
    return refresh_update_status()




@app.post("/")
def read_root_post(request: SearchRequest):
    """
    Alias para /buscar. Permite POST na raiz.
    """
    return buscar_cliente(request)

def build_client_search_mask(termo):
    termo = str(termo or "").lower().strip()
    if not termo:
        return pd.Series(False, index=df.index)

    source = df_search_text
    if source is None or len(source) != len(df):
        source = df.astype(str).agg(" ".join, axis=1).str.lower()

    candidates = [termo]
    if "+" in termo:
        candidates.append(termo.replace("+", ""))
    elif termo.isdigit():
        candidates.append("+" + termo)

    if "55" in termo:
        termo_sem_ddi = termo.replace("+55", "").replace("55", "", 1)
        if len(termo_sem_ddi) > 4:
            candidates.append(termo_sem_ddi)

    seen = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        mask = source.str.contains(candidate, regex=False, na=False)
        if mask.any():
            return mask

    digits_busca = re.sub(r"[^\d]", "", termo)
    if len(digits_busca) >= 8:
        sufixo = digits_busca[-8:]
        digits_source = df_phone_digits
        if digits_source is None or len(digits_source) != len(df):
            if "telefone" in df.columns:
                digits_source = df["telefone"].astype(str).str.replace(r"[^\d]", "", regex=True)
            else:
                digits_source = df.astype(str).agg(" ".join, axis=1).str.replace(r"[^\d]", "", regex=True)
        return digits_source.str.contains(sufixo, regex=False, na=False)

    return pd.Series(False, index=df.index)

def parse_payment_expiration(value):
    text = str(value or "").strip()
    if not text or text in {"N/A", "nao_encontrado", "nan", "None"}:
        return None

    if text.isdigit():
        try:
            return datetime.fromtimestamp(int(text))
        except (ValueError, OSError):
            return None

    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass

    return None

def is_test_client(item):
    fields = [item.get("plano"), item.get("nome"), item.get("Revenda")]
    text = " ".join(str(field or "").lower() for field in fields)
    return any(marker in text for marker in ["teste", "test", "trial", "demo"])

def enrich_payment_client(item):
    item = dict(item)

    if "telefone" in item:
        phone = str(item["telefone"])
        digits = re.sub(r"[^\d]", "", phone)
        item["telefone"] = f"+{digits}" if digits else phone

    dt_row_id = item.get("DT_RowId", "")
    if dt_row_id and str(dt_row_id) != "nao_encontrado":
        item["Link"] = f"https://pagueaqui.top/{dt_row_id}"
    else:
        item["Link"] = "nao_encontrado"

    expiration = parse_payment_expiration(item.get("data_expiracao"))
    if expiration:
        days_left = (expiration.date() - datetime.now().date()).days
        item["dias_restantes"] = days_left
        item["status_vencimento"] = "ativo" if days_left >= 0 else "vencido"
        item["vencimento_formatado"] = expiration.strftime("%d/%m/%Y")
    else:
        item["dias_restantes"] = "N/A"
        item["status_vencimento"] = "sem_data"
        item["vencimento_formatado"] = "N/A"

    item["e_teste"] = "Sim" if is_test_client(item) else "Nao"
    return item

def payment_client_sort_key(item):
    expiration = parse_payment_expiration(item.get("data_expiracao"))
    active_rank = 1 if item.get("status_vencimento") == "ativo" else 0
    timestamp = int(expiration.timestamp()) if expiration else 0
    return (active_rank, timestamp)

@app.post("/buscar")
def buscar_cliente(request: SearchRequest):
    """
    Busca um cliente em todas as colunas pelo termo enviado no corpo da requisiÃ§Ã£o.
    Body: { "termo": "valor da busca" }
    """
    if df is None or df.empty:
        raise HTTPException(status_code=503, detail="Dados nÃ£o carregados ou vazios.")
    
    q = request.termo
    if not q:
        return {"resultados": [], "total": 0}
    
    termo = q.lower().strip()
    
    # --- COMANDO INTERNO DE ATUALIZAÃ‡ÃƒO ---
    if termo == "atualizar":
        response = atualizar()
        status_code = getattr(response, "status_code", 202)
        return {
            "Revenda": "SISTEMA",
            "DT_RowId": "CMD_RUNNING" if status_code == 409 else "CMD_STARTED",
            "Id_client": "00000",
            "nome": "Atualizacao ja esta em andamento" if status_code == 409 else "Atualizacao iniciada",
            "telefone": "Rodando em background",
            "data_expiracao": "Consulte /atualizar/status"
        }
    # Remove o sinal de '+' se existir (ex: '+55...' -> '55...')
    # ATENÃ‡ÃƒO: Como agora os dados no Excel tÃªm '+', nÃ£o devemos remover o '+' da busca se o usuÃ¡rio mandar
    # Se o usuÃ¡rio mandar +55... e no banco estÃ¡ +55..., deve casar.
    # Se o usuÃ¡rio mandar 55... e no banco estÃ¡ +55..., o contains nÃ£o vai casar direto se for exato,
    # mas '55...' estÃ¡ contido em '+55...', entÃ£o contains funciona.
    # O problema Ã© se removermos o '+' da busca (+55 -> 55), e no banco Ã© +55.
    # 55 estÃ¡ em +55? Sim.
    # Mas se a lÃ³gica anterior removia, por que falhava?
    # Talvez o usuÃ¡rio mande +555185216088.
    # CÃ³digo remove + -> 555185216088.
    # Banco tem +555185216088 (se foi atualizado corretamente).
    # '555185216088' estÃ¡ em '+555185216088'? Sim.
    # EntÃ£o deveria funcionar.
    # Mas vamos garantir que a busca seja mais flexÃ­vel: buscar com e sem o +
    
    # Se o termo tem +, vamos tentar buscar exatamente como veio primeiro
    # Se nÃ£o encontrar, tentamos sem o +
    
    mask = build_client_search_mask(termo)
    
    # Se nÃ£o achou e tem +, tenta sem o +
    if False and not mask.any() and "+" in termo:
        termo_sem_plus = termo.replace("+", "")
        mask = df.apply(lambda x: x.astype(str).str.lower().str.contains(termo_sem_plus, regex=False, na=False)).any(axis=1)
    
    # Se nÃ£o achou e NÃƒO tem +, tenta COM o + (caso o usuÃ¡rio mande sem e no banco tenha)
    if False and not mask.any() and "+" not in termo and termo.isdigit():
         termo_com_plus = "+" + termo
         mask = df.apply(lambda x: x.astype(str).str.lower().str.contains(termo_com_plus, regex=False, na=False)).any(axis=1)
         
    # Se ainda nÃ£o achou, e o termo comeÃ§a com 55 (DDI Brasil), tenta sem o 55
    # Ex: Busca +5551... mas no banco estÃ¡ +51...
    if False and not mask.any() and "55" in termo:
        # Tenta remover +55 ou apenas 55 do inÃ­cio
        termo_sem_ddi = termo.replace("+55", "").replace("55", "", 1)
        # Se ficou vazio ou muito curto, ignora
        if len(termo_sem_ddi) > 4:
             mask = df.apply(lambda x: x.astype(str).str.lower().str.contains(termo_sem_ddi, regex=False, na=False)).any(axis=1)

    # BUSCA ROBUSTA POR SUFIXO (ÃšLTIMA TENTATIVA)
    # Se ainda nÃ£o encontrou, vamos comparar apenas os DÃGITOS.
    # Se o usuÃ¡rio mandou um nÃºmero com pelo menos 8 dÃ­gitos,
    # verificamos se esses dÃ­gitos finais existem em algum telefone do banco.
    if False and not mask.any():
        import re
        # Extrai apenas dÃ­gitos da busca
        digits_busca = re.sub(r'[^\d]', '', termo)
        
        # SÃ³ aplica se tiver pelo menos 8 dÃ­gitos (evitar match falso em nÃºmeros curtos)
        if len(digits_busca) >= 8:
            # Pega os Ãºltimos 8 dÃ­gitos (suficiente para identificar unicamente na maioria dos casos)
            sufixo = digits_busca[-8:]
            
            # FunÃ§Ã£o auxiliar para verificar se o telefone da linha contÃ©m esse sufixo
            def check_suffix(val):
                val_str = str(val)
                # Extrai dÃ­gitos do valor da cÃ©lula
                val_digits = re.sub(r'[^\d]', '', val_str)
                return sufixo in val_digits
            
            # Aplica apenas na coluna 'telefone' (mais eficiente e preciso)
            if 'telefone' in df.columns:
                mask = df['telefone'].apply(check_suffix)
            else:
                # Se nÃ£o tiver coluna telefone explÃ­cita, tenta em todas (mais lento)
                mask = df.apply(lambda row: row.astype(str).apply(lambda x: sufixo in re.sub(r'[^\d]', '', x)).any(), axis=1)

    resultados = df[mask]
    
    # Converte para lista de dicionÃ¡rios
    lista_resultados = [
        enrich_payment_client(item)
        for item in resultados.to_dict(orient="records")
        if not is_test_client(item)
    ]
    lista_resultados.sort(key=payment_client_sort_key, reverse=True)
    
    if lista_resultados:
        item = dict(lista_resultados[0])
        item["resultados"] = lista_resultados
        item["total"] = len(lista_resultados)
        return item
    
    # Se nÃ£o encontrar nada, retorna objeto vazio com campos preenchidos com "nao_encontrado"
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
    return {"message": "Para adicionar uma revenda, use o mÃ©todo POST enviando o JSON no corpo da requisiÃ§Ã£o."}

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
    
    # Verifica se jÃ¡ existe
    if any(l['email'] == request.email for l in logins):
        return {"status": "erro", "mensagem": "Revenda com este e-mail jÃ¡ existe."}
    
    # Gera filename se nÃ£o fornecido
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

@app.put("/revenda/credenciais")
def atualizar_credenciais_revenda(request: CredenciaisRevendaRequest):
    """
    Atualiza email e senha de uma revenda existente apos validar o novo login no Gestor.
    Mantem o mesmo arquivo JSON da revenda para preservar os dados locais.
    Body: { "email_atual": "...", "novo_email": "...", "nova_senha": "..." }
    Se nova_senha nao for enviada, reutiliza a senha atual cadastrada.
    """
    LOGINS_FILE = os.path.join(BASE_DIR, "revendas_logins.json")
    email_atual = request.email_atual.strip()
    novo_email = request.novo_email.strip()
    nova_senha = request.nova_senha

    if not email_atual or not novo_email:
        raise HTTPException(status_code=400, detail="Informe email_atual e novo_email.")

    if not os.path.exists(LOGINS_FILE):
        return {"status": "erro", "mensagem": "Arquivo de logins nao encontrado."}

    try:
        with open(LOGINS_FILE, "r", encoding="utf-8") as f:
            logins = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao ler arquivo de logins: {e}")

    revenda_index = None
    for i, revenda in enumerate(logins):
        if revenda.get("email", "").casefold() == email_atual.casefold():
            revenda_index = i
            break

    if revenda_index is None:
        return {"status": "erro", "mensagem": f"Revenda com email {email_atual} nao encontrada."}

    revenda = logins[revenda_index]
    if nova_senha is None or nova_senha == "":
        nova_senha = revenda.get("password", "")

    if not nova_senha:
        raise HTTPException(status_code=400, detail="Informe nova_senha. A revenda encontrada nao tem senha cadastrada.")

    email_duplicado = any(
        i != revenda_index and revenda.get("email", "").casefold() == novo_email.casefold()
        for i, revenda in enumerate(logins)
    )
    if email_duplicado:
        return {"status": "erro", "mensagem": "Ja existe outra revenda cadastrada com este novo email."}

    login_valido, mensagem_login = testar_login_gestor(novo_email, nova_senha)
    if not login_valido:
        return {
            "status": "erro",
            "mensagem": "As novas credenciais nao foram salvas porque o login no Gestor falhou.",
            "detalhe": mensagem_login
        }

    email_anterior = revenda.get("email")
    revenda["email"] = novo_email
    revenda["password"] = nova_senha

    try:
        with open(LOGINS_FILE, "w", encoding="utf-8") as f:
            json.dump(logins, f, indent=4, ensure_ascii=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar arquivo de logins: {e}")

    return {
        "status": "sucesso",
        "mensagem": f"Credenciais da revenda {revenda.get('nome', '')} atualizadas com sucesso.",
        "login_teste": mensagem_login,
        "revenda": {
            "nome": revenda.get("nome"),
            "email_anterior": email_anterior,
            "email": revenda.get("email"),
            "filename": revenda.get("filename")
        }
    }

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
        return {"status": "erro", "mensagem": "Arquivo de logins nÃ£o encontrado."}
    
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
        return {"status": "erro", "mensagem": f"Revenda com email {request.email} nÃ£o encontrada."}
    
    # Salva o arquivo atualizado
    try:
        with open(LOGINS_FILE, 'w', encoding='utf-8') as f:
            json.dump(logins, f, indent=4, ensure_ascii=False)
        
        # TambÃ©m remove o arquivo JSON da revenda se existir
        filename = revenda_encontrada.get('filename')
        if filename and os.path.exists(filename):
            os.remove(filename)
        
        return {
            "status": "sucesso", 
            "mensagem": f"Revenda {revenda_encontrada['nome']} excluÃ­da com sucesso.",
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
        raise HTTPException(status_code=503, detail="Dados nÃ£o carregados ou vazios.")
    
    q = request.termo
    if not q:
        return []
    
    termo = q.lower().strip()
    
    # Busca exata ou parcial (neste caso, parcial funciona bem para datas)
    mask = build_client_search_mask(termo)
    
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

API_KEY_EXTERNA = os.getenv("PAINEL_BEST_API_KEY", "")
API_BASE_URL = os.getenv("PAINEL_BEST_BASE_URL", "https://api.painel.best/lines/")

def normalize_linha_search_term(value):
    text = str(value or "").strip()
    digits = re.sub(r"[^\d]", "", text)
    if len(digits) >= 8:
        return digits
    return text

def build_m3u_url(linha, url_type):
    username = linha.get("username")
    password = linha.get("password")
    dns = linha.get("dns")
    if not username or not password or not dns:
        return "N/A"

    base = str(dns).strip()
    if not base.startswith(("http://", "https://")):
        base = "http://" + base
    return f"{base}/get.php?username={username}&password={password}&type={url_type}&output=ts"

def format_timestamp_date(value, with_time=False):
    if not value:
        return "N/A"

    try:
        fmt = "%d/%m/%Y as %H:%M" if with_time else "%d/%m/%Y"
        return datetime.fromtimestamp(int(value)).strftime(fmt)
    except (TypeError, ValueError, OSError):
        return "N/A"

def format_linha_externa(linha):
    return {
        "status": "ENCONTRADO",
        "id": linha.get("id", "N/A"),
        "telefone": linha.get("phone", "N/A"),
        "usuario": linha.get("username", "N/A"),
        "senha": linha.get("password", "N/A"),
        "vencimento": format_timestamp_date(linha.get("exp_date")),
        "vencimento_completo": format_timestamp_date(linha.get("exp_date"), with_time=True),
        "telas": linha.get("max_connections") or linha.get("connections") or 1,
        "dias_restantes": linha.get("countdown_exp_days", "N/A"),
        "status_conta": "Ativa" if linha.get("is_enabled") else "Desativada",
        "status_interno": linha.get("status", "N/A"),
        "e_teste": "Sim" if linha.get("is_trial") else "Nao",
        "criado_em": format_timestamp_date(linha.get("created_at")),
        "atualizado_em": format_timestamp_date(linha.get("updated_at"), with_time=True),
        "dns": linha.get("dns", "N/A"),
        "url_m3u": build_m3u_url(linha, "m3u"),
        "url_m3u_plus": build_m3u_url(linha, "m3u_plus"),
        "email": linha.get("email", "N/A"),
        "valor_plano": linha.get("plan_value", "N/A"),
        "tipo": linha.get("type", "N/A"),
        "bouquet_ids": linha.get("bouquet_ids") or [],
        "notas": linha.get("notes", ""),
        "revenda": linha.get("user_username", "N/A"),
        "revenda_id": linha.get("user_id", "N/A")
    }

@app.post("/consultar-linha")
def consultar_linha_externa(request: SearchRequest):
    """
    Consulta a API externa buscando por nÃºmero de telefone.
    Body: { "termo": "5511999999999" }
    """
    api_key = require_setting(API_KEY_EXTERNA, "PAINEL_BEST_API_KEY")
    telefone = request.termo.strip()
    
    if not telefone:
        raise HTTPException(status_code=400, detail="Telefone nÃ£o informado")
    
    # Remove caracteres nÃ£o numÃ©ricos para a busca
    termo_busca = normalize_linha_search_term(telefone)
    
    headers = {
        'Api-Key': api_key
    }
    
    params = {
        'search': termo_busca,
        'page': 1,
        'per_page': 100
    }
    
    try:
        response = requests.get(API_BASE_URL, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            try:
                data = response.json()
                # Formata a resposta de forma apresentÃ¡vel
                if data.get('results') and len(data['results']) > 0:
                    linha = data['results'][0]
                    
                    # Converte timestamps para datas legÃ­veis
                    from datetime import datetime
                    exp_date = datetime.fromtimestamp(linha.get('exp_date', 0)).strftime('%d/%m/%Y') if linha.get('exp_date') else 'N/A'
                    exp_date_full = datetime.fromtimestamp(linha.get('exp_date', 0)).strftime('%d/%m/%Y as %H:%M') if linha.get('exp_date') else 'N/A'
                    created_at = datetime.fromtimestamp(linha.get('created_at', 0)).strftime('%d/%m/%Y') if linha.get('created_at') else 'N/A'
                    
                    resultado_formatado = {
                        "status": "ENCONTRADO",
                        "telefone": linha.get('phone', 'N/A'),
                        "usuario": linha.get('username', 'N/A'),
                        "senha": linha.get('password', 'N/A'),
                        "vencimento": exp_date,
                        "vencimento_completo": exp_date_full,
                        "telas": linha.get('max_connections') or linha.get('connections') or 1,
                        "dias_restantes": linha.get('countdown_exp_days', 'N/A'),
                        "status_conta": "Ativa" if linha.get('is_enabled') else "Desativada",
                        "e_teste": "Sim" if linha.get('is_trial') else "Nao",
                        "criado_em": created_at,
                        "notas": linha.get('notes', ''),
                        "revenda": linha.get('user_username', 'N/A')
                    }
                    resultado_formatado = format_linha_externa(linha)
                    
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
                    "erro": "Resposta nÃ£o Ã© JSON vÃ¡lido",
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
        raise HTTPException(status_code=400, detail="Telefone nÃ£o informado")
    
    api_key = require_setting(API_KEY_EXTERNA, "PAINEL_BEST_API_KEY")

    # Remove caracteres nÃ£o numÃ©ricos
    termo_busca = normalize_linha_search_term(telefone)
    
    headers = {
        'Api-Key': api_key
    }
    
    params = {
        'search': termo_busca,
        'page': 1,
        'per_page': 100
    }
    
    try:
        response = requests.get(API_BASE_URL, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            try:
                data = response.json()
                # Formata a resposta de forma apresentÃ¡vel
                if data.get('results') and len(data['results']) > 0:
                    linha = data['results'][0]
                    
                    # Converte timestamps para datas legÃ­veis
                    from datetime import datetime
                    exp_date = datetime.fromtimestamp(linha.get('exp_date', 0)).strftime('%d/%m/%Y') if linha.get('exp_date') else 'N/A'
                    exp_date_full = datetime.fromtimestamp(linha.get('exp_date', 0)).strftime('%d/%m/%Y as %H:%M') if linha.get('exp_date') else 'N/A'
                    created_at = datetime.fromtimestamp(linha.get('created_at', 0)).strftime('%d/%m/%Y') if linha.get('created_at') else 'N/A'
                    
                    resultado_formatado = {
                        "status": "ENCONTRADO",
                        "telefone": linha.get('phone', 'N/A'),
                        "usuario": linha.get('username', 'N/A'),
                        "senha": linha.get('password', 'N/A'),
                        "vencimento": exp_date,
                        "vencimento_completo": exp_date_full,
                        "telas": linha.get('max_connections') or linha.get('connections') or 1,
                        "dias_restantes": linha.get('countdown_exp_days', 'N/A'),
                        "status_conta": "Ativa" if linha.get('is_enabled') else "Desativada",
                        "e_teste": "Sim" if linha.get('is_trial') else "Nao",
                        "criado_em": created_at,
                        "notas": linha.get('notes', ''),
                        "revenda": linha.get('user_username', 'N/A')
                    }
                    resultado_formatado = format_linha_externa(linha)
                    
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
                    "erro": "Resposta nÃ£o Ã© JSON vÃ¡lido",
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

# =============================================================================
# API EXTERNA - MaxPlayer
# =============================================================================

MAXPLAYER_API_TOKEN = os.getenv("MAXPLAYER_API_TOKEN", "")
MAXPLAYER_PANEL_TOKEN = os.getenv("MAXPLAYER_PANEL_TOKEN", "")
MAXPLAYER_USERS_URL = "https://api.maxplayer.tv/v3/api/public/users"
MAXPLAYER_PANEL_BASE_URL = "https://api.maxplayer.tv/v3"
MAXPLAYER_CACHE_SECONDS = int(os.getenv("MAXPLAYER_CACHE_SECONDS", "1800"))
maxplayer_cache = {
    "loaded_at": 0,
    "users": None
}
maxplayer_cache_lock = threading.Lock()

PAINEL_APPS_BASE_URL = os.getenv("PAINEL_APPS_BASE_URL", "https://apps-api.painel.best")
PAINEL_APPS_USERNAME = os.getenv("PAINEL_APPS_USERNAME", "")
PAINEL_APPS_PASSWORD = os.getenv("PAINEL_APPS_PASSWORD", "")
apps_token_cache = {
    "token": None,
    "expires_at": 0
}
apps_data_cache = {}
apps_cache_lock = threading.Lock()

def decode_maxplayer_panel_token():
    try:
        token = MAXPLAYER_PANEL_TOKEN.replace("Bearer ", "")
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        decoded = json.loads(base64.urlsafe_b64decode(payload.encode("utf-8")).decode("utf-8"))
        return {
            "group": decoded.get("group", "reseller"),
            "id": decoded.get("id")
        }
    except Exception:
        return {
            "group": "reseller",
            "id": None
        }

def maxplayer_panel_headers(content_type="application/x-www-form-urlencoded"):
    token = require_setting(MAXPLAYER_PANEL_TOKEN, "MAXPLAYER_PANEL_TOKEN").replace("Bearer ", "")

    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": content_type
    }

def clear_maxplayer_cache():
    with maxplayer_cache_lock:
        maxplayer_cache["users"] = None
        maxplayer_cache["loaded_at"] = 0
    if os.path.exists(MAXPLAYER_CACHE_FILE):
        try:
            os.remove(MAXPLAYER_CACHE_FILE)
        except OSError:
            pass

def read_maxplayer_cache_file():
    if not os.path.exists(MAXPLAYER_CACHE_FILE):
        return None

    try:
        with open(MAXPLAYER_CACHE_FILE, "r", encoding="utf-8") as f:
            cached = json.load(f)
    except Exception:
        return None

    loaded_at = cached.get("loaded_at", 0)
    users = cached.get("users")
    if not isinstance(users, list):
        return None

    if time.time() - loaded_at > MAXPLAYER_CACHE_SECONDS:
        return None

    return users, loaded_at

def write_maxplayer_cache_file(users):
    ensure_log_dir()
    with open(MAXPLAYER_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {
                "loaded_at": time.time(),
                "users": users
            },
            f,
            ensure_ascii=False
        )

def apps_login_token():
    now = time.time()
    with apps_cache_lock:
        token = apps_token_cache["token"]
        expires_at = apps_token_cache["expires_at"]
        if token and now < expires_at - 60:
            return token

    username = require_setting(PAINEL_APPS_USERNAME, "PAINEL_APPS_USERNAME")
    password = require_setting(PAINEL_APPS_PASSWORD, "PAINEL_APPS_PASSWORD")

    try:
        response = requests.post(
            f"{PAINEL_APPS_BASE_URL}/login",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://apps.painel.best",
                "Referer": "https://apps.painel.best/"
            },
            data={"username": username, "password": password},
            timeout=45
        )
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Erro ao conectar no Painel Apps: {str(e)}")

    try:
        data = response.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="Painel Apps retornou uma resposta que nao e JSON valido.")

    if not response.ok:
        raise HTTPException(status_code=response.status_code, detail=data.get("detail") or data.get("message") or response.text[:300])

    token = data.get("access_token")
    if not token:
        raise HTTPException(status_code=502, detail="Painel Apps nao retornou access_token.")

    with apps_cache_lock:
        apps_token_cache["token"] = token
        apps_token_cache["expires_at"] = time.time() + int(data.get("expires_in") or 7200)

    return token

def apps_headers():
    return {
        "Authorization": f"Bearer {apps_login_token()}",
        "Origin": "https://apps.painel.best",
        "Referer": "https://apps.painel.best/"
    }

def apps_get(path, cache_key=None):
    now = time.time()
    if cache_key:
        with apps_cache_lock:
            cached = apps_data_cache.get(cache_key)
            if cached and now - cached["loaded_at"] < MAXPLAYER_CACHE_SECONDS:
                return cached["data"], True

    try:
        response = requests.get(
            f"{PAINEL_APPS_BASE_URL}{path}",
            headers=apps_headers(),
            timeout=60
        )
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Erro ao conectar no Painel Apps: {str(e)}")

    try:
        data = response.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="Painel Apps retornou uma resposta que nao e JSON valido.")

    if not response.ok:
        raise HTTPException(status_code=response.status_code, detail=data.get("detail") or data.get("message") or response.text[:300])

    if cache_key:
        with apps_cache_lock:
            apps_data_cache[cache_key] = {"loaded_at": time.time(), "data": data}

    return data, False

def apps_post(path, payload):
    try:
        response = requests.post(
            f"{PAINEL_APPS_BASE_URL}{path}",
            headers={**apps_headers(), "Content-Type": "application/json"},
            json=payload,
            timeout=60
        )
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Erro ao conectar no Painel Apps: {str(e)}")

    try:
        data = response.json()
    except json.JSONDecodeError:
        data = {"raw": response.text[:500]}

    if not response.ok:
        raise HTTPException(status_code=response.status_code, detail=data.get("detail") or data.get("message") or data.get("error") or response.text[:300])

    with apps_cache_lock:
        apps_data_cache.pop("maxplayer_free_users", None)
        apps_data_cache.pop("apps_lines", None)

    return data

def get_maxplayer_users(force_refresh=False):
    now = time.time()

    with maxplayer_cache_lock:
        users = maxplayer_cache["users"]
        loaded_at = maxplayer_cache["loaded_at"]
        if users is not None and not force_refresh and now - loaded_at < MAXPLAYER_CACHE_SECONDS:
            return users, True

    if not force_refresh:
        cached_file = read_maxplayer_cache_file()
        if cached_file:
            users, loaded_at = cached_file
            with maxplayer_cache_lock:
                maxplayer_cache["users"] = users
                maxplayer_cache["loaded_at"] = loaded_at
            return users, True

    headers = {
        "Api-Token": require_setting(MAXPLAYER_API_TOKEN, "MAXPLAYER_API_TOKEN"),
        "Content-Type": "application/x-www-form-urlencoded"
    }

    try:
        response = requests.get(MAXPLAYER_USERS_URL, headers=headers, timeout=45)
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Erro ao conectar no MaxPlayer: {str(e)}")

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"MaxPlayer retornou HTTP {response.status_code}: {response.text[:300]}"
        )

    try:
        data = response.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="MaxPlayer retornou uma resposta que nao e JSON valido.")

    if not isinstance(data, list):
        raise HTTPException(status_code=502, detail="Resposta inesperada do MaxPlayer: era esperado uma lista de usuarios.")

    with maxplayer_cache_lock:
        maxplayer_cache["users"] = data
        maxplayer_cache["loaded_at"] = time.time()

    write_maxplayer_cache_file(data)

    return data, False

def normalize_search_value(value):
    return str(value or "").strip().lower()

def maxplayer_user_matches(user, termo):
    termo = normalize_search_value(termo)
    termo_numerico = re.sub(r"[^\d]", "", termo)

    candidates = [
        user.get("id"),
        user.get("username"),
        user.get("email")
    ]

    for item in user.get("lists") or []:
        candidates.extend([
            item.get("id"),
            item.get("name")
        ])
        iptv_info = item.get("iptv_info") or {}
        candidates.extend([
            iptv_info.get("username"),
            iptv_info.get("password"),
            iptv_info.get("fqdn")
        ])

    for candidate in candidates:
        value = normalize_search_value(candidate)
        if not value:
            continue

        value_numerico = re.sub(r"[^\d]", "", value)
        if termo == value or termo in value:
            return True
        if termo_numerico and (termo_numerico == value_numerico or termo_numerico in value_numerico):
            return True

    return False

def format_maxplayer_user(user):
    lists = []
    for item in user.get("lists") or []:
        iptv_info = item.get("iptv_info") or {}
        lists.append({
            "id": item.get("id"),
            "nome": item.get("name"),
            "dominio_id": item.get("domain_id"),
            "iptv": {
                "tipo": iptv_info.get("type"),
                "fqdn": iptv_info.get("fqdn"),
                "porta": iptv_info.get("port"),
                "ssl": iptv_info.get("ssl"),
                "usuario": iptv_info.get("username"),
                "senha": iptv_info.get("password")
            }
        })

    return {
        "id": user.get("id"),
        "usuario": user.get("username"),
        "email": user.get("email"),
        "vencimento": user.get("exp_date"),
        "telas": user.get("max_connections") or user.get("connections") or 1,
        "listas": lists
    }

def get_apps_lines():
    lines, from_cache = apps_get("/lines", "apps_lines")
    if not isinstance(lines, list):
        raise HTTPException(status_code=502, detail="Resposta inesperada do Painel Apps: era esperada uma lista de linhas.")
    return lines, from_cache

def get_maxplayer_free_users():
    users, from_cache = apps_get("/max-player/users", "maxplayer_free_users")
    if not isinstance(users, list):
        raise HTTPException(status_code=502, detail="Resposta inesperada do MaxPlayer Free: era esperada uma lista de usuarios.")
    return users, from_cache

def get_maxplayer_free_domains():
    domains, from_cache = apps_get("/max-player/domains", "maxplayer_free_domains")
    if not isinstance(domains, list):
        raise HTTPException(status_code=502, detail="Resposta inesperada do MaxPlayer Free: era esperada uma lista de dominios.")
    return domains, from_cache

def line_apps_matches(line, termo):
    termo = normalize_search_value(termo)
    termo_numerico = re.sub(r"[^\d]", "", termo)
    candidates = [line.get("id"), line.get("username"), line.get("password")]

    for candidate in candidates:
        value = normalize_search_value(candidate)
        if not value:
            continue

        value_numerico = re.sub(r"[^\d]", "", value)
        if termo == value or termo in value:
            return True
        if termo_numerico and (termo_numerico == value_numerico or termo_numerico in value_numerico):
            return True

    return False

def maxplayer_free_user_matches(user, termo):
    termo = normalize_search_value(termo)
    termo_numerico = re.sub(r"[^\d]", "", termo)
    candidates = [user.get("id"), user.get("line_id"), user.get("username"), user.get("password"), user.get("domain_id")]

    for candidate in candidates:
        value = normalize_search_value(candidate)
        if not value:
            continue

        value_numerico = re.sub(r"[^\d]", "", value)
        if termo == value or termo in value:
            return True
        if termo_numerico and (termo_numerico == value_numerico or termo_numerico in value_numerico):
            return True

    return False

def format_apps_line(line):
    return {
        "id": line.get("id"),
        "usuario": line.get("username"),
        "senha": line.get("password"),
        "vencimento": line.get("exp_date"),
        "telas": line.get("max_connections") or line.get("connections") or 1,
        "e_teste": "Sim" if line.get("is_trial") else "Nao"
    }

def format_maxplayer_free_user(user, domain_map=None):
    domain_map = domain_map or {}
    domain_id = str(user.get("domain_id") or "")
    return {
        "id": user.get("id"),
        "line_id": user.get("line_id"),
        "usuario": user.get("username"),
        "senha": user.get("password"),
        "vencimento": user.get("exp_date"),
        "telas": user.get("max_connections") or user.get("connections") or 1,
        "dominio_id": domain_id,
        "dominio": domain_map.get(domain_id, domain_id),
        "e_teste": "Sim" if user.get("is_trial") else "Nao"
    }

def maxplayer_panel_post(path, payload):
    try:
        response = requests.post(
            f"{MAXPLAYER_PANEL_BASE_URL}{path}",
            headers=maxplayer_panel_headers(),
            data=payload,
            timeout=45
        )
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Erro ao conectar no painel MaxPlayer: {str(e)}")

    try:
        body = response.json()
    except json.JSONDecodeError:
        body = {"raw": response.text[:500]}

    if not response.ok:
        detail = body.get("error") or body.get("message") or response.text[:500]
        raise HTTPException(status_code=response.status_code, detail=detail)

    clear_maxplayer_cache()
    return body

@app.get("/maxplayer/domains")
def listar_maxplayer_domains():
    panel = decode_maxplayer_panel_token()
    group = panel["group"] or "reseller"
    path = f"/api/panel/view/{group}/domains"

    try:
        response = requests.get(
            f"{MAXPLAYER_PANEL_BASE_URL}{path}",
            headers=maxplayer_panel_headers("application/json"),
            timeout=45
        )
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Erro ao conectar no MaxPlayer: {str(e)}")

    try:
        data = response.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="MaxPlayer retornou uma resposta que nao e JSON valido.")

    if not response.ok:
        raise HTTPException(status_code=response.status_code, detail=data.get("error") or data.get("message") or response.text[:500])

    content = data.get("data") or {}
    return {
        "status": "sucesso",
        "group": group,
        "domains": content.get("domains") or [],
        "groups": content.get("groups") or []
    }

@app.post("/maxplayer/usuario/criar")
def criar_usuario_maxplayer(request: MaxplayerCreateRequest):
    panel = decode_maxplayer_panel_token()
    group = panel["group"] or "reseller"

    payload = {
        "domain_id": request.domain_id,
        "iptv_user": request.iptv_user,
        "iptv_pass": request.iptv_pass
    }

    if request.username:
        payload["username"] = request.username
    if request.user_password:
        payload["user_password"] = request.user_password
    if request.user_email:
        payload["user_email"] = request.user_email
    if request.fullname:
        payload["fullname"] = request.fullname

    try:
        result = maxplayer_panel_post(f"/api/panel/actions/{group}/create-user", payload)
        log_action("maxplayer_create_user", "sucesso", {"group": group, "payload": payload, "result": result})
    except HTTPException as e:
        log_action("maxplayer_create_user", "erro", {"group": group, "payload": payload, "error": e.detail})
        raise

    return {
        "status": "sucesso",
        "message": "Usuario criado no MaxPlayer.",
        "result": result
    }

@app.post("/maxplayer/usuario/prevalidar")
def prevalidar_criacao_maxplayer(request: SearchRequest):
    data = consulta_cliente_unificada(request)
    linha = data.get("linha", {}).get("linha", {})
    maxplayer = data.get("maxplayer", {})

    can_create = (
        maxplayer.get("status") != "sucesso"
        and bool(linha.get("usuario"))
        and linha.get("usuario") != "N/A"
        and bool(linha.get("senha"))
        and linha.get("senha") != "N/A"
    )

    return {
        "status": "ok",
        "pode_criar": can_create,
        "motivo": "Pronto para criar no MaxPlayer." if can_create else "Nao foi possivel montar usuario/senha IPTV ou usuario ja existe.",
        "sugestao": {
            "iptv_user": linha.get("usuario"),
            "iptv_pass": mask_secret(linha.get("senha")),
            "telefone": data.get("telefone_normalizado")
        },
        "resumo": data.get("resumo")
    }

@app.post("/maxplayer/lista/dominio")
def trocar_dominio_lista_maxplayer(request: MaxplayerEditListRequest):
    panel = decode_maxplayer_panel_token()
    group = panel["group"] or "reseller"

    payload = {
        "list_id": request.list_id,
        "domain_id": request.domain_id,
        "new_list_name": request.new_list_name,
        "iptv_username": request.iptv_username,
        "iptv_password": request.iptv_password
    }

    try:
        result = maxplayer_panel_post(f"/api/panel/actions/{group}/edit-list", payload)
        log_action("maxplayer_edit_list_domain", "sucesso", {"group": group, "payload": payload, "result": result})
    except HTTPException as e:
        log_action("maxplayer_edit_list_domain", "erro", {"group": group, "payload": payload, "error": e.detail})
        raise

    return {
        "status": "sucesso",
        "message": "Dominio atualizado no MaxPlayer.",
        "result": result
    }

@app.post("/maxplayer/usuario")
def pesquisar_usuario_maxplayer(request: SearchRequest):
    termo = request.termo.strip()
    if not termo:
        raise HTTPException(status_code=400, detail="Usuario nao informado")

    users, from_cache = get_maxplayer_users()
    encontrados = [format_maxplayer_user(user) for user in users if maxplayer_user_matches(user, termo)]

    return {
        "status": "sucesso" if encontrados else "nao_encontrado",
        "termo_buscado": termo,
        "total_base": len(users),
        "total_encontrado": len(encontrados),
        "cache": "sim" if from_cache else "nao",
        "usuarios": encontrados[:20],
        "mensagem": "Usuario encontrado no MaxPlayer." if encontrados else "Nenhum usuario encontrado no MaxPlayer com este termo."
    }

@app.get("/maxplayer/usuario/{usuario}")
def pesquisar_usuario_maxplayer_get(usuario: str):
    return pesquisar_usuario_maxplayer(SearchRequest(termo=usuario))

@app.get("/maxplayer-free/domains")
def listar_maxplayer_free_domains():
    domains, from_cache = get_maxplayer_free_domains()
    return {
        "status": "sucesso",
        "cache": "sim" if from_cache else "nao",
        "domains": domains
    }

@app.post("/maxplayer-free/usuario")
def pesquisar_usuario_maxplayer_free(request: SearchRequest):
    termo = request.termo.strip()
    if not termo:
        raise HTTPException(status_code=400, detail="Usuario nao informado")

    users, users_from_cache = get_maxplayer_free_users()
    domains, _ = get_maxplayer_free_domains()
    domain_map = {str(item.get("id")): item.get("label") for item in domains}
    encontrados = [format_maxplayer_free_user(user, domain_map) for user in users if maxplayer_free_user_matches(user, termo)]

    return {
        "status": "sucesso" if encontrados else "nao_encontrado",
        "termo_buscado": termo,
        "total_base": len(users),
        "total_encontrado": len(encontrados),
        "cache": "sim" if users_from_cache else "nao",
        "usuarios": encontrados[:20],
        "mensagem": "Usuario encontrado no MaxPlayer Free." if encontrados else "Nenhum usuario encontrado no MaxPlayer Free com este termo."
    }

@app.post("/maxplayer-free/linha")
def pesquisar_linha_maxplayer_free(request: SearchRequest):
    termo = request.termo.strip()
    if not termo:
        raise HTTPException(status_code=400, detail="Linha nao informada")

    lines, from_cache = get_apps_lines()
    encontrados = [format_apps_line(line) for line in lines if line_apps_matches(line, termo)]

    return {
        "status": "sucesso" if encontrados else "nao_encontrado",
        "termo_buscado": termo,
        "total_base": len(lines),
        "total_encontrado": len(encontrados),
        "cache": "sim" if from_cache else "nao",
        "linhas": encontrados[:20],
        "mensagem": "Linha encontrada no Painel Apps." if encontrados else "Nenhuma linha encontrada no Painel Apps com este termo."
    }

@app.post("/maxplayer-free/usuario/criar")
def criar_usuario_maxplayer_free(request: MaxplayerFreeCreateRequest):
    payload = {
        "line_id": request.line_id,
        "domain_id": request.domain_id
    }

    try:
        result = apps_post("/max-player/users", payload)
        log_action("maxplayer_free_create_user", "sucesso", {"payload": payload, "result": result})
    except HTTPException as e:
        log_action("maxplayer_free_create_user", "erro", {"payload": payload, "error": e.detail})
        raise

    return {
        "status": "sucesso",
        "message": "Usuario criado no MaxPlayer Free.",
        "result": result
    }

def consulta_revenda_result(termo):
    try:
        revenda = buscar_cliente(SearchRequest(termo=termo))
        if isinstance(revenda, dict) and revenda.get("DT_RowId") != "nao_encontrado":
            return {
                **revenda,
                "status": "sucesso",
                "mensagem": "Cadastro encontrado na base das revendas."
            }

        return {
            **(revenda if isinstance(revenda, dict) else {}),
            "status": "nao_encontrado",
            "mensagem": "Nenhum cadastro encontrado na base das revendas."
        }
    except HTTPException as e:
        return {
            "status": "erro",
            "mensagem": e.detail,
            "Link": "nao_encontrado"
        }
    except Exception as e:
        return {
            "status": "erro",
            "mensagem": str(e),
            "Link": "nao_encontrado"
        }

def consulta_linha_result(termo):
    if not termo:
        return {
            "status": "ignorado",
            "mensagem": "A consulta The Best precisa de um termo de busca."
        }

    try:
        return consultar_linha_externa_get(termo)
    except HTTPException as e:
        return {
            "status": "erro",
            "mensagem": e.detail
        }
    except Exception as e:
        return {
            "status": "erro",
            "mensagem": str(e)
        }

def consulta_maxplayer_result(termo):
    try:
        return pesquisar_usuario_maxplayer(SearchRequest(termo=termo))
    except HTTPException as e:
        return {
            "status": "erro",
            "mensagem": e.detail,
            "usuarios": []
        }
    except Exception as e:
        return {
            "status": "erro",
            "mensagem": str(e),
            "usuarios": []
        }

def consulta_maxplayer_free_result(termo):
    try:
        return pesquisar_usuario_maxplayer_free(SearchRequest(termo=termo))
    except HTTPException as e:
        return {
            "status": "erro",
            "mensagem": e.detail,
            "usuarios": []
        }
    except Exception as e:
        return {
            "status": "erro",
            "mensagem": str(e),
            "usuarios": []
        }

def consulta_maxplayer_free_linhas_result(termo):
    try:
        return pesquisar_linha_maxplayer_free(SearchRequest(termo=termo))
    except HTTPException as e:
        return {
            "status": "erro",
            "mensagem": e.detail,
            "linhas": []
        }
    except Exception as e:
        return {
            "status": "erro",
            "mensagem": str(e),
            "linhas": []
        }

@app.post("/cliente/consulta")
def consulta_cliente_unificada(request: SearchRequest):
    termo = request.termo.strip()
    if not termo:
        raise HTTPException(status_code=400, detail="Informe um telefone, usuario, ID ou email para pesquisar.")

    telefone_limpo = re.sub(r"[^\d]", "", termo)

    tasks = {
        "revenda": (consulta_revenda_result, termo),
        "linha": (consulta_linha_result, termo),
        "maxplayer": (consulta_maxplayer_result, termo)
    }
    results = {}

    with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        futures = {
            executor.submit(func, arg): name
            for name, (func, arg) in tasks.items()
        }
        for future in as_completed(futures):
            results[futures[future]] = future.result()

    revenda = results["revenda"]
    linha = results["linha"]
    maxplayer = results["maxplayer"]
    maxplayer_free = {
        "status": "ignorado",
        "mensagem": "Busca de usuario Free pulada para manter a consulta principal rapida.",
        "usuarios": []
    }
    maxplayer_free_linhas = {
        "status": "ignorado",
        "mensagem": "Consulta Free carregada separadamente no painel.",
        "linhas": []
    }

    linha_encontrada = linha.get("status") == "sucesso"
    maxplayer_encontrado = maxplayer.get("status") == "sucesso"
    maxplayer_free_encontrado = maxplayer_free.get("status") == "sucesso"
    revenda_encontrada = revenda.get("status") == "sucesso"

    return {
        "status": "sucesso" if revenda_encontrada or linha_encontrada or maxplayer_encontrado or maxplayer_free_encontrado else "nao_encontrado",
        "termo_buscado": termo,
        "telefone_normalizado": telefone_limpo,
        "resumo": {
            "revenda_encontrada": revenda_encontrada,
            "linha_encontrada": linha_encontrada,
            "maxplayer_encontrado": maxplayer_encontrado,
            "maxplayer_free_encontrado": maxplayer_free_encontrado
        },
        "revenda": revenda,
        "linha": linha,
        "maxplayer": maxplayer,
        "maxplayer_free": maxplayer_free,
        "maxplayer_free_linhas": maxplayer_free_linhas
    }

if __name__ == "__main__":
    import uvicorn
    # Executa o servidor na porta 8080
    uvicorn.run(app, host="0.0.0.0", port=8080)
