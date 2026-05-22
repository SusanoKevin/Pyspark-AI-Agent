from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.auth import ADMIN_USERNAME, decode_token
from src.security import UserContext

_bearer = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> UserContext:
    user = decode_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid or expired token")
    return user


def require_admin(user: UserContext = Depends(get_current_user)) -> UserContext:
    if user.user_id != ADMIN_USERNAME:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Admin access required")
    return user


def get_store(request: Request):
    return request.app.state.store


def get_agent(request: Request):
    return request.app.state.agent
