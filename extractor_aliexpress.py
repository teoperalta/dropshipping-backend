from __future__ import annotations

import json
import random
import sys
from typing import Any

import requests

HEADERS: dict[str, str] = {
    "x-rapidapi-key": "d04f762a3fmshb38264626ff0981p1f81f3jsn00c7f32043b6",
    "x-rapidapi-host": "aliexpress-datahub.p.rapidapi.com",
}

URL_RAPIDAPI: str = "https://aliexpress-datahub.p.rapidapi.com/item_search_2"
URL_API_LOCAL: str = "http://127.0.0.1:8000/productos"
TIMEOUT_EXTERNO: int = 20
TIMEOUT_LOCAL: int = 10

QUERYSTRING: dict[str, str] = {
    "q": "smartwatch",
    "page": "1",
    "sort": "default",
}


class ExcepcionExtraccion(Exception):
    pass


class ExcepcionAPILocal(Exception):
    pass


def obtener_productos_aliexpress() -> list[dict[str, Any]]:
    if not URL_RAPIDAPI:
        raise ExcepcionExtraccion("URL_RAPIDAPI no está configurada.")
    if not HEADERS.get("x-rapidapi-key") or not HEADERS.get("x-rapidapi-host"):
        raise ExcepcionExtraccion("Las credenciales de RapidAPI no están configuradas.")

    try:
        respuesta = requests.get(URL_RAPIDAPI, headers=HEADERS, params=QUERYSTRING, timeout=TIMEOUT_EXTERNO)
        respuesta.raise_for_status()
    except requests.exceptions.ConnectionError as exc:
        raise ExcepcionExtraccion(f"Error de conexión a RapidAPI: {exc}") from exc
    except requests.exceptions.Timeout as exc:
        raise ExcepcionExtraccion(f"Timeout al conectar a RapidAPI: {exc}") from exc
    except requests.exceptions.HTTPError as exc:
        raise ExcepcionExtraccion(
            f"HTTP {exc.response.status_code} desde RapidAPI: {exc.response.text[:300]}"
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise ExcepcionExtraccion(f"Error inesperado en petición a RapidAPI: {exc}") from exc

    try:
        datos = respuesta.json()
    except ValueError as exc:
        raise ExcepcionExtraccion(f"Error al parsear JSON de RapidAPI: {exc}") from exc

    print(json.dumps(datos, indent=4))
    sys.exit(0)

    contenido: dict[str, Any] = datos.get("result", {})

    print("[DEBUG] Claves dentro de result:", list(contenido.keys()) if contenido else "vacío")

    for clave in ("resultList", "item", "items", "products", "results", "data", "list"):
        candidato = contenido.get(clave)
        if isinstance(candidato, list):
            print(
                f"[DEBUG] Lista encontrada en 'result.{clave}' "
                f"({len(candidato)} elementos)."
            )
            return candidato

    for clave in ("results", "products", "items", "data"):
        if isinstance(datos.get(clave), list):
            return datos[clave]

    if isinstance(datos, list):
        return datos

    raise ExcepcionExtraccion(
        f"No se encontró una lista de productos. "
        f"Claves en raíz: {list(datos.keys())} | "
        f"Claves en 'result': {list(contenido.keys()) if contenido else 'N/A'}"
    )


def construir_payload(raw: dict[str, Any]) -> dict[str, Any]:
    titulo: str = (
        str(raw.get("title") or raw.get("product_title") or raw.get("name") or "").strip()
    )
    if not titulo:
        raise ValueError("El producto no contiene un título válido.")

    descripcion: str = (
        str(
            raw.get("description")
            or raw.get("detail")
            or raw.get("product_description")
            or "Producto de AliExpress"
        ).strip()
    )

    precio_raw = (
        raw.get("price")
        or raw.get("sale_price")
        or raw.get("original_price")
        or raw.get("min_price")
        or 0
    )
    precio: float = float(str(precio_raw).replace(",", ".").strip() or 0)

    if precio <= 0:
        raise ValueError(f"El precio del producto '{titulo}' no es válido: {precio_raw}")

    return {
        "titulo": titulo,
        "descripcion": descripcion,
        "precio": precio,
        "precio_comparacion": round(precio * 1.2, 2),
        "inventario": random.randint(50, 200),
    }


def publicar_en_api_local(payload: dict[str, Any]) -> None:
    try:
        respuesta = requests.post(URL_API_LOCAL, json=payload, timeout=TIMEOUT_LOCAL)
        respuesta.raise_for_status()
    except requests.exceptions.ConnectionError as exc:
        raise ExcepcionAPILocal(
            f"No se pudo conectar a '{URL_API_LOCAL}'. ¿Está el servidor activo? {exc}"
        ) from exc
    except requests.exceptions.Timeout as exc:
        raise ExcepcionAPILocal(f"Timeout al hacer POST a '{URL_API_LOCAL}': {exc}") from exc
    except requests.exceptions.HTTPError as exc:
        raise ExcepcionAPILocal(
            f"HTTP {exc.response.status_code} desde API local: {exc.response.text[:300]}"
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise ExcepcionAPILocal(f"Error inesperado al hacer POST: {exc}") from exc


def main() -> None:
    try:
        productos = obtener_productos_aliexpress()
    except ExcepcionExtraccion as exc:
        print(f"[ERROR DE EXTRACCIÓN] {exc}", file=sys.stderr)
        sys.exit(1)

    if not productos:
        print("[AVISO] La API de RapidAPI devolvió una lista vacía.")
        sys.exit(0)

    print(f"[INFO] {len(productos)} productos obtenidos. Iniciando publicación en API local...\n")

    publicados = 0
    errores_payload = 0
    errores_api = 0

    for indice, raw in enumerate(productos, start=1):
        try:
            payload = construir_payload(raw)
        except (ValueError, TypeError, KeyError) as exc:
            print(
                f"[ERROR PARSEO] ({indice}/{len(productos)}) No se pudo construir el payload: {exc}",
                file=sys.stderr,
            )
            errores_payload += 1
            continue

        try:
            publicar_en_api_local(payload)
            print(
                f"[OK] ({indice}/{len(productos)}) '{payload['titulo'][:65]}' | "
                f"Precio: ${payload['precio']:.2f} | Stock: {payload['inventario']}"
            )
            publicados += 1
        except ExcepcionAPILocal as exc:
            print(
                f"[ERROR API] ({indice}/{len(productos)}) '{payload['titulo'][:65]}': {exc}",
                file=sys.stderr,
            )
            errores_api += 1

    print(
        f"\n[RESUMEN] Publicados: {publicados} | "
        f"Errores de parseo: {errores_payload} | "
        f"Errores de API: {errores_api}"
    )


if __name__ == "__main__":
    main()