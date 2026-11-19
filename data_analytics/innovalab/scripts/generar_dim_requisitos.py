"""Genera el CSV maestro normalizado de requisitos únicos de CABA.

Es el equivalente versionado del script de ``pandas`` usado en el análisis:
toma los 13 requisitos únicos del catálogo TECBA, corrige las URLs oficiales
que cambiaron de slug y escribe ``db/seed/dim_requisitos.csv`` con las columnas
exactas de ``dim_requisitos`` en ``db/schema.sql``.

Uso:
    python scripts/generar_dim_requisitos.py
    python scripts/generar_dim_requisitos.py --validar-urls

Las URLs se verificaron con ``curl -L`` el 2026-11-19. ``--validar-urls``
repite la comprobación con ``urllib`` y falla si alguna no responde 2xx/3xx.
"""

from __future__ import annotations

import argparse
import csv
import sys
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "db" / "seed" / "dim_requisitos.csv"
FECHA_ACTUALIZACION = "2026-11-19"

COLUMNAS = (
    "requisito_id",
    "titulo",
    "etapa",
    "tag_familia",
    "documentacion_necesaria",
    "pasos_a_seguir",
    "url_oficial",
    "tipo_accion",
    "organismo_emisor",
    "fuente_normativa",
    "fecha_actualizacion",
)

REQUISITOS = [
    # --- BLOQUE UNIVERSAL (aplica al 100% de los locales) ---
    {
        "requisito_id": "REQ_01",
        "titulo": "Usuario miBA Nivel 3 (reemplaza a Clave Ciudad)",
        "etapa": "previa",
        "tag_familia": "universal",
        "documentacion_necesaria": (
            "DNI argentino vigente y validación biométrica facial desde la app BAX. "
            "La Clave Ciudad de AGIP dejó de usarse en octubre de 2025: hoy se accede con miBA nivel 3."
        ),
        "pasos_a_seguir": (
            "1. Crear cuenta miBA con CUIL y email. "
            "2. Validar la identidad hasta Nivel 3 desde la app BAX con DNI y reconocimiento facial. "
            "3. Usar esa cuenta para AGIP, TAD y el resto de trámites de la Ciudad."
        ),
        "url_oficial": "https://buenosaires.gob.ar/innovacionytransformaciondigital/login-miba/niveles-de-seguridad",
        "tipo_accion": "externo",
        "organismo_emisor": "GCBA / AGIP",
        "fuente_normativa": "Ley 6.101 - Procedimiento Digital TAD",
    },
    {
        "requisito_id": "REQ_02",
        "titulo": "Documentación Personal / Societaria y CUIT",
        "etapa": "previa",
        "tag_familia": "universal",
        "documentacion_necesaria": (
            "DNI del titular, constancia de inscripción en ARCA (ex AFIP). "
            "Si es sociedad: estatuto y acta de designación de autoridades."
        ),
        "pasos_a_seguir": (
            "1. Verificar alta de CUIT y actividad económica en ARCA. "
            "2. Descargar la constancia vigente."
        ),
        "url_oficial": "https://www.arca.gob.ar/inscripcion-digital/",
        "tipo_accion": "externo",
        "organismo_emisor": "ARCA",
        "fuente_normativa": "Resolución General ARCA",
    },
    {
        "requisito_id": "REQ_03",
        "titulo": "Título Habilitante del Local",
        "etapa": "previa",
        "tag_familia": "universal",
        "documentacion_necesaria": (
            "Contrato de locación comercial vigente con firmas certificadas ante escribano, "
            "o escritura traslativa de dominio."
        ),
        "pasos_a_seguir": (
            "1. Verificar que el destino del contrato permita el rubro comercial. "
            "2. Certificar firmas ante escribano."
        ),
        "url_oficial": "",
        "tipo_accion": "checklist",
        "organismo_emisor": "Privado / Escribanía",
        "fuente_normativa": "Ley 6.101 Art. 14",
    },
    {
        "requisito_id": "REQ_04",
        "titulo": "Inscripción en Ingresos Brutos (IIBB)",
        "etapa": "tributaria",
        "tag_familia": "universal",
        "documentacion_necesaria": (
            "miBA nivel 3 (reemplazó a Clave Ciudad), CUIT y código de actividad ClaNAE "
            "coincidente con el rubro."
        ),
        "pasos_a_seguir": (
            "1. Ingresar a AGIP con miBA nivel 3. "
            "2. Dar de alta el impuesto sobre los Ingresos Brutos (régimen Local o Convenio Multilateral)."
        ),
        "url_oficial": "https://www.agip.gob.ar/tramites/ingresos-brutos-inscripcion",
        "tipo_accion": "externo",
        "organismo_emisor": "AGIP",
        "fuente_normativa": "Código Fiscal CABA",
    },
    {
        "requisito_id": "REQ_05",
        "titulo": "Habilitación de Actividad Económica (AGC)",
        "etapa": "habilitacion",
        "tag_familia": "universal",
        "documentacion_necesaria": (
            "Formulario de conformación de unidad de uso, Anexo Técnico firmado por profesional "
            "matriculado (si requiere plano) y pago de boleta."
        ),
        "pasos_a_seguir": (
            "1. Ingresar a la plataforma SSIT de la AGC con miBA nivel 3. "
            "2. Seleccionar 'Nueva Autorización de Actividad Económica'. "
            "3. Cargar la encomienda profesional, el Anexo Técnico y el resto de la documentación; solicitar el CAA."
        ),
        "url_oficial": "https://buenosaires.gob.ar/tramites/habilitacion-de-actividad-economica",
        "tipo_accion": "externo",
        "organismo_emisor": "AGC",
        "fuente_normativa": "Ley 6.101 / Res. 150-AGC",
    },
    {
        "requisito_id": "REQ_06",
        "titulo": "Señalización de Seguridad y Matafuegos",
        "etapa": "operativa",
        "tag_familia": "universal",
        "documentacion_necesaria": (
            "Matafuegos homologados con oblea vigente según carga de fuego, luces de emergencia "
            "y cartelería fotoluminiscente de salida."
        ),
        "pasos_a_seguir": (
            "1. Calcular carga de fuego con profesional. "
            "2. Instalar matafuegos y señalética antes de la apertura."
        ),
        "url_oficial": "",
        "tipo_accion": "checklist",
        "organismo_emisor": "Privado / Matriculado",
        "fuente_normativa": "Código de Edificación CABA",
    },
    # --- BLOQUE EDILICIO / SUPERFICIE ---
    {
        "requisito_id": "REQ_07",
        "titulo": "Sistema de Autoprotección y Plan de Evacuación (Ley 5.920)",
        "etapa": "habilitacion",
        "tag_familia": "edilicio",
        "documentacion_necesaria": (
            "Formulario del Sistema de Autoprotección (Anexo III A de la Disposición 331/DGDCIV/25), "
            "formulario de factores contra riesgo, listado de personas capacitadas, planos de plantas "
            "y registro fotográfico, firmados por profesional inscripto en Defensa Civil."
        ),
        "pasos_a_seguir": (
            "1. Contratar un profesional inscripto en el Registro de Defensa Civil (Ley 5.920). "
            "2. Realizar el relevamiento y elaborar el plan de evacuación. "
            "3. Presentar la documentación por TAD ante la Dirección General de Defensa Civil."
        ),
        "url_oficial": "https://buenosaires.gob.ar/tramites/presentacion-y-evaluacion-del-sistema-de-autoproteccion",
        "tipo_accion": "externo",
        "organismo_emisor": "Defensa Civil GCBA",
        "fuente_normativa": "Ley 5.920 / Disposición 331-DGDCIV/25",
    },
    # --- BLOQUE ALIMENTOS (cafeterías, restaurantes, dietéticas, verdulerías) ---
    {
        "requisito_id": "REQ_08",
        "titulo": "Capacitación en Manipulación Higiénica de Alimentos (Carnet de Manipulador)",
        "etapa": "previa",
        "tag_familia": "alimentos",
        "documentacion_necesaria": (
            "Carnet de Manipulador de Alimentos vigente (3 años) para el titular y todo el personal "
            "en contacto con alimentos: DNI, foto 4x4 y examen aprobado con el 80% de respuestas correctas."
        ),
        "pasos_a_seguir": (
            "1. Registrarse como alumno en el portal de alimentos de la AGC. "
            "2. Cursar el curso online o presencial y rendir el examen. "
            "3. Descargar el carnet digital desde la opción 'Mis inscripciones'."
        ),
        "url_oficial": "https://buenosaires.gob.ar/tramites/inscripcion-al-curso-de-manipulacion-de-alimentos",
        "tipo_accion": "externo",
        "organismo_emisor": "AGC - Unidad de Coordinación Administrativa",
        "fuente_normativa": "Decreto 782/GCABA/01 / Disposición 481-CAAGC/24",
    },
    {
        "requisito_id": "REQ_09",
        "titulo": "Inscripción en el Registro de Establecimientos de Alimentos (RNE / RGCBA-E)",
        "etapa": "rubro",
        "tag_familia": "alimentos",
        "documentacion_necesaria": (
            "Certificado de habilitación librada al uso o aprobada, plano esquemático del establecimiento, "
            "memoria descriptiva, constancia de inscripción en AGIP y manuales de buenas prácticas, "
            "presentados en un único PDF."
        ),
        "pasos_a_seguir": (
            "1. Ingresar a la plataforma de la AGC con miBA nivel 3. "
            "2. Completar el formulario y adjuntar la documentación sanitaria en un único archivo PDF. "
            "3. Subsanar observaciones y retirar el certificado del registro."
        ),
        "url_oficial": "https://buenosaires.gob.ar/tramites/registro-nacional-de-productos-alimenticios-rnpa-registro-nacional-de-establecimientos",
        "tipo_accion": "externo",
        "organismo_emisor": "AGC - Dirección General de Higiene y Seguridad Alimentaria",
        "fuente_normativa": "Código Alimentario Argentino / Res. GMC 080/96",
    },
    # --- BLOQUE AMBIENTAL / INFLAMABLES ---
    {
        "requisito_id": "REQ_10",
        "titulo": "Certificado de Aptitud Ambiental (C.A.A.)",
        "etapa": "habilitacion",
        "tag_familia": "inflamables",
        "documentacion_necesaria": (
            "Datos del establecimiento (domicilio, superficie, plantas, titular, rubro según Código "
            "Urbanístico) y, si corresponde, intervención de profesional inscripto en el Registro de "
            "Evaluación Ambiental."
        ),
        "pasos_a_seguir": (
            "1. Ingresar a TAD con miBA y completar el CUIT. "
            "2. Cargar los datos en el Sistema Público de Solicitudes de APRA (SIPSA). "
            "3. Obtener el CAA: SRE automático o categorización con informe técnico; es previo o simultáneo a la habilitación."
        ),
        "url_oficial": "https://buenosaires.gob.ar/tramites/impacto-ambiental-certificado-de-aptitud-ambiental-caa",
        "tipo_accion": "externo",
        "organismo_emisor": "APRA",
        "fuente_normativa": "Ley 123 de Impacto Ambiental / Res. 315-APRA/25",
    },
    # --- BLOQUE ACTIVIDAD FÍSICA / SALUD ---
    {
        "requisito_id": "REQ_11",
        "titulo": "Seguro de Responsabilidad Civil y Cobertura Médica",
        "etapa": "operativa",
        "tag_familia": "actividad_fisica",
        "documentacion_necesaria": (
            "Póliza vigente de Seguro de Responsabilidad Civil comprensiva y contrato de servicio de "
            "emergencias médicas (área protegida)."
        ),
        "pasos_a_seguir": (
            "1. Contratar póliza RC acorde a capacidad del local. "
            "2. Contratar servicio de emergencias médicas."
        ),
        "url_oficial": "",
        "tipo_accion": "checklist",
        "organismo_emisor": "Privado / Aseguradora",
        "fuente_normativa": "Ley 139 de Gimnasios CABA",
    },
    {
        "requisito_id": "REQ_12",
        "titulo": "Dirección Técnica de Profesor de Educación Física",
        "etapa": "operativa",
        "tag_familia": "actividad_fisica",
        "documentacion_necesaria": (
            "Título terciario o universitario habilitante del profesional a cargo de la supervisión "
            "física y registro de aptos médicos de alumnos."
        ),
        "pasos_a_seguir": (
            "1. Designar Director Técnico matriculado. "
            "2. Implementar legajo de aptos médicos anuales."
        ),
        "url_oficial": "",
        "tipo_accion": "checklist",
        "organismo_emisor": "AGC / Registro Gimnasios",
        "fuente_normativa": "Ley 139 CABA",
    },
    # --- BLOQUE RUIDO / VIBRACIONES ---
    {
        "requisito_id": "REQ_13",
        "titulo": "Inscripción en el Registro de Actividades Catalogadas como Potencialmente Contaminantes por Ruidos (RAC)",
        "etapa": "habilitacion",
        "tag_familia": "ruido",
        "documentacion_necesaria": (
            "Informe de Evaluación de Impacto Acústico (IEIA) firmado por profesional inscripto en el "
            "Registro de Profesionales de Impacto Acústico, formularios 1 y 2, planillas de medición "
            "con calibraciones vigentes y croquis de puntos de medición."
        ),
        "pasos_a_seguir": (
            "1. Contratar profesional inscripto en el Registro de Profesionales de Impacto Acústico. "
            "2. Realizar la medición y firmar el IEIA. "
            "3. Presentar la solicitud RAC por SIPSA de APRA con el número y código de seguridad del CAA."
        ),
        "url_oficial": "https://buenosaires.gob.ar/tramites/registro-de-actividades-contaminantes-rac",
        "tipo_accion": "externo",
        "organismo_emisor": "APRA",
        "fuente_normativa": "Ley 1.540 / Decreto 740/07",
    },
]


def generar(salida: Path = SALIDA) -> int:
    """Escribe el CSV maestro y devuelve la cantidad de filas."""
    salida.parent.mkdir(parents=True, exist_ok=True)
    with salida.open("w", encoding="utf-8", newline="") as fh:
        escritor = csv.DictWriter(fh, fieldnames=COLUMNAS, extrasaction="raise")
        escritor.writeheader()
        for req in REQUISITOS:
            fila = dict(req)
            fila["fecha_actualizacion"] = FECHA_ACTUALIZACION
            escritor.writerow(fila)
    return len(REQUISITOS)


def validar_urls() -> list[str]:
    """Devuelve las URLs que no responden 2xx/3xx (solo para revisión manual)."""
    fallidas: list[str] = []
    for req in REQUISITOS:
        url = req["url_oficial"]
        if not url:
            continue
        peticion = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; innovalab-data/1.0)"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(peticion, timeout=25) as respuesta:
                if respuesta.status >= 400:
                    fallidas.append(f"{req['requisito_id']}: HTTP {respuesta.status} {url}")
        except urllib.error.HTTPError as exc:
            fallidas.append(f"{req['requisito_id']}: HTTP {exc.code} {url}")
        except Exception as exc:  # noqa: BLE001 - solo reporte, no detiene la generación
            fallidas.append(f"{req['requisito_id']}: {type(exc).__name__} {url}")
    return fallidas


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", type=Path, default=SALIDA, help="Ruta del CSV a generar.")
    parser.add_argument("--validar-urls", action="store_true", help="Comprueba las URLs con urllib.")
    args = parser.parse_args()

    n = generar(args.salida)
    print(f"Generado {args.salida} con {n} trámites maestros.")

    if args.validar_urls:
        fallidas = validar_urls()
        if fallidas:
            print("URLs que requieren revisión manual:", file=sys.stderr)
            print("\n".join(f"  - {f}" for f in fallidas), file=sys.stderr)
            return 1
        print("URLs verificadas: todas responden correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
