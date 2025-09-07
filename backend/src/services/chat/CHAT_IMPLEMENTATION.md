# WebSocket Chat System Implementation

## Overview

This implementation provides a comprehensive real-time chat system with WebSocket support, Redis pub/sub for message broadcasting, and PostgreSQL for message persistence. The system is designed for multi-tenant architecture with support for multiple room types, typing indicators, and rich message content.

## Architecture

### Components

1. **WebSocket Manager** (`websocket_manager.py`)
   - Manages WebSocket connections for multiple users
   - Implements Redis pub/sub for real-time message broadcasting
   - Handles room subscriptions and user presence
   - Manages typing indicators with automatic cleanup

2. **Chat Service** (`chat_service.py`)
   - Business logic layer for chat operations
   - Room and participant management
   - Message persistence and retrieval
   - Search and analytics functionality

3. **Database Models** (`models/chat.py`)
   - `ChatRoom`: Multi-tenant chat rooms with various types
   - `ChatRoomParticipant`: User membership and roles
   - `ChatMessage`: Message storage with rich content support
   - `ChatMessageReceipt`: Read/delivery receipt tracking
   - `ChatTypingIndicator`: Real-time typing status

4. **WebSocket Endpoints** (`api/v1/websocket_chat.py`)
   - Main WebSocket endpoint for real-time communication
   - Handles authentication via JWT tokens
   - Message routing and room management

## Features

### Room Types
- **Direct**: One-on-one conversations
- **Group**: Multi-user chat rooms
- **Support**: Customer support channels
- **Broadcast**: Admin announcements

### Message Types
- **Text**: Standard text messages
- **Image**: Image attachments
- **File**: File attachments
- **System**: System notifications
- **Typing**: Typing indicators

### Real-time Features
- Live message delivery via WebSocket
- Typing indicators with 10-second timeout
- Online/offline user presence
- Read receipts and delivery status
- Message reactions with emoji

### Advanced Features
- Message threading (reply to messages)
- Message editing with history
- Soft delete with admin controls
- User mentions with notifications
- Unread message counts
- Room participant roles (admin, moderator, member)
- Mute and ban functionality

## API Usage

### WebSocket Connection

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/chat?token=YOUR_JWT_TOKEN');

// Connection established
ws.onopen = () => {
    console.log('Connected to chat');
};

// Handle incoming messages
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleMessage(data);
};
```

### Message Types

#### Join Room
```json
{
    "type": "join_room",
    "room_id": "uuid-here"
}
```

#### Send Message
```json
{
    "type": "send_message",
    "room_id": "uuid-here",
    "content": "Hello, world!",
    "message_type": "text",
    "attachments": [],
    "mentions": ["user-id"]
}
```

#### Start Typing
```json
{
    "type": "typing_start",
    "room_id": "uuid-here"
}
```

#### Mark Messages Read
```json
{
    "type": "mark_read",
    "room_id": "uuid-here",
    "message_ids": ["msg-id-1", "msg-id-2"]
}
```

#### Create Room
```json
{
    "type": "create_room",
    "name": "Project Discussion",
    "room_type": "group",
    "participants": ["user-id-1", "user-id-2"],
    "description": "Discussion about the project",
    "is_private": false
}
```

## Database Migration

Run the migration to create chat tables:

```bash
# Run migration
alembic upgrade head

# Or run specific migration
alembic upgrade 002_add_chat_tables
```

## Configuration

### Environment Variables

```bash
# Redis configuration
REDIS_URL=redis://localhost:6379

# Database configuration
DATABASE_URL=postgresql+asyncpg://user:password@localhost/prolaunch

# JWT Secret for authentication
JWT_SECRET_KEY=your-secret-key-here
```

### Redis Channels

The system uses the following Redis channels:

- `chat:global` - Global announcements
- `room:{room_id}` - Room-specific messages
- `user:{user_id}` - User-specific notifications
- `typing:{room_id}` - Typing indicators

## Performance Considerations

1. **Connection Pooling**: Database connections are pooled with configurable limits
2. **Message Caching**: Recent messages cached in Redis for 1 hour
3. **Pagination**: Message history retrieved with pagination (max 100 messages)
4. **Indexing**: Optimized database indexes for common queries
5. **Cleanup Tasks**: Automatic cleanup of expired typing indicators

## Security

1. **Authentication**: JWT token required for WebSocket connections
2. **Authorization**: Role-based permissions (admin, moderator, member)
3. **Rate Limiting**: Connection and message rate limits
4. **Input Validation**: All inputs validated before processing
5. **Soft Delete**: Messages soft-deleted, preserving audit trail

## Monitoring

### Health Check Endpoint

```bash
GET /api/v1/chat/health

Response:
{
    "status": "healthy",
    "active_connections": 42,
    "redis_connected": true
}
```

### Metrics Available

- Active WebSocket connections
- Messages per room
- User activity (last 24 hours)
- Room participant counts
- Unread message counts

## Error Handling

The system handles various error scenarios:

1. **Connection Errors**: Automatic reconnection with exponential backoff
2. **Authentication Failures**: Clear error messages with proper status codes
3. **Permission Denied**: Role-based access control with detailed errors
4. **Rate Limiting**: Configurable limits with retry headers
5. **Database Failures**: Graceful degradation with error logging

## Testing

### Unit Tests
```python
# Test message sending
async def test_send_message():
    service = ChatService(db, redis)
    message = await service.send_message(
        room_id="test-room",
        sender_id="test-user",
        content="Test message"
    )
    assert message.content == "Test message"
```

### Integration Tests
```python
# Test WebSocket connection
async def test_websocket_connection():
    async with websocket_connect("/ws/chat?token=valid_token") as ws:
        data = await ws.receive_json()
        assert data["type"] == "connection"
        assert data["status"] == "connected"
```

## Scaling Considerations

1. **Horizontal Scaling**: Multiple backend instances with Redis pub/sub
2. **Load Balancing**: WebSocket sticky sessions required
3. **Database Sharding**: Partition by tenant_id for multi-tenant scaling
4. **Redis Cluster**: Support for Redis cluster mode
5. **Message Archival**: Old messages can be archived to cold storage

## Future Enhancements

- [ ] Voice and video call integration
- [ ] End-to-end encryption for sensitive chats
- [ ] Message translation
- [ ] AI-powered message suggestions
- [ ] Advanced search with full-text indexing
- [ ] Message export functionality
- [ ] Chat analytics dashboard