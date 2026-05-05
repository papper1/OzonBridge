from fastapi import APIRouter

from config import SESSION_FILE
from crawler.session import check_session_valid

from ..schemas.auth_schema import SessionStatusResponse
from ..services.auth_flow_service import auth_flow_service


router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/1688/status", response_model=SessionStatusResponse)
def get_1688_session_status() -> SessionStatusResponse:
    exists = SESSION_FILE.exists()
    valid = check_session_valid() if exists else False
    return SessionStatusResponse(
        exists=exists,
        valid=valid,
        flow_active=auth_flow_service.flow_active,
        session_path=str(SESSION_FILE),
        message="Session is valid." if valid else ("Session file exists but is not valid." if exists else "Session file not found."),
    )


@router.post("/1688/open", response_model=SessionStatusResponse)
def open_1688_session_flow() -> SessionStatusResponse:
    message = auth_flow_service.open_1688_login()
    exists = SESSION_FILE.exists()
    valid = check_session_valid() if exists else False
    return SessionStatusResponse(
        exists=exists,
        valid=valid,
        flow_active=auth_flow_service.flow_active,
        session_path=str(SESSION_FILE),
        message=message,
    )


@router.post("/1688/save", response_model=SessionStatusResponse)
def save_1688_session() -> SessionStatusResponse:
    valid, session_path = auth_flow_service.save_1688_session()
    return SessionStatusResponse(
        exists=True,
        valid=valid,
        flow_active=auth_flow_service.flow_active,
        session_path=session_path,
        message="1688 session saved successfully." if valid else "Session file was saved but validation failed.",
    )
