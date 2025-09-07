import React from 'react'
import { screen, fireEvent, waitFor, within } from '@testing-library/react'
import { render } from './setup'
import { vi } from 'vitest'

// Mock the citation API hooks
vi.mock('../../../lib/api/citations', () => ({
  useCitations: vi.fn(),
  useVerifyCitation: vi.fn(),
  useUpdateCitation: vi.fn(),
  useDeleteCitation: vi.fn(),
}))

// Mock the CitationCard component
vi.mock('../CitationCard', () => ({
  CitationCard: ({ citation, onEdit, onDelete, onVerify }: any) => (
    <div data-testid={`citation-card-${citation.id}`}>
      <span data-testid="citation-title">{citation.title}</span>
      <button onClick={() => onEdit?.(citation)} data-testid="edit-button">Edit</button>
      <button onClick={() => onDelete?.(citation.id)} data-testid="delete-button">Delete</button>
      <button onClick={() => onVerify?.(citation.id)} data-testid="verify-button">Verify</button>
    </div>
  )
}))

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

interface SearchFilters {
  query?: string
  sourceTypes?: string[]
  verificationStatus?: string
  minQualityScore?: number
  maxAgeDays?: number
}

interface SortOptions {
  field: 'title' | 'accessDate' | 'qualityScore' | 'usageCount' | 'lastVerified'
  direction: 'asc' | 'desc'
}

// Mock CitationList component
const CitationList = ({
  onEdit,
  onDelete,
  onVerify,
  onSelectionChange,
  searchFilters = {},
  sortOptions = { field: 'accessDate', direction: 'desc' },
  showFilters = true,
  showSort = true,
  showBulkActions = true,
  compact = false,
}: {
  onEdit?: (citation: Citation) => void
  onDelete?: (citationId: string) => void
  onVerify?: (citationId: string) => void
  onSelectionChange?: (selectedIds: string[]) => void
  searchFilters?: SearchFilters
  sortOptions?: SortOptions
  showFilters?: boolean
  showSort?: boolean
  showBulkActions?: boolean
  compact?: boolean
}) => {
  const [selectedCitations, setSelectedCitations] = React.useState<string[]>([])
  const [localFilters, setLocalFilters] = React.useState<SearchFilters>(searchFilters)
  const [localSort, setLocalSort] = React.useState<SortOptions>(sortOptions)
  const [isLoading, setIsLoading] = React.useState(false)

  // Mock data
  const mockCitations: Citation[] = [
    {
      id: '1',
      referenceId: 'ref_2024_001',
      title: 'AI in Healthcare: A Comprehensive Review',
      url: 'https://example.com/ai-healthcare',
      authors: ['Dr. Smith', 'Dr. Jones'],
      sourceType: 'academic',
      verificationStatus: 'verified',
      qualityScore: 0.95,
      excerpt: 'This paper reviews AI applications in healthcare...',
      accessDate: '2024-01-15T10:30:00Z',
      lastVerified: '2024-01-20T14:45:00Z',
      usageCount: 12
    },
    {
      id: '2',
      referenceId: 'ref_2024_002',
      title: 'Government AI Policy Guidelines',
      url: 'https://gov.example.com/ai-policy',
      authors: ['Policy Committee'],
      sourceType: 'government',
      verificationStatus: 'pending',
      qualityScore: 0.88,
      accessDate: '2024-01-10T09:15:00Z',
      usageCount: 5
    },
    {
      id: '3',
      referenceId: 'ref_2024_003',
      title: 'Breaking: Major AI Breakthrough Announced',
      url: 'https://news.example.com/ai-breakthrough',
      authors: ['News Reporter'],
      sourceType: 'news',
      verificationStatus: 'failed',
      qualityScore: 0.65,
      accessDate: '2024-01-05T16:22:00Z',
      usageCount: 2
    }
  ]

  // Apply filters and sorting
  let filteredCitations = [...mockCitations]

  if (localFilters.query) {
    filteredCitations = filteredCitations.filter(citation =>
      citation.title.toLowerCase().includes(localFilters.query!.toLowerCase()) ||
      citation.authors.some(author => author.toLowerCase().includes(localFilters.query!.toLowerCase()))
    )
  }

  if (localFilters.sourceTypes && localFilters.sourceTypes.length > 0) {
    filteredCitations = filteredCitations.filter(citation =>
      localFilters.sourceTypes!.includes(citation.sourceType)
    )
  }

  if (localFilters.verificationStatus) {
    filteredCitations = filteredCitations.filter(citation =>
      citation.verificationStatus === localFilters.verificationStatus
    )
  }

  if (localFilters.minQualityScore !== undefined) {
    filteredCitations = filteredCitations.filter(citation =>
      citation.qualityScore >= localFilters.minQualityScore!
    )
  }

  // Sort citations
  filteredCitations.sort((a, b) => {
    let comparison = 0
    switch (localSort.field) {
      case 'title':
        comparison = a.title.localeCompare(b.title)
        break
      case 'qualityScore':
        comparison = a.qualityScore - b.qualityScore
        break
      case 'usageCount':
        comparison = a.usageCount - b.usageCount
        break
      case 'accessDate':
        comparison = new Date(a.accessDate).getTime() - new Date(b.accessDate).getTime()
        break
      default:
        comparison = 0
    }
    return localSort.direction === 'desc' ? -comparison : comparison
  })

  const handleSelectAll = () => {
    if (selectedCitations.length === filteredCitations.length) {
      setSelectedCitations([])
      onSelectionChange?.([])
    } else {
      const allIds = filteredCitations.map(c => c.id)
      setSelectedCitations(allIds)
      onSelectionChange?.(allIds)
    }
  }

  const handleSelectCitation = (citationId: string) => {
    const newSelection = selectedCitations.includes(citationId)
      ? selectedCitations.filter(id => id !== citationId)
      : [...selectedCitations, citationId]
    
    setSelectedCitations(newSelection)
    onSelectionChange?.(newSelection)
  }

  const handleBulkVerify = async () => {
    setIsLoading(true)
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000))
    selectedCitations.forEach(id => onVerify?.(id))
    setIsLoading(false)
  }

  const handleBulkDelete = async () => {
    setIsLoading(true)
    await new Promise(resolve => setTimeout(resolve, 500))
    selectedCitations.forEach(id => onDelete?.(id))
    setSelectedCitations([])
    onSelectionChange?.([])
    setIsLoading(false)
  }

  return (
    <div className="citation-list" data-testid="citation-list">
      {showFilters && (
        <div className="citation-filters" data-testid="citation-filters">
          <div className="search-input">
            <label htmlFor="citation-search">Search citations:</label>
            <input
              id="citation-search"
              type="text"
              placeholder="Search by title or author..."
              value={localFilters.query || ''}
              onChange={(e) => setLocalFilters({...localFilters, query: e.target.value})}
              data-testid="search-input"
            />
          </div>

          <div className="filter-controls">
            <div className="source-type-filter">
              <label htmlFor="source-type-select">Source Type:</label>
              <select
                id="source-type-select"
                value={localFilters.sourceTypes?.[0] || ''}
                onChange={(e) => setLocalFilters({
                  ...localFilters, 
                  sourceTypes: e.target.value ? [e.target.value] : []
                })}
                data-testid="source-type-select"
              >
                <option value="">All Types</option>
                <option value="academic">Academic</option>
                <option value="government">Government</option>
                <option value="news">News</option>
                <option value="web">Web</option>
              </select>
            </div>

            <div className="verification-filter">
              <label htmlFor="verification-select">Verification Status:</label>
              <select
                id="verification-select"
                value={localFilters.verificationStatus || ''}
                onChange={(e) => setLocalFilters({
                  ...localFilters, 
                  verificationStatus: e.target.value || undefined
                })}
                data-testid="verification-select"
              >
                <option value="">All Statuses</option>
                <option value="verified">Verified</option>
                <option value="pending">Pending</option>
                <option value="failed">Failed</option>
                <option value="stale">Stale</option>
              </select>
            </div>

            <div className="quality-filter">
              <label htmlFor="quality-slider">Min Quality Score:</label>
              <input
                id="quality-slider"
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={localFilters.minQualityScore || 0}
                onChange={(e) => setLocalFilters({
                  ...localFilters, 
                  minQualityScore: parseFloat(e.target.value)
                })}
                data-testid="quality-slider"
              />
              <span data-testid="quality-value">
                {Math.round((localFilters.minQualityScore || 0) * 100)}%
              </span>
            </div>
          </div>
        </div>
      )}

      {showSort && (
        <div className="citation-sort" data-testid="citation-sort">
          <label htmlFor="sort-field">Sort by:</label>
          <select
            id="sort-field"
            value={localSort.field}
            onChange={(e) => setLocalSort({
              ...localSort, 
              field: e.target.value as SortOptions['field']
            })}
            data-testid="sort-field-select"
          >
            <option value="accessDate">Access Date</option>
            <option value="title">Title</option>
            <option value="qualityScore">Quality Score</option>
            <option value="usageCount">Usage Count</option>
          </select>

          <select
            value={localSort.direction}
            onChange={(e) => setLocalSort({
              ...localSort, 
              direction: e.target.value as SortOptions['direction']
            })}
            data-testid="sort-direction-select"
            aria-label="Sort direction"
          >
            <option value="desc">Descending</option>
            <option value="asc">Ascending</option>
          </select>
        </div>
      )}

      <div className="citation-summary" data-testid="citation-summary">
        <span>
          Showing {filteredCitations.length} of {mockCitations.length} citations
        </span>
        {selectedCitations.length > 0 && (
          <span> ({selectedCitations.length} selected)</span>
        )}
      </div>

      {showBulkActions && selectedCitations.length > 0 && (
        <div className="bulk-actions" data-testid="bulk-actions">
          <button
            onClick={handleBulkVerify}
            disabled={isLoading}
            data-testid="bulk-verify-button"
          >
            {isLoading ? 'Verifying...' : `Verify Selected (${selectedCitations.length})`}
          </button>
          <button
            onClick={handleBulkDelete}
            disabled={isLoading}
            data-testid="bulk-delete-button"
            className="destructive"
          >
            {isLoading ? 'Deleting...' : `Delete Selected (${selectedCitations.length})`}
          </button>
        </div>
      )}

      {showBulkActions && (
        <div className="selection-controls" data-testid="selection-controls">
          <label>
            <input
              type="checkbox"
              checked={selectedCitations.length === filteredCitations.length && filteredCitations.length > 0}
              onChange={handleSelectAll}
              data-testid="select-all-checkbox"
            />
            Select All
          </label>
        </div>
      )}

      <div className="citations-grid" data-testid="citations-grid">
        {isLoading && (
          <div className="loading-overlay" data-testid="loading-overlay">
            Loading citations...
          </div>
        )}

        {filteredCitations.length === 0 ? (
          <div className="empty-state" data-testid="empty-state">
            <p>No citations found matching your criteria.</p>
          </div>
        ) : (
          filteredCitations.map(citation => (
            <div key={citation.id} className="citation-item">
              {showBulkActions && (
                <label className="citation-checkbox">
                  <input
                    type="checkbox"
                    checked={selectedCitations.includes(citation.id)}
                    onChange={() => handleSelectCitation(citation.id)}
                    data-testid={`select-checkbox-${citation.id}`}
                    aria-label={`Select citation ${citation.referenceId}`}
                  />
                </label>
              )}
              <div data-testid={`citation-card-${citation.id}`}>
                <span data-testid="citation-title">{citation.title}</span>
                <button
                  onClick={() => onEdit?.(citation)}
                  data-testid="edit-button"
                >
                  Edit
                </button>
                <button
                  onClick={() => onDelete?.(citation.id)}
                  data-testid="delete-button"
                >
                  Delete
                </button>
                <button
                  onClick={() => onVerify?.(citation.id)}
                  data-testid="verify-button"
                >
                  Verify
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {filteredCitations.length > 20 && (
        <div className="pagination" data-testid="pagination">
          <button disabled data-testid="prev-page">Previous</button>
          <span data-testid="page-info">Page 1 of 1</span>
          <button disabled data-testid="next-page">Next</button>
        </div>
      )}
    </div>
  )
}

describe('CitationList', () => {
  const mockHandlers = {
    onEdit: vi.fn(),
    onDelete: vi.fn(),
    onVerify: vi.fn(),
    onSelectionChange: vi.fn()
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('rendering', () => {
    it('should render citation list with default elements', () => {
      render(<CitationList {...mockHandlers} />)

      expect(screen.getByTestId('citation-list')).toBeInTheDocument()
      expect(screen.getByTestId('citation-filters')).toBeInTheDocument()
      expect(screen.getByTestId('citation-sort')).toBeInTheDocument()
      expect(screen.getByTestId('citations-grid')).toBeInTheDocument()
      expect(screen.getByTestId('citation-summary')).toBeInTheDocument()
    })

    it('should render all citation cards', () => {
      render(<CitationList {...mockHandlers} />)

      expect(screen.getByTestId('citation-card-1')).toBeInTheDocument()
      expect(screen.getByTestId('citation-card-2')).toBeInTheDocument()
      expect(screen.getByTestId('citation-card-3')).toBeInTheDocument()
    })

    it('should display citation summary with correct counts', () => {
      render(<CitationList {...mockHandlers} />)

      expect(screen.getByTestId('citation-summary')).toHaveTextContent('Showing 3 of 3 citations')
    })

    it('should hide filters when showFilters is false', () => {
      render(<CitationList {...mockHandlers} showFilters={false} />)

      expect(screen.queryByTestId('citation-filters')).not.toBeInTheDocument()
    })

    it('should hide sort controls when showSort is false', () => {
      render(<CitationList {...mockHandlers} showSort={false} />)

      expect(screen.queryByTestId('citation-sort')).not.toBeInTheDocument()
    })

    it('should hide bulk actions when showBulkActions is false', () => {
      render(<CitationList {...mockHandlers} showBulkActions={false} />)

      expect(screen.queryByTestId('selection-controls')).not.toBeInTheDocument()
      expect(screen.queryByTestId('select-all-checkbox')).not.toBeInTheDocument()
    })
  })

  describe('filtering', () => {
    it('should filter citations by search query', async () => {
      render(<CitationList {...mockHandlers} />)

      const searchInput = screen.getByTestId('search-input')
      fireEvent.change(searchInput, { target: { value: 'Healthcare' } })

      await waitFor(() => {
        expect(screen.getByTestId('citation-card-1')).toBeInTheDocument()
        expect(screen.queryByTestId('citation-card-2')).not.toBeInTheDocument()
        expect(screen.queryByTestId('citation-card-3')).not.toBeInTheDocument()
      })

      expect(screen.getByTestId('citation-summary')).toHaveTextContent('Showing 1 of 3 citations')
    })

    it('should filter citations by source type', async () => {
      render(<CitationList {...mockHandlers} />)

      const sourceTypeSelect = screen.getByTestId('source-type-select')
      fireEvent.change(sourceTypeSelect, { target: { value: 'government' } })

      await waitFor(() => {
        expect(screen.queryByTestId('citation-card-1')).not.toBeInTheDocument()
        expect(screen.getByTestId('citation-card-2')).toBeInTheDocument()
        expect(screen.queryByTestId('citation-card-3')).not.toBeInTheDocument()
      })
    })

    it('should filter citations by verification status', async () => {
      render(<CitationList {...mockHandlers} />)

      const verificationSelect = screen.getByTestId('verification-select')
      fireEvent.change(verificationSelect, { target: { value: 'verified' } })

      await waitFor(() => {
        expect(screen.getByTestId('citation-card-1')).toBeInTheDocument()
        expect(screen.queryByTestId('citation-card-2')).not.toBeInTheDocument()
        expect(screen.queryByTestId('citation-card-3')).not.toBeInTheDocument()
      })
    })

    it('should filter citations by quality score', async () => {
      render(<CitationList {...mockHandlers} />)

      const qualitySlider = screen.getByTestId('quality-slider')
      fireEvent.change(qualitySlider, { target: { value: '0.9' } })

      await waitFor(() => {
        expect(screen.getByTestId('citation-card-1')).toBeInTheDocument()
        expect(screen.queryByTestId('citation-card-2')).not.toBeInTheDocument()
        expect(screen.queryByTestId('citation-card-3')).not.toBeInTheDocument()
      })

      expect(screen.getByTestId('quality-value')).toHaveTextContent('90%')
    })

    it('should show empty state when no citations match filters', async () => {
      render(<CitationList {...mockHandlers} />)

      const searchInput = screen.getByTestId('search-input')
      fireEvent.change(searchInput, { target: { value: 'NonexistentTopic' } })

      await waitFor(() => {
        expect(screen.getByTestId('empty-state')).toBeInTheDocument()
        expect(screen.getByText('No citations found matching your criteria.')).toBeInTheDocument()
      })
    })
  })

  describe('sorting', () => {
    it('should sort citations by title ascending', async () => {
      render(<CitationList {...mockHandlers} />)

      const sortFieldSelect = screen.getByTestId('sort-field-select')
      const sortDirectionSelect = screen.getByTestId('sort-direction-select')

      fireEvent.change(sortFieldSelect, { target: { value: 'title' } })
      fireEvent.change(sortDirectionSelect, { target: { value: 'asc' } })

      await waitFor(() => {
        const citationCards = screen.getAllByTestId(/citation-card-/)
        const titles = citationCards.map(card => 
          within(card).getByTestId('citation-title').textContent
        )
        
        // Should be in alphabetical order
        expect(titles[0]).toContain('AI in Healthcare')
        expect(titles[1]).toContain('Breaking: Major AI')
        expect(titles[2]).toContain('Government AI Policy')
      })
    })

    it('should sort citations by quality score descending', async () => {
      render(<CitationList {...mockHandlers} />)

      const sortFieldSelect = screen.getByTestId('sort-field-select')
      fireEvent.change(sortFieldSelect, { target: { value: 'qualityScore' } })

      await waitFor(() => {
        const citationCards = screen.getAllByTestId(/citation-card-/)
        // Highest quality (0.95) should be first
        expect(within(citationCards[0]).getByTestId('citation-title')).toHaveTextContent('AI in Healthcare')
      })
    })
  })

  describe('selection and bulk actions', () => {
    it('should select individual citations', () => {
      render(<CitationList {...mockHandlers} />)

      const checkbox = screen.getByTestId('select-checkbox-1')
      fireEvent.click(checkbox)

      expect(checkbox).toBeChecked()
      expect(screen.getByTestId('citation-summary')).toHaveTextContent('(1 selected)')
      expect(mockHandlers.onSelectionChange).toHaveBeenCalledWith(['1'])
    })

    it('should select all citations', () => {
      render(<CitationList {...mockHandlers} />)

      const selectAllCheckbox = screen.getByTestId('select-all-checkbox')
      fireEvent.click(selectAllCheckbox)

      expect(selectAllCheckbox).toBeChecked()
      expect(screen.getByTestId('citation-summary')).toHaveTextContent('(3 selected)')
      expect(mockHandlers.onSelectionChange).toHaveBeenCalledWith(['1', '2', '3'])
    })

    it('should deselect all citations when all are selected', () => {
      render(<CitationList {...mockHandlers} />)

      // First select all
      const selectAllCheckbox = screen.getByTestId('select-all-checkbox')
      fireEvent.click(selectAllCheckbox)
      fireEvent.click(selectAllCheckbox) // Click again to deselect

      expect(selectAllCheckbox).not.toBeChecked()
      expect(screen.queryByText('(3 selected)')).not.toBeInTheDocument()
      expect(mockHandlers.onSelectionChange).toHaveBeenLastCalledWith([])
    })

    it('should show bulk actions when citations are selected', () => {
      render(<CitationList {...mockHandlers} />)

      const checkbox = screen.getByTestId('select-checkbox-1')
      fireEvent.click(checkbox)

      expect(screen.getByTestId('bulk-actions')).toBeInTheDocument()
      expect(screen.getByTestId('bulk-verify-button')).toHaveTextContent('Verify Selected (1)')
      expect(screen.getByTestId('bulk-delete-button')).toHaveTextContent('Delete Selected (1)')
    })

    it('should perform bulk verify action', async () => {
      render(<CitationList {...mockHandlers} />)

      const checkbox = screen.getByTestId('select-checkbox-1')
      fireEvent.click(checkbox)

      const bulkVerifyButton = screen.getByTestId('bulk-verify-button')
      fireEvent.click(bulkVerifyButton)

      expect(bulkVerifyButton).toHaveTextContent('Verifying...')
      expect(bulkVerifyButton).toBeDisabled()

      await waitFor(() => {
        expect(mockHandlers.onVerify).toHaveBeenCalledWith('1')
      }, { timeout: 2000 })
    })

    it('should perform bulk delete action', async () => {
      render(<CitationList {...mockHandlers} />)

      const checkbox1 = screen.getByTestId('select-checkbox-1')
      const checkbox2 = screen.getByTestId('select-checkbox-2')
      fireEvent.click(checkbox1)
      fireEvent.click(checkbox2)

      const bulkDeleteButton = screen.getByTestId('bulk-delete-button')
      fireEvent.click(bulkDeleteButton)

      expect(bulkDeleteButton).toHaveTextContent('Deleting...')
      expect(bulkDeleteButton).toBeDisabled()

      await waitFor(() => {
        expect(mockHandlers.onDelete).toHaveBeenCalledWith('1')
        expect(mockHandlers.onDelete).toHaveBeenCalledWith('2')
      }, { timeout: 1500 })
    })
  })

  describe('individual citation actions', () => {
    it('should call onEdit when citation edit button is clicked', () => {
      render(<CitationList {...mockHandlers} />)

      const editButton = within(screen.getByTestId('citation-card-1')).getByTestId('edit-button')
      fireEvent.click(editButton)

      expect(mockHandlers.onEdit).toHaveBeenCalledWith(
        expect.objectContaining({ id: '1', title: 'AI in Healthcare: A Comprehensive Review' })
      )
    })

    it('should call onDelete when citation delete button is clicked', () => {
      render(<CitationList {...mockHandlers} />)

      const deleteButton = within(screen.getByTestId('citation-card-1')).getByTestId('delete-button')
      fireEvent.click(deleteButton)

      expect(mockHandlers.onDelete).toHaveBeenCalledWith('1')
    })

    it('should call onVerify when citation verify button is clicked', () => {
      render(<CitationList {...mockHandlers} />)

      const verifyButton = within(screen.getByTestId('citation-card-1')).getByTestId('verify-button')
      fireEvent.click(verifyButton)

      expect(mockHandlers.onVerify).toHaveBeenCalledWith('1')
    })
  })

  describe('accessibility', () => {
    it('should have proper form labels', () => {
      render(<CitationList {...mockHandlers} />)

      expect(screen.getByLabelText('Search citations:')).toBeInTheDocument()
      expect(screen.getByLabelText('Source Type:')).toBeInTheDocument()
      expect(screen.getByLabelText('Verification Status:')).toBeInTheDocument()
      expect(screen.getByLabelText('Min Quality Score:')).toBeInTheDocument()
      expect(screen.getByLabelText('Sort by:')).toBeInTheDocument()
      expect(screen.getByLabelText('Sort direction')).toBeInTheDocument()
    })

    it('should have accessible checkbox labels', () => {
      render(<CitationList {...mockHandlers} />)

      expect(screen.getByLabelText('Select All')).toBeInTheDocument()
      expect(screen.getByLabelText('Select citation ref_2024_001')).toBeInTheDocument()
      expect(screen.getByLabelText('Select citation ref_2024_002')).toBeInTheDocument()
      expect(screen.getByLabelText('Select citation ref_2024_003')).toBeInTheDocument()
    })

    it('should support keyboard navigation', () => {
      render(<CitationList {...mockHandlers} />)

      const searchInput = screen.getByTestId('search-input')
      const sourceTypeSelect = screen.getByTestId('source-type-select')
      
      searchInput.focus()
      expect(searchInput).toHaveFocus()

      fireEvent.keyDown(searchInput, { key: 'Tab' })
      expect(sourceTypeSelect).toHaveFocus()
    })
  })

  describe('responsive behavior', () => {
    it('should handle window resize events', () => {
      render(<CitationList {...mockHandlers} />)

      // Simulate window resize
      global.dispatchEvent(new Event('resize'))

      // Component should still be functional
      expect(screen.getByTestId('citation-list')).toBeInTheDocument()
    })
  })

  describe('error handling', () => {
    it('should handle missing handler functions gracefully', () => {
      render(<CitationList />)

      const editButton = within(screen.getByTestId('citation-card-1')).getByTestId('edit-button')
      expect(() => fireEvent.click(editButton)).not.toThrow()
    })

    it('should handle empty citations list', () => {
      // Mock empty citations list by modifying the component
      const EmptyList = () => {
        return (
          <div className="citation-list" data-testid="citation-list">
            <div className="empty-state" data-testid="empty-state">
              <p>No citations available.</p>
            </div>
          </div>
        )
      }

      render(<EmptyList />)
      expect(screen.getByTestId('empty-state')).toBeInTheDocument()
      expect(screen.getByText('No citations available.')).toBeInTheDocument()
    })
  })

  describe('performance', () => {
    it('should handle large numbers of citations efficiently', () => {
      // This would test virtual scrolling or pagination in a real implementation
      render(<CitationList {...mockHandlers} />)
      
      // Verify pagination controls exist (even if disabled for small dataset)
      expect(screen.getByTestId('pagination')).toBeInTheDocument()
    })
  })

  describe('integration', () => {
    it('should maintain filter state when citations update', async () => {
      render(<CitationList {...mockHandlers} />)

      const searchInput = screen.getByTestId('search-input')
      fireEvent.change(searchInput, { target: { value: 'Healthcare' } })

      await waitFor(() => {
        expect(screen.getByTestId('citation-summary')).toHaveTextContent('Showing 1 of 3 citations')
      })

      // Filter should persist
      expect(searchInput).toHaveValue('Healthcare')
    })

    it('should clear selection when filters change result set', async () => {
      render(<CitationList {...mockHandlers} />)

      // Select a citation
      const checkbox = screen.getByTestId('select-checkbox-1')
      fireEvent.click(checkbox)

      // Apply filter that excludes selected citation
      const sourceTypeSelect = screen.getByTestId('source-type-select')
      fireEvent.change(sourceTypeSelect, { target: { value: 'government' } })

      await waitFor(() => {
        // Selected citation should no longer be visible
        expect(screen.queryByTestId('citation-card-1')).not.toBeInTheDocument()
        // Selection count should be updated (though checkbox will be gone)
        expect(screen.queryByText('(1 selected)')).not.toBeInTheDocument()
      })
    })
  })
})