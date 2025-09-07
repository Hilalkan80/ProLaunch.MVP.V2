import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { forgotPasswordSchema } from '../../lib/validation/auth-schemas';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Alert } from '../ui/Alert';
import type { ForgotPasswordData } from '../../types/auth';

export const ForgotPasswordForm = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [isSuccess, setIsSuccess] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotPasswordData>({
    resolver: zodResolver(forgotPasswordSchema),
  });

  const onSubmit = async (data: ForgotPasswordData) => {
    try {
      setIsLoading(true);
      setError('');
      // TODO: Implement password reset logic
      console.log('Forgot password data:', data);
      setIsSuccess(true);
    } catch (err) {
      setError('An error occurred while sending reset instructions');
      setIsSuccess(false);
    } finally {
      setIsLoading(false);
    }
  };

  if (isSuccess) {
    return (
      <div className="text-center">
        <Alert variant="success" className="mb-4">
          Password reset instructions have been sent to your email
        </Alert>
        <p className="text-sm text-gray-600 mb-4">
          Check your email for instructions to reset your password
        </p>
        <a
          href="/auth/signin"
          className="text-blue-600 hover:text-blue-500 text-sm"
        >
          Return to sign in
        </a>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      {error && (
        <Alert variant="error" role="alert">
          {error}
        </Alert>
      )}

      <p className="text-sm text-gray-600">
        Enter your email address and we'll send you instructions to reset your
        password.
      </p>

      <div className="space-y-2">
        <Input
          label="Email"
          type="email"
          {...register('email')}
          error={errors.email?.message}
          disabled={isLoading}
        />
      </div>

      <Button
        type="submit"
        variant="primary"
        isLoading={isLoading}
        className="w-full"
      >
        Send reset instructions
      </Button>

      <p className="text-center text-sm text-gray-600">
        Remember your password?{' '}
        <a href="/auth/signin" className="text-blue-600 hover:text-blue-500">
          Sign in
        </a>
      </p>
    </form>
  );
};