from __future__ import annotations

import sys
import time
from typing import Any
import os
import requests

SHOP_NAME: str = "dev-backend-productos"
SHOPIFY_TOKEN: str = os.getenv("SHOPIFY_TOKEN")
SHOPIFY_URL: str = f"https://dev-backend-productos.myshopify.com/admin/api/2024-04/products.json"
URL_API_LOCAL: str = "http://127.0.0.1:8000/productos"
TIMEOUT: int = 20
RATE_LIMIT_SLEEP: float = 0.5

HEADERS: dict[str, str] = {
    "X-Shopify-Access-Token": SHOPIFY_TOKEN,
    "Content-Type": "application/json",
}


class ExcepcionAPILocal(Exception):
    pass


class ExcepcionShopify(Exception):
    pass


def obtener_productos_locales() -> list[dict[str, Any]]:
    try:
        respuesta = requests.get(URL_API_LOCAL, timeout=TIMEOUT)
        respuesta.raise_for_status()
        return respuesta.json()
    except requests.exceptions.ConnectionError as exc:
        raise ExcepcionAPILocal(
            f"No se pudo conectar a '{URL_API_LOCAL}'. ¿Está el servidor activo? {exc}"
        ) from exc
    except requests.exceptions.Timeout as exc:
        raise ExcepcionAPILocal(f"Timeout al conectar a '{URL_API_LOCAL}': {exc}") from exc
    except requests.exceptions.HTTPError as exc:
        raise ExcepcionAPILocal(
            f"HTTP {exc.response.status_code} al obtener productos locales: {exc.response.text[:300]}"
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise ExcepcionAPILocal(f"Error inesperado al leer API local: {exc}") from exc


def construir_payload(producto: dict[str, Any]) -> dict[str, Any]:
    return {
        "product": {
            "title": producto["titulo"],
            "body_html": producto["descripcion"],
            "status": "active",
            "variants": [
                {
                    "price": str(producto["precio"]),
                    "compare_at_price": str(producto["precio_comparacion"]),
                }
            ],
        }
    }


def publicar_en_shopify(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        respuesta = requests.post(SHOPIFY_URL, headers=HEADERS, json=payload, timeout=TIMEOUT)
        respuesta.raise_for_status()
        return respuesta.json()
    except requests.exceptions.ConnectionError as exc:
        raise ExcepcionShopify(
            f"No se pudo conectar a Shopify en '{SHOPIFY_URL}': {exc}"
        ) from exc
    except requests.exceptions.Timeout as exc:
        raise ExcepcionShopify(f"Timeout al hacer POST a Shopify: {exc}") from exc
    except requests.exceptions.HTTPError as exc:
        raise ExcepcionShopify(
            f"HTTP {exc.response.status_code} desde Shopify: {exc.response.text[:300]}"
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise ExcepcionShopify(f"Error inesperado al publicar en Shopify: {exc}") from exc


def sincronizar(productos: list[dict[str, Any]]) -> None:
    print(f"[INFO] {len(productos)} productos locales. Iniciando sincronización con Shopify...\n")

    publicados = 0
    errores = 0

    for indice, producto in enumerate(productos, start=1):
        titulo: str = str(producto.get("titulo", "Sin título"))[:65]
        payload = construir_payload(producto)

        try:
            resultado = publicar_en_shopify(payload)
            shopify_id = resultado.get("product", {}).get("id", "N/A")
            print(
                f"[OK] ({indice}/{len(productos)}) '{titulo}' "
                f"→ Shopify ID: {shopify_id}"
            )
            publicados += 1
        except ExcepcionShopify as exc:
            print(
                f"[ERROR] ({indice}/{len(productos)}) '{titulo}' → {exc}",
                file=sys.stderr,
            )
            errores += 1

        time.sleep(RATE_LIMIT_SLEEP)

    print(f"\n[RESUMEN] Publicados en Shopify: {publicados} | Errores: {errores}")


def main() -> None:
    try:
        productos = obtener_productos_locales()
    except ExcepcionAPILocal as exc:
        print(f"[ERROR API LOCAL] {exc}", file=sys.stderr)
        sys.exit(1)

    if not productos:
        print("[AVISO] No hay productos en la API local. Nada que sincronizar.")
        sys.exit(0)

    sincronizar(productos)


if __name__ == "__main__":
    main()