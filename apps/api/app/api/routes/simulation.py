import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.motor_session import MotorSession
from app.models.user import User
from app.schemas.motor_session import (
    FaultRequest,
    MotorSessionCreate,
    MotorSessionOut,
    StartRequest,
    TickRequest,
)
from app.services.motor_simulation import apply_simulator_to_session, simulator_from_session

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[5]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from simulation.motor_engine import FaultType, InvalidTransitionError, StartMode  # noqa: E402

router = APIRouter(prefix="/api/simulation/sessions", tags=["simulation"])


def _get_owned_session(session_id: uuid.UUID, db: Session, user: User) -> MotorSession:
    session = (
        db.query(MotorSession)
        .filter(MotorSession.id == session_id, MotorSession.owner_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session de simulation introuvable")
    return session


@router.post("", response_model=MotorSessionOut, status_code=201)
def create_session(
    payload: MotorSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    params = {}
    if payload.rated_voltage_v is not None:
        params["rated_voltage_v"] = payload.rated_voltage_v
    if payload.rated_current_a is not None:
        params["rated_current_a"] = payload.rated_current_a
    if payload.rated_power_kw is not None:
        params["rated_power_kw"] = payload.rated_power_kw

    session = MotorSession(
        owner_id=current_user.id,
        asset_id=payload.asset_id,
        motor_parameters=params,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("", response_model=list[MotorSessionOut])
def list_sessions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(MotorSession).filter(MotorSession.owner_id == current_user.id).all()


@router.get("/{session_id}", response_model=MotorSessionOut)
def get_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_owned_session(session_id, db, current_user)


@router.post("/{session_id}/start", response_model=MotorSessionOut)
def start_session(
    session_id: uuid.UUID,
    payload: StartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = _get_owned_session(session_id, db, current_user)
    try:
        mode = StartMode(payload.mode)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"mode invalide: '{payload.mode}' (attendu: direct|star_delta)")

    sim = simulator_from_session(session)
    try:
        sim.start(mode)
    except InvalidTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))

    apply_simulator_to_session(sim, session)
    db.commit()
    db.refresh(session)
    return session


@router.post("/{session_id}/stop", response_model=MotorSessionOut)
def stop_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = _get_owned_session(session_id, db, current_user)
    sim = simulator_from_session(session)
    try:
        sim.stop()
    except InvalidTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))

    apply_simulator_to_session(sim, session)
    db.commit()
    db.refresh(session)
    return session


@router.post("/{session_id}/fault", response_model=MotorSessionOut)
def inject_fault(
    session_id: uuid.UUID,
    payload: FaultRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = _get_owned_session(session_id, db, current_user)
    try:
        fault = FaultType(payload.fault_type)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"fault_type invalide: '{payload.fault_type}' (attendu: thermal_overload|phase_loss)",
        )

    sim = simulator_from_session(session)
    try:
        sim.inject_fault(fault)
    except InvalidTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))

    apply_simulator_to_session(sim, session)
    db.commit()
    db.refresh(session)
    return session


@router.post("/{session_id}/reset", response_model=MotorSessionOut)
def reset_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = _get_owned_session(session_id, db, current_user)
    sim = simulator_from_session(session)
    try:
        sim.reset()
    except InvalidTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))

    apply_simulator_to_session(sim, session)
    db.commit()
    db.refresh(session)
    return session


@router.post("/{session_id}/acknowledge", response_model=MotorSessionOut)
def acknowledge_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = _get_owned_session(session_id, db, current_user)
    sim = simulator_from_session(session)
    try:
        sim.acknowledge_and_stop()
    except InvalidTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))

    apply_simulator_to_session(sim, session)
    db.commit()
    db.refresh(session)
    return session


@router.post("/{session_id}/tick", response_model=MotorSessionOut)
def tick_session(
    session_id: uuid.UUID,
    payload: TickRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = _get_owned_session(session_id, db, current_user)
    sim = simulator_from_session(session)
    try:
        sim.tick(payload.dt_seconds)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    apply_simulator_to_session(sim, session)
    db.commit()
    db.refresh(session)
    return session
