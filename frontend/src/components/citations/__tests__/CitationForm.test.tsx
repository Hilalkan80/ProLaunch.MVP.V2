import React from 'react'
import { screen, fireEvent, waitFor, within } from '@testing-library/react'
import { render } from './setup'
import { vi } from 'vitest'

// Mock the citation API hooks
vi.mock('../../../lib/api/citations', () => ({
  useCreateCitation: vi.fn(() => ({
    mutate: vi.fn(),
    isLoading: false,
    error: null,
  })),
  useUpdateCitation: vi.fn(() => ({
    mutate: vi.fn(),
    isLoading: false,
    error: null,
  })),
}))

interface Citation {
  id?: string
  referenceId?: string
  title: string
  url?: string
  authors: string[]
  sourceType: 'web' | 'academic' | 'government' | 'news' | 'book' | 'video'
  excerpt?: string
  metadata?: Record<string, any>
  publicationDate?: string
}

interface CitationFormProps {
  citation?: Citation
  onSubmit?: (citation: Citation) => void
  onCancel?: () => void
  isLoading?: boolean
  mode?: 'create' | 'edit'
}

// Mock CitationForm component
const CitationForm = ({ 
  citation, 
  onSubmit, 
  onCancel, 
  isLoading = false,
  mode = 'create' 
}: CitationFormProps) => {
  const [formData, setFormData] = React.useState<Citation>({
    title: citation?.title || '',
    url: citation?.url || '',
    authors: citation?.authors || [],
    sourceType: citation?.sourceType || 'web',
    excerpt: citation?.excerpt || '',
    metadata: citation?.metadata || {},
    publicationDate: citation?.publicationDate || ''
  })

  const [errors, setErrors] = React.useState<Record<string, string>>({})
  const [authorInput, setAuthorInput] = React.useState('')

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (!formData.title.trim()) {
      newErrors.title = 'Title is required'
    }

    if (formData.url && !isValidUrl(formData.url)) {
      newErrors.url = 'Please enter a valid URL'
    }

    if (formData.sourceType === 'academic' && formData.authors.length === 0) {
      newErrors.authors = 'At least one author is required for academic sources'
    }

    if (formData.sourceType === 'book' && !formData.metadata?.isbn) {
      newErrors.isbn = 'ISBN is required for book sources'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const isValidUrl = (url: string): boolean => {
    try {
      new URL(url)
      return true
    } catch {
      return false
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!validateForm()) {
      // Focus first error field
      const firstErrorField = Object.keys(errors)[0]
      const element = document.querySelector(`[name="${firstErrorField}"]`) as HTMLElement
      element?.focus()
      return
    }

    onSubmit?.(formData)
  }

  const handleAddAuthor = () => {
    if (authorInput.trim() && !formData.authors.includes(authorInput.trim())) {
      setFormData({
        ...formData,
        authors: [...formData.authors, authorInput.trim()]
      })
      setAuthorInput('')
    }
  }

  const handleRemoveAuthor = (authorToRemove: string) => {
    setFormData({
      ...formData,
      authors: formData.authors.filter(author => author !== authorToRemove)
    })
  }

  const handleMetadataChange = (key: string, value: string) => {
    setFormData({
      ...formData,
      metadata: {
        ...formData.metadata,
        [key]: value
      }
    })
  }

  return (
    <form 
      onSubmit={handleSubmit} 
      data-testid="citation-form"
      role="form"
      aria-label={mode === 'create' ? 'Create citation' : 'Edit citation'}
    >
      <h2>{mode === 'create' ? 'Add New Citation' : 'Edit Citation'}</h2>

      <div className="form-group">
        <label htmlFor="title">
          Title <span className="required">*</span>
        </label>
        <input
          id="title"
          name="title"
          type="text"
          value={formData.title}
          onChange={(e) => {
            setFormData({ ...formData, title: e.target.value })
            if (errors.title) setErrors({ ...errors, title: '' })
          }}
          placeholder="Enter citation title..."
          data-testid="title-input"
          required
          aria-invalid={!!errors.title}
          aria-describedby={errors.title ? 'title-error' : undefined}
        />
        {errors.title && (
          <div id="title-error" className="error" role="alert" data-testid="title-error">
            {errors.title}
          </div>
        )}
      </div>

      <div className="form-group">
        <label htmlFor="url">URL</label>
        <input
          id="url"
          name="url"
          type="url"
          value={formData.url}
          onChange={(e) => {
            setFormData({ ...formData, url: e.target.value })
            if (errors.url) setErrors({ ...errors, url: '' })
          }}
          placeholder="https://example.com/article"
          data-testid="url-input"
          aria-invalid={!!errors.url}
          aria-describedby={errors.url ? 'url-error' : undefined}
        />
        {errors.url && (
          <div id="url-error" className="error" role="alert" data-testid="url-error">
            {errors.url}
          </div>
        )}
      </div>

      <div className="form-group">
        <label htmlFor="sourceType">Source Type</label>
        <select
          id="sourceType"
          name="sourceType"
          value={formData.sourceType}
          onChange={(e) => setFormData({ 
            ...formData, 
            sourceType: e.target.value as Citation['sourceType']
          })}
          data-testid="source-type-select"
          required
        >
          <option value="web">Web Article</option>
          <option value="academic">Academic Paper</option>
          <option value="government">Government Document</option>
          <option value="news">News Article</option>
          <option value="book">Book</option>
          <option value="video">Video</option>
        </select>
      </div>

      <div className="form-group">
        <label htmlFor="authors">Authors</label>
        <div className="authors-input" data-testid="authors-section">
          <div className="add-author">
            <input
              type="text"
              value={authorInput}
              onChange={(e) => setAuthorInput(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault()
                  handleAddAuthor()
                }
              }}
              placeholder="Enter author name..."
              data-testid="author-input"
              aria-label="Add author"
            />
            <button
              type="button"
              onClick={handleAddAuthor}
              disabled={!authorInput.trim()}
              data-testid="add-author-button"
            >
              Add Author
            </button>
          </div>

          {formData.authors.length > 0 && (
            <div className="authors-list" data-testid="authors-list">
              {formData.authors.map((author, index) => (
                <div key={index} className="author-tag" data-testid={`author-tag-${index}`}>
                  <span>{author}</span>
                  <button
                    type="button"
                    onClick={() => handleRemoveAuthor(author)}
                    aria-label={`Remove author ${author}`}
                    data-testid={`remove-author-${index}`}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}

          {errors.authors && (
            <div className="error" role="alert" data-testid="authors-error">
              {errors.authors}
            </div>
          )}
        </div>
      </div>

      {formData.sourceType === 'academic' && (
        <div className="form-group">
          <label htmlFor="journal">Journal</label>
          <input
            id="journal"
            type="text"
            value={formData.metadata?.journal || ''}
            onChange={(e) => handleMetadataChange('journal', e.target.value)}
            placeholder="Journal name..."
            data-testid="journal-input"
          />
        </div>
      )}

      {formData.sourceType === 'book' && (
        <div className="form-group">
          <label htmlFor="isbn">
            ISBN <span className="required">*</span>
          </label>
          <input
            id="isbn"
            name="isbn"
            type="text"
            value={formData.metadata?.isbn || ''}
            onChange={(e) => {
              handleMetadataChange('isbn', e.target.value)
              if (errors.isbn) setErrors({ ...errors, isbn: '' })
            }}
            placeholder="978-0-123456-78-9"
            data-testid="isbn-input"
            aria-invalid={!!errors.isbn}
            aria-describedby={errors.isbn ? 'isbn-error' : undefined}
          />
          {errors.isbn && (
            <div id="isbn-error" className="error" role="alert" data-testid="isbn-error">
              {errors.isbn}
            </div>
          )}
        </div>
      )}

      <div className="form-group">
        <label htmlFor="publicationDate">Publication Date</label>
        <input
          id="publicationDate"
          name="publicationDate"
          type="date"
          value={formData.publicationDate}
          onChange={(e) => setFormData({ ...formData, publicationDate: e.target.value })}
          data-testid="publication-date-input"
        />
      </div>

      <div className="form-group">
        <label htmlFor="excerpt">Excerpt</label>
        <textarea
          id="excerpt"
          name="excerpt"
          value={formData.excerpt}
          onChange={(e) => setFormData({ ...formData, excerpt: e.target.value })}
          placeholder="Brief excerpt or description..."
          rows={4}
          data-testid="excerpt-textarea"
          maxLength={500}
        />
        <div className="character-count" data-testid="excerpt-character-count">
          {formData.excerpt?.length || 0}/500
        </div>
      </div>

      <div className="form-actions" data-testid="form-actions">
        <button
          type="button"
          onClick={onCancel}
          disabled={isLoading}
          data-testid="cancel-button"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isLoading}
          data-testid="submit-button"
        >
          {isLoading 
            ? (mode === 'create' ? 'Adding...' : 'Saving...') 
            : (mode === 'create' ? 'Add Citation' : 'Save Changes')
          }
        </button>
      </div>

      {isLoading && (
        <div className="loading-overlay" data-testid="loading-overlay">
          <div>Processing citation...</div>
        </div>
      )}
    </form>
  )
}

describe('CitationForm', () => {
  const defaultProps = {
    onSubmit: vi.fn(),
    onCancel: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('rendering', () => {
    it('should render form in create mode by default', () => {
      render(<CitationForm {...defaultProps} />)

      expect(screen.getByText('Add New Citation')).toBeInTheDocument()
      expect(screen.getByTestId('submit-button')).toHaveTextContent('Add Citation')
    })

    it('should render form in edit mode when citation provided', () => {
      const citation: Citation = {
        title: 'Test Citation',
        authors: ['Author 1'],
        sourceType: 'academic'
      }

      render(<CitationForm {...defaultProps} citation={citation} mode="edit" />)

      expect(screen.getByText('Edit Citation')).toBeInTheDocument()
      expect(screen.getByTestId('submit-button')).toHaveTextContent('Save Changes')
      expect(screen.getByTestId('title-input')).toHaveValue('Test Citation')
    })

    it('should render all required form fields', () => {
      render(<CitationForm {...defaultProps} />)

      expect(screen.getByTestId('title-input')).toBeInTheDocument()
      expect(screen.getByTestId('url-input')).toBeInTheDocument()
      expect(screen.getByTestId('source-type-select')).toBeInTheDocument()
      expect(screen.getByTestId('authors-section')).toBeInTheDocument()
      expect(screen.getByTestId('publication-date-input')).toBeInTheDocument()
      expect(screen.getByTestId('excerpt-textarea')).toBeInTheDocument()
    })

    it('should show required field indicators', () => {
      render(<CitationForm {...defaultProps} />)

      const titleLabel = screen.getByLabelText(/Title/)
      expect(titleLabel).toBeRequired()
      
      // Check for required asterisk in the DOM
      expect(screen.getByText('*')).toBeInTheDocument()
    })

    it('should render character counter for excerpt', () => {
      render(<CitationForm {...defaultProps} />)

      expect(screen.getByTestId('excerpt-character-count')).toHaveTextContent('0/500')
    })
  })

  describe('form interactions', () => {
    it('should update title field when typing', async () => {
      render(<CitationForm {...defaultProps} />)

      const titleInput = screen.getByTestId('title-input')
      fireEvent.change(titleInput, { target: { value: 'New Citation Title' } })

      expect(titleInput).toHaveValue('New Citation Title')
    })

    it('should update URL field when typing', async () => {
      render(<CitationForm {...defaultProps} />)

      const urlInput = screen.getByTestId('url-input')
      fireEvent.change(urlInput, { target: { value: 'https://example.com' } })

      expect(urlInput).toHaveValue('https://example.com')
    })

    it('should change source type via select', async () => {
      render(<CitationForm {...defaultProps} />)

      const sourceTypeSelect = screen.getByTestId('source-type-select')
      fireEvent.change(sourceTypeSelect, { target: { value: 'academic' } })

      expect(sourceTypeSelect).toHaveValue('academic')
    })

    it('should add authors to the list', async () => {
      render(<CitationForm {...defaultProps} />)

      const authorInput = screen.getByTestId('author-input')
      const addButton = screen.getByTestId('add-author-button')

      fireEvent.change(authorInput, { target: { value: 'Dr. Jane Smith' } })
      fireEvent.click(addButton)

      expect(screen.getByTestId('authors-list')).toBeInTheDocument()
      expect(screen.getByTestId('author-tag-0')).toHaveTextContent('Dr. Jane Smith')
      expect(authorInput).toHaveValue('')
    })

    it('should add author by pressing Enter', async () => {
      render(<CitationForm {...defaultProps} />)

      const authorInput = screen.getByTestId('author-input')
      fireEvent.change(authorInput, { target: { value: 'Prof. John Doe' } })
      fireEvent.keyPress(authorInput, { key: 'Enter', code: 13 })

      expect(screen.getByTestId('author-tag-0')).toHaveTextContent('Prof. John Doe')
    })

    it('should remove authors from the list', async () => {
      render(<CitationForm {...defaultProps} />)

      const authorInput = screen.getByTestId('author-input')
      const addButton = screen.getByTestId('add-author-button')

      // Add an author
      fireEvent.change(authorInput, { target: { value: 'Test Author' } })
      fireEvent.click(addButton)

      // Remove the author
      const removeButton = screen.getByTestId('remove-author-0')
      fireEvent.click(removeButton)

      expect(screen.queryByTestId('author-tag-0')).not.toBeInTheDocument()
    })

    it('should prevent duplicate authors', async () => {
      render(<CitationForm {...defaultProps} />)

      const authorInput = screen.getByTestId('author-input')
      const addButton = screen.getByTestId('add-author-button')

      // Add same author twice
      fireEvent.change(authorInput, { target: { value: 'Duplicate Author' } })
      fireEvent.click(addButton)
      
      fireEvent.change(authorInput, { target: { value: 'Duplicate Author' } })
      fireEvent.click(addButton)

      // Should only have one author
      expect(screen.getAllByTestId(/author-tag-/).length).toBe(1)
    })

    it('should update excerpt and character count', async () => {
      render(<CitationForm {...defaultProps} />)

      const excerptTextarea = screen.getByTestId('excerpt-textarea')
      const testExcerpt = 'This is a test excerpt for the citation form.'

      fireEvent.change(excerptTextarea, { target: { value: testExcerpt } })

      expect(excerptTextarea).toHaveValue(testExcerpt)
      expect(screen.getByTestId('excerpt-character-count')).toHaveTextContent(`${testExcerpt.length}/500`)
    })
  })

  describe('conditional fields', () => {
    it('should show journal field for academic sources', async () => {
      render(<CitationForm {...defaultProps} />)

      const sourceTypeSelect = screen.getByTestId('source-type-select')
      fireEvent.change(sourceTypeSelect, { target: { value: 'academic' } })

      await waitFor(() => {
        expect(screen.getByTestId('journal-input')).toBeInTheDocument()
      })
    })

    it('should show ISBN field for book sources', async () => {
      render(<CitationForm {...defaultProps} />)

      const sourceTypeSelect = screen.getByTestId('source-type-select')
      fireEvent.change(sourceTypeSelect, { target: { value: 'book' } })

      await waitFor(() => {
        expect(screen.getByTestId('isbn-input')).toBeInTheDocument()
      })
    })

    it('should hide conditional fields when source type changes', async () => {
      render(<CitationForm {...defaultProps} />)

      const sourceTypeSelect = screen.getByTestId('source-type-select')
      
      // Show journal field
      fireEvent.change(sourceTypeSelect, { target: { value: 'academic' } })
      await waitFor(() => {
        expect(screen.getByTestId('journal-input')).toBeInTheDocument()
      })

      // Switch to web and journal field should disappear
      fireEvent.change(sourceTypeSelect, { target: { value: 'web' } })
      await waitFor(() => {
        expect(screen.queryByTestId('journal-input')).not.toBeInTheDocument()
      })
    })
  })

  describe('form validation', () => {
    it('should show error for empty title', async () => {
      render(<CitationForm {...defaultProps} />)

      const submitButton = screen.getByTestId('submit-button')
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(screen.getByTestId('title-error')).toHaveTextContent('Title is required')
      })

      expect(defaultProps.onSubmit).not.toHaveBeenCalled()
    })

    it('should show error for invalid URL', async () => {
      render(<CitationForm {...defaultProps} />)

      const titleInput = screen.getByTestId('title-input')
      const urlInput = screen.getByTestId('url-input')
      const submitButton = screen.getByTestId('submit-button')

      fireEvent.change(titleInput, { target: { value: 'Valid Title' } })
      fireEvent.change(urlInput, { target: { value: 'invalid-url' } })
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(screen.getByTestId('url-error')).toHaveTextContent('Please enter a valid URL')
      })
    })

    it('should require author for academic sources', async () => {
      render(<CitationForm {...defaultProps} />)

      const titleInput = screen.getByTestId('title-input')
      const sourceTypeSelect = screen.getByTestId('source-type-select')
      const submitButton = screen.getByTestId('submit-button')

      fireEvent.change(titleInput, { target: { value: 'Academic Paper' } })
      fireEvent.change(sourceTypeSelect, { target: { value: 'academic' } })
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(screen.getByTestId('authors-error')).toHaveTextContent(
          'At least one author is required for academic sources'
        )
      })
    })

    it('should require ISBN for book sources', async () => {
      render(<CitationForm {...defaultProps} />)

      const titleInput = screen.getByTestId('title-input')
      const sourceTypeSelect = screen.getByTestId('source-type-select')
      const submitButton = screen.getByTestId('submit-button')

      fireEvent.change(titleInput, { target: { value: 'Book Title' } })
      fireEvent.change(sourceTypeSelect, { target: { value: 'book' } })
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(screen.getByTestId('isbn-error')).toHaveTextContent('ISBN is required for book sources')
      })
    })

    it('should clear errors when user starts typing', async () => {
      render(<CitationForm {...defaultProps} />)

      // Trigger title error
      const submitButton = screen.getByTestId('submit-button')
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(screen.getByTestId('title-error')).toBeInTheDocument()
      })

      // Start typing in title field
      const titleInput = screen.getByTestId('title-input')
      fireEvent.change(titleInput, { target: { value: 'New Title' } })

      expect(screen.queryByTestId('title-error')).not.toBeInTheDocument()
    })

    it('should focus first error field on validation failure', async () => {
      render(<CitationForm {...defaultProps} />)

      const titleInput = screen.getByTestId('title-input')
      const submitButton = screen.getByTestId('submit-button')

      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(titleInput).toHaveFocus()
      })
    })
  })

  describe('form submission', () => {
    it('should submit form with valid data', async () => {
      render(<CitationForm {...defaultProps} />)

      const titleInput = screen.getByTestId('title-input')
      const urlInput = screen.getByTestId('url-input')
      const submitButton = screen.getByTestId('submit-button')

      fireEvent.change(titleInput, { target: { value: 'Valid Citation' } })
      fireEvent.change(urlInput, { target: { value: 'https://example.com' } })
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(defaultProps.onSubmit).toHaveBeenCalledWith(
          expect.objectContaining({
            title: 'Valid Citation',
            url: 'https://example.com',
            sourceType: 'web'
          })
        )
      })
    })

    it('should call onCancel when cancel button clicked', () => {
      render(<CitationForm {...defaultProps} />)

      const cancelButton = screen.getByTestId('cancel-button')
      fireEvent.click(cancelButton)

      expect(defaultProps.onCancel).toHaveBeenCalled()
    })

    it('should disable form during loading', () => {
      render(<CitationForm {...defaultProps} isLoading={true} />)

      const submitButton = screen.getByTestId('submit-button')
      const cancelButton = screen.getByTestId('cancel-button')

      expect(submitButton).toBeDisabled()
      expect(cancelButton).toBeDisabled()
      expect(submitButton).toHaveTextContent('Adding...')
      expect(screen.getByTestId('loading-overlay')).toBeInTheDocument()
    })

    it('should show saving text in edit mode during loading', () => {
      const citation: Citation = {
        title: 'Test Citation',
        authors: [],
        sourceType: 'web'
      }

      render(<CitationForm {...defaultProps} citation={citation} mode="edit" isLoading={true} />)

      expect(screen.getByTestId('submit-button')).toHaveTextContent('Saving...')
    })
  })

  describe('accessibility', () => {
    it('should have proper form role and labels', () => {
      render(<CitationForm {...defaultProps} />)

      const form = screen.getByTestId('citation-form')
      expect(form).toHaveAttribute('role', 'form')
      expect(form).toHaveAttribute('aria-label', 'Create citation')
    })

    it('should have accessible field labels', () => {
      render(<CitationForm {...defaultProps} />)

      expect(screen.getByLabelText(/Title/)).toBeInTheDocument()
      expect(screen.getByLabelText(/URL/)).toBeInTheDocument()
      expect(screen.getByLabelText(/Source Type/)).toBeInTheDocument()
      expect(screen.getByLabelText(/Publication Date/)).toBeInTheDocument()
      expect(screen.getByLabelText(/Excerpt/)).toBeInTheDocument()
    })

    it('should associate errors with form fields via aria-describedby', async () => {
      render(<CitationForm {...defaultProps} />)

      const submitButton = screen.getByTestId('submit-button')
      fireEvent.click(submitButton)

      await waitFor(() => {
        const titleInput = screen.getByTestId('title-input')
        const titleError = screen.getByTestId('title-error')
        
        expect(titleInput).toHaveAttribute('aria-invalid', 'true')
        expect(titleInput).toHaveAttribute('aria-describedby', 'title-error')
        expect(titleError).toHaveAttribute('role', 'alert')
      })
    })

    it('should have accessible author removal buttons', async () => {
      render(<CitationForm {...defaultProps} />)

      const authorInput = screen.getByTestId('author-input')
      const addButton = screen.getByTestId('add-author-button')

      fireEvent.change(authorInput, { target: { value: 'Test Author' } })
      fireEvent.click(addButton)

      const removeButton = screen.getByTestId('remove-author-0')
      expect(removeButton).toHaveAttribute('aria-label', 'Remove author Test Author')
    })

    it('should support keyboard navigation', () => {
      render(<CitationForm {...defaultProps} />)

      const titleInput = screen.getByTestId('title-input')
      const urlInput = screen.getByTestId('url-input')

      titleInput.focus()
      expect(titleInput).toHaveFocus()

      fireEvent.keyDown(titleInput, { key: 'Tab' })
      expect(urlInput).toHaveFocus()
    })
  })

  describe('data prefilling', () => {
    it('should prefill form with existing citation data', () => {
      const citation: Citation = {
        id: 'existing-1',
        referenceId: 'ref_001',
        title: 'Existing Citation',
        url: 'https://existing.com',
        authors: ['Dr. Existing', 'Prof. Citation'],
        sourceType: 'academic',
        excerpt: 'This is an existing citation.',
        metadata: { journal: 'Test Journal' },
        publicationDate: '2024-01-15'
      }

      render(<CitationForm {...defaultProps} citation={citation} mode="edit" />)

      expect(screen.getByTestId('title-input')).toHaveValue('Existing Citation')
      expect(screen.getByTestId('url-input')).toHaveValue('https://existing.com')
      expect(screen.getByTestId('source-type-select')).toHaveValue('academic')
      expect(screen.getByTestId('excerpt-textarea')).toHaveValue('This is an existing citation.')
      expect(screen.getByTestId('publication-date-input')).toHaveValue('2024-01-15')
      
      // Check authors are prefilled
      expect(screen.getByText('Dr. Existing')).toBeInTheDocument()
      expect(screen.getByText('Prof. Citation')).toBeInTheDocument()
      
      // Check metadata is prefilled
      expect(screen.getByTestId('journal-input')).toHaveValue('Test Journal')
    })
  })

  describe('error handling', () => {
    it('should handle missing handler functions gracefully', () => {
      render(<CitationForm />)

      const cancelButton = screen.getByTestId('cancel-button')
      expect(() => fireEvent.click(cancelButton)).not.toThrow()
    })

    it('should handle form submission without onSubmit handler', async () => {
      render(<CitationForm onCancel={vi.fn()} />)

      const titleInput = screen.getByTestId('title-input')
      const submitButton = screen.getByTestId('submit-button')

      fireEvent.change(titleInput, { target: { value: 'Valid Title' } })
      
      expect(() => fireEvent.click(submitButton)).not.toThrow()
    })
  })

  describe('edge cases', () => {
    it('should handle very long excerpt text', async () => {
      render(<CitationForm {...defaultProps} />)

      const excerptTextarea = screen.getByTestId('excerpt-textarea')
      const longText = 'a'.repeat(600) // Exceeds 500 character limit

      fireEvent.change(excerptTextarea, { target: { value: longText } })

      // Should be truncated to maxLength
      expect(excerptTextarea.value.length).toBeLessThanOrEqual(500)
    })

    it('should handle empty author input', () => {
      render(<CitationForm {...defaultProps} />)

      const addButton = screen.getByTestId('add-author-button')
      expect(addButton).toBeDisabled()

      // Button should remain disabled for whitespace-only input
      const authorInput = screen.getByTestId('author-input')
      fireEvent.change(authorInput, { target: { value: '   ' } })
      expect(addButton).toBeDisabled()
    })

    it('should handle special characters in author names', async () => {
      render(<CitationForm {...defaultProps} />)

      const authorInput = screen.getByTestId('author-input')
      const addButton = screen.getByTestId('add-author-button')

      const specialAuthor = "O'Connor, Mary-Jane (PhD)"
      fireEvent.change(authorInput, { target: { value: specialAuthor } })
      fireEvent.click(addButton)

      expect(screen.getByText(specialAuthor)).toBeInTheDocument()
    })
  })
})