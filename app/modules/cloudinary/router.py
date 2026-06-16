import cloudinary
import cloudinary.uploader
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends, Path

from app.core.config import settings
from app.modules.rol.enums import RolEnum
from app.core.deps import require_role

router_cloudinary = APIRouter(prefix="/api/v1", tags=["cloudinary"])

# Límite de tamaño de subida exigido por la spec.
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB


def _configure_cloudinary() -> None:
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
    )


@router_cloudinary.post(
    "/upload",
    dependencies=[Depends(require_role([RolEnum.ADMIN]))],
)
async def upload_image(file: UploadFile = File(...)):
    # Validación de tipo: solo imágenes.
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se permiten archivos de imagen",
        )

    # Validación de tamaño: se lee a memoria (máx. 5 MB) para medir antes de subir.
    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="La imagen supera el tamaño máximo de 5 MB",
        )

    _configure_cloudinary()

    try:
        result = cloudinary.uploader.upload(contents)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error al subir la imagen a Cloudinary: {str(e)}",
        )

    return {
        "url": result["secure_url"],
        "public_id": result["public_id"],
        "width": result.get("width"),
        "height": result.get("height"),
        "format": result.get("format"),
    }


@router_cloudinary.delete(
    "/uploads/imagen/{public_id:path}",
    dependencies=[Depends(require_role([RolEnum.ADMIN]))],
)
async def delete_image(
    public_id: str = Path(..., description="public_id devuelto al subir la imagen"),
):
    """Elimina una imagen de Cloudinary por su public_id.

    Se usa `{public_id:path}` porque los public_id de Cloudinary pueden incluir
    barras (carpetas), p. ej. `productos/abc123`.
    """
    _configure_cloudinary()

    try:
        result = cloudinary.uploader.destroy(public_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error al eliminar la imagen en Cloudinary: {str(e)}",
        )

    # "ok" = borrada; "not found" = ya no existía (idempotente, no es error).
    if result.get("result") not in ("ok", "not found"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Cloudinary no pudo eliminar la imagen: {result.get('result')}",
        )

    return {"public_id": public_id, "result": result.get("result")}
