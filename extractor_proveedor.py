from __future__ import annotations

import csv
import sys
from dataclasses import dataclass, field
from typing import List

import requests


class NetworkError(Exception):
    pass


class StorageError(Exception):
    pass


@dataclass
class Producto:
    titulo: str
    descripcion: str
    precio: float
    precio_comparacion: float
    url_imagen: str
    inventario: int = field(default=100)

    @classmethod
    def desde_dict(cls, raw: dict) -> "Producto":
        precio = float(raw["price"])
        return cls(
            titulo=str(raw["title"]),
            descripcion=str(raw["description"]),
            precio=precio,
            precio_comparacion=round(precio * 1.5, 2),
            url_imagen=str(raw["image"]),
            inventario=100,
        )

    def a_fila(self) -> List[str]:
        return [
            self.titulo,
            self.descripcion,
            str(self.precio),
            str(self.precio_comparacion),
            self.url_imagen,
            str(self.inventario),
        ]


class ServicioExtraccion:
    COLUMNAS = ["titulo", "descripcion", "precio", "precio_comparacion", "url_imagen", "inventario"]
    _TIMEOUT = 15

    def __init__(self, url: str) -> None:
        self._url = url

    def obtener_productos(self) -> List[Producto]:
        try:
            respuesta = requests.get(self._url, timeout=self._TIMEOUT)
            respuesta.raise_for_status()
            datos = respuesta.json()
        except requests.exceptions.ConnectionError as exc:
            raise NetworkError(f"No se pudo conectar a '{self._url}': {exc}") from exc
        except requests.exceptions.Timeout as exc:
            raise NetworkError(f"Tiempo de espera agotado al conectar a '{self._url}': {exc}") from exc
        except requests.exceptions.HTTPError as exc:
            raise NetworkError(f"Respuesta HTTP inesperada de '{self._url}': {exc}") from exc
        except requests.exceptions.RequestException as exc:
            raise NetworkError(f"Error de red al acceder a '{self._url}': {exc}") from exc

        return [Producto.desde_dict(item) for item in datos]


class ControladorCSV:
    def __init__(self, ruta: str, columnas: List[str]) -> None:
        self._ruta = ruta
        self._columnas = columnas

    def escribir(self, productos: List[Producto]) -> None:
        try:
            with open(self._ruta, mode="w", newline="", encoding="utf-8") as archivo:
                escritor = csv.writer(archivo)
                escritor.writerow(self._columnas)
                for producto in productos:
                    escritor.writerow(producto.a_fila())
        except IOError as exc:
            raise StorageError(f"No se pudo escribir en '{self._ruta}': {exc}") from exc


def main() -> None:
    API_URL = "https://fakestoreapi.com/products"
    CSV_RUTA = "productos.csv"

    servicio = ServicioExtraccion(API_URL)
    controlador = ControladorCSV(CSV_RUTA, ServicioExtraccion.COLUMNAS)

    try:
        productos = servicio.obtener_productos()
        controlador.escribir(productos)
        print(f"[OK] {len(productos)} productos escritos en '{CSV_RUTA}'.")
    except NetworkError as exc:
        print(f"[ERROR DE RED] {exc}", file=sys.stderr)
        sys.exit(1)
    except StorageError as exc:
        print(f"[ERROR DE ALMACENAMIENTO] {exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()