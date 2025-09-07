import { useEffect, useRef, useCallback, useState } from 'react';
import { WebSocketMessage } from '../types/chat';

interface WebSocketHookOptions {
    url: string;
    onMessage?: (message: WebSocketMessage) => void;
    onConnect?: () => void;
    onDisconnect?: () => void;
    onError?: (error: Error) => void;
    reconnectInterval?: number;
    maxReconnectAttempts?: number;
}

export function useWebSocket({
    url,
    onMessage,
    onConnect,
    onDisconnect,
    onError,
    reconnectInterval = 1000,
    maxReconnectAttempts = 5
}: WebSocketHookOptions) {
    const [isConnected, setIsConnected] = useState(false);
    const ws = useRef<WebSocket | null>(null);
    const reconnectAttempts = useRef(0);
    const reconnectTimeoutId = useRef<NodeJS.Timeout>();

    const connect = useCallback(() => {
        try {
            ws.current = new WebSocket(url);

            ws.current.onopen = () => {
                setIsConnected(true);
                reconnectAttempts.current = 0;
                onConnect?.();
            };

            ws.current.onclose = () => {
                setIsConnected(false);
                onDisconnect?.();

                if (reconnectAttempts.current < maxReconnectAttempts) {
                    const timeout = reconnectInterval * Math.pow(2, reconnectAttempts.current);
                    reconnectTimeoutId.current = setTimeout(() => {
                        reconnectAttempts.current++;
                        connect();
                    }, timeout);
                }
            };

            ws.current.onerror = (error) => {
                onError?.(error as Error);
            };

            ws.current.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    onMessage?.(message);
                } catch (error) {
                    onError?.(new Error('Failed to parse WebSocket message'));
                }
            };
        } catch (error) {
            onError?.(error as Error);
        }
    }, [url, onMessage, onConnect, onDisconnect, onError, reconnectInterval, maxReconnectAttempts]);

    const disconnect = useCallback(() => {
        if (reconnectTimeoutId.current) {
            clearTimeout(reconnectTimeoutId.current);
        }

        if (ws.current) {
            ws.current.close();
            ws.current = null;
        }

        setIsConnected(false);
        reconnectAttempts.current = maxReconnectAttempts;
    }, [maxReconnectAttempts]);

    const send = useCallback((message: WebSocketMessage) => {
        if (ws.current?.readyState === WebSocket.OPEN) {
            ws.current.send(JSON.stringify(message));
            return true;
        }
        return false;
    }, []);

    useEffect(() => {
        connect();
        return () => {
            disconnect();
        };
    }, [connect, disconnect]);

    return {
        isConnected,
        send,
        connect,
        disconnect
    };
}