from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, PositiveFloat, PositiveInt


class ProductoBase(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=512)
    descripcion: str = Field(..., min_length=1)
    precio: PositiveFloat
    precio_comparacion: PositiveFloat
    inventario: int = Field(..., ge=0)


class ProductoCrear(ProductoBase):
    pass


class ProductoActualizar(BaseModel):
    precio: PositiveFloat | None = None
    precio_comparacion: PositiveFloat | None = None
    inventario: int | None = Field(default=None, ge=0)


class ProductoRespuesta(ProductoBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class VentaCreate(BaseModel):
    producto_id: int = Field(..., gt=0)
    cantidad: int = Field(..., gt=0)


class VentaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    producto_id: int
    cantidad: int
    total: float
    fecha_venta: datetime