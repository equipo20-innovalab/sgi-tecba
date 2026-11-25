import logging

from fastapi import APIRouter, File, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app.schemas.voz import TranscripcionResponse
from app.services.voz_service import transcribir_audio

router = APIRouter()
logger = logging.getLogger(__name__)

# ~10 MB de audio comprimido alcanzan para varios minutos de dictado.
MAX_BYTES = 10 * 1024 * 1024


@router.post(
    "/voz/transcribir",
    response_model=TranscripcionResponse,
    summary="Transcripción local del dictado por voz",
    description=(
        "Recibe el audio grabado por MediaRecorder y lo transcribe con "
        "faster-whisper (modelo base, en CPU). Se usa como respaldo cuando el "
        "navegador no dispone de Web Speech API."
    ),
)
async def transcribir_dictado(archivo: UploadFile = File(...)):
    contenido = await archivo.read(MAX_BYTES + 1)

    if not contenido:
        raise HTTPException(status_code=400, detail="El archivo de audio está vacío.")
    if len(contenido) > MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail="El audio supera el límite de 10 MB. Grabá un dictado más corto.",
        )

    try:
        texto = await run_in_threadpool(
            transcribir_audio,
            contenido,
            archivo.filename or "dictado.webm",
        )
    except ImportError as error:
        raise HTTPException(
            status_code=503,
            detail="El respaldo de voz no está instalado (falta faster-whisper).",
        ) from error
    except Exception as error:
        logger.exception("Error al transcribir el dictado")
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo transcribir el audio: {error}",
        ) from error

    return TranscripcionResponse(texto=texto)
