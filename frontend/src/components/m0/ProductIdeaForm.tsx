import { forwardRef, useState, useEffect } from 'react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const productIdeaSchema = z.object({
  productIdea: z.string()
    .min(10, 'Please provide at least 10 characters describing your product idea')
    .max(500, 'Please keep your description under 500 characters'),
});

type ProductIdeaFormData = z.infer<typeof productIdeaSchema>;

interface ProductIdeaFormProps {
  onSubmit: (data: ProductIdeaFormData) => void;
  isLoading?: boolean;
  placeholder?: string;
  className?: string;
}

export const ProductIdeaForm = forwardRef<HTMLFormElement, ProductIdeaFormProps>(
  ({ onSubmit, isLoading = false, placeholder, className = '' }, ref) => {
    const [characterCount, setCharacterCount] = useState(0);

    const {
      register,
      handleSubmit,
      watch,
      formState: { errors, isValid },
      setValue,
      reset
    } = useForm<ProductIdeaFormData>({
      resolver: zodResolver(productIdeaSchema),
      mode: 'onChange'
    });

    const watchedValue = watch('productIdea', '');

    useEffect(() => {
      setCharacterCount(watchedValue?.length || 0);
    }, [watchedValue]);

    const handleFormSubmit = (data: ProductIdeaFormData) => {
      if (!isLoading) {
        onSubmit(data);
      }
    };

    const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (isValid && !isLoading) {
          handleSubmit(handleFormSubmit)();
        }
      }
    };

    return (
      <form
        ref={ref}
        onSubmit={handleSubmit(handleFormSubmit)}
        className={`w-full space-y-4 ${className}`}
        data-testid="product-idea-form"
      >
        <div className="relative">
          <div className="flex flex-col space-y-2">
            <label 
              htmlFor="productIdea" 
              className="block text-sm font-medium text-gray-700"
              data-testid="product-idea-label"
            >
              What's your product idea?
            </label>
            
            <div className="relative">
              <textarea
                id="productIdea"
                {...register('productIdea')}
                placeholder={placeholder || "Tell me about your product idea and I'll help validate it step by step. What are you thinking of launching?"}
                onKeyPress={handleKeyPress}
                disabled={isLoading}
                className={`
                  block w-full min-h-[120px] p-4 rounded-lg border resize-none
                  focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:ring-opacity-20
                  disabled:cursor-not-allowed disabled:bg-gray-50 disabled:text-gray-500
                  transition-all duration-200 ease-in-out
                  ${errors.productIdea 
                    ? 'border-red-300 focus:border-red-500 focus:ring-red-500' 
                    : 'border-gray-300 hover:border-gray-400'
                  }
                `}
                rows={4}
                data-testid="product-idea-textarea"
              />
              
              {/* Character counter */}
              <div className="absolute bottom-2 right-2 text-xs text-gray-400" data-testid="character-counter">
                {characterCount}/500
              </div>
            </div>

            {errors.productIdea && (
              <p className="text-sm text-red-600" role="alert" data-testid="product-idea-error">
                {errors.productIdea.message}
              </p>
            )}
          </div>

          {/* Suggestion chips for quick ideas */}
          <div className="mt-3" data-testid="suggestion-chips">
            <p className="text-xs text-gray-500 mb-2" data-testid="suggestions-label">Quick ideas:</p>
            <div className="flex flex-wrap gap-2">
              {[
                'Organic dog treats',
                'Smart home gadget',
                'Eco-friendly packaging',
                'Online fitness app',
                'Sustainable fashion'
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => setValue('productIdea', suggestion)}
                  disabled={isLoading}
                  className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded-full 
                           text-gray-700 transition-colors duration-150 ease-in-out
                           disabled:opacity-50 disabled:cursor-not-allowed"
                  data-testid={`suggestion-chip-${suggestion.toLowerCase().replace(/\s+/g, '-')}`}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between pt-2">
          <div className="text-xs text-gray-500" data-testid="form-instructions">
            Press Enter to submit, Shift+Enter for new line
          </div>
          
          <div className="flex items-center space-x-2" data-testid="form-actions">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => reset()}
              disabled={isLoading || !watchedValue}
              className="text-gray-500"
              data-testid="clear-button"
            >
              Clear
            </Button>
            
            <Button
              type="submit"
              isLoading={isLoading}
              disabled={!isValid || isLoading}
              className="min-w-[100px]"
              data-testid="submit-button"
            >
              {isLoading ? 'Analyzing...' : 'Start Analysis'}
            </Button>
          </div>
        </div>
      </form>
    );
  }
);

ProductIdeaForm.displayName = 'ProductIdeaForm';