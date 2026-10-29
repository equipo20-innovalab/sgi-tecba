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

export async function consultarProyecto(texto, { signal } = {}) {
    return requestJson('/consulta', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ texto }),
        signal,
    });
}

export async function obtenerRubros({ signal } = {}) {
    return requestJson('/rubros', { signal });
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

export async function obtenerHealth({ signal } = {}) {
    return requestJson('/health', { signal });
}
