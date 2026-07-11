import csv
import json
import os
import sys
import time

import requests
from dotenv import load_dotenv

load_dotenv()

STORE_URL = os.environ["SHOPIFY_STORE_URL"].rstrip("/")
ACCESS_TOKEN = os.environ["SHOPIFY_ACCESS_TOKEN"]

ENDPOINT = f"{STORE_URL}/admin/api/2024-04/products.json"

HEADERS = {
    "Content-Type": "application/json",
    "X-Shopify-Access-Token": ACCESS_TOKEN,
}


def parse_float(value: str) -> str:
    try:
        return str(float(value.replace(",", ".")))
    except ValueError:
        return "0.00"


def parse_int(value: str) -> int:
    try:
        return int(value.strip())
    except ValueError:
        return 0


def build_payload(row: dict) -> dict:
    return {
        "product": {
            "title": row["titulo"].strip(),
            "body_html": row["descripcion"].strip(),
            "variants": [
                {
                    "price": parse_float(row["precio"]),
                    "compare_at_price": parse_float(row["precio_comparacion"]),
                    "inventory_management": "shopify",
                    "inventory_quantity": parse_int(row["inventario"]),
                    "requires_shipping": True,
                    "taxable": True,
                }
            ],
            "images": [
                {
                    "src": row["url_imagen"].strip()
                }
            ] if row.get("url_imagen", "").strip() else [],
        }
    }


def create_product(payload: dict) -> dict:
    response = requests.post(ENDPOINT, headers=HEADERS, data=json.dumps(payload), timeout=30)
    response.raise_for_status()
    return response.json()


def main():
    csv_path = "productos.csv"

    if not os.path.exists(csv_path):
        print(f"Error: no se encontró el archivo '{csv_path}'.", file=sys.stderr)
        sys.exit(1)

    required_columns = {"titulo", "descripcion", "precio", "precio_comparacion", "url_imagen", "inventario"}

    success_count = 0
    error_count = 0

    with open(csv_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)

        if not required_columns.issubset(set(reader.fieldnames or [])):
            missing = required_columns - set(reader.fieldnames or [])
            print(f"Error: columnas faltantes en el CSV: {missing}", file=sys.stderr)
            sys.exit(1)

        for line_number, row in enumerate(reader, start=2):
            payload = build_payload(row)
            try:
                result = create_product(payload)
                product_id = result["product"]["id"]
                title = result["product"]["title"]
                print(f"[OK] Línea {line_number} → ID {product_id} | {title}")
                success_count += 1
            except requests.exceptions.HTTPError as exc:
                status = exc.response.status_code
                body = exc.response.text
                print(f"[ERROR] Línea {line_number} → HTTP {status} | {body}", file=sys.stderr)
                error_count += 1
            except requests.exceptions.RequestException as exc:
                print(f"[ERROR] Línea {line_number} → {exc}", file=sys.stderr)
                error_count += 1

            time.sleep(0.5)

    print(f"\nResumen: {success_count} creados, {error_count} errores.")


if __name__ == "__main__":
    main()