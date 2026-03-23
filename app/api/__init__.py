from fastapi import APIRouter

from api.chats import router as chats_router

router = APIRouter(prefix="/api")
router.include_router(chats_router)
