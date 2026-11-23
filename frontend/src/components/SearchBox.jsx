/**
 * @file SearchBox.jsx
 * @description Buscador principal del flujo de consulta: rubro (catálogo cargado
 * en el backend) y lugar (texto libre), como campos separados, con dictado por
 * voz (Web Speech API y respaldo local con faster-whisper).
 * @author Equipo Frontend - SGI TECBA
 */

import { useEffect, useRef, useState } from 'react';
import { obtenerRubros, transcribirVoz } from '../services/api';
import { parsearDictado, vozDisponible } from '../services/voz';

/** Rubros mínimos si el catálogo del backend no está disponible. */
const RUBROS_RESPALDO = ['Cafetería', 'Pizzería'];

/** Duración máxima de la grabación de respaldo. */
const MAX_GRABACION_MS = 15000;

export const SearchBox = ({ onSearch, isLoading = false }) => {
    const [rubro, setRubro] = useState('');
    const [lugar, setLugar] = useState('');
    const [rubros, setRubros] = useState([]);
    const [cargandoRubros, setCargandoRubros] = useState(true);
    const [estadoVoz, setEstadoVoz] = useState('inactivo');
    const [mensajeVoz, setMensajeVoz] = useState('');

    const recognitionRef = useRef(null);
    const recorderRef = useRef(null);
    const streamRef = useRef(null);
    const temporizadorRef = useRef(null);
    const activoRef = useRef(false);

    useEffect(() => {
        const control = new AbortController();

        obtenerRubros({ signal: control.signal })
            .then((lista) => {
                if (control.signal.aborted) return;
                const disponibles = Array.isArray(lista) && lista.length ? lista : RUBROS_RESPALDO;
                setRubros(disponibles);
                setRubro((actual) => actual || disponibles[0]);
            })
            .catch(() => {
                if (control.signal.aborted) return;
                setRubros(RUBROS_RESPALDO);
                setRubro(RUBROS_RESPALDO[0]);
            })
            .finally(() => {
                if (!control.signal.aborted) setCargandoRubros(false);
            });

        return () => control.abort();
    }, []);

    // Al desmontar, cortamos micrófono y grabación para no dejarlos prendidos.
    useEffect(() => () => {
        activoRef.current = false;
        try { recognitionRef.current?.abort(); } catch { /* ya detenido */ }
        try { recorderRef.current?.stop(); } catch { /* ya detenido */ }
        streamRef.current?.getTracks().forEach((pista) => pista.stop());
        clearTimeout(temporizadorRef.current);
    }, []);

    const limpiarRecursos = () => {
        clearTimeout(temporizadorRef.current);
        temporizadorRef.current = null;
        try {
            if (recorderRef.current && recorderRef.current.state !== 'inactive') {
                recorderRef.current.stop();
            }
        } catch { /* ya detenido */ }
        streamRef.current?.getTracks().forEach((pista) => pista.stop());
        streamRef.current = null;
        recorderRef.current = null;
    };

    const aplicarDictado = (texto, origen) => {
        const transcripcion = (texto || '').trim();
        if (!transcripcion) {
            setMensajeVoz('No se entendió el dictado. Probá otra vez o completá los campos a mano.');
            return;
        }

        const resultado = parsearDictado(transcripcion, rubros, rubro);
        if (resultado.rubro) setRubro(resultado.rubro);
        if (resultado.lugar) setLugar(resultado.lugar);

        const fuente = origen === 'local' ? 'transcripción local' : 'navegador';
        setMensajeVoz(`Dictado por ${fuente}: “${transcripcion}”. Revisá los campos antes de Buscar.`);
    };

    /** Respaldo: grabar en el navegador y transcribir con el modelo local. */
    const iniciarConRespaldo = async (aviso = '') => {
        if (!activoRef.current) return;

        if (typeof MediaRecorder === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
            activoRef.current = false;
            setEstadoVoz('inactivo');
            setMensajeVoz(
                aviso
                    ? `${aviso} Tampoco hay grabación disponible: escribí los campos manualmente.`
                    : 'Tu navegador no permite dictado ni grabación. Escribí los campos manualmente.'
            );
            return;
        }

        setEstadoVoz('transcribiendo');
        setMensajeVoz(aviso || 'Grabando… hablá ahora (hasta 15 segundos).');

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            if (!activoRef.current) {
                stream.getTracks().forEach((pista) => pista.stop());
                return;
            }
            streamRef.current = stream;

            const tipo = typeof MediaRecorder.isTypeSupported === 'function'
                ? [
                    'audio/webm;codecs=opus',
                    'audio/webm',
                    'audio/ogg;codecs=opus',
                ].find((candidato) => MediaRecorder.isTypeSupported(candidato)) || ''
                : '';

            const recorder = new MediaRecorder(stream, tipo ? { mimeType: tipo } : undefined);
            recorderRef.current = recorder;
            const partes = [];

            const grabacion = new Promise((resolve, reject) => {
                recorder.ondataavailable = (evento) => {
                    if (evento.data?.size) partes.push(evento.data);
                };
                recorder.onstop = () => resolve(
                    new Blob(partes, { type: recorder.mimeType || tipo || 'audio/webm' })
                );
                recorder.onerror = (evento) => reject(evento.error || new Error('Falló la grabación'));
            });

            recorder.start();
            temporizadorRef.current = setTimeout(() => {
                if (recorderRef.current?.state === 'recording') recorderRef.current.stop();
            }, MAX_GRABACION_MS);
            setMensajeVoz('Grabando… hablá ahora. Se detiene solo a los 15 s (o tocá Voz para terminar).');

            const audio = await grabacion;
            if (!activoRef.current || !audio.size) return;

            setMensajeVoz('Transcribiendo con el modelo local…');
            const respuesta = await transcribirVoz(audio);
            if (!activoRef.current) return;
            aplicarDictado(respuesta?.texto, 'local');
        } catch (error) {
            if (!activoRef.current) return;
            const sinPermiso = ['NotAllowedError', 'PermissionDeniedError'].includes(error?.name);
            setMensajeVoz(sinPermiso
                ? 'Permiso de micrófono denegado. Habilitalo en el navegador para usar la voz.'
                : `No se pudo transcribir: ${error?.message || 'error inesperado'}. Podés escribir los campos manualmente.`);
        } finally {
            limpiarRecursos();
            activoRef.current = false;
            setEstadoVoz('inactivo');
        }
    };

    /** Camino principal: Web Speech API con lang es-AR. */
    const iniciarConNavegador = () => {
        const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        let recognition;
        try {
            recognition = new Recognition();
        } catch {
            iniciarConRespaldo();
            return;
        }

        recognition.lang = 'es-AR';
        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.maxAlternatives = 1;

        let texto = '';

        recognition.onresult = (evento) => {
            let final = '';
            let interino = '';
            for (let i = evento.resultIndex; i < evento.results.length; i += 1) {
                const parte = evento.results[i][0]?.transcript || '';
                if (evento.results[i].isFinal) final += `${parte} `;
                else interino += parte;
            }
            if (final) texto += final;
            const mostrado = (texto + interino).trim();
            if (mostrado) setMensajeVoz(`Escuchando: “${mostrado}”`);
        };

        recognition.onerror = (evento) => {
            if (!activoRef.current) return;
            const error = evento?.error;
            if (['not-allowed', 'service-not-allowed'].includes(error)) {
                activoRef.current = false;
                recognitionRef.current = null;
                setEstadoVoz('inactivo');
                setMensajeVoz('Permiso de micrófono denegado. Habilitalo en el navegador para usar la voz.');
                return;
            }
            recognitionRef.current = null;
            iniciarConRespaldo(
                `Reconocimiento del navegador no disponible (${error || 'error'}). Usando transcripción local…`
            );
        };

        recognition.onend = () => {
            if (recognitionRef.current !== recognition || !activoRef.current) return;
            recognitionRef.current = null;
            if (texto.trim()) {
                aplicarDictado(texto, 'navegador');
                activoRef.current = false;
                setEstadoVoz('inactivo');
            } else {
                iniciarConRespaldo('No se oyó nada por el navegador. Usando transcripción local…');
            }
        };

        recognitionRef.current = recognition;
        setEstadoVoz('escuchando');
        setMensajeVoz('Escuchando… hablá natural, por ejemplo: “quiero abrir una cafetería en Lavalle 1345”.');

        try {
            recognition.start();
        } catch {
            recognitionRef.current = null;
            iniciarConRespaldo();
        }
    };

    const detenerDictado = () => {
        activoRef.current = false;
        try { recognitionRef.current?.stop(); } catch { /* ya detenido */ }
        recognitionRef.current = null;
        limpiarRecursos();
        setEstadoVoz('inactivo');
        setMensajeVoz('Dictado detenido. Revisá los campos y tocá Buscar cuando quieras.');
    };

    const handleVoiceSearch = () => {
        if (estadoVoz !== 'inactivo') {
            detenerDictado();
            return;
        }
        activoRef.current = true;
        setMensajeVoz('');
        if (vozDisponible()) iniciarConNavegador();
        else iniciarConRespaldo('El navegador no tiene reconocimiento de voz. Usando transcripción local…');
    };

    const handleSubmit = (event) => {
        event.preventDefault();
        if (!rubro || !lugar.trim() || isLoading) return;
        onSearch({ rubro, direccion: lugar.trim() });
    };

    const vozActiva = estadoVoz !== 'inactivo';
    const etiquetaVoz = estadoVoz === 'escuchando'
        ? 'Escuchando…'
        : estadoVoz === 'transcribiendo'
            ? 'Transcribiendo…'
            : 'Voz';

    return (
        <div className="w-full max-w-6xl mx-auto py-12 px-4">
            <div className="text-center mb-10 space-y-4">
                <h2
                    className="text-3xl sm:text-4xl font-bold text-slate-800"
                    style={{ textShadow: '0 0 14px rgba(255,255,255,0.95), 0 0 5px rgba(255,255,255,0.9)' }}
                >
                    Sistema de Gestión Inteligente
                </h2>
                <p
                    className="text-base sm:text-lg font-semibold text-gcba-dark"
                    style={{ textShadow: '0 0 16px rgba(255,255,255,1), 0 0 5px rgba(255,255,255,1)' }}
                >
                    Los trámites que necesitás para realizar tu actividad, en un solo lugar.
                </p>
            </div>

            <form onSubmit={handleSubmit} className="mx-auto max-w-6xl">
                {/* Barra unificada */}
                <div className="flex flex-col rounded-2xl bg-white p-3 shadow-md sm:flex-row sm:items-end sm:gap-6 sm:px-6 sm:py-3">
                    {/* Rubro */}
                    <div className="min-w-0 flex-1">
                        <span
                            id="label-buscador-rubro"
                            className="block text-xs font-bold uppercase tracking-wider text-slate-400 outline-none"
                        >
                            Rubro
                        </span>
                        <div className="relative mt-1.5 flex items-center">
                            <span className="mr-2 text-base text-slate-400" aria-hidden="true">
                                🏷️
                            </span>
                            <select
                                id="buscador-rubro"
                                aria-labelledby="label-buscador-rubro"
                                value={rubro}
                                onChange={(event) => setRubro(event.target.value)}
                                disabled={cargandoRubros || isLoading}
                                style={{ border: 'none', boxShadow: 'none', background: 'transparent' }}
                                className="w-full cursor-pointer appearance-none bg-transparent py-2.5 pr-6 text-base font-semibold text-slate-800 outline-none disabled:cursor-wait disabled:opacity-60"
                            >
                                <option value="">
                                    {cargandoRubros ? 'Cargando rubros…' : 'Seleccionar rubro'}
                                </option>
                                {rubros.map((item) => (
                                    <option key={item} value={item}>
                                        {item}
                                    </option>
                                ))}
                            </select>
                            <span className="pointer-events-none absolute right-0 text-xs text-slate-400">
                                ▾
                            </span>
                        </div>
                    </div>

                    {/* Lugar */}
                    <div className="min-w-0 flex-[1.4]">
                        <span
                            id="label-buscador-lugar"
                            className="block text-xs font-bold uppercase tracking-wider text-slate-400 outline-none"
                        >
                            Lugar
                        </span>
                        <div className="mt-1.5 flex items-center">
                            <span className="mr-2 text-base text-slate-400" aria-hidden="true">
                                📍
                            </span>
                            <input
                                id="buscador-lugar"
                                aria-labelledby="label-buscador-lugar"
                                type="text"
                                value={lugar}
                                onChange={(event) => setLugar(event.target.value)}
                                placeholder="Ej: Lavalle 1345, CABA"
                                style={{ border: 'none', boxShadow: 'none', background: 'transparent' }}
                                className="w-full bg-transparent py-2.5 text-base font-medium text-slate-800 placeholder-slate-400 outline-none"
                            />
                        </div>
                    </div>

                    {/* Acciones: Voz + Buscar alineados con los campos */}
                    <div className="mt-3 flex shrink-0 items-center justify-end gap-3 sm:mt-0">
                        <button
                            type="button"
                            onClick={handleVoiceSearch}
                            disabled={isLoading}
                            aria-label={vozActiva ? 'Detener dictado' : 'Dictar consulta por voz'}
                            aria-pressed={vozActiva}
                            title={vozActiva
                                ? 'Detener dictado'
                                : `${etiquetaVoz}: dictar por voz (es-AR); si falla se usa transcripción local`}
                            className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-full p-0 leading-none transition-all ${
                                estadoVoz === 'escuchando'
                                    ? 'animate-pulse bg-red-50 text-red-600'
                                    : estadoVoz === 'transcribiendo'
                                        ? 'animate-pulse bg-amber-50 text-amber-700'
                                        : 'bg-[#f2f2f2] text-gcba-primary hover:bg-slate-200'
                            }`}
                        >
                            <svg
                                xmlns="http://www.w3.org/2000/svg"
                                fill="none"
                                viewBox="0 0 24 24"
                                strokeWidth={2}
                                stroke="currentColor"
                                className="h-5 w-5"
                                aria-hidden="true"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    d="M12 18.75a6 6 0 0 0 6-6v-1.5m-6 7.5a6 6 0 0 1-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 0 1-3-3V4.5a3 3 0 1 1 6 0v8.25a3 3 0 0 1-3 3Z"
                                />
                            </svg>
                        </button>

                        <button
                            type="submit"
                            disabled={isLoading || !rubro || !lugar.trim()}
                            className="inline-flex h-11 shrink-0 items-center justify-center gap-2 rounded-xl bg-gcba-primary px-7 text-base font-semibold leading-none text-white shadow-sm transition-colors hover:bg-blue-900 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            <span>{isLoading ? 'Consultando…' : 'Buscar'}</span>
                            {!isLoading && <span aria-hidden="true">→</span>}
                        </button>
                    </div>
                </div>

                {/* Texto de estado del dictado; el resto de los estados no se muestra. */}
                {mensajeVoz && (
                    <p
                        className="mt-3 text-center text-sm sm:text-base font-semibold text-gcba-dark"
                        role="status"
                        aria-live="polite"
                        style={{ textShadow: '0 0 16px rgba(255,255,255,1), 0 0 5px rgba(255,255,255,1)' }}
                    >
                        {mensajeVoz}
                    </p>
                )}
            </form>
        </div>
    );
};