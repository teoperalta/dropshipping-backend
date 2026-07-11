from typing import Optional, Sequence
from sqlalchemy import func
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import Producto, Venta
from schemas import ProductoActualizar, ProductoCrear, VentaCreate


def crear_producto(db: Session, datos: ProductoCrear) -> Producto:
    producto = Producto(
        titulo=datos.titulo,
        descripcion=datos.descripcion,
        precio=datos.precio,
        precio_comparacion=datos.precio_comparacion,
        inventario=datos.inventario,
    )
    db.add(producto)
    try:
        db.commit()
        db.refresh(producto)
    except IntegrityError:
        db.rollback()
        raise
    return producto


def obtener_productos(
    db: Session,
    offset: int = 0,
    limit: int = 100,
) -> Sequence[Producto]:
    return db.query(Producto).offset(offset).limit(limit).all()


def obtener_producto_por_id(db: Session, producto_id: int) -> Optional[Producto]:
    return db.query(Producto).filter(Producto.id == producto_id).first()


def actualizar_producto(
    db: Session,
    producto: Producto,
    datos: ProductoActualizar,
) -> Producto:
    campos = datos.model_dump(exclude_unset=True)
    for campo, valor in campos.items():
        setattr(producto, campo, valor)
    try:
        db.commit()
        db.refresh(producto)
    except IntegrityError:
        db.rollback()
        raise
    return producto


def registrar_venta(db: Session, datos: VentaCreate) -> Venta:
    producto: Optional[Producto] = (
        db.query(Producto)
        .filter(Producto.id == datos.producto_id)
        .with_for_update()
        .first()
    )

    if producto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Producto con id={datos.producto_id} no encontrado.",
        )

    if producto.inventario < datos.cantidad:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Stock insuficiente para '{producto.titulo}'. "
                f"Disponible: {producto.inventario}, solicitado: {datos.cantidad}."
            ),
        )

    total: float = round(producto.precio * datos.cantidad, 2)
    producto.inventario -= datos.cantidad

    venta = Venta(
        producto_id=datos.producto_id,
        cantidad=datos.cantidad,
        total=total,
    )

    db.add(venta)
    db.commit()
    db.refresh(venta)

    return venta


def obtener_estadisticas_ventas(db: Session) -> dict[str, float | int]:
    resultado = db.query(
        func.sum(Venta.total),
        func.sum(Venta.cantidad),
    ).first()

    ingresos = round(float(resultado[0]), 2) if resultado[0] is not None else 0.0
    articulos = int(resultado[1]) if resultado[1] is not None else 0

    return {
        "ingresos_totales": ingresos,
        "articulos_vendidos": articulos,
    }