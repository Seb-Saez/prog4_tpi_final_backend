from typing import List, Optional
from fastapi import HTTPException
from sqlmodel import Session, col, select

from app.modules.producto.model import Producto
from app.modules.producto.schema import (
    DisponibilidadUpdate,
    ImagenesUpdate,
    ProductoCreate,
    ProductoIngredienteInput,
    ProductoIngredienteOut,
    ProductoUpdate,
    ProductoResponse,
)
from app.modules.producto.unit_of_work import ProductoUnitOfWork
from app.modules.categoria.model import Categoria
from app.modules.producto_ingrediente.model import ProductoIngrediente
from app.core.datetime_utils import utcnow

class ProductoService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _get_or_404(self, uow: ProductoUnitOfWork, producto_id: int) -> Producto:
        producto = uow.productos.get_by_id_ingredientes(producto_id)
        if not producto:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        return producto

    def _sync_ingredientes(self, uow: ProductoUnitOfWork, producto: Producto, ingredientes_data: list) -> None:
        existing_ids = {pi.ingrediente_id for pi in producto.producto_ingredientes}
        new_ids = {i.ingrediente_id for i in ingredientes_data}

        to_delete = [pi for pi in producto.producto_ingredientes if pi.ingrediente_id not in new_ids]
        for pi in to_delete:
            uow.session.delete(pi)

        for item in ingredientes_data:
            if item.ingrediente_id in existing_ids:
                pi = next(pi for pi in producto.producto_ingredientes if pi.ingrediente_id == item.ingrediente_id)
                pi.cantidad = item.cantidad
                pi.unidad_medida_id = item.unidad_medida_id
                pi.es_removible = item.es_removible
            else:
                pi = ProductoIngrediente(
                    producto_id=producto.id,
                    ingrediente_id=item.ingrediente_id,
                    cantidad=item.cantidad,
                    unidad_medida_id=item.unidad_medida_id,
                    es_removible=item.es_removible,
                )
                uow.session.add(pi)

    def create(self, data: ProductoCreate) -> Producto:
        with ProductoUnitOfWork(self._session) as uow:
            if data.imagenes_url is None:
                data.imagenes_url = []
            producto = Producto.model_validate(data)

            if producto.stock_cantidad == 0:
                producto.disponible = False
            elif producto.stock_cantidad > 0:
                producto.disponible = True

            if hasattr(data, "categorias_ids") and data.categorias_ids:
                categorias = list(
                    uow.session.exec(
                        select(Categoria).where(col(Categoria.id).in_(data.categorias_ids))
                    ).all()
                )
                producto.categorias = categorias

            uow.productos.add(producto)
            uow.session.flush()

            if data.ingredientes:
                for item in data.ingredientes:
                    pi = ProductoIngrediente(
                        producto_id=producto.id,
                        ingrediente_id=item.ingrediente_id,
                        cantidad=item.cantidad,
                        unidad_medida_id=item.unidad_medida_id,
                        es_removible=item.es_removible,
                    )
                    uow.session.add(pi)

            return Producto.model_validate(producto)

    def get_by_id(self, producto_id: int) -> Producto:
        with ProductoUnitOfWork(self._session) as uow:
            return self._get_or_404(uow, producto_id)

    def list(self, skip: int = 0, limit: int = 20, disponible: Optional[bool] = None) -> list[Producto]:
        with ProductoUnitOfWork(self._session) as uow:
            productos = uow.productos.get_all_ingredientes()

            if disponible is not None:
                productos = [p for p in productos if p.disponible == disponible]

            return list(productos)[skip : skip + limit]

    def update(self, producto_id: int, data: ProductoUpdate) -> Producto:
        with ProductoUnitOfWork(self._session) as uow:
            producto = self._get_or_404(uow, producto_id)

            update_data = data.model_dump(
                exclude_unset=True,
                exclude={"categorias_ids", "ingredientes"},
                )

            if "categorias_ids" in data.model_fields_set and data.categorias_ids is not None:
                categorias = list(
                        uow.session.exec(
                            select(Categoria).where(col(Categoria.id).in_(data.categorias_ids))
                        ).all()
                    )
                producto.categorias = categorias

            if "ingredientes_ids" in data.model_fields_set and data.ingredientes is not None:
                self._sync_ingredientes(uow, producto, data.ingredientes)

            for field, value in update_data.items():
                setattr(producto, field, value)

            if producto.stock_cantidad == 0:
                producto.disponible = False
            elif producto.stock_cantidad > 0:
                producto.disponible = True

            producto.updated_at = utcnow()

            uow.productos.add(producto)
            return producto

    def set_disponibilidad(self, producto_id: int, disponible: bool) -> Producto:
        with ProductoUnitOfWork(self._session) as uow:
            producto = self._get_or_404(uow, producto_id)
            producto.disponible = disponible
            producto.updated_at = utcnow()
            uow.productos.add(producto)
            return producto

    def set_imagenes(self, producto_id: int, imagenes_url: Optional[List[str]]) -> Producto:
        with ProductoUnitOfWork(self._session) as uow:
            producto = self._get_or_404(uow, producto_id)
            producto.imagenes_url = imagenes_url or []
            producto.updated_at = utcnow()
            uow.productos.add(producto)
            return producto

    def get_ingredientes(self, producto_id: int) -> List[ProductoIngredienteOut]:
        with ProductoUnitOfWork(self._session) as uow:
            producto = self._get_or_404(uow, producto_id)
            return [
                ProductoIngredienteOut(
                    ingrediente_id=pi.ingrediente_id,
                    cantidad=pi.cantidad,
                    unidad_medida_id=pi.unidad_medida_id,
                    es_removible=pi.es_removible,
                    nombre=pi.ingrediente.nombre,
                    stock_cantidad=pi.ingrediente.stock_cantidad,
                )
                for pi in producto.producto_ingredientes
            ]

    def add_ingrediente(
        self, producto_id: int, data: ProductoIngredienteInput
    ) -> List[ProductoIngrediente]:
        with ProductoUnitOfWork(self._session) as uow:
            producto = self._get_or_404(uow, producto_id)

            # Verifica si el vínculo ya existe
            existe = any(
                pi.ingrediente_id == data.ingrediente_id
                for pi in producto.producto_ingredientes
            )
            if existe:
                raise HTTPException(
                    status_code=409,
                    detail="El ingrediente ya está asociado al producto",
                )

            pi = ProductoIngrediente(
                producto_id=producto_id,
                ingrediente_id=data.ingrediente_id,
                cantidad=data.cantidad,
                unidad_medida_id=data.unidad_medida_id,
                es_removible=data.es_removible,
            )
            uow.session.add(pi)
            uow.session.flush()

            # Recarga para devolver la lista actualizada
            producto_actualizado = self._get_or_404(uow, producto_id)
            return list(producto_actualizado.producto_ingredientes)

    def delete(self, producto_id: int) -> bool:
        with ProductoUnitOfWork(self._session) as uow:
            producto = self._get_or_404(uow, producto_id)
            uow.productos.delete(producto)
            return True


def create_producto(session: Session, data: ProductoCreate) -> Producto:
    service = ProductoService(session)
    return service.create(data)


def get_producto_by_id(session: Session, producto_id: int) -> Producto:
    service = ProductoService(session)
    return service.get_by_id(producto_id)


def list_productos(
    session: Session,
    skip: int = 0,
    limit: int = 20,
    disponible: Optional[bool] = None,
) -> list[Producto]:
    service = ProductoService(session)
    return service.list(skip=skip, limit=limit, disponible=disponible)


def update_producto(session: Session, producto_id: int, data: ProductoUpdate) -> Producto:
    service = ProductoService(session)
    return service.update(producto_id, data)


def delete_producto(session: Session, producto_id: int) -> bool:
    service = ProductoService(session)
    return service.delete(producto_id)


def set_disponibilidad_producto(
    session: Session, producto_id: int, disponible: bool
) -> Producto:
    service = ProductoService(session)
    return service.set_disponibilidad(producto_id, disponible)


def set_imagenes_producto(
    session: Session, producto_id: int, imagenes_url: Optional[List[str]]
) -> Producto:
    service = ProductoService(session)
    return service.set_imagenes(producto_id, imagenes_url)


def get_ingredientes_producto(
    session: Session, producto_id: int
) -> list[ProductoIngredienteOut]:
    service = ProductoService(session)
    return service.get_ingredientes(producto_id)


def add_ingrediente_producto(
    session: Session, producto_id: int, data: ProductoIngredienteInput
) -> list[ProductoIngrediente]:
    service = ProductoService(session)
    return service.add_ingrediente(producto_id, data)
