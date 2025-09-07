import {
    Box,
    Flex,
    IconButton,
    Input,
    useColorModeValue
} from '@chakra-ui/react';
import { useState, useRef, useEffect } from 'react';
import { AttachmentIcon, SmileIcon } from '@chakra-ui/icons';
import EmojiPicker from './EmojiPicker';

interface MessageInputProps {
    onSendMessage: (content: string) => void;
    onTyping: (isTyping: boolean) => void;
}

export default function MessageInput({ onSendMessage, onTyping }: MessageInputProps) {
    const [content, setContent] = useState('');
    const [showEmojiPicker, setShowEmojiPicker] = useState(false);
    const [isTyping, setIsTyping] = useState(false);
    const typingTimeoutRef = useRef<NodeJS.Timeout>();
    const bgColor = useColorModeValue('white', 'gray.800');
    const inputBgColor = useColorModeValue('gray.100', 'gray.700');

    const handleSend = () => {
        const trimmedContent = content.trim();
        if (trimmedContent) {
            onSendMessage(trimmedContent);
            setContent('');
            setIsTyping(false);
            onTyping(false);
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setContent(e.target.value);

        if (!isTyping) {
            setIsTyping(true);
            onTyping(true);
        }

        if (typingTimeoutRef.current) {
            clearTimeout(typingTimeoutRef.current);
        }

        typingTimeoutRef.current = setTimeout(() => {
            setIsTyping(false);
            onTyping(false);
        }, 3000);
    };

    const handleEmojiSelect = (emoji: string) => {
        setContent(prev => prev + emoji);
        setShowEmojiPicker(false);
    };

    useEffect(() => {
        return () => {
            if (typingTimeoutRef.current) {
                clearTimeout(typingTimeoutRef.current);
            }
        };
    }, []);

    return (
        <Box position="relative">
            {showEmojiPicker && (
                <Box
                    position="absolute"
                    bottom="100%"
                    right={0}
                    mb={2}
                >
                    <EmojiPicker onSelect={handleEmojiSelect} />
                </Box>
            )}
            
            <Flex gap={2}>
                <IconButton
                    icon={<AttachmentIcon />}
                    aria-label="Attach file"
                    variant="ghost"
                    onClick={() => {}}
                />
                <IconButton
                    icon={<SmileIcon />}
                    aria-label="Add emoji"
                    variant="ghost"
                    onClick={() => setShowEmojiPicker(!showEmojiPicker)}
                />
                <Input
                    flex={1}
                    value={content}
                    onChange={handleInputChange}
                    onKeyPress={handleKeyPress}
                    placeholder="Type a message..."
                    bg={inputBgColor}
                    _focus={{
                        bg: inputBgColor,
                        borderColor: 'blue.500'
                    }}
                />
            </Flex>
        </Box>
    );
}