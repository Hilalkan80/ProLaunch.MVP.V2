import {
    Box,
    Flex,
    Skeleton,
    SkeletonCircle,
    useColorModeValue,
    VStack
} from '@chakra-ui/react';

interface LoadingStatesProps {
    type: 'room-list' | 'message-thread' | 'full';
}

export default function LoadingStates({ type }: LoadingStatesProps) {
    const bgColor = useColorModeValue('white', 'gray.800');
    const borderColor = useColorModeValue('gray.200', 'gray.700');

    const RoomListSkeleton = () => (
        <VStack spacing={0} align="stretch">
            {[...Array(5)].map((_, i) => (
                <Box key={i} p={4} borderBottomWidth={1} borderColor={borderColor}>
                    <Flex align="center">
                        <SkeletonCircle size="10" mr={3} />
                        <Box flex={1}>
                            <Skeleton height="20px" width="60%" mb={2} />
                            <Skeleton height="16px" width="80%" />
                        </Box>
                    </Flex>
                </Box>
            ))}
        </VStack>
    );

    const MessageThreadSkeleton = () => (
        <Box h="100%" bg={bgColor}>
            <Box p={4} borderBottomWidth={1} borderColor={borderColor}>
                <Skeleton height="24px" width="200px" />
            </Box>
            <Box p={4}>
                <VStack spacing={4} align="stretch">
                    {[...Array(6)].map((_, i) => {
                        const isRight = i % 2 === 0;
                        return (
                            <Flex
                                key={i}
                                justify={isRight ? 'flex-end' : 'flex-start'}
                            >
                                <Box maxW="70%">
                                    {!isRight && (
                                        <Skeleton
                                            height="16px"
                                            width="100px"
                                            mb={2}
                                        />
                                    )}
                                    <Skeleton
                                        height="60px"
                                        width="300px"
                                        borderRadius="lg"
                                    />
                                </Box>
                            </Flex>
                        );
                    })}
                </VStack>
            </Box>
            <Box p={4} borderTopWidth={1} borderColor={borderColor}>
                <Skeleton height="40px" />
            </Box>
        </Box>
    );

    const FullSkeleton = () => (
        <Flex h="100%">
            <Box
                w="300px"
                borderRightWidth={1}
                borderColor={borderColor}
                bg={bgColor}
            >
                <RoomListSkeleton />
            </Box>
            <Box flex={1}>
                <MessageThreadSkeleton />
            </Box>
        </Flex>
    );

    switch (type) {
        case 'room-list':
            return <RoomListSkeleton />;
        case 'message-thread':
            return <MessageThreadSkeleton />;
        case 'full':
            return <FullSkeleton />;
        default:
            return null;
    }
}