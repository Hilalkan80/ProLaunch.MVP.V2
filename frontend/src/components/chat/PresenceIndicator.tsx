import React from 'react';
import {
  Box,
  HStack,
  VStack,
  Text,
  Avatar,
  AvatarGroup,
  Badge,
  Tooltip,
  useColorModeValue
} from '@chakra-ui/react';
import type { User, ReadReceipt } from '@/types/chat';

interface PresenceIndicatorProps {
  user: User;
  size?: 'xs' | 'sm' | 'md' | 'lg';
  showStatus?: boolean;
  showLabel?: boolean;
}

interface OnlineUsersListProps {
  users: User[];
  maxDisplay?: number;
}

interface ReadReceiptsProps {
  readBy: ReadReceipt[];
  currentUserId: string;
  maxDisplay?: number;
  size?: 'xs' | 'sm' | 'md' | 'lg';
}

interface UserStatusProps {
  user: User;
  showLastSeen?: boolean;
}

export const PresenceIndicator: React.FC<PresenceIndicatorProps> = ({
  user,
  size = 'sm',
  showStatus = true,
  showLabel = false
}) => {
  const indicatorSize = {
    xs: '8px',
    sm: '10px',
    md: '12px',
    lg: '14px'
  }[size];

  const borderWidth = {
    xs: '1px',
    sm: '2px',
    md: '2px',
    lg: '3px'
  }[size];

  const getStatusColor = () => {
    if (user.isOnline) return 'green.400';
    return 'gray.400';
  };

  const getLastSeenText = () => {
    if (user.isOnline) return 'Online';
    if (!user.lastSeen) return 'Offline';
    
    const now = new Date();
    const lastSeen = new Date(user.lastSeen);
    const diffInMinutes = Math.floor((now.getTime() - lastSeen.getTime()) / (1000 * 60));
    
    if (diffInMinutes < 1) return 'Just now';
    if (diffInMinutes < 60) return `${diffInMinutes}m ago`;
    if (diffInMinutes < 1440) return `${Math.floor(diffInMinutes / 60)}h ago`;
    if (diffInMinutes < 10080) return `${Math.floor(diffInMinutes / 1440)}d ago`;
    return 'Long time ago';
  };

  if (showLabel) {
    return (
      <HStack spacing={2} align="center">
        <Box position="relative">
          <Avatar size={size} name={user.username} src={user.avatar} />
          {showStatus && (
            <Box
              position="absolute"
              bottom={0}
              right={0}
              w={indicatorSize}
              h={indicatorSize}
              bg={getStatusColor()}
              borderRadius="full"
              border={`${borderWidth} solid`}
              borderColor={useColorModeValue('white', 'gray.800')}
            />
          )}
        </Box>
        <VStack align="flex-start" spacing={0}>
          <Text fontSize="sm" fontWeight="medium">
            {user.username}
          </Text>
          <Text fontSize="xs" color="gray.500">
            {getLastSeenText()}
          </Text>
        </VStack>
      </HStack>
    );
  }

  return (
    <Tooltip label={`${user.username} - ${getLastSeenText()}`} placement="top">
      <Box position="relative" display="inline-block">
        <Avatar size={size} name={user.username} src={user.avatar} />
        {showStatus && (
          <Box
            position="absolute"
            bottom={0}
            right={0}
            w={indicatorSize}
            h={indicatorSize}
            bg={getStatusColor()}
            borderRadius="full"
            border={`${borderWidth} solid`}
            borderColor={useColorModeValue('white', 'gray.800')}
          />
        )}
      </Box>
    </Tooltip>
  );
};

export const OnlineUsersList: React.FC<OnlineUsersListProps> = ({
  users,
  maxDisplay = 5
}) => {
  const onlineUsers = users.filter(user => user.isOnline);
  const displayUsers = onlineUsers.slice(0, maxDisplay);
  const extraCount = onlineUsers.length - maxDisplay;

  if (onlineUsers.length === 0) {
    return (
      <VStack spacing={2} align="center" p={4}>
        <Text fontSize="sm" color="gray.500">
          No one is online right now
        </Text>
      </VStack>
    );
  }

  return (
    <VStack spacing={2} align="stretch">
      <HStack justify="space-between">
        <Text fontSize="sm" fontWeight="semibold">
          Online Now
        </Text>
        <Badge variant="subtle" colorScheme="green">
          {onlineUsers.length}
        </Badge>
      </HStack>

      <VStack spacing={2} align="stretch">
        {displayUsers.map((user) => (
          <PresenceIndicator
            key={user.id}
            user={user}
            size="sm"
            showStatus={true}
            showLabel={true}
          />
        ))}
        
        {extraCount > 0 && (
          <Text fontSize="xs" color="gray.500" textAlign="center">
            +{extraCount} more online
          </Text>
        )}
      </VStack>
    </VStack>
  );
};

export const ReadReceipts: React.FC<ReadReceiptsProps> = ({
  readBy,
  currentUserId,
  maxDisplay = 3,
  size = 'xs'
}) => {
  // Filter out current user's read receipt
  const othersReadBy = readBy.filter(receipt => receipt.userId !== currentUserId);
  
  if (othersReadBy.length === 0) {
    return null;
  }

  const displayReceipts = othersReadBy.slice(0, maxDisplay);
  const extraCount = othersReadBy.length - maxDisplay;

  const getTooltipText = () => {
    if (othersReadBy.length === 1) {
      return `Read by ${othersReadBy[0].user.username}`;
    }
    
    const names = othersReadBy.map(r => r.user.username);
    if (names.length <= 3) {
      return `Read by ${names.join(', ')}`;
    }
    
    return `Read by ${names.slice(0, 2).join(', ')} and ${names.length - 2} others`;
  };

  return (
    <Tooltip label={getTooltipText()} placement="top">
      <HStack spacing={1} align="center">
        <AvatarGroup size={size} max={maxDisplay} spacing="-0.5">
          {displayReceipts.map((receipt) => (
            <Avatar
              key={receipt.id}
              name={receipt.user.username}
              src={receipt.user.avatar}
              border="2px solid"
              borderColor={useColorModeValue('white', 'gray.800')}
            />
          ))}
        </AvatarGroup>
        
        {extraCount > 0 && (
          <Text fontSize="xs" color="gray.500">
            +{extraCount}
          </Text>
        )}
      </HStack>
    </Tooltip>
  );
};

export const UserStatus: React.FC<UserStatusProps> = ({
  user,
  showLastSeen = true
}) => {
  const getLastSeenText = () => {
    if (user.isOnline) return 'Active now';
    if (!user.lastSeen) return 'Last seen unknown';
    
    const now = new Date();
    const lastSeen = new Date(user.lastSeen);
    const diffInMinutes = Math.floor((now.getTime() - lastSeen.getTime()) / (1000 * 60));
    
    if (diffInMinutes < 1) return 'Last seen just now';
    if (diffInMinutes < 60) return `Last seen ${diffInMinutes} minute${diffInMinutes !== 1 ? 's' : ''} ago`;
    if (diffInMinutes < 1440) {
      const hours = Math.floor(diffInMinutes / 60);
      return `Last seen ${hours} hour${hours !== 1 ? 's' : ''} ago`;
    }
    if (diffInMinutes < 10080) {
      const days = Math.floor(diffInMinutes / 1440);
      return `Last seen ${days} day${days !== 1 ? 's' : ''} ago`;
    }
    
    return `Last seen ${lastSeen.toLocaleDateString()}`;
  };

  const statusColor = user.isOnline ? 'green.500' : 'gray.500';
  const statusText = user.isOnline ? 'Online' : 'Offline';

  return (
    <VStack align="flex-start" spacing={1}>
      <HStack spacing={2} align="center">
        <Box
          w="8px"
          h="8px"
          bg={statusColor}
          borderRadius="full"
        />
        <Text fontSize="sm" fontWeight="medium" color={statusColor}>
          {statusText}
        </Text>
      </HStack>
      
      {showLastSeen && (
        <Text fontSize="xs" color="gray.500">
          {getLastSeenText()}
        </Text>
      )}
    </VStack>
  );
};

// Utility hook for managing presence updates
export const usePresenceManager = (users: User[]) => {
  const onlineUsers = users.filter(user => user.isOnline);
  const offlineUsers = users.filter(user => !user.isOnline);
  
  const getOnlineCount = () => onlineUsers.length;
  
  const getUserStatus = (userId: string) => {
    const user = users.find(u => u.id === userId);
    return user ? {
      isOnline: user.isOnline,
      lastSeen: user.lastSeen
    } : null;
  };
  
  const sortUsersByActivity = (userList: User[]) => {
    return [...userList].sort((a, b) => {
      // Online users first
      if (a.isOnline && !b.isOnline) return -1;
      if (!a.isOnline && b.isOnline) return 1;
      
      // If both online or both offline, sort by last activity
      if (a.lastSeen && b.lastSeen) {
        return new Date(b.lastSeen).getTime() - new Date(a.lastSeen).getTime();
      }
      
      // Users with known last seen time come before unknown
      if (a.lastSeen && !b.lastSeen) return -1;
      if (!a.lastSeen && b.lastSeen) return 1;
      
      // Fallback to alphabetical
      return a.username.localeCompare(b.username);
    });
  };
  
  return {
    onlineUsers,
    offlineUsers,
    getOnlineCount,
    getUserStatus,
    sortUsersByActivity
  };
};