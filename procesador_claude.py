import os
import requests

SHOPIFY_STORE_URL = "cjzr0t-in.myshopify.com"
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_TOKEN")
API_VERSION = "2024-04"

def optimizar_producto_completo():
    return {
        "titulo": "Smartwatch V2 Ultra | Monitor de Salud",
        "descripcion": "<ul><li><strong>Ritmo cardíaco:</strong> 24/7.</li><li><strong>Batería:</strong> 5 días.</li></ul>",
        "precio": "49.99",
        "precio_comparacion": "89.99",
        "url_imagen": "https://via.placeholder.com/600x600.png?text=Smartwatch+V2",
        "inventario": 100
    }

def subir_a_shopify_completo(datos):
    url = f"https://{SHOPIFY_STORE_URL}/admin/api/{API_VERSION}/products.json"
    
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN
    }
    
    payload = {
        "product": {
            "title": datos["titulo"],
            "body_html": datos["descripcion"],
            "vendor": "Dropshipping Auto",
            "product_type": "Electrónica",
            "status": "active",
            "variants": [
                {
                    "price": datos["precio"],
                    "compare_at_price": datos["precio_comparacion"],
                    "inventory_management": "shopify",
                    "inventory_quantity": datos["inventario"]
                }
            ],
            "images": [
                {
                    "src": datos["url_imagen"]
                }
            ]
        }
    }
    
    try:
        respuesta = requests.post(url, json=payload, headers=headers)
        respuesta.raise_for_status()
        
        producto_creado = respuesta.json()
        print("EXITO. Producto completo creado.")
        print(f"ID del Producto: {producto_creado['product']['id']}")
        
    except requests.exceptions.RequestException as e:
        print(f"Error de conexion: {e}")

if __name__ == "__main__":
    producto_listo = optimizar_producto_completo()
    subir_a_shopify_completo(producto_listo)