import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { signInSchema } from '../../lib/validation/auth-schemas';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Alert } from '../ui/Alert';
import type { SignInData } from '../../types/auth';

export const SignInForm = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<SignInData>({
    resolver: zodResolver(signInSchema),
  });

  const onSubmit = async (data: SignInData) => {
    try {
      setIsLoading(true);
      setError('');
      // TODO: Implement sign in logic
      console.log('Sign in data:', data);
    } catch (err) {
      setError('An error occurred during sign in');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      {error && (
        <Alert variant="error" role="alert">
          {error}
        </Alert>
      )}
      
      <div className="space-y-2">
        <Input
          label="Email"
          type="email"
          {...register('email')}
          error={errors.email?.message}
          disabled={isLoading}
        />
      </div>

      <div className="space-y-2">
        <Input
          label="Password"
          type="password"
          {...register('password')}
          error={errors.password?.message}
          disabled={isLoading}
        />
      </div>

      <div className="flex items-center justify-between">
        <label className="flex items-center space-x-2">
          <input
            type="checkbox"
            {...register('rememberMe')}
            className="h-4 w-4 rounded border-gray-300"
          />
          <span className="text-sm text-gray-600">Remember me</span>
        </label>

        <a
          href="/auth/forgot-password"
          className="text-sm text-blue-600 hover:text-blue-500"
        >
          Forgot password?
        </a>
      </div>

      <Button
        type="submit"
        variant="primary"
        isLoading={isLoading}
        className="w-full"
      >
        Sign in
      </Button>

      <p className="text-center text-sm text-gray-600">
        Don't have an account?{' '}
        <a href="/auth/signup" className="text-blue-600 hover:text-blue-500">
          Sign up
        </a>
      </p>
    </form>
  );
};