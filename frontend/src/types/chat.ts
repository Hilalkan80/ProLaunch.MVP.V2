export type ChatRoomType = 'direct' | 'group' | 'support' | 'broadcast';
export type ChatParticipantRole = 'admin' | 'moderator' | 'member';
export type ChatMessageType = 'text' | 'image' | 'file' | 'system';
export type UserStatus = 'online' | 'offline' | 'away';

export interface User {
    id: string;
    name: string;
    avatar?: string;
    status: UserStatus;
    lastSeen?: string;
}

export interface ChatRoom {
    id: string;
    tenantId: string;
    type: ChatRoomType;
    name?: string;
    createdAt: string;
    updatedAt: string;
    metadata: Record<string, any>;
    participants: ChatRoomParticipant[];
    unreadCount?: number;
    lastMessage?: ChatMessage;
}

export interface ChatRoomParticipant {
    id: string;
    roomId: string;
    userId: string;
    role: ChatParticipantRole;
    joinedAt: string;
    lastReadAt: string;
    isMuted: boolean;
    settings: Record<string, any>;
    user?: User;
}

export interface ChatMessage {
    id: string;
    roomId: string;
    userId: string;
    content: string;
    contentType: ChatMessageType;
    metadata: Record<string, any>;
    parentId?: string;
    createdAt: string;
    updatedAt: string;
    deletedAt?: string;
    user?: User;
    reactions?: ChatMessageReaction[];
    receipts?: ChatMessageReceipt[];
    parent?: ChatMessage;
    replies?: ChatMessage[];
    status?: 'sending' | 'sent' | 'delivered' | 'read' | 'failed';
}

export interface ChatMessageReaction {
    id: string;
    messageId: string;
    userId: string;
    emoji: string;
    createdAt: string;
    user?: User;
}

export interface ChatMessageReceipt {
    id: string;
    messageId: string;
    userId: string;
    receivedAt: string;
    readAt?: string;
    user?: User;
}

export interface TypingIndicator {
    userId: string;
    roomId: string;
    timestamp: string;
    user?: User;
}

export interface WebSocketMessage {
    type: WebSocketMessageType;
    roomId: string;
    [key: string]: any;
}

export type WebSocketMessageType =
    | 'join_room'
    | 'leave_room'
    | 'send_message'
    | 'typing'
    | 'mark_read'
    | 'get_history'
    | 'user_joined'
    | 'user_left'
    | 'new_message'
    | 'typing_indicator'
    | 'messages_read'
    | 'user_offline'
    | 'message_history'
    | 'error';

export interface ChatState {
    activeRoom?: ChatRoom;
    rooms: ChatRoom[];
    messages: Record<string, ChatMessage[]>;
    typingUsers: Record<string, TypingIndicator[]>;
    onlineUsers: Set<string>;
    isConnected: boolean;
    error?: Error;
}

export interface ChatContextValue extends ChatState {
    connect: () => Promise<void>;
    disconnect: () => void;
    joinRoom: (roomId: string) => Promise<void>;
    leaveRoom: (roomId: string) => Promise<void>;
    sendMessage: (roomId: string, content: string, options?: SendMessageOptions) => Promise<void>;
    markAsRead: (roomId: string, messageIds: string[]) => Promise<void>;
    setTyping: (roomId: string, isTyping: boolean) => Promise<void>;
    loadMoreMessages: (roomId: string, beforeId?: string) => Promise<void>;
    addReaction: (messageId: string, emoji: string) => Promise<void>;
    removeReaction: (messageId: string, emoji: string) => Promise<void>;
}

export interface SendMessageOptions {
    contentType?: ChatMessageType;
    metadata?: Record<string, any>;
    parentId?: string;
    optimisticId?: string;
}

export interface ChatUIConfig {
    theme?: {
        primaryColor?: string;
        secondaryColor?: string;
        backgroundColor?: string;
        textColor?: string;
    };
    features?: {
        reactions?: boolean;
        typing?: boolean;
        receipts?: boolean;
        threading?: boolean;
        attachments?: boolean;
        voiceMessages?: boolean;
    };
    layout?: {
        showSidebar?: boolean;
        sidebarWidth?: number;
        messageWidth?: number;
        inputHeight?: number;
    };
}