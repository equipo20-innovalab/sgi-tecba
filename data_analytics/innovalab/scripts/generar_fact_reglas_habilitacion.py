"""Genera la tabla puente ``fact_reglas_habilitacion.csv``.

Toma los códigos de rubro de CABA, les asigna ``tag_familia`` por palabras
clave y cruza esos tags contra el catálogo maestro ``dim_requisitos.csv``.

Fuente de rubros
----------------
``codigo_urbanistico_limpio.csv`` **no tiene** ``codigo_rubro`` ni
``nombre_rubro``: es una tabla de parcelas (clave ``smp``, usos urbanísticos).
Los rubros comerciales viven en ``habilitaciones_caba_clean.csv``, con
``codigo_rubro`` y ``descripcion_rubro``; por eso es la fuente por defecto.
Si tu entorno tiene otro CSV con esas columnas, pasalo con ``--rubros-csv``.

Uso:
    python scripts/generar_fact_reglas_habilitacion.py
    python scripts/generar_fact_reglas_habilitacion.py --reporte-smp
"""

from __future__ import annotations

import argparse
import csv
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CSV_HAB = RAIZ / "data" / "processed" / "habilitaciones_caba_clean.csv"
CSV_CU = RAIZ / "data" / "processed" / "codigo_urbanistico_limpio.csv"
DIM_CSV = RAIZ / "db" / "seed" / "dim_requisitos.csv"
SALIDA = RAIZ / "db" / "seed" / "fact_reglas_habilitacion.csv"

COLUMNAS = (
    "codigo_rubro",
    "requisito_id",
    "obligatoriedad",
    "condicion_superficie_min",
    "condicion_tipo_tramite",
    "nota_condicion",
)

# Palabras clave del relevamiento. Se normalizan acentos y se usan límites de
# palabra en los términos cortos para evitar falsos positivos ("talabartería"
# no es un bar, "embarcaciones" no es comida).
PALABRAS_CLAVE = {
    "alimentos": (
        r"aliment", r"gastronom", r"cafe", r"restauran", r"panader", r"helader",
        r"comida", r"verdul", r"carnic", r"\bbar\b",
    ),
    "actividad_fisica": (
        r"gimnasio", r"gimnastic", r"deport", r"fitness", r"natatorio",
        r"yoga", r"pilates", r"danza",
    ),
    "inflamables": (
        r"ferreter", r"pintur", r"quimic", r"combust", r"\btaller\b", r"mecan",
        r"automot", r"carpinter", r"inflamable", r"soldad",
    ),
    "ropa": (
        r"\bropa\b", r"indumentaria", r"calzado", r"bazar", r"librer",
        r"regaler", r"optica",
    ),
}

TAGS_POR_GRUPO = {
    "alimentos": ("alimentos", "inflamables"),
    "actividad_fisica": ("actividad_fisica", "edilicio", "ruido"),
    "inflamables": ("inflamables", "ruido"),
    "ropa": ("edilicio",),
}


def _normalizar(texto: str) -> str:
    sin_acentos = unicodedata.normalize("NFKD", str(texto).lower())
    return "".join(ch for ch in sin_acentos if not unicodedata.combining(ch))


def detectar_tags(nombre_rubro: str) -> list[str]:
    """Devuelve las familias aplicables; ``universal`` siempre va primero."""
    texto = _normalizar(nombre_rubro)
    tags = ["universal"]
    for grupo, patrones in PALABRAS_CLAVE.items():
        if any(re.search(patron, texto) for patron in patrones):
            for tag in TAGS_POR_GRUPO[grupo]:
                if tag not in tags:
                    tags.append(tag)
    return tags


def _codigo_limpio(valor: str | None) -> str | None:
    codigo = re.sub(r"\.0+$", "", (valor or "").strip())
    return codigo or None


def leer_requisitos(ruta: Path = DIM_CSV) -> list[dict[str, str]]:
    with ruta.open(encoding="utf-8-sig", newline="") as fh:
        filas = [{k: (v or "").strip() for k, v in fila.items()} for fila in csv.DictReader(fh)]
    if not filas:
        raise ValueError(f"El catálogo {ruta} está vacío")
    return filas


def leer_rubros(ruta: Path = CSV_HAB) -> dict[str, str]:
    """Agrupa descripciones por código de rubro. Falla si el CSV no tiene rubros."""
    with ruta.open(encoding="utf-8-sig", newline="") as fh:
        lector = csv.DictReader(fh)
        columnas = set(lector.fieldnames or [])
        col_codigo = next((c for c in ("codigo_rubro", "cod_rubro") if c in columnas), None)
        col_nombre = next(
            (c for c in ("nombre_rubro", "descripcion_rubro", "rubro") if c in columnas), None
        )
        if not col_codigo or not col_nombre:
            raise ValueError(
                f"{ruta.name} no tiene códigos de rubro (buscó codigo_rubro/cod_rubro y "
                "nombre_rubro/descripcion_rubro/rubro). El Código Urbanístico limpio es una "
                "tabla de parcelas por SMP; usá habilitaciones_caba_clean.csv o pasá "
                "--rubros-csv con un archivo que tenga esas columnas."
            )

        descripciones: dict[str, set[str]] = defaultdict(set)
        for fila in lector:
            codigo = _codigo_limpio(fila.get(col_codigo))
            nombre = (fila.get(col_nombre) or "").strip()
            if codigo and len(nombre) >= 4:
                descripciones[codigo].add(nombre)

    if not descripciones:
        raise ValueError(f"No se encontraron rubros con descripción en {ruta}")
    return {codigo: " | ".join(sorted(nombres)) for codigo, nombres in descripciones.items()}


def generar_reglas(rubros: dict[str, str], requisitos: list[dict[str, str]]) -> list[dict[str, str]]:
    """Cruza rubros × requisitos por tag y aplica las reglas de superficie/obligatoriedad."""
    reglas: list[dict[str, str]] = []
    vistos: set[tuple[str, str]] = set()

    def clave(codigo: str) -> tuple[int, int]:
        return (0, int(codigo)) if codigo.isdigit() else (1, 0)

    for codigo in sorted(rubros, key=clave):
        tags = detectar_tags(rubros[codigo])
        for req in requisitos:
            if req["tag_familia"] not in tags:
                continue
            requisito_id = req["requisito_id"]
            if (codigo, requisito_id) in vistos:
                continue
            vistos.add((codigo, requisito_id))

            sup_min = 500 if requisito_id == "REQ_07" and "actividad_fisica" not in tags else 0
            obligatoriedad = "condicional" if sup_min > 0 or requisito_id == "REQ_10" else "obligatorio"
            if sup_min > 0:
                nota = f"Obligatorio a partir de {sup_min} m2"
            elif requisito_id == "REQ_10":
                nota = "Condicional según categorización ambiental (APRA)"
            else:
                nota = "Aplica según rubro"

            reglas.append({
                "codigo_rubro": codigo,
                "requisito_id": requisito_id,
                "obligatoriedad": obligatoriedad,
                "condicion_superficie_min": str(sup_min),
                "condicion_tipo_tramite": "TODOS",
                "nota_condicion": nota,
            })
    return reglas


def escribir_csv(reglas: list[dict[str, str]], salida: Path) -> int:
    salida.parent.mkdir(parents=True, exist_ok=True)
    with salida.open("w", encoding="utf-8", newline="") as fh:
        escritor = csv.DictWriter(fh, fieldnames=COLUMNAS, extrasaction="raise")
        escritor.writeheader()
        escritor.writerows(reglas)
    return len(reglas)


def reporte_smp() -> tuple[int, int, int] | None:
    """Cobertura informativa SMP: habilitaciones ∩ Código Urbanístico."""
    if not CSV_CU.exists() or not CSV_HAB.exists():
        return None
    smp_cu = set()
    with CSV_CU.open(encoding="utf-8-sig", newline="") as fh:
        for fila in csv.DictReader(fh):
            if fila.get("smp"):
                smp_cu.add(fila["smp"].strip())
    smp_hab = set()
    with CSV_HAB.open(encoding="utf-8-sig", newline="") as fh:
        for fila in csv.DictReader(fh):
            if fila.get("smp"):
                smp_hab.add(fila["smp"].strip())
    return len(smp_hab), len(smp_cu), len(smp_hab & smp_cu)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rubros-csv", type=Path, default=CSV_HAB, help="CSV con codigo_rubro y descripcion_rubro.")
    parser.add_argument("--dim-csv", type=Path, default=DIM_CSV, help="Catálogo maestro de requisitos.")
    parser.add_argument("--salida", type=Path, default=SALIDA, help="CSV de la matriz a generar.")
    parser.add_argument("--reporte-smp", action="store_true", help="Informa la cobertura SMP contra el Código Urbanístico.")
    args = parser.parse_args()

    rubros = leer_rubros(args.rubros_csv)
    requisitos = leer_requisitos(args.dim_csv)
    reglas = generar_reglas(rubros, requisitos)
    n = escribir_csv(reglas, args.salida)

    print(f"Fuente de rubros: {args.rubros_csv}")
    print(f"Rubros únicos: {len(rubros)} | requisitos: {len(requisitos)}")
    print(f"Generado {args.salida} con {n} reglas cruzadas.")
    if args.reporte_smp:
        cobertura = reporte_smp()
        if cobertura:
            hab, cu, inter = cobertura
            print(f"SMP: {hab:,} en habilitaciones · {cu:,} en CU · {inter:,} en ambos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
