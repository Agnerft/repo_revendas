import requests
import json
import time

# Configuration
LOGIN_URL = "https://app.gestorinove.com.br/valida"
DATA_URL = "https://app.gestorinove.com.br/modulos/cliente/ajax.php"

ACCOUNTS = [
    {
        "email": "mairobtonimanumartins@gmail.com",
        "password": "@Manu102030",
        "filename": "revendarobson.json"
    }
]

def get_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    return session

def login(session, email, password):
    print(f"Attempting to login as {email}...")
    payload = {
        'email': email,
        'senha': password,
        'redir': ''
    }
    
    try:
        session.get("https://app.gestorinove.com.br/login")
        response = session.post(LOGIN_URL, data=payload)
        
        if response.url == "https://app.gestorinove.com.br/painel" or "painel" in response.url:
            print("Login successful!")
            return True
        elif "Erro" in response.text or "inválido" in response.text:
            print("Login failed: Invalid credentials.")
            return False
        elif 'GESTOR_SESSION' in session.cookies:
             print("Login successful (Session cookie found).")
             return True
        else:
            print(f"Login uncertain. URL: {response.url}")
            # Assume success if we got redirected somewhere else but no explicit error
            return True 
            
    except Exception as e:
        print(f"Login error: {e}")
        return False

def fetch_data(session):
    print("Fetching data...")
    params = {
        "draw": "3",
        "start": "0",
        "length": "10000",
        "search[value]": "",
        "search[regex]": "false",
        "colunas": '["id_externo","nome","sobrenome","email","whatsapp","id_plano","id_categoria","data_vencimento","status"]',
        "modulo": "cliente",
        "plano": "",
        "categoria": "",
        "dataIni": "",
        "dataFim": "",
        "idStatus": "",
        "_": str(int(time.time() * 1000))
    }
    
    for i in range(10):
        params[f"columns[{i}][data]"] = str(i)
        params[f"columns[{i}][name]"] = ""
        params[f"columns[{i}][searchable]"] = "true"
        params[f"columns[{i}][orderable]"] = "true" if i < 9 else "false"
        params[f"columns[{i}][search][value]"] = ""
        params[f"columns[{i}][search][regex]"] = "false"
        
    params["order[0][column]"] = "0"
    params["order[0][dir]"] = "desc"

    try:
        response = session.get(DATA_URL, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Fetch failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"Fetch error: {e}")
        return None

def process_and_save(raw_data, filename):
    if not raw_data or 'data' not in raw_data:
        print(f"No valid data to process for {filename}")
        return

    raw_list = raw_data['data']
    processed_list = []
    seen_ids = set()
    
    print(f"Processing {len(raw_list)} records...")

    for item in raw_list:
        dt_row_id = item.get('DT_RowId')
        id_client = item.get('0')
        nome = item.get('1')
        telefone = item.get('4')
        data_expiracao = item.get('7')
        
        if id_client in seen_ids:
            continue
        seen_ids.add(id_client)
        
        processed_list.append({
            "DT_RowId": dt_row_id,
            "Id_client": id_client,
            "nome": nome,
            "telefone": telefone,
            "data_expiracao": data_expiracao
        })
        
    print(f"Saving {len(processed_list)} unique records to {filename}")
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(processed_list, f, indent=4, ensure_ascii=False)

def main():
    for acc in ACCOUNTS:
        print(f"\n--- Processing {acc['filename']} ---")
        session = get_session()
        if login(session, acc['email'], acc['password']):
            data = fetch_data(session)
            if data:
                process_and_save(data, acc['filename'])
        session.close()

if __name__ == "__main__":
    main()
