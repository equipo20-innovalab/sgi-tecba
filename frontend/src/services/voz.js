/**
 * @file voz.js
 * @description Utilidades de dictado: parseo propio en español rioplatense y
 * envío del audio al respaldo local (faster-whisper) cuando el navegador no
 * puede reconocer la voz.
 * @author Equipo Frontend - SGI TECBA
 */

/** Reemplazos para buscar con/sin tilde y con ñ. */
const ACENTOS = {
    a: '[aáàä]',
    e: '[eéèë]',
    i: '[iíìï]',
    o: '[oóòö]',
    u: '[uúùü]',
    n: '[nñ]',
};

/** Sinónimos conocidos, alineados con extraccion_service.py del backend. */
const SINONIMOS = {
    cafeteria: ['cafeteria', 'cafe', 'confiteria', 'bar', 'cafetero'],
    pizzeria: ['pizzeria', 'pizza'],
    restaurante: ['restaurante', 'resto', 'parrilla'],
    'gastronomia general': ['gastronomia general', 'gastronomico'],
    'comercio minorista': ['comercio minorista', 'tienda', 'local comercial'],
    general: ['general'],
};

/** Barrios de CABA: permiten aceptar lugares sin número ("Palermo", "San Telmo"). */
const BARRIOS = [
    'Agronomía', 'Almagro', 'Barracas', 'Belgrano', 'Boedo', 'Caballito',
    'Chacarita', 'Coghlan', 'Colegiales', 'Constitución', 'Flores', 'Floresta',
    'La Boca', 'La Recoleta', 'La Reina', 'Liniers', 'Mataderos', 'Monte Castro',
    'Monserrat', 'Nueva Pompeya', 'Núñez', 'Palermo', 'Parque Avellaneda',
    'Parque Chacabuco', 'Parque Chas', 'Parque Patricios', 'Puerto Madero',
    'Recoleta', 'Retiro', 'Saavedra', 'San Cristóbal', 'San Nicolás', 'San Telmo',
    'Vélez Sarsfield', 'Versalles', 'Villa Crespo', 'Villa del Parque',
    'Villa Devoto', 'Villa Luro', 'Villa Lugano', 'Villa Pueyrredón', 'Villa Real',
    'Villa Riachuelo', 'Villa Sarmiento', 'Villa Urquiza', 'Villa General Belgrano',
];

/** Errores típicos del reconocedor con nombres de calles y barrios. */
const CORRECCIONES = [
    [/\bla\s+valle\b/gi, 'Lavalle'],
    [/\bvilla\s+parque\b/gi, 'Villa del Parque'],
];

/** Palabras de relleno que no aportan al lugar. */
const RUIDO = [
    'quiero', 'necesito', 'deseo', 'busco', 'estoy buscando', 'me gustaria',
    'consulta', 'consultar', 'evaluar', 'evaluacion', 'verificar', 'saber',
    'informacion sobre', 'datos de', 'por favor', 'gracias',
    'abrir', 'montar', 'instalar', 'poner', 'hacer', 'realizar', 'gestionar',
    'un', 'una', 'unos', 'unas', 'el', 'la', 'los', 'las', 'del', 'para',
    'sobre', 'acerca de', 'referido a', 'ubicado en', 'situado en',
    'local de', 'local', 'barrio', 'en', 'de', 'caba', 'buenos aires',
    'capital federal', 'ciudad autonoma',
];

/** Alias de actividad que se sacan del lugar aunque el rubro no esté en el catálogo. */
const ALIAS_ACTIVIDAD = Object.values(SINONIMOS)
    .flat()
    .filter((alias) => alias !== 'general');

function normalizar(texto) {
    return (texto || '')
        .toLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '');
}

function escapar(texto) {
    return texto.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/** Devuelve un patrón tolerante a tildes/ñ para el texto dado. */
function patron(texto) {
    return [...escapar(texto.toLowerCase())]
        .map((caracter) => ACENTOS[caracter] || caracter)
        .join('');
}

function patronPalabra(texto) {
    return new RegExp(`\\b${patron(texto)}\\b`, 'gi');
}

function aliasDelRubro(rubro) {
    const vistos = new Set();
    return [rubro, ...(SINONIMOS[normalizar(rubro)] || [])].filter((item) => {
        const clave = normalizar(item);
        if (vistos.has(clave)) return false;
        vistos.add(clave);
        return true;
    });
}

/**
 * Detecta el rubro mencionado en el dictado usando el catálogo disponible.
 * Se probaron primero los alias más largos para no confundir "General" con
 * "Gastronomía general", por ejemplo.
 */
function detectarRubro(texto, rubros) {
    const candidatos = rubros
        .flatMap((rubro) => aliasDelRubro(rubro).map((alias) => ({ rubro, alias })))
        .sort((a, b) => b.alias.length - a.alias.length);

    for (const candidato of candidatos) {
        if (patronPalabra(candidato.alias).test(texto)) return candidato.rubro;
    }
    return null;
}

function extraerLugar(texto, rubroDetectado) {
    let resto = texto;

    CORRECCIONES.forEach(([patronCorreccion, reemplazo]) => {
        resto = resto.replace(patronCorreccion, reemplazo);
    });

    const alias = rubroDetectado ? aliasDelRubro(rubroDetectado) : ALIAS_ACTIVIDAD;
    alias.forEach((item) => {
        resto = resto.replace(patronPalabra(item), ' ');
    });

    // El barrio se detecta antes de limpiar artículos ("Villa del Parque").
    const tieneBarrio = BARRIOS.some((barrio) => patronPalabra(barrio).test(resto));

    RUIDO.forEach((frase) => {
        resto = resto.replace(patronPalabra(frase), ' ');
    });

    CORRECCIONES.forEach(([patronCorreccion, reemplazo]) => {
        resto = resto.replace(patronCorreccion, reemplazo);
    });

    resto = resto
        .replace(/[¿?¡!;:,"'()]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim()
        .replace(/\.$/, '');

    const tieneNumero = /\d/.test(resto);
    if (!tieneNumero && !tieneBarrio) return '';

    return resto.length >= 3 ? resto.slice(0, 120) : '';
}

/**
 * Convierte una transcripción en los dos campos del buscador. Nunca dispara
 * la consulta: el usuario siempre revisa y confirmá con "Buscar".
 *
 * @param {string} transcripcion - Texto devuelto por el reconocedor.
 * @param {string[]} rubros - Catálogo cargado desde GET /rubros.
 * @param {string} rubroActual - Rubro ya seleccionado, si el dictado no lo menciona.
 * @returns {{rubro: string, lugar: string}}
 */
export function parsearDictado(transcripcion, rubros = [], rubroActual = '') {
    const texto = (transcripcion || '').replace(/\s+/g, ' ').trim();
    if (!texto) return { rubro: rubroActual, lugar: '' };

    const rubroDetectado = detectarRubro(texto, rubros);
    return {
        rubro: rubroDetectado || rubroActual,
        lugar: extraerLugar(texto, rubroDetectado),
    };
}

/** true cuando el navegador expone la Web Speech API. */
export function vozDisponible() {
    if (typeof window === 'undefined') return false;
    return Boolean(window.SpeechRecognition || window.webkitSpeechRecognition);
}
