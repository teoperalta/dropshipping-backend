from __future__ import annotations

import random
import sys
import time
from typing import Any

import requests

URL_PRODUCTOS = "http://127.0.0.1:8000/productos"
URL_VENTAS = "http://127.0.0.1:8000/ventas"
TOTAL_VENTAS = 5
PAUSA = 1.5
TIMEOUT = 10


class ExcepcionConexion(Exception):
    pass


def obtener_productos() -> list[dict[str, Any]]:
    try:
        respuesta = requests.get(URL_PRODUCTOS, timeout=TIMEOUT)
        respuesta.raise_for_status()
        return respuesta.json()
    except requests.exceptions.ConnectionError as exc:
        raise ExcepcionConexion(
            f"No se pudo conectar a '{URL_PRODUCTOS}'. ¿Está el servidor activo? {exc}"
        ) from exc
    except requests.exceptions.Timeout as exc:
        raise ExcepcionConexion(f"Timeout al conectar a '{URL_PRODUCTOS}': {exc}") from exc
    except requests.exceptions.HTTPError as exc:
        raise ExcepcionConexion(
            f"HTTP {exc.response.status_code} al obtener productos: {exc.response.text[:300]}"
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise ExcepcionConexion(f"Error de red inesperado: {exc}") from exc


def registrar_venta(producto_id: int, cantidad: int) -> None:
    payload: dict[str, int] = {
        "producto_id": producto_id,
        "cantidad": cantidad,
    }
    try:
        respuesta = requests.post(URL_VENTAS, json=payload, timeout=TIMEOUT)

        if respuesta.status_code == 201:
            datos = respuesta.json()
            print(
                f"  ✓ APROBADA  — Venta id={datos['id']} | "
                f"Total: ${datos['total']:.2f} | "
                f"Fecha: {datos['fecha_venta']}\n"
            )
            return

        if respuesta.status_code == 400:
            detalle = respuesta.json().get("detail", "Sin detalle.")
            print(f"  ✗ RECHAZADA — {detalle}\n")
            return

        if respuesta.status_code == 404:
            detalle = respuesta.json().get("detail", "Producto no encontrado.")
            print(f"  ✗ RECHAZADA — {detalle}\n")
            return

        respuesta.raise_for_status()

    except requests.exceptions.ConnectionError as exc:
        print(
            f"  ✗ ERROR DE CONEXIÓN — No se pudo conectar a '{URL_VENTAS}': {exc}\n",
            file=sys.stderr,
        )
    except requests.exceptions.Timeout as exc:
        print(f"  ✗ TIMEOUT — {exc}\n", file=sys.stderr)
    except requests.exceptions.HTTPError as exc:
        print(
            f"  ✗ ERROR HTTP {exc.response.status_code} — {exc.response.text[:300]}\n",
            file=sys.stderr,
        )
    except requests.exceptions.RequestException as exc:
        print(f"  ✗ ERROR INESPERADO — {exc}\n", file=sys.stderr)


def simular_ventas(productos: list[dict[str, Any]], total: int) -> None:
    print(f"\n[SIMULADOR] Iniciando {total} compras sobre {len(productos)} productos disponibles.\n")

    for numero in range(1, total + 1):
        producto = random.choice(productos)
        producto_id: int = producto["id"]
        titulo: str = producto.get("titulo", "desconocido")[:65]

        print(f"[COMPRA {numero}/{total}] Producto: '{titulo}' (id={producto_id})")

        registrar_venta(producto_id=producto_id, cantidad=1)

        time.sleep(PAUSA)

    print("[SIMULADOR] Simulación completada.")


def main() -> None:
    try:
        productos = obtener_productos()
    except ExcepcionConexion as exc:
        print(f"[ERROR DE CONEXIÓN] {exc}", file=sys.stderr)
        sys.exit(1)

    if not productos:
        print("[AVISO] El catálogo está vacío. No hay productos para simular ventas.")
        sys.exit(0)

    simular_ventas(productos, TOTAL_VENTAS)


if __name__ == "__main__":
    main()