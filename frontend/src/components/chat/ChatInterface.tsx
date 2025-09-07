import { Box, Flex, useBreakpointValue } from '@chakra-ui/react';
import { useState } from 'react';
import { ChatRoom } from '../../types/chat';
import ChatRoomList from './ChatRoomList';
import MessageThread from './MessageThread';
import { useChat } from '../../hooks/useChat';

interface ChatInterfaceProps {
    tenantId: string;
    userId: string;
    initialRooms?: ChatRoom[];
    config?: {
        sidebarWidth?: number;
        messageWidth?: number;
        showSidebar?: boolean;
    };
}

export default function ChatInterface({
    tenantId,
    userId,
    initialRooms = [],
    config = {}
}: ChatInterfaceProps) {
    const {
        sidebarWidth = 300,
        messageWidth = 800,
        showSidebar = true
    } = config;

    const [activeRoom, setActiveRoom] = useState<ChatRoom | null>(null);
    const isMobile = useBreakpointValue({ base: true, md: false });
    const [showMobileSidebar, setShowMobileSidebar] = useState(true);

    const {
        rooms,
        messages,
        typingUsers,
        onlineUsers,
        isConnected,
        joinRoom,
        leaveRoom,
        sendMessage,
        setTyping,
        markAsRead,
        loadMoreMessages
    } = useChat(tenantId, userId);

    const handleRoomSelect = (room: ChatRoom) => {
        if (activeRoom?.id !== room.id) {
            if (activeRoom) {
                leaveRoom(activeRoom.id);
            }
            setActiveRoom(room);
            joinRoom(room.id);
            if (isMobile) {
                setShowMobileSidebar(false);
            }
        }
    };

    const handleBackToRooms = () => {
        setShowMobileSidebar(true);
    };

    return (
        <Flex
            h="100%"
            maxH="100vh"
            overflow="hidden"
            position="relative"
        >
            {/* Room List Sidebar */}
            {showSidebar && ((!isMobile || showMobileSidebar)) && (
                <Box
                    w={isMobile ? "100%" : `${sidebarWidth}px`}
                    borderRightWidth="1px"
                    h="100%"
                    bg="white"
                    position={isMobile ? "absolute" : "relative"}
                    zIndex={2}
                    left={0}
                    top={0}
                >
                    <ChatRoomList
                        rooms={rooms}
                        activeRoom={activeRoom}
                        onRoomSelect={handleRoomSelect}
                        onlineUsers={onlineUsers}
                    />
                </Box>
            )}

            {/* Message Thread */}
            <Box
                flex={1}
                maxW={isMobile ? "100%" : `${messageWidth}px`}
                h="100%"
                position="relative"
                display={isMobile && showMobileSidebar ? "none" : "block"}
            >
                {activeRoom ? (
                    <MessageThread
                        room={activeRoom}
                        messages={messages[activeRoom.id] || []}
                        typingUsers={typingUsers[activeRoom.id] || []}
                        onSendMessage={(content, options) => 
                            sendMessage(activeRoom.id, content, options)
                        }
                        onTyping={(isTyping) => 
                            setTyping(activeRoom.id, isTyping)
                        }
                        onLoadMore={() => 
                            loadMoreMessages(activeRoom.id)
                        }
                        onMarkRead={(messageIds) => 
                            markAsRead(activeRoom.id, messageIds)
                        }
                        onBack={isMobile ? handleBackToRooms : undefined}
                        userId={userId}
                    />
                ) : (
                    <Flex
                        h="100%"
                        align="center"
                        justify="center"
                        p={4}
                        bg="gray.50"
                    >
                        Select a chat room to start messaging
                    </Flex>
                )}
            </Box>
        </Flex>
    );
}