import sys
import os
import httpx
import os
import httpx
from dotenv import load_dotenv
load_dotenv()
PROVEEDOR_URL: str = "https://developers.cjdropshipping.com/api2.0/v1/shopping/order/createOrder"
PROVEEDOR_TIMEOUT: float = 10.0
from typing import Generator, List
from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
import json
import asyncio
from fastapi import Request
from models import TransaccionDropshipping
import crud
from database import Base, SessionLocal, engine
from schemas import (
    ProductoActualizar,
    ProductoCrear,
    ProductoRespuesta,
    VentaCreate,
    VentaResponse,
)
load_dotenv()

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Catálogo de Productos",
    version="2.0.0",
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get(
    "/productos",
    response_model=List[ProductoRespuesta],
    status_code=status.HTTP_200_OK,
    tags=["Productos"],
)
def listar_productos(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=250),
    db: Session = Depends(get_db),
) -> List[ProductoRespuesta]:
    return list(crud.obtener_productos(db, offset=offset, limit=limit))


@app.post(
    "/productos",
    response_model=ProductoRespuesta,
    status_code=status.HTTP_201_CREATED,
    tags=["Productos"],
)
def crear_producto(
    datos: ProductoCrear,
    db: Session = Depends(get_db),
) -> ProductoRespuesta:
    try:
        return crud.crear_producto(db, datos)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un producto con el título '{datos.titulo}'.",
        )


@app.put(
    "/productos/{producto_id}",
    response_model=ProductoRespuesta,
    status_code=status.HTTP_200_OK,
    tags=["Productos"],
)
def actualizar_producto(
    producto_id: int,
    datos: ProductoActualizar,
    db: Session = Depends(get_db),
) -> ProductoRespuesta:
    producto = crud.obtener_producto_por_id(db, producto_id)
    if producto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Producto con id={producto_id} no encontrado.",
        )
    try:
        return crud.actualizar_producto(db, producto, datos)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El título proporcionado ya pertenece a otro producto.",
        )


@app.post(
    "/ventas",
    response_model=VentaResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Ventas"],
)
def registrar_venta(
    datos: VentaCreate,
    db: Session = Depends(get_db),
) -> VentaResponse:
    return crud.registrar_venta(db, datos)

@app.get(
    "/estadisticas",
    response_model=dict[str, float | int],
    status_code=status.HTTP_200_OK,
    tags=["Analíticas"],
)
def obtener_estadisticas(
    db: Session = Depends(get_db),
) -> dict[str, float | int]:
    return crud.obtener_estadisticas_ventas(db)

async def enviar_orden_proveedor(datos_orden: dict) -> bool:
    api_key: str | None = os.getenv("PROVEEDOR_API_KEY")

    if not api_key:
        print("[ERROR PROVEEDOR] La variable de entorno PROVEEDOR_API_KEY no está configurada.", file=sys.stderr)
        return False

    orden: dict = datos_orden.get("orden", {})
    cliente: dict = datos_orden.get("cliente", {})
    productos: list = datos_orden.get("productos", [])

    payload: dict = {
        "orderNumber":          str(orden.get("order_number", "")),
        "shippingCustomerName": cliente.get("nombre_completo") or "Sin Nombre",
        "shippingAddress":      cliente.get("direccion") or "Sin Direccion",
        "shippingCity":         cliente.get("ciudad") or "Sin Ciudad",
        "shippingProvince":     cliente.get("provincia") or "Sin Provincia",
        "shippingCountry":  cliente.get("pais") or "US",
        "shippingCountryCode":  cliente.get("pais") or "US",
        "shippingZip":          cliente.get("codigo_postal") or "00000",
        "shippingPhone":        "0000000000", # CJ suele exigir un número de teléfono
        "fromCountryCode":      "CN",
        "logisticName":         "CJPacket Ordinary",
        "products": [
            {
            
                "variantSku": item.get("sku") or "SKU-DE-PRUEBA",
                "quantity": item.get("quantity", 1)
            }
            for item in productos
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            
            # --- PASO 1: INTERCAMBIAR LA API KEY POR UN TOKEN TEMPORAL ---
            url_auth = "https://developers.cjdropshipping.com/api2.0/v1/authentication/getAccessToken"
            respuesta_auth = await client.post(url_auth, json={"apiKey": api_key})
            respuesta_auth.raise_for_status()
            
            auth_data = respuesta_auth.json()
            if not auth_data.get("result"):
                print(f"[ERROR CJ AUTH] Falló el login en CJ: {auth_data.get('message')}", file=sys.stderr)
                return False
                
            # Extraemos el pase VIP temporal
            access_token = auth_data["data"]["accessToken"]

            # --- PASO 2: ENVIAR LA ORDEN CON EL NUEVO TOKEN ---
            url_cj = "https://developers.cjdropshipping.com/api2.0/v1/shopping/order/createOrder"
            headers = {
                "CJ-Access-Token": access_token,
                "Content-Type": "application/json",
            }
            
            respuesta_orden = await client.post(url_cj, headers=headers, json=payload)
            respuesta_orden.raise_for_status()

        print(
            f"[PROVEEDOR] ✅ Orden {orden.get('order_number')} enviada. "
            f"Status: {respuesta_orden.status_code} | "
            f"Respuesta: {respuesta_orden.text[:200]}"
        )
        return True

    except httpx.TimeoutException as exc:
        print(f"[ERROR PROVEEDOR] Timeout al comunicar con CJ: {exc}", file=sys.stderr)
        return False
    except httpx.HTTPStatusError as exc:
        print(
            f"[ERROR PROVEEDOR] HTTP {exc.response.status_code} al comunicar con CJ: {exc.response.text[:300]}",
            file=sys.stderr,
        )
        return False
    except httpx.RequestError as exc:
        print(f"[ERROR PROVEEDOR] Error de red general: {exc}", file=sys.stderr)
        return False

@app.post(
    "/webhook/ordenes",
    status_code=status.HTTP_200_OK,
    tags=["Webhooks"],
)
async def webhook_ordenes(
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    try:
        datos = await request.json()

        direccion = datos.get("shipping_address") or {}
        nombre_cliente = (
            f"{direccion.get('first_name', '')} {direccion.get('last_name', '')}".strip()
        )

        productos = [
            {
                "product_id": item.get("product_id"),
                "title":      item.get("title"),
                "sku":        item.get("sku"),
                "quantity":   item.get("quantity"),
                "price":      item.get("price"),
            }
            for item in datos.get("line_items", [])
        ]

        orden_procesada: dict = {
            "orden": {
                "id":               datos.get("id"),
                "order_number":     datos.get("order_number"),
                "total_price":      datos.get("total_price"),
                "financial_status": datos.get("financial_status"),
            },
            "cliente": {
                "nombre_completo": nombre_cliente,
                "direccion":       direccion.get("address1"),
                "ciudad":          direccion.get("city"),
                "provincia":       direccion.get("province"),
                "pais":            direccion.get("country"),
                "codigo_postal":   direccion.get("zip"),
            },
            "productos": productos,
        }

        print("\n" + "=" * 60)
        print("🚨  NUEVA ORDEN SHOPIFY — DATOS ESTRUCTURADOS  🚨")
        print("=" * 60)
        print(json.dumps(orden_procesada, indent=4, ensure_ascii=False))
        print("=" * 60 + "\n")

        financial_status: str = orden_procesada["orden"].get("financial_status", "")
        orden_id = orden_procesada["orden"].get("id", "N/A")

        if financial_status == "paid":
            transaccion = TransaccionDropshipping(
                shopify_order_id=orden_procesada["orden"]["id"],
                numero_orden=str(orden_procesada["orden"].get("order_number", "")),
                estado_pago=financial_status,
                cliente_nombre=orden_procesada["cliente"].get("nombre_completo"),
                cliente_direccion=orden_procesada["cliente"].get("direccion"),
                estado_proveedor="pendiente",
            )

            try:
                db.add(transaccion)
                db.commit()
                db.refresh(transaccion)
                print(f"[DB] Transacción {transaccion.id} registrada con estado 'pendiente'.")
            except IntegrityError:
                db.rollback()
                print(
                    f"[DB] ⚠️  Orden {orden_id} ya existe en la base de datos. Webhook duplicado ignorado.",
                    file=sys.stderr,
                )
                return {"status": "success"}

            exito: bool = await enviar_orden_proveedor(orden_procesada)
            transaccion.estado_proveedor = "enviado" if exito else "error"
            db.commit()
            print(
            f"[DB] Transacción {transaccion.id} → estado_proveedor='{transaccion.estado_proveedor}'"
            )

        else:
            print(
                f"⚠️  Orden {orden_id} ignorada. "
                f"Estado financiero: '{financial_status}' — no requiere acción.\n"
            )

    except Exception as exc:
        print(f"[ERROR WEBHOOK] No se pudo procesar el payload: {exc}", file=sys.stderr)

    return {"status": "success"}