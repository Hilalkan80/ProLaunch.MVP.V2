import { Box } from '@chakra-ui/react';
import { GetServerSideProps } from 'next';
import ChatInterface from '../../components/chat/ChatInterface';
import ChatErrorBoundary from '../../components/chat/ChatErrorBoundary';
import LoadingStates from '../../components/chat/LoadingStates';
import { ChatRoom } from '../../types/chat';

interface DemoPageProps {
    initialRooms: ChatRoom[];
    tenantId: string;
    userId: string;
}

export default function DemoPage({
    initialRooms,
    tenantId,
    userId
}: DemoPageProps) {
    return (
        <Box h="100vh">
            <ChatErrorBoundary>
                <ChatInterface
                    tenantId={tenantId}
                    userId={userId}
                    initialRooms={initialRooms}
                    config={{
                        sidebarWidth: 320,
                        messageWidth: 800,
                        showSidebar: true
                    }}
                />
            </ChatErrorBoundary>
        </Box>
    );
}

export const getServerSideProps: GetServerSideProps = async (context) => {
    try {
        // In a real app, you would fetch these from your API
        const mockRooms: ChatRoom[] = [
            {
                id: '1',
                tenantId: 'demo-tenant',
                type: 'direct',
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString(),
                metadata: {},
                participants: [
                    {
                        id: '1',
                        roomId: '1',
                        userId: 'demo-user',
                        role: 'member',
                        joinedAt: new Date().toISOString(),
                        lastReadAt: new Date().toISOString(),
                        isMuted: false,
                        settings: {},
                        user: {
                            id: 'demo-user',
                            name: 'Demo User',
                            status: 'online'
                        }
                    },
                    {
                        id: '2',
                        roomId: '1',
                        userId: 'ai-assistant',
                        role: 'member',
                        joinedAt: new Date().toISOString(),
                        lastReadAt: new Date().toISOString(),
                        isMuted: false,
                        settings: {},
                        user: {
                            id: 'ai-assistant',
                            name: 'AI Assistant',
                            status: 'online'
                        }
                    }
                ],
                lastMessage: {
                    id: '1',
                    roomId: '1',
                    userId: 'ai-assistant',
                    content: 'Hello! How can I help you today?',
                    contentType: 'text',
                    metadata: {},
                    createdAt: new Date().toISOString(),
                    updatedAt: new Date().toISOString()
                }
            },
            {
                id: '2',
                tenantId: 'demo-tenant',
                type: 'group',
                name: 'Project Team',
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString(),
                metadata: {},
                participants: [
                    {
                        id: '3',
                        roomId: '2',
                        userId: 'demo-user',
                        role: 'admin',
                        joinedAt: new Date().toISOString(),
                        lastReadAt: new Date().toISOString(),
                        isMuted: false,
                        settings: {},
                        user: {
                            id: 'demo-user',
                            name: 'Demo User',
                            status: 'online'
                        }
                    },
                    {
                        id: '4',
                        roomId: '2',
                        userId: 'team-member-1',
                        role: 'member',
                        joinedAt: new Date().toISOString(),
                        lastReadAt: new Date().toISOString(),
                        isMuted: false,
                        settings: {},
                        user: {
                            id: 'team-member-1',
                            name: 'Team Member 1',
                            status: 'offline'
                        }
                    },
                    {
                        id: '5',
                        roomId: '2',
                        userId: 'team-member-2',
                        role: 'member',
                        joinedAt: new Date().toISOString(),
                        lastReadAt: new Date().toISOString(),
                        isMuted: false,
                        settings: {},
                        user: {
                            id: 'team-member-2',
                            name: 'Team Member 2',
                            status: 'online'
                        }
                    }
                ],
                lastMessage: {
                    id: '2',
                    roomId: '2',
                    userId: 'team-member-2',
                    content: 'Great progress everyone! Let\'s sync up tomorrow.',
                    contentType: 'text',
                    metadata: {},
                    createdAt: new Date().toISOString(),
                    updatedAt: new Date().toISOString()
                }
            }
        ];

        return {
            props: {
                initialRooms: mockRooms,
                tenantId: 'demo-tenant',
                userId: 'demo-user'
            }
        };
    } catch (error) {
        console.error('Failed to fetch initial data:', error);
        return {
            props: {
                initialRooms: [],
                tenantId: 'demo-tenant',
                userId: 'demo-user'
            }
        };
    }
};