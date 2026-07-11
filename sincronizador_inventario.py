from __future__ import annotations

import csv
import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()


class LecturaArchivoError(Exception):
    pass


class ShopifyAPIError(Exception):
    pass


COLUMNAS_REQUERIDAS = {"titulo", "precio", "precio_comparacion", "inventario"}


@dataclass
class ProductoLocal:
    titulo: str
    precio: str
    precio_comparacion: str
    inventario: str

    @classmethod
    def desde_fila(cls, fila: dict) -> "ProductoLocal":
        return cls(
            titulo=fila["titulo"].strip(),
            precio=fila["precio"].strip(),
            precio_comparacion=fila["precio_comparacion"].strip(),
            inventario=fila["inventario"].strip(),
        )


@dataclass
class VarianteShopify:
    variant_id: int
    titulo_producto: str
    precio_actual: str


class ServicioShopify:
    _TIMEOUT = 20
    _API_VERSION = "2024-04"

    def __init__(self, store_url: str, access_token: str) -> None:
        self._base = f"{store_url.rstrip('/')}/admin/api/{self._API_VERSION}"
        self._headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": access_token,
        }

    def _get(self, endpoint: str) -> dict:
        url = f"{self._base}{endpoint}"
        try:
            response = requests.get(url, headers=self._headers, timeout=self._TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError as exc:
            raise ShopifyAPIError(f"Error de conexión al hacer GET a '{url}': {exc}") from exc
        except requests.exceptions.Timeout as exc:
            raise ShopifyAPIError(f"Timeout al hacer GET a '{url}': {exc}") from exc
        except requests.exceptions.HTTPError as exc:
            raise ShopifyAPIError(
                f"HTTP {exc.response.status_code} al hacer GET a '{url}': {exc.response.text}"
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise ShopifyAPIError(f"Error inesperado al hacer GET a '{url}': {exc}") from exc

    def _put(self, endpoint: str, payload: dict) -> dict:
        url = f"{self._base}{endpoint}"
        try:
            response = requests.put(
                url,
                headers=self._headers,
                data=json.dumps(payload),
                timeout=self._TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError as exc:
            raise ShopifyAPIError(f"Error de conexión al hacer PUT a '{url}': {exc}") from exc
        except requests.exceptions.Timeout as exc:
            raise ShopifyAPIError(f"Timeout al hacer PUT a '{url}': {exc}") from exc
        except requests.exceptions.HTTPError as exc:
            raise ShopifyAPIError(
                f"HTTP {exc.response.status_code} al hacer PUT a '{url}': {exc.response.text}"
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise ShopifyAPIError(f"Error inesperado al hacer PUT a '{url}': {exc}") from exc

    def obtener_productos(self) -> List[VarianteShopify]:
        data = self._get("/products.json?limit=250")
        variantes: List[VarianteShopify] = []
        for producto in data.get("products", []):
            titulo = producto.get("title", "")
            for variante in producto.get("variants", []):
                variantes.append(
                    VarianteShopify(
                        variant_id=variante["id"],
                        titulo_producto=titulo,
                        precio_actual=variante.get("price", "0"),
                    )
                )
        return variantes

    def actualizar_variante(
        self,
        variant_id: int,
        precio: str,
        precio_comparacion: str,
        inventario: str,
    ) -> dict:
        payload = {
            "variant": {
                "id": variant_id,
                "price": precio,
                "compare_at_price": precio_comparacion,
                "inventory_quantity": int(inventario),
            }
        }
        return self._put(f"/variants/{variant_id}.json", payload)


class LectorCSV:
    def __init__(self, ruta: str) -> None:
        self._ruta = ruta

    def leer(self) -> List[ProductoLocal]:
        try:
            with open(self._ruta, newline="", encoding="utf-8") as archivo:
                lector = csv.DictReader(archivo)
                columnas = set(lector.fieldnames or [])
                faltantes = COLUMNAS_REQUERIDAS - columnas
                if faltantes:
                    raise LecturaArchivoError(
                        f"Columnas faltantes en '{self._ruta}': {faltantes}"
                    )
                return [ProductoLocal.desde_fila(fila) for fila in lector]
        except FileNotFoundError as exc:
            raise LecturaArchivoError(f"No se encontró el archivo '{self._ruta}'.") from exc
        except IOError as exc:
            raise LecturaArchivoError(f"Error de I/O al leer '{self._ruta}': {exc}") from exc


class ControladorSincronizacion:
    _RATE_LIMIT_SLEEP = 0.5

    def __init__(self, servicio: ServicioShopify, lector: LectorCSV) -> None:
        self._servicio = servicio
        self._lector = lector

    def _construir_indice_shopify(
        self, variantes: List[VarianteShopify]
    ) -> Dict[str, VarianteShopify]:
        return {v.titulo_producto.strip().lower(): v for v in variantes}

    def ejecutar(self) -> None:
        try:
            productos_locales = self._lector.leer()
        except LecturaArchivoError as exc:
            print(f"[ERROR DE ARCHIVO] {exc}", file=sys.stderr)
            sys.exit(1)

        print(f"[INFO] {len(productos_locales)} productos leídos del CSV.")

        try:
            variantes_shopify = self._servicio.obtener_productos()
        except ShopifyAPIError as exc:
            print(f"[ERROR DE API] {exc}", file=sys.stderr)
            sys.exit(2)

        print(f"[INFO] {len(variantes_shopify)} variantes obtenidas de Shopify.")

        indice = self._construir_indice_shopify(variantes_shopify)

        actualizados = 0
        no_encontrados = 0
        errores = 0

        for producto in productos_locales:
            clave = producto.titulo.lower()

            if clave not in indice:
                print(f"[NO ENCONTRADO] '{producto.titulo}' no existe en Shopify. Omitiendo.")
                no_encontrados += 1
                continue

            variante = indice[clave]

            try:
                self._servicio.actualizar_variante(
                    variant_id=variante.variant_id,
                    precio=producto.precio,
                    precio_comparacion=producto.precio_comparacion,
                    inventario=producto.inventario,
                )
                print(
                    f"[OK] '{producto.titulo}' "
                    f"(variant_id={variante.variant_id}) → "
                    f"precio={producto.precio} | "
                    f"comparacion={producto.precio_comparacion} | "
                    f"stock={producto.inventario}"
                )
                actualizados += 1
            except ShopifyAPIError as exc:
                print(f"[ERROR API] '{producto.titulo}': {exc}", file=sys.stderr)
                errores += 1

            time.sleep(self._RATE_LIMIT_SLEEP)

        print(
            f"\n[RESUMEN] Actualizados: {actualizados} | "
            f"No encontrados: {no_encontrados} | "
            f"Errores: {errores}"
        )


def main() -> None:
    store_url = os.environ.get("SHOPIFY_STORE_URL", "")
    access_token = os.environ.get("SHOPIFY_ACCESS_TOKEN", "")

    if not store_url or not access_token:
        print(
            "[ERROR] Las variables de entorno SHOPIFY_STORE_URL y "
            "SHOPIFY_ACCESS_TOKEN son obligatorias.",
            file=sys.stderr,
        )
        sys.exit(1)

    servicio = ServicioShopify(store_url, access_token)
    lector = LectorCSV("productos.csv")
    controlador = ControladorSincronizacion(servicio, lector)
    controlador.ejecutar()


if __name__ == "__main__":
    main()