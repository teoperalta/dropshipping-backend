from __future__ import annotations

import csv
import os
import sys
import time
from dataclasses import dataclass
from typing import List

import anthropic
from dotenv import load_dotenv

load_dotenv()


class LecturaCSVError(Exception):
    pass


class APIInteligenciaArtificialError(Exception):
    pass


class EscrituraCSVError(Exception):
    pass


COLUMNAS = [
    "titulo",
    "descripcion",
    "precio",
    "precio_comparacion",
    "url_imagen",
    "inventario",
]

SYSTEM_PROMPT = (
    "Eres un experto en copywriting para e-commerce y dropshipping. "
    "Tu única tarea es transformar descripciones de productos en textos de venta "
    "persuasivos y estructurados en HTML. "
    "Responde ÚNICAMENTE con el bloque HTML resultante, sin explicaciones, "
    "sin bloques de código Markdown y sin texto adicional fuera del HTML."
)

USER_PROMPT_TEMPLATE = (
    "Convierte la siguiente descripción de producto en un texto de ventas persuasivo "
    "usando SOLO etiquetas HTML <ul>, <li> y <strong>. "
    "Destaca los beneficios clave, usa lenguaje orientado al cliente y genera urgencia de compra. "
    "No incluyas etiquetas <html>, <body>, <head> ni ningún otro elemento fuera de <ul>.\n\n"
    "Descripción original:\n{descripcion}"
)


@dataclass
class Producto:
    titulo: str
    descripcion: str
    precio: str
    precio_comparacion: str
    url_imagen: str
    inventario: str

    @classmethod
    def desde_fila(cls, fila: dict) -> "Producto":
        return cls(
            titulo=fila["titulo"],
            descripcion=fila["descripcion"],
            precio=fila["precio"],
            precio_comparacion=fila["precio_comparacion"],
            url_imagen=fila["url_imagen"],
            inventario=fila["inventario"],
        )

    def a_fila(self) -> dict:
        return {
            "titulo": self.titulo,
            "descripcion": self.descripcion,
            "precio": self.precio,
            "precio_comparacion": self.precio_comparacion,
            "url_imagen": self.url_imagen,
            "inventario": self.inventario,
        }


class ServicioIA:
    _MODELO = "claude-haiku-4-5-20251001"
    _MAX_TOKENS = 1024
    _REINTENTOS = 3
    _ESPERA_BASE = 2.0

    def __init__(self, api_key: str) -> None:
        self._cliente = anthropic.Anthropic(api_key=api_key)

    def optimizar_descripcion(self, descripcion: str) -> str:
        prompt = USER_PROMPT_TEMPLATE.format(descripcion=descripcion)
        ultimo_error: Exception | None = None

        for intento in range(self._REINTENTOS):
            try:
                respuesta = self._cliente.messages.create(
                    model=self._MODELO,
                    max_tokens=self._MAX_TOKENS,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}],
                )
                return respuesta.content[0].text.strip()
            except anthropic.APIStatusError as exc:
                ultimo_error = exc
                if exc.status_code in {429, 529}:
                    time.sleep(self._ESPERA_BASE * (2 ** intento))
                    continue
                raise APIInteligenciaArtificialError(
                    f"Error HTTP {exc.status_code} de la API de Anthropic: {exc.message}"
                ) from exc
            except anthropic.APIConnectionError as exc:
                ultimo_error = exc
                time.sleep(self._ESPERA_BASE * (2 ** intento))
            except anthropic.AnthropicError as exc:
                raise APIInteligenciaArtificialError(
                    f"Error inesperado del SDK de Anthropic: {exc}"
                ) from exc

        raise APIInteligenciaArtificialError(
            f"Se agotaron {self._REINTENTOS} reintentos al llamar a la API: {ultimo_error}"
        )


class GestorCSV:
    def __init__(self, ruta_entrada: str, ruta_salida: str) -> None:
        self._ruta_entrada = ruta_entrada
        self._ruta_salida = ruta_salida

    def leer(self) -> List[Producto]:
        try:
            with open(self._ruta_entrada, newline="", encoding="utf-8") as archivo:
                lector = csv.DictReader(archivo)
                columnas_presentes = set(lector.fieldnames or [])
                faltantes = set(COLUMNAS) - columnas_presentes
                if faltantes:
                    raise LecturaCSVError(
                        f"Columnas faltantes en '{self._ruta_entrada}': {faltantes}"
                    )
                return [Producto.desde_fila(fila) for fila in lector]
        except FileNotFoundError as exc:
            raise LecturaCSVError(
                f"No se encontró el archivo '{self._ruta_entrada}'."
            ) from exc
        except IOError as exc:
            raise LecturaCSVError(
                f"Error de I/O al leer '{self._ruta_entrada}': {exc}"
            ) from exc

    def escribir(self, productos: List[Producto]) -> None:
        try:
            with open(self._ruta_salida, mode="w", newline="", encoding="utf-8") as archivo:
                escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS)
                escritor.writeheader()
                for producto in productos:
                    escritor.writerow(producto.a_fila())
        except IOError as exc:
            raise EscrituraCSVError(
                f"Error de I/O al escribir '{self._ruta_salida}': {exc}"
            ) from exc


def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("[ERROR] La variable de entorno ANTHROPIC_API_KEY no está definida.", file=sys.stderr)
        sys.exit(1)

    gestor = GestorCSV("productos.csv", "productos_optimizados.csv")
    servicio_ia = ServicioIA(api_key)

    try:
        productos = gestor.leer()
    except LecturaCSVError as exc:
        print(f"[ERROR DE LECTURA] {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] {len(productos)} productos leídos. Iniciando optimización...")

    exitosos = 0
    fallidos = 0

    for indice, producto in enumerate(productos, start=1):
        try:
            descripcion_optimizada = servicio_ia.optimizar_descripcion(producto.descripcion)
            producto.descripcion = descripcion_optimizada
            exitosos += 1
            print(f"[OK] ({indice}/{len(productos)}) '{producto.titulo[:60]}'")
        except APIInteligenciaArtificialError as exc:
            fallidos += 1
            print(
                f"[ERROR IA] ({indice}/{len(productos)}) '{producto.titulo[:60]}': {exc}",
                file=sys.stderr,
            )

        time.sleep(0.3)

    try:
        gestor.escribir(productos)
    except EscrituraCSVError as exc:
        print(f"[ERROR DE ESCRITURA] {exc}", file=sys.stderr)
        sys.exit(2)

    print(
        f"\n[RESUMEN] Completado: {exitosos} optimizados, {fallidos} con error. "
        f"Resultado guardado en 'productos_optimizados.csv'."
    )


if __name__ == "__main__":
    main()