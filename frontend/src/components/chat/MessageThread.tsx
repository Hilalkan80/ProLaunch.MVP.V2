import {
    Box,
    VStack,
    IconButton,
    Flex,
    Text,
    useColorModeValue,
    useTheme
} from '@chakra-ui/react';
import { useEffect, useRef, useState } from 'react';
import { ChatMessage, ChatRoom, TypingIndicator } from '../../types/chat';
import MessageInput from './MessageInput';
import { ArrowBackIcon } from '@chakra-ui/icons';
import { formatDistanceToNow } from 'date-fns';
import { useInView } from 'react-intersection-observer';

interface MessageThreadProps {
    room: ChatRoom;
    messages: ChatMessage[];
    typingUsers: TypingIndicator[];
    onSendMessage: (content: string, options: any) => void;
    onTyping: (isTyping: boolean) => void;
    onLoadMore: () => void;
    onMarkRead: (messageIds: string[]) => void;
    onBack?: () => void;
    userId: string;
}

export default function MessageThread({
    room,
    messages,
    typingUsers,
    onSendMessage,
    onTyping,
    onLoadMore,
    onMarkRead,
    onBack,
    userId
}: MessageThreadProps) {
    const theme = useTheme();
    const [replyTo, setReplyTo] = useState<ChatMessage | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const [loadMoreRef, inView] = useInView({
        threshold: 0.5,
        triggerOnce: true
    });

    const bgColor = useColorModeValue('white', 'gray.800');
    const borderColor = useColorModeValue('gray.200', 'gray.700');

    useEffect(() => {
        if (inView) {
            onLoadMore();
        }
    }, [inView, onLoadMore]);

    useEffect(() => {
        const unreadMessages = messages
            .filter(msg => 
                msg.userId !== userId && 
                !msg.receipts?.some(r => r.userId === userId && r.readAt)
            )
            .map(msg => msg.id);

        if (unreadMessages.length > 0) {
            onMarkRead(unreadMessages);
        }
    }, [messages, userId, onMarkRead]);

    useEffect(() => {
        if (messagesEndRef.current) {
            messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages.length]);

    const renderMessage = (message: ChatMessage) => {
        const isOwnMessage = message.userId === userId;
        const time = formatDistanceToNow(new Date(message.createdAt), { addSuffix: true });

        return (
            <Box
                key={message.id}
                maxW="70%"
                alignSelf={isOwnMessage ? 'flex-end' : 'flex-start'}
                mb={4}
            >
                {message.parentId && messages.find(m => m.id === message.parentId) && (
                    <Box
                        p={2}
                        mb={2}
                        borderRadius="md"
                        bg={useColorModeValue('gray.100', 'gray.700')}
                        fontSize="sm"
                    >
                        <Text fontWeight="bold">
                            {messages.find(m => m.id === message.parentId)?.user?.name}
                        </Text>
                        <Text>
                            {messages.find(m => m.id === message.parentId)?.content}
                        </Text>
                    </Box>
                )}

                <Box
                    bg={isOwnMessage ? theme.colors.blue[500] : useColorModeValue('gray.100', 'gray.700')}
                    color={isOwnMessage ? 'white' : undefined}
                    p={3}
                    borderRadius="lg"
                    position="relative"
                >
                    {!isOwnMessage && (
                        <Text fontSize="sm" fontWeight="bold" mb={1}>
                            {message.user?.name}
                        </Text>
                    )}

                    <Text>{message.content}</Text>

                    <Flex 
                        mt={2}
                        fontSize="xs"
                        color={isOwnMessage ? 'whiteAlpha.800' : 'gray.500'}
                        align="center"
                        justify="space-between"
                    >
                        <Text>{time}</Text>
                        
                        {isOwnMessage && (
                            <Text>
                                {message.status === 'sending' && 'Sending...'}
                                {message.status === 'sent' && 'Sent'}
                                {message.status === 'delivered' && 'Delivered'}
                                {message.status === 'read' && 'Read'}
                                {message.status === 'failed' && 'Failed'}
                            </Text>
                        )}
                    </Flex>

                    {message.reactions && message.reactions.length > 0 && (
                        <Flex mt={2} flexWrap="wrap" gap={1}>
                            {message.reactions.map(reaction => (
                                <Box
                                    key={`${reaction.userId}-${reaction.emoji}`}
                                    bg={useColorModeValue('gray.100', 'gray.700')}
                                    px={2}
                                    py={1}
                                    borderRadius="full"
                                    fontSize="sm"
                                >
                                    {reaction.emoji}
                                </Box>
                            ))}
                        </Flex>
                    )}
                </Box>
            </Box>
        );
    };

    return (
        <Flex
            direction="column"
            h="100%"
            bg={bgColor}
            borderLeftWidth="1px"
            borderColor={borderColor}
        >
            {/* Header */}
            <Flex
                p={4}
                borderBottomWidth="1px"
                borderColor={borderColor}
                align="center"
            >
                {onBack && (
                    <IconButton
                        icon={<ArrowBackIcon />}
                        aria-label="Back to rooms"
                        variant="ghost"
                        mr={2}
                        onClick={onBack}
                    />
                )}
                <Box>
                    <Text fontWeight="bold">{room.name}</Text>
                    <Text fontSize="sm" color="gray.500">
                        {room.participants.length} participants
                    </Text>
                </Box>
            </Flex>

            {/* Message List */}
            <VStack
                flex={1}
                p={4}
                spacing={4}
                overflowY="auto"
                align="stretch"
            >
                <div ref={loadMoreRef} />
                {messages.map(renderMessage)}
                
                {typingUsers.length > 0 && (
                    <Box
                        p={3}
                        borderRadius="lg"
                        bg={useColorModeValue('gray.100', 'gray.700')}
                        alignSelf="flex-start"
                    >
                        <Text fontSize="sm" color="gray.500">
                            {typingUsers
                                .map(t => t.user?.name)
                                .filter(Boolean)
                                .join(', ')}{' '}
                            {typingUsers.length === 1 ? 'is' : 'are'} typing...
                        </Text>
                    </Box>
                )}
                <div ref={messagesEndRef} />
            </VStack>

            {/* Message Input */}
            <Box p={4} borderTopWidth="1px" borderColor={borderColor}>
                {replyTo && (
                    <Box
                        p={2}
                        mb={2}
                        borderRadius="md"
                        bg={useColorModeValue('gray.100', 'gray.700')}
                        position="relative"
                    >
                        <IconButton
                            icon={<CloseIcon />}
                            aria-label="Cancel reply"
                            size="sm"
                            position="absolute"
                            right={2}
                            top={2}
                            onClick={() => setReplyTo(null)}
                        />
                        <Text fontSize="sm" fontWeight="bold">
                            Replying to {replyTo.user?.name}
                        </Text>
                        <Text fontSize="sm" noOfLines={1}>
                            {replyTo.content}
                        </Text>
                    </Box>
                )}
                <MessageInput
                    onSendMessage={(content) => {
                        onSendMessage(content, {
                            parentId: replyTo?.id,
                        });
                        setReplyTo(null);
                    }}
                    onTyping={onTyping}
                />
            </Box>
        </Flex>
    );
}