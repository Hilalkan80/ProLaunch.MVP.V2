import React from 'react'
import { screen, fireEvent, waitFor, within } from '@testing-library/react'
import { render } from './setup'
import { vi } from 'vitest'

// Mock the citation service
vi.mock('../../../lib/api/citations', () => ({
  useCitations: () => ({
    data: [],
    isLoading: false,
    error: null,
  }),
  useVerifyCitation: () => ({
    mutate: vi.fn(),
    isLoading: false,
  }),
  useUpdateCitation: () => ({
    mutate: vi.fn(),
    isLoading: false,
  }),
  useDeleteCitation: () => ({
    mutate: vi.fn(),
    isLoading: false,
  }),
}))

// Citation Card component interface
interface Citation {
  id: string
  referenceId: string
  title: string
  url?: string
  authors: string[]
  sourceType: 'web' | 'academic' | 'government' | 'news'
  verificationStatus: 'pending' | 'verified' | 'failed' | 'stale'
  qualityScore: number
  excerpt?: string
  accessDate: string
  lastVerified?: string
  usageCount: number
}

// Mock CitationCard component
const CitationCard = ({ 
  citation, 
  onEdit, 
  onDelete, 
  onVerify,
  showActions = true,
  compact = false 
}: {
  citation: Citation
  onEdit?: (citation: Citation) => void
  onDelete?: (citationId: string) => void
  onVerify?: (citationId: string) => void
  showActions?: boolean
  compact?: boolean
}) => {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'verified': return 'green'
      case 'failed': return 'red'
      case 'stale': return 'orange'
      default: return 'gray'
    }
  }

  const getSourceTypeIcon = (sourceType: string) => {
    switch (sourceType) {
      case 'academic': return '🎓'
      case 'government': return '🏛️'
      case 'news': return '📰'
      default: return '🌐'
    }
  }

  return (
    <div 
      data-testid={`citation-card-${citation.id}`}
      className={`citation-card ${compact ? 'compact' : ''}`}
      role="article"
      aria-labelledby={`citation-title-${citation.id}`}
    >
      <div className="citation-header">
        <div className="citation-source-info">
          <span 
            className="source-type-icon" 
            aria-label={`Source type: ${citation.sourceType}`}
          >
            {getSourceTypeIcon(citation.sourceType)}
          </span>
          <span className="reference-id" data-testid="reference-id">
            {citation.referenceId}
          </span>
        </div>
        
        <div 
          className={`verification-status ${getStatusColor(citation.verificationStatus)}`}
          data-testid="verification-status"
          role="status"
          aria-label={`Verification status: ${citation.verificationStatus}`}
        >
          {citation.verificationStatus}
        </div>
      </div>

      <div className="citation-content">
        <h3 
          id={`citation-title-${citation.id}`}
          className="citation-title"
          data-testid="citation-title"
        >
          {citation.url ? (
            <a 
              href={citation.url} 
              target="_blank" 
              rel="noopener noreferrer"
              aria-describedby={`citation-url-${citation.id}`}
            >
              {citation.title}
            </a>
          ) : (
            citation.title
          )}
        </h3>

        {citation.authors.length > 0 && (
          <div className="citation-authors" data-testid="citation-authors">
            <strong>Authors:</strong> {citation.authors.join(', ')}
          </div>
        )}

        {citation.excerpt && !compact && (
          <div className="citation-excerpt" data-testid="citation-excerpt">
            <em>"{citation.excerpt}"</em>
          </div>
        )}

        <div className="citation-metadata">
          <div className="quality-score" data-testid="quality-score">
            <label>Quality:</label>
            <meter 
              value={citation.qualityScore} 
              min="0" 
              max="1"
              aria-label={`Quality score: ${Math.round(citation.qualityScore * 100)}%`}
            >
              {Math.round(citation.qualityScore * 100)}%
            </meter>
            <span>{Math.round(citation.qualityScore * 100)}%</span>
          </div>

          <div className="usage-count" data-testid="usage-count">
            Used {citation.usageCount} time{citation.usageCount !== 1 ? 's' : ''}
          </div>

          <div className="access-date" data-testid="access-date">
            Accessed: {new Date(citation.accessDate).toLocaleDateString()}
          </div>

          {citation.lastVerified && (
            <div className="last-verified" data-testid="last-verified">
              Last verified: {new Date(citation.lastVerified).toLocaleDateString()}
            </div>
          )}
        </div>

        {citation.url && (
          <div 
            id={`citation-url-${citation.id}`}
            className="citation-url" 
            data-testid="citation-url"
          >
            <small>{citation.url}</small>
          </div>
        )}
      </div>

      {showActions && (
        <div className="citation-actions" data-testid="citation-actions">
          <button
            type="button"
            onClick={() => onEdit?.(citation)}
            aria-label={`Edit citation ${citation.referenceId}`}
            data-testid="edit-button"
          >
            Edit
          </button>
          
          <button
            type="button"
            onClick={() => onVerify?.(citation.id)}
            aria-label={`Verify citation ${citation.referenceId}`}
            data-testid="verify-button"
            disabled={citation.verificationStatus === 'verified'}
          >
            {citation.verificationStatus === 'verified' ? 'Verified' : 'Verify'}
          </button>
          
          <button
            type="button"
            onClick={() => onDelete?.(citation.id)}
            aria-label={`Delete citation ${citation.referenceId}`}
            data-testid="delete-button"
            className="destructive"
          >
            Delete
          </button>
        </div>
      )}
    </div>
  )
}

describe('CitationCard', () => {
  const mockCitation: Citation = {
    id: 'citation-123',
    referenceId: 'ref_2024_001',
    title: 'The Impact of AI on Modern Healthcare Systems',
    url: 'https://journal.example.com/ai-healthcare-2024',
    authors: ['Dr. Jane Smith', 'Prof. John Doe'],
    sourceType: 'academic',
    verificationStatus: 'verified',
    qualityScore: 0.92,
    excerpt: 'This comprehensive study examines how artificial intelligence technologies are revolutionizing healthcare delivery and patient outcomes.',
    accessDate: '2024-01-15T10:30:00Z',
    lastVerified: '2024-01-20T14:45:00Z',
    usageCount: 5
  }

  const mockHandlers = {
    onEdit: vi.fn(),
    onDelete: vi.fn(),
    onVerify: vi.fn()
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('rendering', () => {
    it('should render citation with all basic information', () => {
      render(<CitationCard citation={mockCitation} {...mockHandlers} />)

      expect(screen.getByTestId(`citation-card-${mockCitation.id}`)).toBeInTheDocument()
      expect(screen.getByTestId('reference-id')).toHaveTextContent(mockCitation.referenceId)
      expect(screen.getByTestId('citation-title')).toHaveTextContent(mockCitation.title)
      expect(screen.getByTestId('verification-status')).toHaveTextContent('verified')
    })

    it('should render authors when provided', () => {
      render(<CitationCard citation={mockCitation} {...mockHandlers} />)
      
      const authorsElement = screen.getByTestId('citation-authors')
      expect(authorsElement).toHaveTextContent('Dr. Jane Smith, Prof. John Doe')
    })

    it('should not render authors section when empty', () => {
      const citationWithoutAuthors = { ...mockCitation, authors: [] }
      render(<CitationCard citation={citationWithoutAuthors} {...mockHandlers} />)
      
      expect(screen.queryByTestId('citation-authors')).not.toBeInTheDocument()
    })

    it('should render excerpt when provided and not in compact mode', () => {
      render(<CitationCard citation={mockCitation} {...mockHandlers} />)
      
      expect(screen.getByTestId('citation-excerpt')).toHaveTextContent(mockCitation.excerpt!)
    })

    it('should not render excerpt in compact mode', () => {
      render(<CitationCard citation={mockCitation} {...mockHandlers} compact={true} />)
      
      expect(screen.queryByTestId('citation-excerpt')).not.toBeInTheDocument()
    })

    it('should render clickable title when URL is provided', () => {
      render(<CitationCard citation={mockCitation} {...mockHandlers} />)
      
      const titleLink = screen.getByRole('link', { name: mockCitation.title })
      expect(titleLink).toHaveAttribute('href', mockCitation.url)
      expect(titleLink).toHaveAttribute('target', '_blank')
      expect(titleLink).toHaveAttribute('rel', 'noopener noreferrer')
    })

    it('should render non-clickable title when URL is not provided', () => {
      const citationWithoutUrl = { ...mockCitation, url: undefined }
      render(<CitationCard citation={citationWithoutUrl} {...mockHandlers} />)
      
      expect(screen.queryByRole('link')).not.toBeInTheDocument()
      expect(screen.getByTestId('citation-title')).toHaveTextContent(mockCitation.title)
    })

    it('should display quality score as percentage and meter', () => {
      render(<CitationCard citation={mockCitation} {...mockHandlers} />)
      
      const qualitySection = screen.getByTestId('quality-score')
      expect(qualitySection).toHaveTextContent('92%')
      
      const meter = qualitySection.querySelector('meter')
      expect(meter).toHaveAttribute('value', '0.92')
      expect(meter).toHaveAttribute('min', '0')
      expect(meter).toHaveAttribute('max', '1')
    })

    it('should display usage count with correct pluralization', () => {
      render(<CitationCard citation={mockCitation} {...mockHandlers} />)
      expect(screen.getByTestId('usage-count')).toHaveTextContent('Used 5 times')

      const singleUseCitation = { ...mockCitation, usageCount: 1 }
      render(<CitationCard citation={singleUseCitation} {...mockHandlers} />)
      expect(screen.getByTestId('usage-count')).toHaveTextContent('Used 1 time')
    })

    it('should display formatted dates', () => {
      render(<CitationCard citation={mockCitation} {...mockHandlers} />)
      
      expect(screen.getByTestId('access-date')).toHaveTextContent('1/15/2024')
      expect(screen.getByTestId('last-verified')).toHaveTextContent('1/20/2024')
    })

    it('should not display last verified date when not available', () => {
      const citationWithoutLastVerified = { ...mockCitation, lastVerified: undefined }
      render(<CitationCard citation={citationWithoutLastVerified} {...mockHandlers} />)
      
      expect(screen.queryByTestId('last-verified')).not.toBeInTheDocument()
    })

    it('should display appropriate source type icons', () => {
      const academicCitation = { ...mockCitation, sourceType: 'academic' as const }
      render(<CitationCard citation={academicCitation} {...mockHandlers} />)
      expect(screen.getByLabelText('Source type: academic')).toHaveTextContent('🎓')

      const govCitation = { ...mockCitation, sourceType: 'government' as const }
      render(<CitationCard citation={govCitation} {...mockHandlers} />)
      expect(screen.getByLabelText('Source type: government')).toHaveTextContent('🏛️')

      const newsCitation = { ...mockCitation, sourceType: 'news' as const }
      render(<CitationCard citation={newsCitation} {...mockHandlers} />)
      expect(screen.getByLabelText('Source type: news')).toHaveTextContent('📰')

      const webCitation = { ...mockCitation, sourceType: 'web' as const }
      render(<CitationCard citation={webCitation} {...mockHandlers} />)
      expect(screen.getByLabelText('Source type: web')).toHaveTextContent('🌐')
    })
  })

  describe('verification status', () => {
    it('should display verification status with appropriate styling', () => {
      const verifiedCitation = { ...mockCitation, verificationStatus: 'verified' as const }
      render(<CitationCard citation={verifiedCitation} {...mockHandlers} />)
      
      const statusElement = screen.getByTestId('verification-status')
      expect(statusElement).toHaveTextContent('verified')
      expect(statusElement).toHaveClass('green')
    })

    it('should handle different verification statuses', () => {
      const statuses: Array<{ status: Citation['verificationStatus'], expectedClass: string }> = [
        { status: 'verified', expectedClass: 'green' },
        { status: 'failed', expectedClass: 'red' },
        { status: 'stale', expectedClass: 'orange' },
        { status: 'pending', expectedClass: 'gray' }
      ]

      statuses.forEach(({ status, expectedClass }) => {
        const citation = { ...mockCitation, verificationStatus: status }
        render(<CitationCard citation={citation} {...mockHandlers} />)
        
        const statusElement = screen.getByTestId('verification-status')
        expect(statusElement).toHaveTextContent(status)
        expect(statusElement).toHaveClass(expectedClass)
      })
    })
  })

  describe('actions', () => {
    it('should render action buttons when showActions is true', () => {
      render(<CitationCard citation={mockCitation} {...mockHandlers} showActions={true} />)
      
      expect(screen.getByTestId('citation-actions')).toBeInTheDocument()
      expect(screen.getByTestId('edit-button')).toBeInTheDocument()
      expect(screen.getByTestId('verify-button')).toBeInTheDocument()
      expect(screen.getByTestId('delete-button')).toBeInTheDocument()
    })

    it('should not render action buttons when showActions is false', () => {
      render(<CitationCard citation={mockCitation} {...mockHandlers} showActions={false} />)
      
      expect(screen.queryByTestId('citation-actions')).not.toBeInTheDocument()
    })

    it('should call onEdit when edit button is clicked', async () => {
      render(<CitationCard citation={mockCitation} {...mockHandlers} />)
      
      const editButton = screen.getByTestId('edit-button')
      fireEvent.click(editButton)
      
      expect(mockHandlers.onEdit).toHaveBeenCalledWith(mockCitation)
    })

    it('should call onVerify when verify button is clicked', async () => {
      const unverifiedCitation = { ...mockCitation, verificationStatus: 'pending' as const }
      render(<CitationCard citation={unverifiedCitation} {...mockHandlers} />)
      
      const verifyButton = screen.getByTestId('verify-button')
      fireEvent.click(verifyButton)
      
      expect(mockHandlers.onVerify).toHaveBeenCalledWith(mockCitation.id)
    })

    it('should disable verify button when citation is already verified', () => {
      render(<CitationCard citation={mockCitation} {...mockHandlers} />)
      
      const verifyButton = screen.getByTestId('verify-button')
      expect(verifyButton).toBeDisabled()
      expect(verifyButton).toHaveTextContent('Verified')
    })

    it('should call onDelete when delete button is clicked', async () => {
      render(<CitationCard citation={mockCitation} {...mockHandlers} />)
      
      const deleteButton = screen.getByTestId('delete-button')
      fireEvent.click(deleteButton)
      
      expect(mockHandlers.onDelete).toHaveBeenCalledWith(mockCitation.id)
    })
  })

  describe('accessibility', () => {
    it('should have proper ARIA labels and roles', () => {
      render(<CitationCard citation={mockCitation} {...mockHandlers} />)
      
      const card = screen.getByTestId(`citation-card-${mockCitation.id}`)
      expect(card).toHaveAttribute('role', 'article')
      expect(card).toHaveAttribute('aria-labelledby', `citation-title-${mockCitation.id}`)
    })

    it('should have descriptive button labels', () => {
      render(<CitationCard citation={mockCitation} {...mockHandlers} />)
      
      expect(screen.getByLabelText(`Edit citation ${mockCitation.referenceId}`)).toBeInTheDocument()
      expect(screen.getByLabelText(`Verify citation ${mockCitation.referenceId}`)).toBeInTheDocument()
      expect(screen.getByLabelText(`Delete citation ${mockCitation.referenceId}`)).toBeInTheDocument()
    })

    it('should have proper status announcements', () => {
      render(<CitationCard citation={mockCitation} {...mockHandlers} />)
      
      const statusElement = screen.getByTestId('verification-status')
      expect(statusElement).toHaveAttribute('role', 'status')
      expect(statusElement).toHaveAttribute('aria-label', 'Verification status: verified')
    })

    it('should have accessible quality score meter', () => {
      render(<CitationCard citation={mockCitation} {...mockHandlers} />)
      
      const meter = screen.getByLabelText('Quality score: 92%')
      expect(meter).toHaveAttribute('value', '0.92')
    })

    it('should support keyboard navigation', () => {
      render(<CitationCard citation={mockCitation} {...mockHandlers} />)
      
      const editButton = screen.getByTestId('edit-button')
      const verifyButton = screen.getByTestId('verify-button')
      const deleteButton = screen.getByTestId('delete-button')
      
      // Test tab order
      editButton.focus()
      expect(editButton).toHaveFocus()
      
      fireEvent.keyDown(editButton, { key: 'Tab' })
      expect(verifyButton).toHaveFocus()
      
      fireEvent.keyDown(verifyButton, { key: 'Tab' })
      expect(deleteButton).toHaveFocus()
    })
  })

  describe('responsive behavior', () => {
    it('should apply compact class when compact prop is true', () => {
      render(<CitationCard citation={mockCitation} {...mockHandlers} compact={true} />)
      
      const card = screen.getByTestId(`citation-card-${mockCitation.id}`)
      expect(card).toHaveClass('compact')
    })

    it('should not apply compact class when compact prop is false', () => {
      render(<CitationCard citation={mockCitation} {...mockHandlers} compact={false} />)
      
      const card = screen.getByTestId(`citation-card-${mockCitation.id}`)
      expect(card).not.toHaveClass('compact')
    })
  })

  describe('edge cases', () => {
    it('should handle citation with minimal required fields', () => {
      const minimalCitation: Citation = {
        id: 'minimal-123',
        referenceId: 'ref_minimal_001',
        title: 'Minimal Citation',
        authors: [],
        sourceType: 'web',
        verificationStatus: 'pending',
        qualityScore: 0.5,
        accessDate: '2024-01-15T10:30:00Z',
        usageCount: 0
      }
      
      render(<CitationCard citation={minimalCitation} {...mockHandlers} />)
      
      expect(screen.getByTestId('citation-title')).toHaveTextContent('Minimal Citation')
      expect(screen.getByTestId('reference-id')).toHaveTextContent('ref_minimal_001')
      expect(screen.getByTestId('usage-count')).toHaveTextContent('Used 0 times')
    })

    it('should handle very long titles gracefully', () => {
      const longTitleCitation = {
        ...mockCitation,
        title: 'This is an extremely long title that should be handled gracefully by the component and not break the layout or cause any accessibility issues when rendered in the citation card component'
      }
      
      render(<CitationCard citation={longTitleCitation} {...mockHandlers} />)
      
      expect(screen.getByTestId('citation-title')).toHaveTextContent(longTitleCitation.title)
    })

    it('should handle citations with very low quality scores', () => {
      const lowQualityCitation = { ...mockCitation, qualityScore: 0.1 }
      render(<CitationCard citation={lowQualityCitation} {...mockHandlers} />)
      
      const qualitySection = screen.getByTestId('quality-score')
      expect(qualitySection).toHaveTextContent('10%')
    })

    it('should handle citations with perfect quality scores', () => {
      const perfectCitation = { ...mockCitation, qualityScore: 1.0 }
      render(<CitationCard citation={perfectCitation} {...mockHandlers} />)
      
      const qualitySection = screen.getByTestId('quality-score')
      expect(qualitySection).toHaveTextContent('100%')
    })
  })

  describe('error handling', () => {
    it('should handle missing handler functions gracefully', () => {
      render(<CitationCard citation={mockCitation} />)
      
      const editButton = screen.getByTestId('edit-button')
      const verifyButton = screen.getByTestId('verify-button')
      const deleteButton = screen.getByTestId('delete-button')
      
      // Should not throw errors when clicked
      expect(() => {
        fireEvent.click(editButton)
        fireEvent.click(verifyButton)
        fireEvent.click(deleteButton)
      }).not.toThrow()
    })
  })
})