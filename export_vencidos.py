import json
import pandas as pd
from datetime import datetime
import os

# Configuração
# Data de hoje para filtro: 23/01/2026
HOJE_STR = "23/01/2026"
OUTPUT_FILE = "vencidos_hoje_23_01.xlsx"

FILES = [
    {
        "filename": "revendagabriel.json",
        "etiqueta": "REVENDA GABRIEL, EX23.01"
    },
    {
        "filename": "revendajacques.json",
        "etiqueta": "REVENDA JACQUES, EX23.01"
    }
]

def format_phone(phone_raw):
    """Limpa e formata o telefone (opcional, mantendo string por enquanto)."""
    if not phone_raw:
        return ""
    return str(phone_raw).strip()

def main():
    final_data = []

    print(f"Buscando clientes com vencimento em: {HOJE_STR}")

    for item in FILES:
        fname = item['filename']
        tag = item['etiqueta']
        
        if not os.path.exists(fname):
            print(f"Arquivo não encontrado: {fname}")
            continue

        with open(fname, 'r', encoding='utf-8') as f:
            data = json.load(f)

        count = 0
        for cliente in data:
            # Filtra pela data exata
            if cliente.get('data_expiracao') == HOJE_STR:
                # Estrutura solicitada:
                # nome -> nome do JSON
                # sobrenome -> telefone do JSON
                # telefone -> telefone do JSON
                # etiqueta -> tag definida
                
                tel = format_phone(cliente.get('telefone', ''))
                
                row = {
                    "nome": cliente.get('nome', ''),
                    "sobrenome": tel,
                    "telefone": tel,
                    "etiqueta": tag
                }
                final_data.append(row)
                count += 1
        
        print(f"Encontrados {count} clientes em {fname}")

    if final_data:
        df = pd.DataFrame(final_data)
        df.to_excel(OUTPUT_FILE, index=False)
        print(f"\nSucesso! Arquivo gerado: {OUTPUT_FILE}")
        print(f"Total de registros: {len(df)}")
    else:
        print("\nNenhum cliente encontrado com vencimento hoje.")

if __name__ == "__main__":
    main()
