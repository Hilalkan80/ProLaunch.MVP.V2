import { forwardRef, useState, useEffect } from 'react';
import { Button } from '../ui/Button';

interface ShareOption {
  id: string;
  label: string;
  icon: React.ReactNode;
  action: (url: string, title: string) => void;
  available: boolean;
}

interface ShareModalProps {
  isOpen: boolean;
  onClose: () => void;
  url: string;
  title: string;
  description?: string;
  className?: string;
}

export const ShareModal = forwardRef<HTMLDivElement, ShareModalProps>(
  ({ isOpen, onClose, url, title, description, className = '' }, ref) => {
    const [copied, setCopied] = useState(false);

    const copyToClipboard = async (text: string) => {
      try {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      } catch (err) {
        console.error('Failed to copy text: ', err);
      }
    };

    const shareOptions: ShareOption[] = [
      {
        id: 'twitter',
        label: 'Twitter',
        icon: (
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M23.953 4.57a10 10 0 01-2.825.775 4.958 4.958 0 002.163-2.723c-.951.555-2.005.959-3.127 1.184a4.92 4.92 0 00-8.384 4.482C7.69 8.095 4.067 6.13 1.64 3.162a4.822 4.822 0 00-.666 2.475c0 1.71.87 3.213 2.188 4.096a4.904 4.904 0 01-2.228-.616v.06a4.923 4.923 0 003.946 4.827 4.996 4.996 0 01-2.212.085 4.936 4.936 0 004.604 3.417 9.867 9.867 0 01-6.102 2.105c-.39 0-.779-.023-1.17-.067a13.995 13.995 0 007.557 2.209c9.053 0 13.998-7.496 13.998-13.985 0-.21 0-.42-.015-.63A9.935 9.935 0 0024 4.59z"/>
          </svg>
        ),
        action: (url, title) => {
          const text = encodeURIComponent(`Check out my feasibility report: ${title}`);
          window.open(`https://twitter.com/intent/tweet?text=${text}&url=${encodeURIComponent(url)}`, '_blank');
        },
        available: true
      },
      {
        id: 'linkedin',
        label: 'LinkedIn',
        icon: (
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
          </svg>
        ),
        action: (url, title) => {
          const summary = encodeURIComponent(`Check out my product feasibility analysis: ${title}`);
          window.open(`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}&summary=${summary}`, '_blank');
        },
        available: true
      },
      {
        id: 'facebook',
        label: 'Facebook',
        icon: (
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
          </svg>
        ),
        action: (url, title) => {
          window.open(`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`, '_blank');
        },
        available: true
      },
      {
        id: 'email',
        label: 'Email',
        icon: (
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 12.713L.015 3h23.97L12 12.713zM0 4.562v15.176L8.728 12 0 4.562zm10.382 8.244L1.077 21h21.846l-9.305-8.194-1.536 1.355c-.363.32-.864.32-1.227 0l-1.473-1.355zM15.272 12L24 4.562v15.176L15.272 12z"/>
          </svg>
        ),
        action: (url, title) => {
          const subject = encodeURIComponent(`Check out my feasibility report: ${title}`);
          const body = encodeURIComponent(`I just completed a feasibility analysis for my product idea. Take a look: ${url}`);
          window.location.href = `mailto:?subject=${subject}&body=${body}`;
        },
        available: true
      },
      {
        id: 'native',
        label: 'Share',
        icon: (
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.81 2.04.81 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.50-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92s2.92-1.31 2.92-2.92S19.61 16.08 18 16.08z"/>
          </svg>
        ),
        action: async (url, title) => {
          if (navigator.share) {
            try {
              await navigator.share({
                title: title,
                url: url,
                text: `Check out my feasibility report: ${title}`
              });
            } catch (err) {
              console.error('Error sharing:', err);
            }
          }
        },
        available: typeof navigator !== 'undefined' && 'share' in navigator
      }
    ];

    useEffect(() => {
      if (isOpen) {
        document.body.style.overflow = 'hidden';
      } else {
        document.body.style.overflow = 'unset';
      }

      return () => {
        document.body.style.overflow = 'unset';
      };
    }, [isOpen]);

    if (!isOpen) return null;

    return (
      <div className="fixed inset-0 z-50 overflow-y-auto" data-testid="share-modal">
        <div className="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
          <div 
            className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" 
            onClick={onClose}
            data-testid="share-modal-backdrop"
          />
          
          <div 
            ref={ref}
            className={`relative transform overflow-hidden rounded-lg bg-white px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-sm sm:p-6 ${className}`}
            data-testid="share-modal-content"
          >
            <div>
              <div className="flex items-center justify-between mb-4" data-testid="share-modal-header">
                <h3 className="text-lg font-medium text-gray-900" data-testid="share-modal-title">
                  Share Report
                </h3>
                <button
                  onClick={onClose}
                  className="text-gray-400 hover:text-gray-600"
                  data-testid="share-modal-close"
                >
                  <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M6 18L18 6M6 6l12 12" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </button>
              </div>

              <div className="mb-4" data-testid="share-modal-description">
                <p className="text-sm text-gray-600 mb-2" data-testid="share-instruction">Share your feasibility report:</p>
                <p className="font-medium text-gray-900 text-sm" data-testid="share-title">{title}</p>
                {description && (
                  <p className="text-xs text-gray-500 mt-1" data-testid="share-description">{description}</p>
                )}
              </div>

              {/* Copy Link */}
              <div className="mb-4" data-testid="copy-link-section">
                <label className="block text-sm font-medium text-gray-700 mb-2" data-testid="copy-link-label">
                  Copy Link
                </label>
                <div className="flex">
                  <input
                    type="text"
                    value={url}
                    readOnly
                    className="block w-full min-w-0 flex-1 rounded-l-md border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-blue-500"
                    data-testid="share-url-input"
                  />
                  <button
                    onClick={() => copyToClipboard(url)}
                    className={`inline-flex items-center rounded-r-md border border-l-0 px-3 py-2 text-sm font-medium transition-colors ${
                      copied 
                        ? 'border-green-300 bg-green-50 text-green-700' 
                        : 'border-gray-300 bg-gray-50 text-gray-700 hover:bg-gray-100'
                    }`}
                    data-testid="copy-url-button"
                  >
                    {copied ? 'Copied!' : 'Copy'}
                  </button>
                </div>
              </div>

              {/* Share Options */}
              <div className="grid grid-cols-2 gap-3" data-testid="share-options">
                {shareOptions
                  .filter(option => option.available)
                  .map((option) => (
                  <button
                    key={option.id}
                    onClick={() => option.action(url, title)}
                    className="flex items-center justify-center space-x-2 rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                    data-testid={`share-option-${option.id}`}
                  >
                    {option.icon}
                    <span>{option.label}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }
);

ShareModal.displayName = 'ShareModal';

interface ShareButtonProps {
  url: string;
  title: string;
  description?: string;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'primary' | 'secondary' | 'ghost';
  className?: string;
}

export const ShareButton = forwardRef<HTMLButtonElement, ShareButtonProps>(
  ({ url, title, description, size = 'md', variant = 'ghost', className = '' }, ref) => {
    const [isShareModalOpen, setIsShareModalOpen] = useState(false);

    return (
      <>
        <Button
          ref={ref}
          onClick={() => setIsShareModalOpen(true)}
          variant={variant}
          size={size}
          className={className}
          data-testid="share-button"
        >
          <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 24 24">
            <path d="M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.81 2.04.81 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.50-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92s2.92-1.31 2.92-2.92S19.61 16.08 18 16.08z"/>
          </svg>
          Share
        </Button>

        <ShareModal
          isOpen={isShareModalOpen}
          onClose={() => setIsShareModalOpen(false)}
          url={url}
          title={title}
          description={description}
        />
      </>
    );
  }
);

ShareButton.displayName = 'ShareButton';

interface ExportButtonProps {
  onExportPDF?: () => void;
  onExportJSON?: () => void;
  onExportCSV?: () => void;
  isLoading?: boolean;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'primary' | 'secondary' | 'ghost';
  className?: string;
}

export const ExportButton = forwardRef<HTMLButtonElement, ExportButtonProps>(
  ({ 
    onExportPDF, 
    onExportJSON, 
    onExportCSV, 
    isLoading = false,
    size = 'md', 
    variant = 'ghost',
    className = '' 
  }, ref) => {
    const [showDropdown, setShowDropdown] = useState(false);

    const exportOptions = [
      { label: 'Export as PDF', action: onExportPDF, icon: '📄' },
      { label: 'Export as JSON', action: onExportJSON, icon: '📄' },
      { label: 'Export as CSV', action: onExportCSV, icon: '📊' }
    ].filter(option => option.action);

    if (exportOptions.length === 1) {
      // Single export option - show as direct button
      return (
        <Button
          ref={ref}
          onClick={exportOptions[0].action}
          variant={variant}
          size={size}
          isLoading={isLoading}
          className={className}
          data-testid="export-button-single"
        >
          <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 24 24">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z"/>
            <polyline points="14,2 14,8 20,8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
            <polyline points="10,9 9,9 8,9"/>
          </svg>
          Export
        </Button>
      );
    }

    return (
      <div className="relative" data-testid="export-dropdown">
        <Button
          ref={ref}
          onClick={() => setShowDropdown(!showDropdown)}
          variant={variant}
          size={size}
          isLoading={isLoading}
          className={className}
          data-testid="export-button-dropdown"
        >
          <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 24 24">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z"/>
            <polyline points="14,2 14,8 20,8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
            <polyline points="10,9 9,9 8,9"/>
          </svg>
          Export
          <svg className="w-4 h-4 ml-1" fill="currentColor" viewBox="0 0 24 24">
            <path d="M7 10l5 5 5-5z"/>
          </svg>
        </Button>

        {showDropdown && (
          <>
            <div 
              className="fixed inset-0 z-10" 
              onClick={() => setShowDropdown(false)}
              data-testid="export-dropdown-backdrop"
            />
            <div className="absolute right-0 z-20 mt-1 w-48 rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5" data-testid="export-dropdown-menu">
              <div className="py-1">
                {exportOptions.map((option, index) => (
                  <button
                    key={index}
                    onClick={() => {
                      option.action!();
                      setShowDropdown(false);
                    }}
                    className="flex w-full items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    data-testid={`export-option-${index}`}
                  >
                    <span className="mr-3">{option.icon}</span>
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    );
  }
);

ExportButton.displayName = 'ExportButton';