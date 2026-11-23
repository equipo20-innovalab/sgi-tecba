const API_BASE = '/api/v1';

async function requestJson(path, options = {}) {
    const response = await fetch(`${API_BASE}${path}`, options);

    let payload;
    try {
        payload = await response.json();
    } catch {
        throw new Error('El backend devolvió una respuesta que no es JSON.');
    }

    if (!response.ok) {
        const detail = payload?.detail;
        const message = typeof detail === 'string'
            ? detail
            : detail
                ? JSON.stringify(detail)
                : `El backend respondió con el estado ${response.status}.`;
        throw new Error(message);
    }

    return payload;
}

/**
 * Consulta al backend. Acepta el texto libre original o el modo estructurado
 * `{ rubro, direccion }` que usa el buscador con campos separados.
 */
export async function consultarProyecto(consulta, { signal } = {}) {
    const cuerpo = typeof consulta === 'string' ? { texto: consulta } : consulta;
    return requestJson('/consulta', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(cuerpo),
        signal,
    });
}

export async function obtenerRubros({ signal } = {}) {
    return requestJson('/rubros', { signal });
}

/**
 * Envía el audio del dictado al respaldo local (faster-whisper en el backend).
 * No se fija Content-Type: el navegador agrega el boundary de FormData.
 */
export async function transcribirVoz(archivo, { signal } = {}) {
    const cuerpo = new FormData();
    cuerpo.append('archivo', archivo, 'dictado.webm');
    return requestJson('/voz/transcribir', {
        method: 'POST',
        body: cuerpo,
        signal,
    });
}

export async function obtenerRequisitos(rubro, { signal } = {}) {
    return requestJson(`/rubros/${encodeURIComponent(rubro)}/requisitos`, { signal });
}

export async function obtenerCobertura({ signal } = {}) {
    return requestJson('/habilitaciones/cobertura', { signal });
}

export async function obtenerHabilitacionesPorComuna(comuna, { signal } = {}) {
    return requestJson(`/habilitaciones/por-comuna/${comuna}`, { signal });
}

export async function obtenerRubrosPorComuna(comuna, { limite = 10, signal } = {}) {
    return requestJson(
        `/habilitaciones/rubros-por-comuna/${comuna}?limit=${limite}`,
        { signal }
    );
}

/**
 * Obtiene parcelas georreferenciadas con sus habilitaciones y rubros.
 * Se usa desde el visor para enriquecer el popup de la parcela seleccionada.
 *
 * @param {Object} [filtros] - Filtros opcionales de la API `/mapa/parcelas`.
 * @param {number} [filtros.oeste] - Longitud oeste del bounding box.
 * @param {number} [filtros.sur] - Latitud sur del bounding box.
 * @param {number} [filtros.este] - Longitud este del bounding box.
 * @param {number} [filtros.norte] - Latitud norte del bounding box.
 * @param {number} [filtros.comuna] - Comuna (1..15).
 * @param {string} [filtros.rubro] - Texto a buscar en el rubro.
 * @param {number} [filtros.limite] - Máximo de resultados (por defecto 200).
 * @param {AbortSignal} [filtros.signal] - Señal para cancelar la petición.
 */
export async function obtenerParcelasMapa({
    oeste,
    sur,
    este,
    norte,
    comuna,
    rubro,
    limite = 200,
    signal,
} = {}) {
    const params = new URLSearchParams();
    const filtros = { oeste, sur, este, norte, comuna, rubro, limite };
    Object.entries(filtros).forEach(([clave, valor]) => {
        if (valor !== undefined && valor !== null && valor !== '') {
            params.set(clave, String(valor));
        }
    });
    return requestJson(`/mapa/parcelas?${params.toString()}`, { signal });
}

export async function obtenerHealth({ signal } = {}) {
    return requestJson('/health', { signal });
}
