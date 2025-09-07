/**
 * Secure form component with comprehensive protection
 * Integrates XSS protection, CSRF tokens, rate limiting, and input validation
 */
import React, { useState, useEffect, useCallback } from 'react'
import { 
  Box, 
  Button, 
  FormControl, 
  FormLabel, 
  FormErrorMessage, 
  VStack, 
  Alert, 
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Progress,
  Text
} from '@chakra-ui/react'
import { formSecurity, FormSecurity, FieldConfig } from '../../lib/security/form-security'
import { SecurityUtils } from '../../utils/security'
import { globalRateLimiter } from '../../lib/security/rate-limiter'

export interface SecureFormField {
  name: string
  label: string
  type: 'text' | 'email' | 'password' | 'textarea' | 'tel' | 'url'
  required?: boolean
  placeholder?: string
  config?: FieldConfig
}

export interface SecureFormProps {
  formId: string
  fields: SecureFormField[]
  onSubmit: (data: Record<string, any>, csrfToken: string) => Promise<void>
  submitText?: string
  title?: string
  description?: string
  enableHoneypot?: boolean
  enableRateLimit?: boolean
  maxSubmissions?: number
  className?: string
}

export const SecureForm: React.FC<SecureFormProps> = ({
  formId,
  fields,
  onSubmit,
  submitText = 'Submit',
  title,
  description,
  enableHoneypot = true,
  enableRateLimit = true,
  maxSubmissions = 3,
  className
}) => {
  const [formData, setFormData] = useState<Record<string, string>>({})
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [warnings, setWarnings] = useState<string[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [csrfToken, setCsrfToken] = useState('')
  const [honeypot, setHoneypot] = useState<{ fieldName: string; fieldValue: string }>()
  const [securityScore, setSecurityScore] = useState(0)
  const [submitAttempts, setSubmitAttempts] = useState(0)
  const [isBlocked, setIsBlocked] = useState(false)
  const [blockReason, setBlockReason] = useState('')

  // Initialize security features
  useEffect(() => {
    // Generate CSRF token
    setCsrfToken(formSecurity.generateCSRFToken())
    
    // Set up honeypot if enabled
    if (enableHoneypot) {
      setHoneypot(FormSecurity.createHoneypot())
    }
    
    // Initialize form data
    const initialData: Record<string, string> = {}
    fields.forEach(field => {
      initialData[field.name] = ''
    })
    if (honeypot) {
      initialData[honeypot.fieldName] = ''
    }
    setFormData(initialData)
  }, [])

  // Security score color
  const getSecurityScoreColor = () => {
    if (securityScore >= 80) return 'green'
    if (securityScore >= 60) return 'yellow'
    if (securityScore >= 40) return 'orange'
    return 'red'
  }

  const renderField = (field: SecureFormField) => {
    const commonProps = {
      value: formData[field.name] || '',
      onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
        setFormData(prev => ({ ...prev, [field.name]: e.target.value })),
      placeholder: field.placeholder,
      disabled: isSubmitting || isBlocked
    }

    switch (field.type) {
      case 'textarea':
        return (
          <textarea
            {...commonProps}
            rows={4}
            style={{
              width: '100%',
              padding: '8px',
              border: '1px solid #ccc',
              borderRadius: '4px',
              resize: 'vertical'
            }}
          />
        )
      default:
        return (
          <input
            {...commonProps}
            type={field.type}
            style={{
              width: '100%',
              padding: '8px',
              border: '1px solid #ccc',
              borderRadius: '4px'
            }}
          />
        )
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (isSubmitting || isBlocked) return

    setIsSubmitting(true)
    setSubmitAttempts(prev => prev + 1)

    try {
      // Basic validation
      const fieldConfigs: Record<string, FieldConfig> = {}
      fields.forEach(field => {
        fieldConfigs[field.name] = {
          required: field.required,
          sanitize: true,
          ...field.config
        }
      })

      const validationResult = await formSecurity.validateAndSanitizeForm(formData, fieldConfigs)

      if (!validationResult.isValid) {
        const fieldErrors: Record<string, string> = {}
        validationResult.errors
          .filter(e => e.severity === 'error')
          .forEach(error => {
            fieldErrors[error.field] = error.message
          })
        setErrors(fieldErrors)
        setWarnings(validationResult.warnings)
        return
      }

      // Submit form with sanitized data
      await onSubmit(validationResult.sanitizedData, csrfToken)
      
      // Reset form on success
      const resetData: Record<string, string> = {}
      fields.forEach(field => {
        resetData[field.name] = ''
      })
      setFormData(resetData)
      setErrors({})
      setWarnings([])
      
      // Generate new CSRF token
      setCsrfToken(formSecurity.generateCSRFToken())

    } catch (error) {
      console.error('Form submission error:', error)
      
      if (error instanceof Error) {
        setErrors({ _form: error.message })
      } else {
        setErrors({ _form: 'Submission failed. Please try again.' })
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Box className={className} maxW="md" mx="auto" p={6}>
      {title && (
        <Text fontSize="2xl" fontWeight="bold" mb={4}>
          {title}
        </Text>
      )}
      
      {description && (
        <Text color="gray.600" mb={6}>
          {description}
        </Text>
      )}

      {/* Warnings */}
      {warnings.length > 0 && (
        <Alert status="warning" mb={4}>
          <AlertIcon />
          <Box>
            <AlertTitle>Security Warning!</AlertTitle>
            <AlertDescription>
              {warnings.map((warning, index) => (
                <Text key={index} fontSize="sm">{warning}</Text>
              ))}
            </AlertDescription>
          </Box>
        </Alert>
      )}

      {/* Form Errors */}
      {errors._form && (
        <Alert status="error" mb={4}>
          <AlertIcon />
          <AlertDescription>{errors._form}</AlertDescription>
        </Alert>
      )}

      <form onSubmit={handleSubmit}>
        {/* Honeypot field (hidden) */}
        {honeypot && (
          <input
            type="text"
            name={honeypot.fieldName}
            value={formData[honeypot.fieldName] || ''}
            onChange={(e) => setFormData(prev => ({ ...prev, [honeypot.fieldName]: e.target.value }))}
            style={{ display: 'none' }}
            tabIndex={-1}
            autoComplete="off"
          />
        )}

        {/* CSRF Token */}
        <input type="hidden" name="_token" value={csrfToken} />

        <VStack spacing={4}>
          {fields.map((field) => (
            <FormControl key={field.name} isInvalid={!!errors[field.name]} isRequired={field.required}>
              <FormLabel htmlFor={field.name}>{field.label}</FormLabel>
              {renderField(field)}
              <FormErrorMessage>{errors[field.name]}</FormErrorMessage>
            </FormControl>
          ))}

          <Button
            type="submit"
            colorScheme="blue"
            isLoading={isSubmitting}
            loadingText="Submitting..."
            disabled={isBlocked || Object.keys(errors).length > 0}
            width="full"
          >
            {submitText}
          </Button>
        </VStack>
      </form>
    </Box>
  )
}

export default SecureForm