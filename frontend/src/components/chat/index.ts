export { ChatInterface } from './ChatInterface';
export { ChatRoomList } from './ChatRoomList';
export { MessageThread } from './MessageThread';
export { MessageInput } from './MessageInput';
export {
  PresenceIndicator,
  OnlineUsersList,
  ReadReceipts,
  UserStatus,
  usePresenceManager
} from './PresenceIndicator';
export { ChatErrorBoundary } from './ChatErrorBoundary';
export {
  ChatRoomListSkeleton,
  MessageThreadSkeleton,
  MessageInputSkeleton,
  ConnectionSpinner,
  ReconnectingIndicator,
  TypingIndicator,
  LoadMoreButton,
  ChatLoadingSkeleton
} from './LoadingStates';

// Re-export types for convenience
export type {
  ChatState,
  ChatRoom,
  Message,
  User,
  Reaction,
  ReadReceipt,
  TypingIndicator,
  MessageType,
  MilestoneCardData,
  WebSocketEvents
} from '@/types/chat';