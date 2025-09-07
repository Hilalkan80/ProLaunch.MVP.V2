"""
Database Models Package

This package contains all database models for the ProLaunch MVP.
"""

from .base import Base, get_db
from .user import User, UserProfile, SubscriptionTier
from .token import RefreshToken, TokenBlacklist
from .chat import (
    ChatRoom, ChatRoomParticipant, ChatMessage,
    ChatMessageReceipt,
    RoomType, MessageType, MessageStatus
)
from .citation import (
    Citation, CitationUsage, AccuracyTracking,
    VerificationLog, CitationCollection,
    SourceType, VerificationStatus, ContentType,
    FeedbackType, MetricType
)
from .milestone import (
    Milestone, MilestoneDependency, UserMilestone,
    MilestoneArtifact, UserMilestoneArtifact,
    MilestoneProgressLog, MilestoneCache,
    MilestoneStatus, MilestoneType,
    get_user_milestone_tree, check_milestone_dependencies,
    update_dependent_milestones
)
from .m0_feasibility import (
    M0FeasibilitySnapshot, M0ResearchCache, M0PerformanceLog,
    ViabilityScoreRange, M0Status
)

__all__ = [
    'Base',
    'get_db',
    'User',
    'UserProfile',
    'SubscriptionTier',
    'RefreshToken',
    'TokenBlacklist',
    'ChatRoom',
    'ChatRoomParticipant',
    'ChatMessage',
    'ChatMessageReceipt',
    'RoomType',
    'MessageType',
    'MessageStatus',
    'Citation',
    'CitationUsage',
    'AccuracyTracking',
    'VerificationLog',
    'CitationCollection',
    'SourceType',
    'VerificationStatus',
    'ContentType',
    'FeedbackType',
    'MetricType',
    'Milestone',
    'MilestoneDependency',
    'UserMilestone',
    'MilestoneArtifact',
    'UserMilestoneArtifact',
    'MilestoneProgressLog',
    'MilestoneCache',
    'MilestoneStatus',
    'MilestoneType',
    'get_user_milestone_tree',
    'check_milestone_dependencies',
    'update_dependent_milestones',
    'M0FeasibilitySnapshot',
    'M0ResearchCache',
    'M0PerformanceLog',
    'ViabilityScoreRange',
    'M0Status'
]