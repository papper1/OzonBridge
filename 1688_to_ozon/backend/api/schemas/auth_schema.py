from pydantic import BaseModel


class SessionStatusResponse(BaseModel):
    exists: bool = False
    valid: bool = False
    flow_active: bool = False
    session_path: str = ""
    message: str = ""
