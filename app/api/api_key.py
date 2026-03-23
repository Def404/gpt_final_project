from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from config import settings


api_key_header = APIKeyHeader(name="X-API-KEY")


def validate(api_key: str = Depends(api_key_header)) -> str:
    if api_key != settings.API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    
    return api_key