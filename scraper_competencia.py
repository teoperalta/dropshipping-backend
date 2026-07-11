from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from typing import List

import requests


URL_COMPETENCIA = "https://fakestoreapi.com/products"
URL_API_LOCAL = "http://127.0.0.1:8000/productos"

HEADERS_SCRAPER = {
    
}


class ExcepcionRed(Exception):
    pass


class ExcepcionParseo(Exception):
    pass


class ExcepcionAPILocal(Exception):
    pass


@dataclass
class ProductoCompetidor:
    titulo: str
    descripcion: str
    precio: float

    @classmethod
    def desde_dict(cls, raw: dict) -> "ProductoCompetidor":
        return cls(
            titulo=str(raw.get("title", "")).strip(),
            descripcion=str(raw.get("category", "")).strip(),
            precio=float(raw.get("price", 0)),
        )

    def a_payload(self) -> dict:
        return {
            "titulo": self.titulo,
            "descripcion": self.descripcion,
            "precio": self.precio,
            "precio_comparacion": round(self.precio * 1.2, 2),
            "inventario": 100,
        }


class ServicioExtraccionHTTP:
    _TIMEOUT = 20

    def __init__(self, url: str) -> None:
        self._url = url
        self._session = requests.Session()
        self._session.headers.update(HEADERS_SCRAPER)

    def extraer_todos(self) -> List[ProductoCompetidor]:
        try:
            respuesta = self._session.get(self._url, timeout=self._TIMEOUT)
            respuesta.raise_for_status()
        except requests.exceptions.ConnectionError as exc:
            raise ExcepcionRed(f"Error de conexión a '{self._url}': {exc}") from exc
        except requests.exceptions.Timeout as exc:
            raise ExcepcionRed(f"Timeout al conectar a '{self._url}': {exc}") from exc
        except requests.exceptions.HTTPError as exc:
            raise ExcepcionRed(
                f"HTTP {exc.response.status_code} desde '{self._url}': {exc.response.text[:300]}"
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise ExcepcionRed(f"Error de red inesperado en '{self._url}': {exc}") from exc

        try:
            datos = respuesta.json()
            if not isinstance(datos, list):
                raise ExcepcionParseo(
                    f"Se esperaba una lista JSON pero se recibió: {type(datos).__name__}"
                )
        except (ValueError, KeyError) as exc:
            raise ExcepcionParseo(f"Error al parsear JSON de '{self._url}': {exc}") from exc

        productos: List[ProductoCompetidor] = []
        for raw in datos:
            try:
                productos.append(ProductoCompetidor.desde_dict(raw))
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                titulo = raw.get("title", "desconocido")
                print(
                    f"[AVISO] No se pudo parsear '{titulo}': {exc}",
                    file=sys.stderr,
                )

        return productos


class ServicioAPILocal:
    _TIMEOUT = 10

    def __init__(self, url_endpoint: str) -> None:
        self._url = url_endpoint

    def publicar_producto(self, producto: ProductoCompetidor) -> None:
        payload = producto.a_payload()
        try:
            respuesta = requests.post(self._url, json=payload, timeout=self._TIMEOUT)
            respuesta.raise_for_status()
        except requests.exceptions.ConnectionError as exc:
            raise ExcepcionAPILocal(
                f"No se pudo conectar a la API local en '{self._url}'. "
                f"¿Está el servidor levantado? Detalle: {exc}"
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise ExcepcionAPILocal(
                f"Timeout al hacer POST a '{self._url}': {exc}"
            ) from exc
        except requests.exceptions.HTTPError as exc:
            raise ExcepcionAPILocal(
                f"HTTP {exc.response.status_code} desde la API local: {exc.response.text[:300]}"
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise ExcepcionAPILocal(
                f"Error inesperado al hacer POST a '{self._url}': {exc}"
            ) from exc


def main() -> None:
    servicio_scraper = ServicioExtraccionHTTP(URL_COMPETENCIA)
    servicio_api = ServicioAPILocal(URL_API_LOCAL)

    print(f"[INFO] Extrayendo productos desde '{URL_COMPETENCIA}'...")

    try:
        productos = servicio_scraper.extraer_todos()
    except ExcepcionRed as exc:
        print(f"[ERROR DE RED] {exc}", file=sys.stderr)
        sys.exit(1)
    except ExcepcionParseo as exc:
        print(f"[ERROR DE PARSEO] {exc}", file=sys.stderr)
        sys.exit(2)

    if not productos:
        print("[AVISO] No se extrajeron productos. No hay nada que publicar.")
        sys.exit(0)

    print(f"[INFO] {len(productos)} productos extraídos. Iniciando publicación en API local...")

    publicados = 0
    errores = 0

    for indice, producto in enumerate(productos, start=1):
        try:
            servicio_api.publicar_producto(producto)
            print(f"[OK] ({indice}/{len(productos)}) '{producto.titulo[:70]}'")
            publicados += 1
        except ExcepcionAPILocal as exc:
            print(f"[ERROR API] ({indice}/{len(productos)}) '{producto.titulo[:70]}': {exc}", file=sys.stderr)
            errores += 1

        time.sleep(0.3)

    print(f"\n[RESUMEN] Publicados: {publicados} | Errores: {errores}")


if __name__ == "__main__":
    main()