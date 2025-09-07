/**
 * Login form component
 */
import React, { useState } from 'react'
import {
  Box,
  Button,
  Checkbox,
  FormControl,
  FormErrorMessage,
  FormLabel,
  Input,
  InputGroup,
  InputRightElement,
  Link,
  Stack,
  Text,
  useToast,
  VStack
} from '@chakra-ui/react'
import { useForm } from 'react-hook-form'
import { AuthService } from '../../lib/auth'

interface LoginFormProps {
  onSuccess?: () => void
  onError?: (error: Error) => void
  redirectTo?: string
}

interface LoginFormInputs {
  email: string
  password: string
  rememberMe?: boolean
}

export const LoginForm: React.FC<LoginFormProps> = ({ onSuccess, onError, redirectTo }) => {
  const [isLoading, setIsLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const authService = new AuthService()
  const toast = useToast()

  const {
    register,
    handleSubmit,
    formState: { errors },
    setError,
    setFocus
  } = useForm<LoginFormInputs>()

  const onSubmit = async (data: LoginFormInputs) => {
    try {
      setIsLoading(true)

      await authService.login({ email: data.email, password: data.password })

      if (data.rememberMe) {
        localStorage.setItem('remembered_email', data.email)
      }

      onSuccess?.()

      toast({
        title: 'Login successful',
        status: 'success',
        duration: 3000,
        isClosable: true
      })
    } catch (error) {
      setError('root', {
        type: 'manual',
        message: error.message
      })

      onError?.(error)

      toast({
        title: 'Login failed',
        description: error.message,
        status: 'error',
        duration: 5000,
        isClosable: true
      })

      // Focus first invalid field
      if (errors.email) {
        setFocus('email')
      } else if (errors.password) {
        setFocus('password')
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Box as="form" onSubmit={handleSubmit(onSubmit)} role="form" aria-label="Login form">
      <VStack spacing={4}>
        <FormControl isInvalid={!!errors.email}>
          <FormLabel htmlFor="email">Email</FormLabel>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            {...register('email', {
              required: 'Email is required',
              pattern: {
                value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                message: 'Invalid email format'
              }
            })}
          />
          <FormErrorMessage role="alert">{errors.email?.message}</FormErrorMessage>
        </FormControl>

        <FormControl isInvalid={!!errors.password}>
          <FormLabel htmlFor="password" aria-label="Password input">Password</FormLabel>
          <InputGroup>
            <Input
              id="password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              {...register('password', {
                required: 'Password is required'
              })}
            />
            <InputRightElement width="4.5rem">
              <Button
                h="1.75rem"
                size="sm"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? 'Hide' : 'Show'}
              </Button>
            </InputRightElement>
          </InputGroup>
          <FormErrorMessage role="alert">{errors.password?.message}</FormErrorMessage>
        </FormControl>

        <Stack
          direction={{ base: 'column', sm: 'row' }}
          align="center"
          justify="space-between"
          width="100%"
        >
          <Checkbox {...register('rememberMe')}>Remember me</Checkbox>
          <Link color="blue.500" href="/forgot-password">
            Forgot password?
          </Link>
        </Stack>

        {errors.root && (
          <Text color="red.500" role="alert">
            {errors.root.message}
          </Text>
        )}

        <Button
          type="submit"
          colorScheme="blue"
          width="100%"
          isLoading={isLoading}
          loadingText="Signing in"
        >
          Sign in
        </Button>

        <Stack direction="row" spacing={1}>
          <Text>Don't have an account?</Text>
          <Link color="blue.500" href="/signup">
            Sign up
          </Link>
        </Stack>
      </VStack>
    </Box>
  )
}