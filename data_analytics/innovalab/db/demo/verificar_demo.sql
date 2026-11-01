-- =============================================================================
-- Verifica que el fixture de demo se haya cargado completo y que el cruce
-- habilitaciones ↔ epok_fichas funcione. Falla con excepción si algo no cierra.
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f db/demo/verificar_demo.sql
-- =============================================================================

\set ON_ERROR_STOP on

DO $$
DECLARE
    n_hab      bigint;
    n_epok     bigint;
    n_rubros   bigint;
    huerfanas  bigint;
    sin_comuna bigint;
BEGIN
    SELECT count(*) INTO n_hab    FROM habilitaciones;
    SELECT count(*) INTO n_epok   FROM epok_fichas;
    SELECT count(*) INTO n_rubros FROM rubros_requisitos;

    IF n_hab = 0 OR n_epok = 0 OR n_rubros = 0 THEN
        RAISE EXCEPTION
            'Fixture incompleto: habilitaciones=%, epok_fichas=%, rubros_requisitos=%',
            n_hab, n_epok, n_rubros;
    END IF;

    SELECT count(*) INTO huerfanas
    FROM habilitaciones h
    LEFT JOIN epok_fichas e USING (smp)
    WHERE e.smp IS NULL;

    IF huerfanas > 0 THEN
        RAISE EXCEPTION
            'Hay % habilitaciones del fixture sin ficha EPOK (el cruce por SMP está roto).',
            huerfanas;
    END IF;

    SELECT count(*) INTO sin_comuna FROM habilitaciones WHERE comuna IS NULL;
    IF sin_comuna > 0 THEN
        RAISE EXCEPTION 'Hay % habilitaciones sin comuna en el fixture.', sin_comuna;
    END IF;

    RAISE NOTICE 'Fixture OK: % habilitaciones, % fichas EPOK, % requisitos',
        n_hab, n_epok, n_rubros;
END
$$;

SELECT 'habilitaciones' AS tabla, count(*) FROM habilitaciones
UNION ALL SELECT 'epok_fichas', count(*) FROM epok_fichas
UNION ALL SELECT 'rubros_requisitos', count(*) FROM rubros_requisitos;
