import os

import requests

STORE_URL = "cjzr0t-in.myshopify.com"
CLIENT_ID = "b1b334b2a03d2f0871249c66db86618f"
CLIENT_SECRET =os.getenv("SHOPIFY_SHARED_SECRET")
AUTH_CODE = "c9d46027b39ddd802f85be018c25e8b2"

def intercambiar_token():
    url = f"https://{STORE_URL}/admin/oauth/access_token"
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": AUTH_CODE
    }
    respuesta = requests.post(url, json=payload)
    datos = respuesta.json()
    
    print("=== RESPUESTA DE SHOPIFY ===")
    if "access_token" in datos:
        print(f"ÉXITO. Tu Token Permanente es: {datos['access_token']}")
    else:
        print("Error:", datos)

if __name__ == "__main__":
    intercambiar_token()