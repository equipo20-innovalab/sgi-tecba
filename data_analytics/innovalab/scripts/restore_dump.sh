#!/usr/bin/env bash
# =============================================================================
# restore_dump.sh — restaura un dump SQL plano de PostgreSQL sin sorpresas.
#
# El dump de referencia (db/innovalab_dump.sql) se generó con pg_dump 18.3 y
# pesa ~89 MB (Git LFS). Este script:
#
#   * detecta si el archivo es un puntero de Git LFS y explica cómo bajarlo;
#   * compara la versión del dump con la del servidor destino;
#   * filtra meta-comandos que un servidor viejo no entiende
#     (\restrict, \unrestrict, SET transaction_timeout);
#   * reasigna OWNER TO al rol que restaura (evita el error "role postgres
#     does not exist");
#   * restaura en una sola transacción y verifica los conteos al final.
#
# Uso:
#   scripts/restore_dump.sh                          # dump por defecto + DSN local
#   scripts/restore_dump.sh --dsn "$DATABASE_URL"
#   scripts/restore_dump.sh otro.sql --con-esquema
#   scripts/restore_dump.sh --solo-filtrar --salida /tmp/dump_limpio.sql
#   scripts/restore_dump.sh --info
#
# Variables: DATABASE_URL o PGDATABASE (default: dbname=innovalab).
# =============================================================================

set -euo pipefail

VERSION="1.1.0"
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DUMP="$RAIZ/db/innovalab_dump.sql"
DSN="${DATABASE_URL:-${PGDATABASE:-dbname=innovalab}}"
OWNER=""
SALIDA=""
SOLO_FILTRAR=0
SIN_TRANSACCION=0
CON_ESQUEMA=0
SIN_VERIFICAR=0
INFO=0
SERVIDOR_MAJOR=""
ESPERA=30
TMP=""

msg()  { printf '%s\n' "$*" >&2; }
err()  { printf 'ERROR: %s\n' "$*" >&2; }
uso() {
    sed -n '2,28p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
    cat >&2 <<'AYUDA'

Opciones:
  --dsn DSN             Cadena de conexión (default: $DATABASE_URL o dbname=innovalab).
  --owner ROL           Rol dueño de los objetos restaurados (default: usuario actual).
  --solo-filtrar        Escribe el dump filtrado en stdout o en --salida, sin conectar.
  --salida ARCHIVO      Archivo de salida para --solo-filtrar.
  --servidor-major N    Fuerza la versión mayor del servidor (para pruebas).
  --con-esquema         Aplica db/schema.sql después de restaurar (migraciones idempotentes).
  --sin-transaccion     No usa --single-transaction (para dumps con CREATE INDEX CONCURRENTLY).
  --sin-verificar       Omite el conteo de tablas al final.
  --esperar SEGUNDOS    Espera máxima a que el servidor responda (default 30).
  --info                Muestra versiones y estado del dump, sin restaurar.
  -h, --help            Muestra esta ayuda.
  --version             Muestra la versión del script.

Códigos de salida: 0 OK · 2 uso/archivo inválido · 3 LFS o dump ilegible · 4 error de psql.
AYUDA
}

# --- utilidades --------------------------------------------------------------
es_pointer_lfs() {
    [ -f "$1" ] && head -c 200 "$1" 2>/dev/null | grep -q '^version https://git-lfs.github.com/spec/v1'
}

version_dump() {
    sed -n 's/^-- Dumped from database version \([0-9][0-9]*\)\.\([0-9][0-9]*\).*/\1.\2/p' "$1" | head -n 1
}

major_version() {
    printf '%s' "${1%%.*}"
}

version_servidor() {
    psql "$DSN" -X -Atqc "SHOW server_version" 2>/dev/null || true
}

esperar_servidor() {
    local restante="$1"
    while [ "$restante" -gt 0 ]; do
        if psql "$DSN" -X -Atqc "SELECT 1" >/dev/null 2>&1; then
            return 0
        fi
        sleep 1
        restante=$((restante - 1))
    done
    return 1
}

limpiar() {
    # No dejar que el trap pise el código de salida del script.
    if [ -n "$TMP" ]; then rm -f "$TMP"; fi
    return 0
}
trap limpiar EXIT

# --- argumentos --------------------------------------------------------------
while [ "$#" -gt 0 ]; do
    case "$1" in
        --dsn)             DSN="${2:?falta el valor de --dsn}"; shift 2 ;;
        --owner)           OWNER="${2:?falta el valor de --owner}"; shift 2 ;;
        --solo-filtrar)    SOLO_FILTRAR=1; shift ;;
        --salida)          SALIDA="${2:?falta el valor de --salida}"; shift 2 ;;
        --servidor-major)  SERVIDOR_MAJOR="${2:?falta el valor de --servidor-major}"; shift 2 ;;
        --con-esquema)     CON_ESQUEMA=1; shift ;;
        --sin-transaccion) SIN_TRANSACCION=1; shift ;;
        --sin-verificar)   SIN_VERIFICAR=1; shift ;;
        --esperar)         ESPERA="${2:?falta el valor de --esperar}"; shift 2 ;;
        --info)            INFO=1; shift ;;
        -h|--help)         uso; exit 0 ;;
        --version)         printf '%s\n' "$VERSION"; exit 0 ;;
        -*)                err "opción desconocida: $1"; uso; exit 2 ;;
        *)                 DUMP="$1"; shift ;;
    esac
done

if [ -n "$OWNER" ] && ! printf '%s' "$OWNER" | grep -Eq '^[A-Za-z_][A-Za-z0-9_]*$'; then
    err "--owner debe ser un identificador simple (letras, números y _)."
    exit 2
fi

if [ ! -f "$DUMP" ]; then
    err "no existe el dump: $DUMP"
    exit 2
fi
if [ ! -s "$DUMP" ]; then
    err "el dump está vacío: $DUMP"
    exit 3
fi

DUMP_VERSION="$(version_dump "$DUMP")"
DUMP_MAJOR="$(major_version "${DUMP_VERSION:-0}")"

if es_pointer_lfs "$DUMP"; then
    err "el dump es un puntero de Git LFS, no el archivo real: $DUMP"
    msg "  Solución: git lfs install && git lfs pull --include=\"${DUMP#$RAIZ/}\""
    msg "  Verificá con: head -c 80 \"$DUMP\" (debe empezar con \"--\" y no con \"version https\")."
    exit 3
fi

if [ -z "$DUMP_VERSION" ]; then
    msg "AVISO: no se pudo detectar la versión del dump; se filtran solo \\restrict y \\unrestrict."
    DUMP_MAJOR=0
fi

# El servidor real manda, salvo que se fuerce o que solo se filtre a stdout
# (en ese caso no tiene sentido exigir una conexión).
if [ -z "$SERVIDOR_MAJOR" ] && [ "$SOLO_FILTRAR" = "1" ]; then
    SERVIDOR_MAJOR=0
    SERVIDOR_VERSION="no consultado"
elif [ -z "$SERVIDOR_MAJOR" ]; then
    if ! command -v psql >/dev/null 2>&1; then
        err "no se encontró psql en el PATH."
        exit 2
    fi
    if ! esperar_servidor "$ESPERA"; then
        err "el servidor no respondió en ${ESPERA}s."
        exit 4
    fi
    SERVIDOR_VERSION="$(version_servidor)"
    SERVIDOR_MAJOR="$(major_version "${SERVIDOR_VERSION:-0}")"
else
    SERVIDOR_VERSION="forzada"
fi

if [ "$INFO" = "1" ]; then
    TAMANO="$(du -h "$DUMP" | cut -f1)"
    echo "Script:            $VERSION"
    echo "Dump:              $DUMP ($TAMANO)"
    echo "Versión del dump:  ${DUMP_VERSION:-desconocida} (major ${DUMP_MAJOR})"
    echo "Servidor destino:  ${SERVIDOR_VERSION} (major ${SERVIDOR_MAJOR})"
    if [ "${DUMP_MAJOR:-0}" -gt "${SERVIDOR_MAJOR:-0}" ]; then
        echo "Compatibilidad:    se filtrarán meta-comandos del dump más nuevo"
    else
        echo "Compatibilidad:    sin filtros por versión (solo \\restrict y \\unrestrict)"
    fi
    exit 0
fi

# --- filtrado ----------------------------------------------------------------
# \restrict y \unrestrict son meta-comandos de psql 18; eliminarlos es inocuo.
# SET transaction_timeout no existe antes de PostgreSQL 17.
filtrar() {
    local origen="$1" destino="$2"
    awk -v server_major="${SERVIDOR_MAJOR:-0}" '
        /^\\restrict[[:space:]]/      { next }
        /^\\unrestrict[[:space:]]/    { next }
        /^SET[[:space:]]+transaction_timeout/ {
            if (server_major + 0 < 17) next
            print; next
        }
        { print }
    ' "$origen" > "$destino"
}

reasignar_owner() {
    local archivo="$1" rol="$2"
    [ -z "$rol" ] && return 0
    # Sin `sed -i` para que funcione igual en GNU sed y BSD sed (macOS).
    sed "s/OWNER TO [^;]*/OWNER TO \"$rol\"/g" "$archivo" > "${archivo}.owner"
    mv "${archivo}.owner" "$archivo"
}

TMP="$(mktemp "${TMPDIR:-/tmp}/innovalab_restore.XXXXXX.sql")"
filtrar "$DUMP" "$TMP"

if [ "$SOLO_FILTRAR" = "1" ]; then
    reasignar_owner "$TMP" "$OWNER"
    if [ -n "$SALIDA" ]; then
        cp "$TMP" "$SALIDA"
        msg "Dump filtrado: $SALIDA"
    else
        cat "$TMP"
    fi
    exit 0
fi

# --- restauración ------------------------------------------------------------
if [ -z "$OWNER" ]; then
    OWNER="$(psql "$DSN" -X -Atqc "SELECT current_user" 2>/dev/null || true)"
fi
reasignar_owner "$TMP" "$OWNER"

PSQL_ARGS=(-X -v ON_ERROR_STOP=1 -q)
if [ "$SIN_TRANSACCION" = "0" ]; then
    PSQL_ARGS+=(--single-transaction)
fi

msg "Restaurando $DUMP ($(du -h "$DUMP" | cut -f1))…"
msg "  dump ${DUMP_VERSION:-desconocido} → servidor ${SERVIDOR_VERSION}; owner: ${OWNER:-sin cambios}"
INICIO="$(date +%s)"

if ! psql "${PSQL_ARGS[@]}" -d "$DSN" -f "$TMP"; then
    err "psql falló al restaurar. No se aplicaron cambios (transacción revertida)."
    exit 4
fi

if [ "$CON_ESQUEMA" = "1" ]; then
    msg "Aplicando migraciones de db/schema.sql…"
    if ! psql "${PSQL_ARGS[@]}" -d "$DSN" -f "$RAIZ/db/schema.sql"; then
        err "falló la aplicación de db/schema.sql."
        exit 4
    fi
fi

DURACION=$(( $(date +%s) - INICIO ))
msg "Restauración completada en ${DURACION}s."

# --- verificación ------------------------------------------------------------
if [ "$SIN_VERIFICAR" = "0" ]; then
    msg "Conteos:"
    for tabla in rubros_requisitos habilitaciones epok_fichas codigo_urbanistico urbanismo_smp indice_oportunidad; do
        existe="$(psql "$DSN" -X -Atqc "SELECT to_regclass('public.$tabla') IS NOT NULL" 2>/dev/null || echo f)"
        if [ "$existe" = "t" ]; then
            filas="$(psql "$DSN" -X -Atqc "SELECT count(*) FROM public.$tabla")"
            printf '  %-22s %s\n' "$tabla" "$filas" >&2
        fi
    done
fi

exit 0
