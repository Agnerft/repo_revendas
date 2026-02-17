import requests
import json

def test_filter(termo):
    url = "http://localhost:8080/filtrar"
    payload = {"termo": termo}
    try:
        response = requests.post(url, json=payload)
        print(f"Termo: '{termo}' -> Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Total encontrado: {len(data)}")
            if data:
                print("Primeiro resultado:", data[0])
                print("Ultimo resultado:", data[-1])
        else:
            print("Error:", response.text)
    except Exception as e:
        print(f"Erro ao conectar: {e}")

if __name__ == "__main__":
    print("--- Teste de Filtro por Data ---")
    # Usando uma data que vi no log anterior
    test_filter("19/08/2025")
