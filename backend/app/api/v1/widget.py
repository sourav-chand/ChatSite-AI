"""Widget CORS-enabled configuration endpoint (read by widget.js on init)."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import settings

router = APIRouter(prefix="/widget", tags=["Widget"])


@router.get("/config/{chatbot_id}")
async def widget_config(chatbot_id: str):
    return JSONResponse(
        content={
            "chatbot_id": chatbot_id,
            "api_base": f"{settings.WIDGET_CDN_URL}/api/v1",
            "version": settings.WIDGET_VERSION,
        },
        headers={"Access-Control-Allow-Origin": "*"},
    )
