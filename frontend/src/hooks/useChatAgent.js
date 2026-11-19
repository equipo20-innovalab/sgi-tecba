import { useRef, useState } from 'react';

function normalizeHistory(messages) {
    if (!Array.isArray(messages)) {
        return [];
    }

    const history = [];

    messages.forEach((message) => {
        if (
            !message
            || !['user', 'assistant'].includes(message.role)
            || typeof message.content !== 'string'
        ) {
            return;
        }

        const content = message.content.trim();
        if (!content || content.length > 4000) {
            return;
        }

        if (history[history.length - 1]?.role !== message.role) {
            history.push({ role: message.role, content });
        }
    });

    if (history[0]?.role !== 'user') {
        return [];
    }

    if (history[history.length - 1]?.role === 'user') {
        history.pop();
    }

    return history;
}

export default function useChatAgent(context) {
    const [messages, setMessages] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');
    const messagesRef = useRef([]);
    const isSendingRef = useRef(false);

    const sendMessage = async (rawMessage) => {
        const content = typeof rawMessage === 'string' ? rawMessage.trim() : '';
        if (!content || content.length > 4000 || isSendingRef.current) {
            return false;
        }

        const history = normalizeHistory(messagesRef.current);
        const nextMessages = [...history, { role: 'user', content }];
        const requestContext = context && typeof context === 'object' && !Array.isArray(context)
            ? context
            : {};

        isSendingRef.current = true;
        setMessages(nextMessages);
        setIsLoading(true);
        setError('');

        try {
            const response = await fetch('/api/v1/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    messages: nextMessages,
                    context: requestContext,
                }),
            });

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
                    : Array.isArray(detail)
                        ? detail.map((issue) => {
                            const location = Array.isArray(issue.loc)
                                ? issue.loc.slice(1).join('.')
                                : '';
                            return location ? `${location}: ${issue.msg}` : issue.msg;
                        }).join(' ')
                        : `El backend respondió con el estado ${response.status}.`;
                const backendError = new Error(message);
                backendError.status = response.status;
                backendError.detail = detail;
                throw backendError;
            }

            if (typeof payload?.reply !== 'string' || !payload.reply.trim()) {
                throw new Error('El backend no devolvió una respuesta válida del asistente.');
            }

            const completedMessages = [
                ...nextMessages,
                { role: 'assistant', content: payload.reply.trim() },
            ];
            messagesRef.current = completedMessages;
            setMessages(completedMessages);
            return true;
        } catch (requestError) {
            console.error('Error al enviar un mensaje al asistente:', {
                status: requestError?.status,
                detail: requestError?.detail ?? requestError?.message ?? requestError,
            });
            setMessages(history);
            setError(
                requestError instanceof Error
                    ? requestError.message
                    : 'No se pudo enviar el mensaje. Intentá nuevamente.'
            );
            return false;
        } finally {
            isSendingRef.current = false;
            setIsLoading(false);
        }
    };

    return { messages, sendMessage, isLoading, error };
}
