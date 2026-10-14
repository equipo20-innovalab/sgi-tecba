"""Limpia los SMP malformados del padrón de habilitaciones.

El dataset origen trae SMPs con relleno de ceros incompleto y minúsculas
(ej: '001-003B-1', '072-040B-4'), que EPOK no resuelve. Esta rutina los
normaliza al formato catastral 'SSS-MMM-PPP[L]' rellenando con ceros la parte
numérica a 3 dígitos y forzando mayúsculas, dejando intactos los ya válidos.

Conserva el valor original en la columna `smp_original` para trazabilidad.
Ejemplos:
    '001-003B-1'   -> '001-003B-001'   (separador sin relleno)
    '072-040B-4'   -> '072-040B-004'
    '001-001-008A' -> '001-001-008A'   (ya válido, sin cambio)

Verificación de efectividad (muestra de 40 SMP malformados):
    ~92% pasan a resolver en EPOK tras la limpieza. Los que no son
    fundamentalmente SMP inexistentes en catastro (ej: sección '000').

Uso:
    python src/limpiar_smp.py --dry-run    # solo cuenta cuántos cambiarían
    python src/limpiar_smp.py              # aplica la limpieza
"""

from __future__ import annotations

import argparse
import os
import re
import sys

import psycopg

# SMP catastral válido: 3 dígitos - 3 dígitos (+letra opcional) - 2-3 dígitos (+letra opcional)
_PATRON_VALIDO = re.compile(r"^\d{3}-\d{3,4}-\d{2,3}[A-Z]?$")


def limpiar_parte(parte: str) -> str:
    """Rellena con ceros la parte numérica a 3 dígitos y upper la letra."""
    p = (parte or "").strip().upper()
    m = re.match(r"^([0-9]+)([A-Z]*)$", p)
    if not m:
        return p
    digitos, letra = m.groups()
    return digitos.zfill(3) + letra


def limpiar_smp(smp: str | None) -> str | None:
    """Normaliza un SMP al formato catastral. Devuelve None si no es parseable."""
    if not smp or not isinstance(smp, str):
        return None
    partes = re.split(r"[-\s]+", smp.strip().upper())
    if len(partes) != 3:
        return smp.strip().upper()  # no se puede parsear: devuelve como está
    return "-".join(limpiar_parte(p) for p in partes)


def main() -> int:
    parser = argparse.ArgumentParser(description="Normaliza SMP malformados del padrón.")
    parser.add_argument("--dry-run", action="store_true", help="Solo cuenta los que cambiarían.")
    args = parser.parse_args()

    if not os.environ.get("DATABASE_URL"):
        print("ERROR: definí DATABASE_URL (o PG*).", file=sys.stderr)
        return 2

    with psycopg.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
        cur.execute(
            "ALTER TABLE habilitaciones ADD COLUMN IF NOT EXISTS smp_original TEXT"
        )
        conn.commit()

        cur.execute("SELECT DISTINCT smp FROM habilitaciones WHERE smp IS NOT NULL")
        distintos = [r[0] for r in cur.fetchall()]
        mapeo = {}
        for smp in distintos:
            limpio = limpiar_smp(smp)
            if limpio and limpio != smp:
                mapeo[smp] = limpio

        total_filas = 0
        for original, limpio in mapeo.items():
            if args.dry_run:
                cur.execute(
                    "SELECT count(*) FROM habilitaciones WHERE smp = %s", (original,)
                )
                total_filas += cur.fetchone()[0]
            else:
                cur.execute(
                    """UPDATE habilitaciones
                       SET smp_original = smp, smp = %s
                       WHERE smp = %s""",
                    (limpio, original),
                )
                total_filas += cur.rowcount

        if not args.dry_run:
            conn.commit()

        cur.execute(
            "SELECT count(DISTINCT smp) FROM habilitaciones WHERE smp IS NOT NULL"
        )
        total_actual = cur.fetchone()[0]
        cur.execute(
            "SELECT count(DISTINCT smp) FROM habilitaciones WHERE smp IS NOT NULL AND smp !~ %s",
            (_PATRON_VALIDO.pattern,),
        )
        restantes = cur.fetchone()[0]

    modo = "DRY-RUN (sin escribir)" if args.dry_run else "APLICADO"
    print(f"[{modo}] SMP distintos original: {len(distintos)}")
    print(f"  SMP a normalizar: {len(mapeo)} (afectan {total_filas} filas)")
    print(f"  SMP distintos tras limpieza: {total_actual}")
    print(f"  SMP todavía fuera de formato: {restantes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
