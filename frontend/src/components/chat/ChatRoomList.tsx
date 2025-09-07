import {
    VStack,
    Box,
    Text,
    Avatar,
    Flex,
    Input,
    useColorModeValue,
    Badge
} from '@chakra-ui/react';
import { SearchIcon } from '@chakra-ui/icons';
import { ChatRoom } from '../../types/chat';
import { formatDistanceToNow } from 'date-fns';
import { useState } from 'react';

interface ChatRoomListProps {
    rooms: ChatRoom[];
    activeRoom: ChatRoom | null;
    onRoomSelect: (room: ChatRoom) => void;
    onlineUsers: Set<string>;
}

export default function ChatRoomList({
    rooms,
    activeRoom,
    onRoomSelect,
    onlineUsers
}: ChatRoomListProps) {
    const [searchQuery, setSearchQuery] = useState('');
    const bgColor = useColorModeValue('white', 'gray.800');
    const hoverBgColor = useColorModeValue('gray.100', 'gray.700');
    const activeBgColor = useColorModeValue('blue.50', 'gray.700');
    const textColor = useColorModeValue('gray.800', 'white');
    const mutedColor = useColorModeValue('gray.500', 'gray.400');

    const filteredRooms = rooms.filter(room => 
        room.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        room.participants.some(p => 
            p.user?.name.toLowerCase().includes(searchQuery.toLowerCase())
        )
    );

    const getDisplayName = (room: ChatRoom): string => {
        if (room.name) return room.name;

        if (room.type === 'direct') {
            const otherParticipant = room.participants.find(p => 
                !onlineUsers.has(p.userId)
            );
            return otherParticipant?.user?.name || 'Unknown User';
        }

        return `Group (${room.participants.length} members)`;
    };

    const getRoomAvatar = (room: ChatRoom): string => {
        if (room.type === 'direct') {
            const otherParticipant = room.participants.find(p => 
                !onlineUsers.has(p.userId)
            );
            return otherParticipant?.user?.avatar || '';
        }
        return ''; // Return group avatar or default avatar
    };

    return (
        <Box h="100%" bg={bgColor}>
            <Box p={4} borderBottomWidth="1px">
                <Flex align="center" mb={4}>
                    <SearchIcon color={mutedColor} mr={2} />
                    <Input
                        placeholder="Search chats..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        variant="unstyled"
                        _placeholder={{ color: mutedColor }}
                    />
                </Flex>
            </Box>

            <VStack
                spacing={0}
                align="stretch"
                overflowY="auto"
                maxH="calc(100vh - 80px)"
            >
                {filteredRooms.map(room => {
                    const isActive = room.id === activeRoom?.id;
                    const displayName = getDisplayName(room);
                    const avatarSrc = getRoomAvatar(room);
                    const lastMessage = room.lastMessage;
                    const hasUnread = room.unreadCount && room.unreadCount > 0;

                    return (
                        <Box
                            key={room.id}
                            p={4}
                            cursor="pointer"
                            bg={isActive ? activeBgColor : undefined}
                            _hover={{ bg: isActive ? activeBgColor : hoverBgColor }}
                            onClick={() => onRoomSelect(room)}
                            position="relative"
                        >
                            <Flex align="center">
                                <Avatar
                                    size="sm"
                                    name={displayName}
                                    src={avatarSrc}
                                    mr={3}
                                />
                                <Box flex={1}>
                                    <Flex justify="space-between" align="center" mb={1}>
                                        <Text
                                            fontWeight={hasUnread ? "bold" : "normal"}
                                            color={textColor}
                                            noOfLines={1}
                                        >
                                            {displayName}
                                        </Text>
                                        {lastMessage && (
                                            <Text
                                                fontSize="xs"
                                                color={mutedColor}
                                            >
                                                {formatDistanceToNow(new Date(lastMessage.createdAt), {
                                                    addSuffix: true
                                                })}
                                            </Text>
                                        )}
                                    </Flex>
                                    <Flex align="center">
                                        <Text
                                            fontSize="sm"
                                            color={mutedColor}
                                            noOfLines={1}
                                            flex={1}
                                        >
                                            {lastMessage?.content || 'No messages yet'}
                                        </Text>
                                        {hasUnread && (
                                            <Badge
                                                ml={2}
                                                colorScheme="blue"
                                                borderRadius="full"
                                            >
                                                {room.unreadCount}
                                            </Badge>
                                        )}
                                    </Flex>
                                </Box>
                            </Flex>

                            {/* Online indicator for direct chats */}
                            {room.type === 'direct' && room.participants.some(p => onlineUsers.has(p.userId)) && (
                                <Box
                                    position="absolute"
                                    w={2}
                                    h={2}
                                    bg="green.500"
                                    borderRadius="full"
                                    bottom={4}
                                    left={10}
                                />
                            )}
                        </Box>
                    );
                })}
            </VStack>
        </Box>
    );
}