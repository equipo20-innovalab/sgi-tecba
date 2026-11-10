import { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import useChatAgent from '../hooks/useChatAgent';

const SUGERENCIAS_RESPUESTA = [
    { label: '¿Qué documentación necesito?', message: '¿Qué documentación necesito?' },
    { label: 'Explicame el paso 1', message: 'Explicame el paso 1' },
];

const CONSULTAS_RAPIDAS = [
    { label: 'Tu avance', message: '¿Cuál es mi avance en el trámite?', icon: '▤' },
    { label: 'Fuentes oficiales', message: '¿Cuáles son las fuentes oficiales para este trámite?', icon: '⌕' },
    { label: 'Preguntas frecuentes', message: '¿Cuáles son las preguntas frecuentes sobre esta habilitación?', icon: '?' },
    { label: 'Ver más opciones', message: '¿Qué otras consultas puedo hacer?', icon: '▦' },
];

export default function AsistenteSGI({
    rubro,
    direccion,
    avance = 0,
    totalPasos = 4,
}) {
    const context = { rubro, direccion, ciudad: 'CABA' };
    const { messages, sendMessage, isLoading, error } = useChatAgent(context);
    const [draft, setDraft] = useState('');
    const [dismissedSuggestions, setDismissedSuggestions] = useState(() => new Set());
    const messagesContainerRef = useRef(null);
    const porcentajeAvance = totalPasos > 0
        ? Math.min((avance / totalPasos) * 100, 100)
        : 0;

    useEffect(() => {
        if (!messages.length && !isLoading) {
            return;
        }

        const container = messagesContainerRef.current;
        if (container) {
            container.scrollTo({
                top: container.scrollHeight,
                behavior: 'smooth',
            });
        }
    }, [messages, isLoading]);

    const handleSubmit = async (event) => {
        event.preventDefault();
        dismissAllSuggestions();
        const sent = await sendMessage(draft);
        if (sent) {
            setDraft('');
        }
    };

    const dismissAllSuggestions = () => {
        setDismissedSuggestions((previous) => {
            const next = new Set(previous);
            messages.forEach((message, index) => {
                if (message.role === 'assistant') {
                    next.add(index);
                }
            });
            return next;
        });
    };

    const handleSuggestedMessage = (message, assistantIndex) => {
        setDismissedSuggestions((previous) => new Set(previous).add(assistantIndex));
        void sendMessage(message);
    };

    const handleQuickConsultation = (message) => {
        dismissAllSuggestions();
        void sendMessage(message);
    };

    return (
        <section
            aria-label="Asistente SGI"
            className="mx-auto flex h-[85vh] min-h-[850px] max-h-none w-full max-w-full flex-none flex-col overflow-hidden rounded-2xl border border-slate-200 bg-slate-50 shadow-xl"
        >
            <style>{`
                .sgi-chat-scroll {
                    scrollbar-width: thin;
                    scrollbar-color: transparent transparent;
                }
                .sgi-chat-scroll:hover {
                    scrollbar-color: #cbd5e1 transparent;
                }
                .sgi-chat-scroll::-webkit-scrollbar {
                    width: 4px;
                }
                .sgi-chat-scroll::-webkit-scrollbar-track {
                    background: transparent;
                }
                .sgi-chat-scroll::-webkit-scrollbar-thumb {
                    border-radius: 9999px;
                    background: transparent;
                }
                .sgi-chat-scroll:hover::-webkit-scrollbar-thumb {
                    background: #cbd5e1;
                }
            `}</style>
            <header className="flex-none border-b-4 border-amber-400 bg-gradient-to-r from-teal-950 via-cyan-950 to-teal-900 px-4 py-3 text-white">
                <div className="flex items-center gap-3">
                    <span
                        aria-hidden="true"
                        className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-amber-400 text-2xl font-bold text-teal-950 shadow-md"
                    >
                        ✦
                    </span>
                    <div className="min-w-0 flex-1">
                        <h3 className="text-base font-bold text-white">Asistente SGI</h3>
                        <p className="whitespace-nowrap text-sm text-teal-100">Tu acompañante en cada paso</p>
                    </div>
                    <span aria-hidden="true" className="text-xl text-teal-100">↗</span>
                </div>
            </header>

            <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-slate-100">
                <section
                    aria-label="Contexto de la consulta"
                    className="shrink-0 bg-slate-50 px-4 py-1"
                >
                    <p className="mb-0.5 text-xs text-slate-600">Estás consultando sobre</p>
                    <div className="flex min-w-0 flex-row flex-nowrap gap-1">
                        <span className="inline-flex w-[42%] min-w-0 items-center gap-1 rounded-full border-2 border-slate-200 bg-white px-2 py-1 text-xs text-blue-600">
                            <span aria-hidden="true">☕</span>
                            <span className="truncate">{rubro}</span>
                        </span>
                        <span className="inline-flex min-w-0 flex-1 items-center gap-1 rounded-full border-2 border-slate-200 bg-white px-2 py-1 text-xs text-blue-600">
                            <span aria-hidden="true">📍</span>
                            <span className="truncate">{direccion}</span>
                        </span>
                    </div>
                </section>

                <section
                    aria-label="Avance del recorrido"
                    className="shrink-0 bg-slate-200/70 px-4 py-1"
                >
                    <div className="rounded-2xl bg-white p-2 shadow-sm">
                        <div className="mb-0.5 flex items-center justify-between gap-2">
                            <span className="text-xs font-medium text-slate-800">Tu avance</span>
                            <span className="whitespace-nowrap text-xs text-slate-500">
                                {avance} de {totalPasos} pasos
                            </span>
                        </div>
                        <div
                            className="h-1 overflow-hidden rounded-full bg-slate-200"
                            role="progressbar"
                            aria-label="Avance del recorrido"
                            aria-valuemin={0}
                            aria-valuemax={totalPasos}
                            aria-valuenow={avance}
                        >
                            <div
                                className="h-full rounded-full bg-amber-400 transition-[width]"
                                style={{ width: `${porcentajeAvance}%` }}
                            />
                        </div>
                        <p className="mt-0.5 text-[10px] text-slate-500">
                            Sin apuro: avanzá cuando quieras.
                        </p>
                    </div>
                </section>

                <div
                    ref={messagesContainerRef}
                    className="sgi-chat-scroll min-h-0 min-w-0 flex-1 scroll-smooth overflow-x-hidden overflow-y-auto overscroll-contain p-4"
                >
                    <div
                        className="flex min-w-0 flex-col space-y-4"
                        role="log"
                        aria-label="Conversación con Asistente SGI"
                        aria-live="polite"
                    >
                        <div className="mb-5 text-center">
                            <p className="mb-2 inline-flex rounded-full bg-blue-100 px-5 py-2.5 text-sm font-semibold text-slate-800">
                                ¡Hola! 👋
                            </p>
                            <p className="text-sm text-slate-600">
                                Estoy para ayudarte con {rubro.toLowerCase()}. ¿Qué necesitás saber?
                            </p>
                        </div>
                        {messages.map((message, index) => (
                            message.role === 'assistant' ? (
                                <div key={`${message.role}-${index}`} className="flex min-w-0 items-start gap-2.5">
                                    <span
                                        aria-hidden="true"
                                        className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-amber-400 text-lg font-bold text-teal-950 shadow-sm"
                                    >
                                        ✦
                                    </span>
                                    <div className="flex min-w-0 max-w-full flex-col items-start gap-2">
                                        <div className="max-w-full break-words rounded-2xl border border-slate-100 bg-white p-4 text-sm leading-relaxed text-slate-800 shadow-sm [overflow-wrap:anywhere]">
                                            <ReactMarkdown
                                                components={{
                                                    p: ({ children }) => (
                                                        <p className="mb-2 text-sm last:mb-0">{children}</p>
                                                    ),
                                                    ul: ({ children }) => (
                                                        <ul className="my-2 list-disc space-y-1 pl-5 text-sm">
                                                            {children}
                                                        </ul>
                                                    ),
                                                    ol: ({ children }) => (
                                                        <ol className="my-2 list-decimal space-y-1 pl-5 text-sm">
                                                            {children}
                                                        </ol>
                                                    ),
                                                    li: ({ children }) => <li className="text-sm">{children}</li>,
                                                    strong: ({ children }) => (
                                                        <strong className="text-sm font-semibold text-slate-800">
                                                            {children}
                                                        </strong>
                                                    ),
                                                    h1: ({ children }) => (
                                                        <p className="mb-2 text-sm font-semibold last:mb-0">{children}</p>
                                                    ),
                                                    h2: ({ children }) => (
                                                        <p className="mb-2 text-sm font-semibold last:mb-0">{children}</p>
                                                    ),
                                                    h3: ({ children }) => (
                                                        <p className="mb-2 text-sm font-semibold last:mb-0">{children}</p>
                                                    ),
                                                    h4: ({ children }) => (
                                                        <p className="mb-2 text-sm font-semibold last:mb-0">{children}</p>
                                                    ),
                                                    h5: ({ children }) => (
                                                        <p className="mb-2 text-sm font-semibold last:mb-0">{children}</p>
                                                    ),
                                                    h6: ({ children }) => (
                                                        <p className="mb-2 text-sm font-semibold last:mb-0">{children}</p>
                                                    ),
                                                }}
                                            >
                                                {message.content}
                                            </ReactMarkdown>
                                        </div>
                                        {!dismissedSuggestions.has(index) && (
                                            <div className="flex max-w-full flex-wrap gap-2">
                                                {SUGERENCIAS_RESPUESTA.map((suggestion) => (
                                                    <button
                                                        key={suggestion.label}
                                                        type="button"
                                                        disabled={isLoading}
                                                        onClick={() => handleSuggestedMessage(suggestion.message, index)}
                                                        className="rounded-full border border-blue-500 bg-white px-3 py-1.5 text-sm font-medium text-blue-600 transition-colors hover:bg-blue-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:cursor-not-allowed disabled:opacity-60"
                                                    >
                                                        {suggestion.label}
                                                    </button>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ) : (
                                <div key={`${message.role}-${index}`} className="flex min-w-0 justify-end">
                                    <p className="max-w-[85%] break-words rounded-2xl bg-blue-600 px-4 py-3 text-sm leading-relaxed text-white shadow-sm [overflow-wrap:anywhere]">
                                        {message.content}
                                    </p>
                                </div>
                            )
                        ))}
                        {isLoading && (
                            <p className="flex w-fit items-center gap-1.5 rounded-full bg-blue-100 px-4 py-3 text-sm text-slate-500" role="status">
                                <span className="sr-only">Consultando la información...</span>
                                <span aria-hidden="true" className="h-2 w-2 animate-bounce rounded-full bg-blue-500 [animation-delay:-0.3s]" />
                                <span aria-hidden="true" className="h-2 w-2 animate-bounce rounded-full bg-blue-500 [animation-delay:-0.15s]" />
                                <span aria-hidden="true" className="h-2 w-2 animate-bounce rounded-full bg-blue-500" />
                            </p>
                        )}
                    </div>
                </div>
            </div>

            <footer className="flex-none min-w-0 overflow-x-hidden border-t border-blue-100 bg-slate-50/95 px-2 py-3">
                <section className="mb-1 min-w-0 flex-none rounded-2xl border border-blue-100 bg-white p-1 shadow-sm">
                    <h4 className="mb-0.5 text-xs font-semibold text-slate-800">
                        <span aria-hidden="true" className="mr-1 text-[10px]">💡</span>
                        También podés consultar:
                    </h4>
                    <ul className="grid min-w-0 grid-cols-2 gap-1" aria-label="Consultas rápidas">
                        {CONSULTAS_RAPIDAS.map((consultation) => (
                            <li key={consultation.label}>
                                <button
                                    type="button"
                                    disabled={isLoading}
                                    onClick={() => handleQuickConsultation(consultation.message)}
                                    className="flex min-w-0 w-full items-center gap-1 rounded-xl border border-blue-300 bg-white px-1.5 py-1 text-left text-xs font-medium leading-tight text-blue-700 transition-colors hover:bg-blue-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                    <span aria-hidden="true" className="shrink-0 text-[10px] text-blue-600">
                                        {consultation.icon}
                                    </span>
                                    {consultation.label}
                                </button>
                            </li>
                        ))}
                    </ul>
                </section>
                <form onSubmit={handleSubmit} className="mt-0 flex min-w-0 flex-none items-center gap-1 rounded-full border border-blue-100 bg-white p-1 shadow-sm">
                    <input
                        type="text"
                        value={draft}
                        onChange={(event) => setDraft(event.target.value)}
                        disabled={isLoading}
                        maxLength={4000}
                        aria-label="Escribí tu pregunta"
                        aria-describedby="asistente-sgi-status"
                        placeholder="Escribí tu consulta..."
                        className="min-w-0 flex-1 bg-transparent py-1 pl-4 pr-2 text-sm text-slate-700 outline-none placeholder:text-slate-400 disabled:cursor-not-allowed"
                    />
                    <button
                        type="submit"
                        disabled={isLoading || !draft.trim()}
                        aria-label="Enviar pregunta"
                        className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-blue-600 text-base font-bold text-white shadow-sm transition-colors hover:bg-blue-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        ➤
                    </button>
                </form>
                <p
                    id="asistente-sgi-status"
                    className={`mt-0.5 px-2 text-xs leading-tight ${error ? 'text-red-600' : 'text-slate-500'}`}
                    role={error ? 'alert' : 'status'}
                >
                    {error || 'Escribí tu pregunta y presioná Enter para enviarla.'}
                </p>
            </footer>
        </section>
    );
}
