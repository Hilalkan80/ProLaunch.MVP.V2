# ProLaunch Chat UI Components

A complete, production-ready chat interface built with Next.js 14, React 18, TypeScript, and Chakra UI, featuring real-time messaging via WebSocket integration.

## Features

### Core Functionality
- ✅ **Real-time messaging** via WebSocket with automatic reconnection
- ✅ **Message threading** and replies
- ✅ **Typing indicators** with timeout management
- ✅ **Read receipts** and message status tracking
- ✅ **User presence indicators** (online/offline status)
- ✅ **Emoji reactions** with customizable picker
- ✅ **File attachments** support (UI ready)
- ✅ **Message pagination** with "load more" functionality
- ✅ **Milestone cards** for AI-generated content

### Mobile Responsive Design
- ✅ **Mobile-first approach** with breakpoint optimization
- ✅ **Touch-optimized interactions** (44px minimum touch targets)
- ✅ **Drawer navigation** for mobile devices
- ✅ **Responsive layouts** across all screen sizes
- ✅ **Progressive enhancement** for better performance

### User Experience
- ✅ **Loading states** and skeleton screens
- ✅ **Error boundaries** with graceful fallbacks
- ✅ **Connection status** indicators
- ✅ **Automatic reconnection** with exponential backoff
- ✅ **Optimistic UI updates** for smooth interactions
- ✅ **Keyboard shortcuts** (Enter to send, Shift+Enter for new line)

### Accessibility
- ✅ **WCAG AA compliance** with proper color contrast
- ✅ **Keyboard navigation** support
- ✅ **Screen reader compatibility** with ARIA labels
- ✅ **Focus management** and logical tab order

## Architecture

### Component Structure
```
src/components/chat/
├── ChatInterface.tsx          # Main chat container
├── ChatRoomList.tsx          # Room sidebar with presence
├── MessageThread.tsx         # Message display with threading
├── MessageInput.tsx          # Input with emoji picker
├── PresenceIndicator.tsx     # User status components
├── ChatErrorBoundary.tsx     # Error handling
├── LoadingStates.tsx         # Skeleton screens
└── index.ts                  # Export barrel
```

### Hooks
```
src/hooks/
├── useWebSocket.ts           # WebSocket connection management
├── useChat.ts                # Chat state and operations
└── index.ts                  # Export barrel
```

### Types
```
src/types/
└── chat.ts                   # Complete type definitions
```

## Usage

### Basic Implementation

```tsx
import React from 'react';
import { ChatInterface } from '@/components/chat';
import type { User } from '@/types/chat';

const currentUser: User = {
  id: 'user-123',
  username: 'Sarah K.',
  avatar: 'https://example.com/avatar.jpg',
  isOnline: true,
  lastSeen: new Date()
};

export const ChatPage: React.FC = () => {
  return (
    <ChatInterface
      currentUser={currentUser}
      websocketUrl="ws://localhost:8000/ws"
      onRoomCreate={() => console.log('Create room')}
      onUserProfileClick={(user) => console.log('User clicked:', user)}
      onSettingsClick={() => console.log('Settings clicked')}
    />
  );
};
```

### With Error Boundary

```tsx
import React from 'react';
import { ChatInterface, ChatErrorBoundary } from '@/components/chat';

export const ChatPage: React.FC = () => {
  return (
    <ChatErrorBoundary
      onError={(error, errorInfo) => {
        console.error('Chat error:', error);
        // Send to error reporting service
      }}
    >
      <ChatInterface
        currentUser={currentUser}
        websocketUrl="ws://localhost:8000/ws"
      />
    </ChatErrorBoundary>
  );
};
```

### Individual Components

```tsx
import React from 'react';
import {
  ChatRoomList,
  MessageThread,
  MessageInput,
  PresenceIndicator
} from '@/components/chat';

// Use components individually for custom layouts
export const CustomChatLayout: React.FC = () => {
  return (
    <div className="custom-chat-layout">
      <ChatRoomList
        rooms={rooms}
        currentRoomId={currentRoomId}
        currentUser={currentUser}
        onRoomSelect={handleRoomSelect}
      />
      <MessageThread
        messages={messages}
        currentUser={currentUser}
        typingUsers={typingUsers}
      />
      <MessageInput
        onSendMessage={handleSendMessage}
        onTypingStart={handleTypingStart}
        onTypingStop={handleTypingStop}
      />
    </div>
  );
};
```

## WebSocket Events

The chat system uses a comprehensive set of WebSocket events for real-time communication:

### Client → Server Events
- `join_room` - Join a chat room
- `leave_room` - Leave a chat room
- `send_message` - Send a new message
- `typing_start` - Start typing indicator
- `typing_stop` - Stop typing indicator
- `mark_read` - Mark message as read
- `add_reaction` - Add emoji reaction
- `remove_reaction` - Remove emoji reaction

### Server → Client Events
- `message_received` - New message received
- `message_updated` - Message was edited
- `message_deleted` - Message was deleted
- `typing_indicator` - User typing status
- `user_joined` - User joined room
- `user_left` - User left room
- `user_status_changed` - Online/offline status
- `read_receipt` - Message read confirmation
- `reaction_added` - New reaction added
- `reaction_removed` - Reaction removed
- `room_updated` - Room information updated
- `error` - Error occurred

## Customization

### Theme Integration

The components are designed to work with Chakra UI's theme system:

```tsx
import { extendTheme } from '@chakra-ui/react';

const theme = extendTheme({
  colors: {
    brand: {
      500: '#1A8CFF', // ProLaunch primary blue
      // ... other brand colors
    }
  },
  components: {
    Button: {
      defaultProps: {
        colorScheme: 'brand',
      },
    },
  },
});
```

### Message Types

Support for different message types including milestone cards:

```tsx
import type { MessageType, MilestoneCardData } from '@/types/chat';

const milestoneMessage = {
  id: 'msg-123',
  type: MessageType.MILESTONE_CARD,
  content: JSON.stringify({
    title: 'M1: Unit Economics',
    description: 'Analyze costs and profit margins',
    progress: 75,
    status: 'in_progress'
  } as MilestoneCardData),
  // ... other message properties
};
```

### Emoji Customization

The emoji picker includes categorized emojis:

```tsx
const EMOJI_CATEGORIES = {
  recent: ['😀', '😂', '❤️', '👍'],
  people: ['😀', '😃', '😄', '😁'],
  nature: ['🐶', '🐱', '🐭', '🐹'],
  food: ['🍎', '🍊', '🍋', '🍌'],
  activity: ['⚽', '🏀', '🏈', '⚾'],
  objects: ['⌚', '📱', '📲', '💻'],
  symbols: ['❤️', '🧡', '💛', '💚']
};
```

## Performance Features

### Optimizations
- **Message virtualization** for large chat histories
- **Lazy loading** of message attachments
- **Debounced typing indicators** (1-second timeout)
- **Connection pooling** with automatic reconnection
- **Optimistic updates** for immediate UI feedback

### Caching
- **Local message cache** for offline viewing
- **Image caching** for avatars and attachments
- **Presence state management** with automatic cleanup

## Mobile Responsive Features

### Breakpoints
- **Mobile**: 320-767px (single column, stacked elements)
- **Tablet**: 768-1023px (two column layouts)
- **Desktop**: 1024px+ (multi-column layouts)

### Mobile-Specific Features
- **Drawer navigation** for room and user lists
- **Touch-optimized** button sizes (minimum 44px)
- **Swipe gestures** for mobile interactions
- **Voice message support** (UI ready)

## Testing

### Component Tests
```bash
# Run unit tests for chat components
npm run test:unit src/components/chat

# Run integration tests
npm run test:integration

# Run security tests
npm run test:security
```

### Example Test
```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { MessageInput } from '@/components/chat';

test('sends message on Enter key', () => {
  const onSendMessage = jest.fn();
  render(
    <MessageInput
      onSendMessage={onSendMessage}
      onTypingStart={() => {}}
      onTypingStop={() => {}}
    />
  );
  
  const input = screen.getByPlaceholderText('Type a message...');
  fireEvent.change(input, { target: { value: 'Test message' } });
  fireEvent.keyDown(input, { key: 'Enter' });
  
  expect(onSendMessage).toHaveBeenCalledWith('Test message');
});
```

## Environment Variables

```env
# WebSocket connection URL
NEXT_PUBLIC_WEBSOCKET_URL=ws://localhost:8000/ws

# Chat API endpoints
NEXT_PUBLIC_CHAT_API_URL=http://localhost:8000/api/chat

# File upload settings
NEXT_PUBLIC_MAX_FILE_SIZE=10485760  # 10MB
NEXT_PUBLIC_ALLOWED_FILE_TYPES=image/*,application/pdf
```

## Browser Support

- **Chrome**: 90+ ✅
- **Firefox**: 88+ ✅
- **Safari**: 14+ ✅
- **Edge**: 90+ ✅
- **Mobile Safari**: 14+ ✅
- **Chrome Mobile**: 90+ ✅

## Contributing

When adding new features to the chat system:

1. **Follow TypeScript** strict mode requirements
2. **Add comprehensive tests** for new components
3. **Update type definitions** in `src/types/chat.ts`
4. **Maintain accessibility** standards (WCAG AA)
5. **Test mobile responsiveness** on actual devices
6. **Document new WebSocket events** in this README

## Troubleshooting

### Common Issues

**WebSocket connection fails:**
```tsx
// Check network connectivity and URL
const { isConnected, connectionError } = useWebSocket({
  url: websocketUrl,
  autoConnect: true
});

if (connectionError) {
  console.error('Connection failed:', connectionError);
}
```

**Messages not updating:**
```tsx
// Ensure proper event handling
useEffect(() => {
  const unsubscribe = on('message_received', (message) => {
    console.log('New message:', message);
    // Handle message update
  });
  
  return unsubscribe;
}, [on]);
```

**Mobile layout issues:**
```tsx
// Use Chakra UI breakpoints
const isMobile = useBreakpointValue({ base: true, md: false });

return (
  <Box
    display={{ base: 'block', md: 'flex' }}
    height="100vh"
  >
    {/* Responsive layout */}
  </Box>
);
```

## License

This chat implementation is part of the ProLaunch.AI project and follows the project's licensing terms.