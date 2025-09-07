import { useCallback, useEffect, useRef, useState } from 'react';
import { v4 as uuidv4 } from 'uuid';
import {
    ChatState,
    ChatMessage,
    WebSocketMessage,
    SendMessageOptions,
    ChatRoom,
    TypingIndicator
} from '../types/chat';
import { useWebSocket } from './useWebSocket';

const TYPING_TIMEOUT = 3000;

export function useChat(tenantId: string, userId: string) {
    const [state, setState] = useState<ChatState>({
        rooms: [],
        messages: {},
        typingUsers: {},
        onlineUsers: new Set(),
        isConnected: false
    });

    const typingTimeouts = useRef<Record<string, NodeJS.Timeout>>({});

    const { isConnected, send } = useWebSocket({
        url: `${process.env.NEXT_PUBLIC_WS_URL}/chat?token=${localStorage.getItem('token')}`,
        onMessage: handleWebSocketMessage,
        onConnect: () => {
            setState(prev => ({ ...prev, isConnected: true }));
        },
        onDisconnect: () => {
            setState(prev => ({ ...prev, isConnected: false }));
        },
        onError: (error) => {
            setState(prev => ({ ...prev, error }));
        }
    });

    function handleWebSocketMessage(message: WebSocketMessage) {
        switch (message.type) {
            case 'new_message':
                handleNewMessage(message);
                break;
            case 'typing_indicator':
                handleTypingIndicator(message);
                break;
            case 'messages_read':
                handleMessagesRead(message);
                break;
            case 'user_joined':
            case 'user_offline':
                handleUserPresence(message);
                break;
            case 'message_history':
                handleMessageHistory(message);
                break;
        }
    }

    const handleNewMessage = useCallback((message: WebSocketMessage) => {
        setState(prev => {
            const roomMessages = [...(prev.messages[message.roomId] || [])];
            const newMessage = message.message as ChatMessage;

            // Replace optimistic message if exists
            const optimisticIndex = roomMessages.findIndex(
                m => m.id === newMessage.metadata?.optimisticId
            );

            if (optimisticIndex > -1) {
                roomMessages[optimisticIndex] = newMessage;
            } else {
                roomMessages.unshift(newMessage);
            }

            return {
                ...prev,
                messages: {
                    ...prev.messages,
                    [message.roomId]: roomMessages
                }
            };
        });
    }, []);

    const handleTypingIndicator = useCallback((message: WebSocketMessage) => {
        const { roomId, userId, isTyping } = message;
        
        setState(prev => {
            const roomTypingUsers = [...(prev.typingUsers[roomId] || [])];
            const existingIndex = roomTypingUsers.findIndex(t => t.userId === userId);

            if (isTyping && existingIndex === -1) {
                roomTypingUsers.push({
                    userId,
                    roomId,
                    timestamp: new Date().toISOString()
                });
            } else if (!isTyping && existingIndex > -1) {
                roomTypingUsers.splice(existingIndex, 1);
            }

            return {
                ...prev,
                typingUsers: {
                    ...prev.typingUsers,
                    [roomId]: roomTypingUsers
                }
            };
        });
    }, []);

    const handleMessagesRead = useCallback((message: WebSocketMessage) => {
        const { roomId, userId, messageIds } = message;

        setState(prev => {
            const roomMessages = [...(prev.messages[roomId] || [])];
            const updatedMessages = roomMessages.map(msg => {
                if (messageIds.includes(msg.id)) {
                    return {
                        ...msg,
                        receipts: [
                            ...(msg.receipts || []),
                            {
                                messageId: msg.id,
                                userId,
                                readAt: new Date().toISOString()
                            }
                        ]
                    };
                }
                return msg;
            });

            return {
                ...prev,
                messages: {
                    ...prev.messages,
                    [roomId]: updatedMessages
                }
            };
        });
    }, []);

    const handleUserPresence = useCallback((message: WebSocketMessage) => {
        const { userId, type } = message;

        setState(prev => {
            const onlineUsers = new Set(prev.onlineUsers);
            if (type === 'user_joined') {
                onlineUsers.add(userId);
            } else {
                onlineUsers.delete(userId);
            }

            return {
                ...prev,
                onlineUsers
            };
        });
    }, []);

    const handleMessageHistory = useCallback((message: WebSocketMessage) => {
        const { roomId, messages } = message;

        setState(prev => ({
            ...prev,
            messages: {
                ...prev.messages,
                [roomId]: [...(prev.messages[roomId] || []), ...messages]
            }
        }));
    }, []);

    const joinRoom = useCallback((roomId: string) => {
        send({
            type: 'join_room',
            roomId
        });

        send({
            type: 'get_history',
            roomId
        });
    }, [send]);

    const leaveRoom = useCallback((roomId: string) => {
        send({
            type: 'leave_room',
            roomId
        });

        setState(prev => {
            const { [roomId]: _, ...remainingMessages } = prev.messages;
            return {
                ...prev,
                messages: remainingMessages
            };
        });
    }, [send]);

    const sendMessage = useCallback((
        roomId: string,
        content: string,
        options: SendMessageOptions = {}
    ) => {
        const optimisticId = uuidv4();
        const optimisticMessage: ChatMessage = {
            id: optimisticId,
            roomId,
            userId,
            content,
            contentType: options.contentType || 'text',
            metadata: {
                ...options.metadata,
                optimisticId
            },
            parentId: options.parentId,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            status: 'sending'
        };

        setState(prev => ({
            ...prev,
            messages: {
                ...prev.messages,
                [roomId]: [optimisticMessage, ...(prev.messages[roomId] || [])]
            }
        }));

        send({
            type: 'send_message',
            roomId,
            content,
            contentType: options.contentType,
            metadata: options.metadata,
            parentId: options.parentId
        });
    }, [send, userId]);

    const setTyping = useCallback((roomId: string, isTyping: boolean) => {
        send({
            type: 'typing',
            roomId,
            isTyping
        });

        if (isTyping) {
            if (typingTimeouts.current[roomId]) {
                clearTimeout(typingTimeouts.current[roomId]);
            }

            typingTimeouts.current[roomId] = setTimeout(() => {
                send({
                    type: 'typing',
                    roomId,
                    isTyping: false
                });
            }, TYPING_TIMEOUT);
        }
    }, [send]);

    const markAsRead = useCallback((roomId: string, messageIds: string[]) => {
        send({
            type: 'mark_read',
            roomId,
            messageIds
        });
    }, [send]);

    const loadMoreMessages = useCallback((roomId: string, beforeId?: string) => {
        send({
            type: 'get_history',
            roomId,
            beforeId
        });
    }, [send]);

    useEffect(() => {
        return () => {
            Object.values(typingTimeouts.current).forEach(clearTimeout);
        };
    }, []);

    return {
        ...state,
        joinRoom,
        leaveRoom,
        sendMessage,
        setTyping,
        markAsRead,
        loadMoreMessages
    };
}