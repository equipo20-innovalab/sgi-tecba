import logging
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.services.chat_agent import GroqServiceError, generar_respuesta_chat


logger = logging.getLogger(__name__)
router = APIRouter()


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    context: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    reply: str


@router.post("/chat", response_model=ChatResponse, summary="Conversación con el asistente SGI")
def chat(req: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    if not req.messages:
        raise HTTPException(status_code=400, detail="El chat no tiene mensajes.")
    if req.messages[-1].role != "user":
        raise HTTPException(
            status_code=400,
            detail="El último mensaje del chat debe ser de la persona usuaria.",
        )
    if not settings.GROQ_API_KEY.strip():
        logger.error("GROQ_API_KEY no configurada")
        raise HTTPException(
            status_code=503,
            detail="El asistente no está disponible porque falta configurar la API key de Groq.",
        )

    try:
        reply = generar_respuesta_chat(
            db=db,
            messages=[message.model_dump() for message in req.messages],
            contexto=req.context,
            groq_api_key=settings.GROQ_API_KEY,
            groq_model=settings.GROQ_MODEL,
        )
    except GroqServiceError as error:
        logger.exception("El proveedor Groq no pudo generar la respuesta.")
        raise HTTPException(
            status_code=503,
            detail="El asistente no está disponible en este momento. Intentá nuevamente.",
        ) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.exception("Error interno procesando el chat.")
        raise HTTPException(
            status_code=500,
            detail="Ocurrió un error interno al procesar el mensaje.",
        ) from error

    return ChatResponse(reply=reply)
