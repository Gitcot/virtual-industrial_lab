import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.asset import Asset
from app.models.user import User
from app.services.motor_generation import (
    MissingNameplateDataError,
    frame_dimensions_for_asset,
    generate_glb_for_asset,
    motor_physics_for_asset,
)

router = APIRouter(prefix="/api/assets", tags=["motor-generation"])


def _get_asset_or_404(asset_id: uuid.UUID, db: Session) -> Asset:
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset introuvable")
    return asset


@router.get("/{asset_id}/motor-physics")
def get_motor_physics(
    asset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Calcule les grandeurs électromécaniques (vitesse de synchronisme,
    glissement, couple nominal/démarrage/décrochage) à partir des données
    de plaque signalétique stockées sur l'Asset. Théorie du circuit
    équivalent / formule de Kloss — voir simulation/motor_physics.py pour
    le détail et le statut épistémique de chaque valeur.
    """
    asset = _get_asset_or_404(asset_id, db)
    try:
        return motor_physics_for_asset(asset)
    except MissingNameplateDataError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/{asset_id}/frame-dimensions")
def get_frame_dimensions(
    asset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retourne les dimensions de carcasse utilisées pour la génération 3D :
    cotes réelles si fournies dans asset.geometry, sinon estimation IEC
    60072 depuis la puissance nominale (voir frame_dimensions.py).
    """
    asset = _get_asset_or_404(asset_id, db)
    try:
        dims = frame_dimensions_for_asset(asset)
    except MissingNameplateDataError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {
        "frame_designation": dims.frame_designation,
        "shaft_height_mm": dims.shaft_height_mm,
        "body_diameter_mm": dims.body_diameter_mm,
        "body_length_mm": dims.body_length_mm,
        "shaft_diameter_mm": dims.shaft_diameter_mm,
        "shaft_length_mm": dims.shaft_length_mm,
    }


@router.post("/{asset_id}/generate-3d-model")
def generate_3d_model(
    asset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Génère (ou régénère) le modèle 3D GLB de cet Asset via Blender, à
    partir de ses dimensions de carcasse (réelles ou estimées). Opération
    synchrone de quelques secondes (lance un sous-processus Blender).
    """
    asset = _get_asset_or_404(asset_id, db)
    try:
        output_path = generate_glb_for_asset(asset)
    except MissingNameplateDataError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "asset_id": str(asset.id),
        "model_url": f"/api/assets/{asset.id}/3d-model",
        "file_size_bytes": output_path.stat().st_size,
    }


@router.get("/{asset_id}/3d-model")
def download_3d_model(
    asset_id: uuid.UUID,
    db: Session = Depends(get_db)
    
):
    """Télécharge le modèle GLB déjà généré (appeler generate-3d-model avant si absent)."""
    asset = _get_asset_or_404(asset_id, db)
    from app.services.motor_generation import GENERATED_MODELS_DIR
    glb_path = GENERATED_MODELS_DIR / f"{asset.id}.glb"
    if not glb_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Aucun modèle 3D généré pour cet asset. Appelez POST .../generate-3d-model d'abord.",
        )
    return FileResponse(glb_path, media_type="model/gltf-binary", filename=f"{asset.name}.glb")
