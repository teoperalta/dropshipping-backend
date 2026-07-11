from __future__ import annotations

import json
import random
import sys

import requests

API_KEY: str = "CJ5546807@api@eee41ba01c3f4a719e1e81abe7d8701a"

URL_AUTH: str = "https://developers.cjdropshipping.com/api2.0/v1/authentication/getAccessToken"
URL_PRODUCTOS: str = "https://developers.cjdropshipping.com/api2.0/v1/product/list"
URL_API_LOCAL: str = "http://127.0.0.1:8000/productos"
TIMEOUT: int = 20


class ExcepcionAutenticacion(Exception):
    pass


class ExcepcionExtraccion(Exception):
    pass


def obtener_access_token() -> str:
    payload: dict[str, str] = {"apiKey": API_KEY}

    try:
        respuesta = requests.post(URL_AUTH, json=payload, timeout=TIMEOUT)
        respuesta.raise_for_status()
    except requests.exceptions.ConnectionError as exc:
        raise ExcepcionAutenticacion(f"Error de conexión al endpoint de auth: {exc}") from exc
    except requests.exceptions.Timeout as exc:
        raise ExcepcionAutenticacion(f"Timeout al autenticar: {exc}") from exc
    except requests.exceptions.HTTPError as exc:
        raise ExcepcionAutenticacion(
            f"HTTP {exc.response.status_code} en auth: {exc.response.text[:300]}"
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise ExcepcionAutenticacion(f"Error inesperado en auth: {exc}") from exc

    try:
        datos = respuesta.json()
    except ValueError as exc:
        raise ExcepcionAutenticacion(f"No se pudo parsear la respuesta de auth: {exc}") from exc

    access_token: str | None = datos.get("data", {}).get("accessToken")

    if not access_token:
        raise ExcepcionAutenticacion(
            f"No se obtuvo accessToken. Respuesta completa:\n{json.dumps(datos, indent=4)}"
        )

    return access_token


def obtener_productos(access_token: str) -> None:
    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "CJ-Access-Token": access_token,
    }
    querystring: dict[str, object] = {
        "keyword": "smartwatch",
        "page": 1,
        "size": 10,
    }

    try:
        respuesta = requests.get(URL_PRODUCTOS, headers=headers, params=querystring, timeout=TIMEOUT)
        respuesta.raise_for_status()
    except requests.exceptions.ConnectionError as exc:
        raise ExcepcionExtraccion(f"Error de conexión al endpoint de productos: {exc}") from exc
    except requests.exceptions.Timeout as exc:
        raise ExcepcionExtraccion(f"Timeout al obtener productos: {exc}") from exc
    except requests.exceptions.HTTPError as exc:
        raise ExcepcionExtraccion(
            f"HTTP {exc.response.status_code} en productos: {exc.response.text[:300]}"
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise ExcepcionExtraccion(f"Error inesperado al obtener productos: {exc}") from exc

    try:
        datos = respuesta.json()
    except ValueError as exc:
        raise ExcepcionExtraccion(f"No se pudo parsear la respuesta de productos: {exc}") from exc

    productos: list[dict[str, object]] = datos.get("data", {}).get("list", [])

    if not productos:
        print("[AVISO] La respuesta no contiene productos en 'data.list'.")
        return

    print(f"[INFO] {len(productos)} productos obtenidos. Inyectando los primeros 10...\n")

    publicados = 0
    errores = 0

    for indice, producto in enumerate(productos[:10], start=1):
        titulo: str = str(producto.get("productNameEn") or "Sin título").strip()
        pid: str = str(producto.get("pid") or "N/A")
        descripcion: str = f"Importado de CJ Dropshipping - PID: {pid}"

        try:
            precio_raw = producto.get("sellPrice") or producto.get("salePrice") or producto.get("price")
            precio: float = float(str(precio_raw).replace(",", ".")) if precio_raw else round(random.uniform(10.0, 50.0), 2)
            if precio <= 0:
                raise ValueError("Precio no positivo")
        except (ValueError, TypeError):
            precio = round(random.uniform(10.0, 50.0), 2)

        payload: dict[str, object] = {
            "titulo": titulo,
            "descripcion": descripcion,
            "precio": precio,
            "precio_comparacion": round(precio * 1.3, 2),
            "inventario": random.randint(50, 200),
        }

        try:
            respuesta_local = requests.post(URL_API_LOCAL, json=payload, timeout=10)
            respuesta_local.raise_for_status()
            print(f"[OK] ({indice}/10) '{titulo[:65]}' | Precio: ${precio:.2f}")
            publicados += 1
        except requests.exceptions.ConnectionError:
            print(f"[ERROR CONEXIÓN] ({indice}/10) API local no disponible. ¿Está el servidor activo?", file=sys.stderr)
            errores += 1
        except requests.exceptions.HTTPError as exc:
            print(
                f"[ERROR API] ({indice}/10) '{titulo[:65]}' → "
                f"HTTP {exc.response.status_code}: {exc.response.text[:200]}",
                file=sys.stderr,
            )
            errores += 1
        except requests.exceptions.RequestException as exc:
            print(f"[ERROR RED] ({indice}/10) '{titulo[:65]}': {exc}", file=sys.stderr)
            errores += 1

    print(f"\n[RESUMEN] Publicados: {publicados} | Errores: {errores}")


def main() -> None:
    if not API_KEY:
        print("[ERROR] API_KEY no está configurada.", file=sys.stderr)
        sys.exit(1)

    try:
        access_token = obtener_access_token()
        print(f"[OK] Access token obtenido: {access_token[:20]}...\n")
    except ExcepcionAutenticacion as exc:
        print(f"[ERROR DE AUTENTICACIÓN] {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        obtener_productos(access_token)
    except ExcepcionExtraccion as exc:
        print(f"[ERROR DE EXTRACCIÓN] {exc}", file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()