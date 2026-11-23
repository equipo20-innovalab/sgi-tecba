"""
Transcripción local del dictado por voz usando faster-whisper.

El modelo se carga una sola vez (lazy) y corre en CPU con cuantización int8:
no requiere API key ni envía el audio a terceros. La primera llamada descarga
el modelo desde HuggingFace; las siguientes reutilizan el caché local.
"""
import logging
import tempfile
from functools import lru_cache
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def obtener_modelo():
    """Carga el modelo una única vez por proceso."""
    from faster_whisper import WhisperModel

    logger.info("Cargando modelo de voz '%s' (CPU, int8)", settings.VOZ_MODELO)
    return WhisperModel(settings.VOZ_MODELO, device="cpu", compute_type="int8")


def transcribir_audio(contenido: bytes, nombre_archivo: str = "dictado.webm") -> str:
    """
    Transcribe un blob de audio (webm/opus, ogg, wav) a texto en español.

    Se escribe en un archivo temporal porque la librería decodifica desde ruta.
    El archivo se elimina siempre, incluso si la transcripción falla.
    """
    sufijo = Path(nombre_archivo or "").suffix
    if not sufijo or len(sufijo) > 8 or any(caracter not in ".-_abcdefghijklmnopqrstuvwxyz0123456789" for caracter in sufijo.lower()):
        sufijo = ".webm"

    with tempfile.NamedTemporaryFile(suffix=sufijo, delete=False) as temporal:
        temporal.write(contenido)
        ruta = Path(temporal.name)

    try:
        modelo = obtener_modelo()
        segmentos, _informacion = modelo.transcribe(
            str(ruta),
            language=settings.VOZ_IDIOMA,
            beam_size=5,
            vad_filter=False,
            condition_on_previous_text=False,
        )
        return " ".join(
            segmento.text.strip()
            for segmento in segmentos
            if segmento.text and segmento.text.strip()
        ).strip()
    finally:
        ruta.unlink(missing_ok=True)
