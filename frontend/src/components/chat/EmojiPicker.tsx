import {
    Box,
    SimpleGrid,
    Tab,
    TabList,
    TabPanel,
    TabPanels,
    Tabs,
    useColorModeValue
} from '@chakra-ui/react';

interface EmojiPickerProps {
    onSelect: (emoji: string) => void;
}

const emojiCategories = {
    'Smileys': ['😀', '😃', '😄', '😁', '😅', '😂', '🤣', '😊', '😇', '🙂', '🙃', '😉'],
    'Reactions': ['👍', '👎', '❤️', '🎉', '👋', '👏', '🙌', '👊', '✊', '🤝', '🤔', '👀'],
    'Objects': ['💼', '📱', '💻', '⌨️', '🖥️', '🖨️', '📄', '📝', '✏️', '📌', '⭐', '📊'],
    'Symbols': ['✅', '❌', '❗', '❓', '⚠️', '🔔', '🔊', '🔇', '➡️', '⬅️', '⬆️', '⬇️']
};

export default function EmojiPicker({ onSelect }: EmojiPickerProps) {
    const bgColor = useColorModeValue('white', 'gray.800');
    const borderColor = useColorModeValue('gray.200', 'gray.700');

    return (
        <Box
            bg={bgColor}
            boxShadow="lg"
            borderRadius="md"
            borderWidth="1px"
            borderColor={borderColor}
            w="300px"
        >
            <Tabs>
                <TabList>
                    {Object.keys(emojiCategories).map(category => (
                        <Tab key={category} fontSize="sm">
                            {category}
                        </Tab>
                    ))}
                </TabList>

                <TabPanels>
                    {Object.entries(emojiCategories).map(([category, emojis]) => (
                        <TabPanel key={category} p={2}>
                            <SimpleGrid columns={8} spacing={1}>
                                {emojis.map(emoji => (
                                    <Box
                                        key={emoji}
                                        p={1}
                                        cursor="pointer"
                                        borderRadius="md"
                                        textAlign="center"
                                        fontSize="xl"
                                        _hover={{ bg: useColorModeValue('gray.100', 'gray.700') }}
                                        onClick={() => onSelect(emoji)}
                                    >
                                        {emoji}
                                    </Box>
                                ))}
                            </SimpleGrid>
                        </TabPanel>
                    ))}
                </TabPanels>
            </Tabs>
        </Box>
    );
}