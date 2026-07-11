from datetime import datetime, timezone
from typing import List
from datetime import datetime, timezone
from sqlalchemy import BigInteger, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Producto(Base):
    __tablename__ = "productos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    titulo: Mapped[str] = mapped_column(String(512), unique=True, nullable=False, index=True)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    precio: Mapped[float] = mapped_column(Float, nullable=False)
    precio_comparacion: Mapped[float] = mapped_column(Float, nullable=False)
    inventario: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    ventas: Mapped[List["Venta"]] = relationship(
        "Venta",
        back_populates="producto",
        cascade="all, delete-orphan",
    )


class Venta(Base):
    __tablename__ = "ventas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    producto_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("productos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    total: Mapped[float] = mapped_column(Float, nullable=False)
    fecha_venta: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    producto: Mapped["Producto"] = relationship("Producto", back_populates="ventas")
class TransaccionDropshipping(Base):
    __tablename__ = "transacciones_dropshipping"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    shopify_order_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    numero_orden: Mapped[str] = mapped_column(String(64), nullable=False)
    estado_pago: Mapped[str] = mapped_column(String(64), nullable=False)
    cliente_nombre: Mapped[str] = mapped_column(String(256), nullable=True)
    cliente_direccion: Mapped[str] = mapped_column(String(512), nullable=True)
    estado_proveedor: Mapped[str] = mapped_column(String(64), nullable=False, default="pendiente")
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )