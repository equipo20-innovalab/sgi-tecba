import json
import logging
import re
import unicodedata
from typing import Any

from fastapi.encoders import jsonable_encoder
from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq

from app.api.v1.endpoints.catastro import get_catastro
from app.api.v1.endpoints.consulta import consulta
from app.api.v1.endpoints.habilitaciones import (
    buscar_cafeterias as buscar_cafeterias_endpoint,
    rubros_por_comuna,
)
from app.api.v1.endpoints.rubros import get_requisitos, listar_rubros as listar_rubros_endpoint
from app.schemas.consulta import ConsultaRequest


logger = logging.getLogger(__name__)

RESPUESTA_CONTINGENCIA = (
    "En este momento no logro conectar con nuestro sistema de registros, "
    "pero dame un momento o facilítame más detalles para intentar ayudarte de otra manera."
)
RESPUESTA_SIN_DATOS = (
    "No tengo información consultable suficiente para responder eso con certeza. "
    "Puedo ayudarte con requisitos por rubro, rubros frecuentes por comuna o una ficha "
    "catastral si tenés el identificador SMP."
)
RESPUESTA_SIN_PLAZO = (
    "No cuento con un plazo oficial registrado para completar este trámite. "
    "Puedo resumirte los pasos y requisitos disponibles para tu rubro y dirección."
)
RESPUESTA_CONFIRMACION = (
    "¡Perfecto! ¿Necesitás algo más sobre tu trámite?"
)
MAX_TURNOS_CON_HERRAMIENTAS = 5


class ConsultaIntegradaArgs(BaseModel):
    pregunta: str = Field(description="La consulta concreta del usuario.")
    rubro: str | None = Field(
        default=None,
        description="Rubro explícito en la pregunta; si falta, usar el rubro del trámite activo.",
    )
    direccion: str | None = Field(
        default=None,
        description="Dirección explícita en la pregunta; si falta, usar la dirección del trámite activo.",
    )


class SinParametrosArgs(BaseModel):
    pass


class RequisitosRubroArgs(BaseModel):
    rubro: str = Field(description="Nombre del rubro, por ejemplo cafetería.")


class RubrosComunaArgs(BaseModel):
    comuna: int = Field(ge=1, le=15, description="Número de comuna de la Ciudad de Buenos Aires.")


class BuscarCafeteriasArgs(BaseModel):
    comuna: int | None = Field(
        default=None,
        ge=1,
        le=15,
        description="Número de comuna si el usuario la especificó; sin comuna busca en toda la Ciudad.",
    )


class CatastroSmpArgs(BaseModel):
    smp: str = Field(description="Identificador catastral SMP, por ejemplo 001-001-008A.")


class GroqServiceError(Exception):
    """Error de conexión o respuesta del proveedor Groq."""


def _a_json(data: Any) -> str:
    return json.dumps(jsonable_encoder(data), ensure_ascii=False)


def _invocar_endpoint(endpoint: Any, *args: Any, **kwargs: Any) -> str:
    try:
        return _a_json(endpoint(*args, **kwargs))
    except HTTPException as error:
        if error.status_code == 404:
            return "null"
        raise


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFD", texto.lower())
    return "".join(caracter for caracter in texto if unicodedata.category(caracter) != "Mn")


def _es_saludo(texto: str) -> bool:
    texto_normalizado = _normalizar(texto).strip()
    saludo = (
        r"(?:hola|holis|hoal|buenas(?:\s+(?:tardes|noches|dias))?|"
        r"buen dia|buenos dias|que tal|que haces|como va|todo bien|che|como andas|"
        r"como estas|(?:podrias|puedes)\s+(?:empezar|comenzar)|empecemos)"
    )
    continuacion = r"(?:[\s,¿¡]+(?:como estas|como andas|como va|que tal|todo bien|que haces))*"
    return bool(
        re.fullmatch(
            r"[\s¿¡]*" + saludo + continuacion + r"[\s!¡,.?¿]*",
            texto_normalizado,
        )
    )


def _es_consulta_sobre_plazos(texto: str) -> bool:
    texto_normalizado = _normalizar(texto)
    return bool(
        re.search(
            r"\b(demora|tarda|plazo|duracion|tiempo)\b",
            texto_normalizado,
        )
    )


def _es_confirmacion(texto: str) -> bool:
    texto_normalizado = _normalizar(texto).strip()
    return bool(
        re.fullmatch(
            r"(?:si|dale|ok|okay|okey|bueno|perfecto|de acuerdo|de una|genial|va|"
            r"por favor|porfa)(?:[\s,]+(?:si|dale|ok|por favor))*[\s!¡,.?¿]*",
            texto_normalizado,
        )
    )


def _es_solicitud_revision(texto: str) -> bool:
    texto_normalizado = _normalizar(texto).strip()
    return bool(
        re.fullmatch(
            r"(?:revisa|verifica|comprueba|confirma)\s+"
            r"(?:eso|lo anterior|tu respuesta|lo que dijiste)[\s!¡,.?¿]*",
            texto_normalizado,
        )
    )


def _ultimo_mensaje_asistente(historial: list[dict[str, str]]) -> str | None:
    return next(
        (
            mensaje["content"]
            for mensaje in reversed(historial[:-1])
            if mensaje["role"] == "assistant"
        ),
        None,
    )


def _es_oferta(texto: str) -> bool:
    texto_normalizado = _normalizar(texto)
    return any(
        expresion in texto_normalizado
        for expresion in ("puedo ", "queres que", "te gustaria", "si queres", "si te parece")
    )


def _crear_tools(db: Session, contexto: dict[str, Any]) -> list:
    rubro_contexto = contexto.get("rubro")
    direccion_contexto = contexto.get("direccion")

    @tool(
        "consulta_integrada",
        args_schema=ConsultaIntegradaArgs,
        description=(
            "Consulta integrada en lenguaje natural. Úsala como PRIMERA opción solo "
            "cuando la pregunta combine rubro + ubicación, o cuando no esté claro qué "
            "tool específica corresponde. Ya resuelve extracción de rubro y ubicación, "
            "geocodificación, checklist y fuentes; usa el trámite activo como contexto "
            "si la pregunta no indica otro rubro o dirección. NO la uses si la pregunta "
            "encaja claramente en una tool específica: para listar rubros usá "
            "listar_rubros; para requisitos de un rubro concreto sin ubicación usá "
            "consultar_requisitos_rubro; para rubros frecuentes de una comuna usá "
            "rubros_frecuentes_por_comuna; para catastro por SMP usá "
            "consultar_catastro_smp. NO la uses para saludos."
        ),
    )
    def consulta_integrada(
        pregunta: str,
        rubro: str | None = None,
        direccion: str | None = None,
    ) -> str:
        rubro_consulta = rubro or rubro_contexto
        direccion_consulta = direccion or direccion_contexto
        request = ConsultaRequest(
            texto=pregunta,
            rubro=rubro_consulta,
            direccion=direccion_consulta,
        )
        return _invocar_endpoint(consulta, request, db)

    @tool(
        "listar_rubros",
        args_schema=SinParametrosArgs,
        description=(
            "Lista los rubros disponibles en los registros de requisitos. Úsala cuando "
            "el usuario pregunte qué actividades o rubros están disponibles. NO la uses "
            "para consultar requisitos de un rubro concreto, una ubicación, una "
            "habilitación o un saludo."
        ),
    )
    def listar_rubros() -> str:
        return _invocar_endpoint(listar_rubros_endpoint, db)

    @tool(
        "consultar_requisitos_rubro",
        args_schema=RequisitosRubroArgs,
        description=(
            "Obtiene el checklist de requisitos generales y específicos de un rubro. "
            "Úsala cuando el usuario pregunte qué documentación, permisos, trámites o "
            "requisitos necesita una actividad concreta. NO la uses para preguntas "
            "generales que también requieren ubicación (usa consulta_integrada), "
            "listados de rubros, datos catastrales ni saludos."
        ),
    )
    def consultar_requisitos_rubro(rubro: str) -> str:
        return _invocar_endpoint(get_requisitos, rubro, db)

    @tool(
        "rubros_frecuentes_por_comuna",
        args_schema=RubrosComunaArgs,
        description=(
            "Devuelve los rubros con más habilitaciones registradas en una comuna "
            "específica de CABA. Úsala ante preguntas por rubros más frecuentes, "
            "comercios habituales o actividad comercial de una comuna cuando se "
            "conoce su número (1 a 15). NO la uses para requisitos, una dirección "
            "particular, el total de habilitaciones, datos catastrales ni saludos."
        ),
    )
    def rubros_frecuentes_por_comuna(comuna: int) -> str:
        return _invocar_endpoint(rubros_por_comuna, comuna, limit=20, db=db)

    @tool(
        "buscar_cafeterias",
        args_schema=BuscarCafeteriasArgs,
        description=(
            "Busca registros existentes de habilitaciones de cafeterías y pizzerías; "
            "puede acotarse a una comuna. Úsala si el usuario pide ejemplos o locales "
            "de esos rubros ya habilitados, en especial dentro de una comuna indicada. "
            "NO la uses para averiguar requisitos, buscar cualquier rubro, consultar "
            "un inmueble puntual por dirección/SMP ni responder saludos."
        ),
    )
    def buscar_cafeterias(comuna: int | None = None) -> str:
        return _invocar_endpoint(buscar_cafeterias_endpoint, comuna=comuna, db=db)

    @tool(
        "consultar_catastro_smp",
        args_schema=CatastroSmpArgs,
        description=(
            "Consulta la ficha catastral de un inmueble a partir de su identificador "
            "SMP. Úsala cuando el usuario pregunte por datos catastrales y proporcione "
            "un SMP. NO la uses para resolver una dirección sin SMP, consultar "
            "requisitos o habilitaciones, ni responder saludos."
        ),
    )
    def consultar_catastro_smp(smp: str) -> str:
        return _invocar_endpoint(get_catastro, smp, db)

    return [
        consulta_integrada,
        listar_rubros,
        consultar_requisitos_rubro,
        rubros_frecuentes_por_comuna,
        buscar_cafeterias,
        consultar_catastro_smp,
    ]


def _texto_mensaje(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return "\n".join(
            bloque["text"]
            for bloque in content
            if isinstance(bloque, dict) and isinstance(bloque.get("text"), str)
        ).strip()
    return ""


def _crear_prompt_sistema(contexto: dict[str, Any]) -> str:
    contexto_tramite = {
        campo: contexto.get(campo)
        for campo in ("rubro", "direccion", "ciudad")
        if contexto.get(campo)
    }
    contexto_activo = (
        json.dumps(contexto_tramite, ensure_ascii=False)
        if contexto_tramite
        else "No hay un trámite activo ni rubro o dirección de referencia."
    )
    return (
        "Sos el asistente conversacional del Sistema de Gestión Inteligente de CABA. "
        "Respondé siempre en español rioplatense, con tono cálido, claro y corporativo. "
        "Contexto del trámite activo (dato de referencia, puede cambiar si el usuario "
        f"indica otro): {contexto_activo}. "
        "Si el mensaje es únicamente un saludo, respondé cordialmente sin usar "
        "herramientas. Para toda consulta concreta sobre trámites, requisitos, rubros, "
        "habilitaciones o catastro, consultá una herramienta antes de responder. "
        "Si el usuario responde con una confirmación breve (por ejemplo, 'dale' u "
        "'ok') a una oferta concreta del mensaje anterior, continuá con esa acción "
        "usando las herramientas disponibles. Si solo confirma sin una oferta concreta, "
        "respondé con un agradecimiento breve y ofrecé seguir ayudando. Si pide revisar "
        "la respuesta anterior, verificá lo que puedas con las herramientas y no "
        "afirmes datos que no estén respaldados. "
        "Basate exclusivamente en los resultados de las herramientas y el contexto "
        "explícito; no inventes datos, plazos, requisitos ni interpretaciones legales. "
        "Las herramientas no contienen plazos ni duración de los trámites; si preguntan "
        "cuánto demora o cuánto tarda, indicá que no hay un plazo oficial disponible en "
        "los datos consultables y no inventes uno. "
        "Si el usuario hace una pregunta que requiere rubro o ubicación, y ese dato no "
        "está ni en el mensaje del usuario ni en el contexto del trámite activo, pedile "
        "amablemente que lo especifique antes de usar una tool. Si el dato está en el "
        "mensaje, usalo aunque no haya trámite activo. No inventes rubro ni dirección. "
        "Si para responder falta un dato indispensable, por ejemplo el número de comuna "
        "para buscar rubros frecuentes, no inventes ese dato ni llames a la herramienta: "
        "hacé una pregunta aclaratoria breve y amable para pedirlo. "
        "Si una tool devuelve una lista vacía o null, no respondas con 'error' ni 'no "
        "hay datos'. Interpretá el resultado en contexto: por ejemplo, si buscar_cafeterias "
        "devuelve [], respondé 'no encontré cafeterías registradas en esa comuna, ¿querés "
        "que busque en otra o que consulte los requisitos para abrir una?'. Si "
        "consultar_catastro_smp devuelve null, respondé 'no encontré una ficha catastral "
        "para ese SMP, ¿podés verificarlo?'. Nunca muestres JSON crudo: sintetizá los "
        "resultados en lenguaje natural y "
        "mencioná los datos relevantes. La respuesta debe sonar conversacional, cercana "
        "y fácil de leer en un chat, con frases cortas y respetando los saltos de línea. "
        "Separá los párrafos y las listas con una línea en blanco. Para respuestas con "
        "requisitos o pasos, empezá con un párrafo introductorio breve de una o dos "
        "líneas, seguí con una lista y cerrá con una frase corta ofreciendo ayuda. "
        "Usá viñetas con guion únicamente para enumerar requisitos o pasos, nunca para "
        "el texto introductorio. Usá negritas solo para resaltar conceptos clave, como "
        "nombres de documentos, trámites o plazos; no pongas párrafos enteros en "
        "negrita. Si la lista es larga, resumí los puntos principales y ofrecé ampliar "
        "alguno. No uses encabezados como '###' o '##', tablas Markdown ni separadores "
        "como '---'. No copies ni pegues la estructura, etiquetas o formato crudo que "
        "devuelve la base de datos o una herramienta: interpretá los datos y redactá "
        "una respuesta nueva con tus propias palabras. Si no hay información "
        "suficiente, pedí el dato faltante sin asumirlo."
    )


def generar_respuesta_chat(
    db: Session,
    messages: list[dict[str, str]],
    contexto: dict[str, Any] | None,
    groq_api_key: str,
    groq_model: str = "llama-3.3-70b-versatile",
) -> str:
    """Genera una respuesta conversacional usando las rutas de datos existentes."""
    if not messages:
        raise ValueError("El chat no tiene mensajes.")
    if not groq_api_key or not groq_api_key.strip():
        logger.error("GROQ_API_KEY no configurada")
        raise ValueError("La API key de Groq no está configurada. Revisá el .env del backend.")

    contexto = contexto or {}
    historial = [
        mensaje
        for mensaje in messages
        if mensaje.get("role") in {"user", "assistant"}
        and isinstance(mensaje.get("content"), str)
        and mensaje["content"].strip()
    ][-40:]
    if not historial or historial[-1]["role"] != "user":
        raise ValueError("El último mensaje del chat debe ser de la persona usuaria.")

    ultimo_mensaje = historial[-1]["content"].strip()
    if _es_saludo(ultimo_mensaje):
        rubro = contexto.get("rubro")
        direccion = contexto.get("direccion")
        if rubro and direccion:
            return (
                f"¡Hola! Soy el asistente del SGI. Estoy para ayudarte con los pasos "
                f"para habilitar tu local de {rubro} en {direccion}. ¿Qué te gustaría saber?"
            )
        return "¡Hola! Soy el asistente del SGI. ¿Qué trámite o gestión te gustaría consultar?"
    if _es_consulta_sobre_plazos(ultimo_mensaje):
        return RESPUESTA_SIN_PLAZO

    mensaje_anterior = _ultimo_mensaje_asistente(historial)
    if _es_confirmacion(ultimo_mensaje):
        anterior_normalizado = _normalizar(mensaje_anterior or "")
        if not mensaje_anterior or not _es_oferta(mensaje_anterior):
            return RESPUESTA_CONFIRMACION
        if "busque en otra" in anterior_normalizado or "busques en otra" in anterior_normalizado:
            return "¿En qué comuna querés que busque?"
        if "rubros frecuentes" in anterior_normalizado and "ficha catastral" in anterior_normalizado:
            return (
                "¿Cuál de estas opciones querés consultar: requisitos por rubro, "
                "rubros frecuentes por comuna o ficha catastral por SMP?"
            )
        if "pasos" in anterior_normalizado and "requisitos" in anterior_normalizado:
            historial[-1] = {
                **historial[-1],
                "content": (
                    "Acepto la oferta anterior de resumir los pasos y requisitos del "
                    "trámite activo. Consultá los datos disponibles y presentá el resumen "
                    "sin inventar plazos ni requisitos."
                ),
            }
        elif "requisitos" in anterior_normalizado:
            historial[-1] = {
                **historial[-1],
                "content": (
                    "Acepto la oferta anterior de consultar los requisitos del rubro "
                    "activo. Consultá los datos disponibles para ese rubro."
                ),
            }
        else:
            return "¡Dale! ¿Qué acción de las que mencioné querés que realice?"

    if _es_solicitud_revision(ultimo_mensaje):
        if not mensaje_anterior:
            return "¿Qué información querés que revise?"
        if any(palabra in _normalizar(mensaje_anterior) for palabra in ("plazo", "demora")):
            return RESPUESTA_SIN_PLAZO
        historial[-1] = {
            **historial[-1],
            "content": (
                "Revisá y verificá la respuesta inmediatamente anterior con las "
                "herramientas disponibles, indicando qué datos se pueden confirmar "
                "y cuáles no tienen respaldo."
            ),
        }

    tools = _crear_tools(db, contexto)
    tools_por_nombre = {herramienta.name: herramienta for herramienta in tools}
    try:
        modelo = ChatGroq(
            api_key=groq_api_key,
            model=groq_model,
            temperature=0,
        ).bind_tools(tools)
    except Exception as error:
        logger.exception("No se pudo configurar el cliente de Groq.")
        raise GroqServiceError("No se pudo configurar el cliente de Groq.") from error
    conversacion = [
        SystemMessage(content=_crear_prompt_sistema(contexto)),
        *[
            HumanMessage(content=mensaje["content"])
            if mensaje["role"] == "user"
            else AIMessage(content=mensaje["content"])
            for mensaje in historial
        ],
    ]
    ejecuto_tool = False

    for _ in range(MAX_TURNOS_CON_HERRAMIENTAS):
        try:
            respuesta = modelo.invoke(conversacion)
        except Exception as error:
            logger.exception("Falló la comunicación con Groq.")
            raise GroqServiceError("Falló la comunicación con Groq.") from error
        if not respuesta.tool_calls:
            texto = _texto_mensaje(respuesta.content)
            if texto:
                return texto
            logger.warning("El agente no devolvió texto ni seleccionó una herramienta.")
            continue

        conversacion.append(respuesta)
        for llamada in respuesta.tool_calls:
            herramienta = tools_por_nombre.get(llamada["name"])
            if herramienta is None:
                logger.error("El agente solicitó una herramienta no registrada: %s", llamada["name"])
                return RESPUESTA_CONTINGENCIA
            try:
                resultado = herramienta.invoke(llamada["args"])
            except Exception:
                logger.exception("Falló la herramienta conversacional %s", llamada["name"])
                return RESPUESTA_CONTINGENCIA

            ejecuto_tool = True
            conversacion.append(
                ToolMessage(
                    content=resultado if isinstance(resultado, str) else _a_json(resultado),
                    tool_call_id=llamada["id"],
                )
            )

    logger.warning("El agente alcanzó el máximo de turnos con herramientas.")
    return RESPUESTA_CONTINGENCIA
