import cloudinary
import cloudinary.uploader
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends

from app.core.config import settings
from app.modules.rol.enums import RolEnum
from app.core.deps import require_role

router_cloudinary = APIRouter(prefix="/api/v1", tags=["cloudinary"])


@router_cloudinary.post(
    "/upload",
    dependencies=[Depends(require_role([RolEnum.ADMIN]))],
)
async def upload_image(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se permiten archivos de imagen",
        )

    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
    )

    try:
        result = cloudinary.uploader.upload(file.file)
        return {"url": result["secure_url"]}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error al subir la imagen a Cloudinary: {str(e)}",
        )
