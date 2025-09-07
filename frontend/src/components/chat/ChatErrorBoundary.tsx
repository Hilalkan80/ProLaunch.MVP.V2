import React from 'react';
import { Alert, AlertIcon, AlertTitle, AlertDescription, Button, Box } from '@chakra-ui/react';

interface ErrorBoundaryState {
    hasError: boolean;
    error?: Error;
}

interface ErrorBoundaryProps {
    children: React.ReactNode;
    onReset?: () => void;
}

export default class ChatErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
    constructor(props: ErrorBoundaryProps) {
        super(props);
        this.state = { hasError: false };
    }

    static getDerivedStateFromError(error: Error): ErrorBoundaryState {
        return {
            hasError: true,
            error
        };
    }

    componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
        console.error('Chat error:', error, errorInfo);
    }

    handleReset = () => {
        this.setState({ hasError: false, error: undefined });
        this.props.onReset?.();
    };

    render() {
        if (this.state.hasError) {
            return (
                <Box p={4}>
                    <Alert
                        status="error"
                        variant="subtle"
                        flexDirection="column"
                        alignItems="center"
                        justifyContent="center"
                        textAlign="center"
                        borderRadius="lg"
                        p={6}
                    >
                        <AlertIcon boxSize="40px" mr={0} />
                        <AlertTitle mt={4} mb={1} fontSize="lg">
                            Chat Error
                        </AlertTitle>
                        <AlertDescription maxWidth="sm" mb={4}>
                            {this.state.error?.message || 'An error occurred in the chat interface.'}
                        </AlertDescription>
                        <Button colorScheme="red" onClick={this.handleReset}>
                            Try Again
                        </Button>
                    </Alert>
                </Box>
            );
        }

        return this.props.children;
    }
}