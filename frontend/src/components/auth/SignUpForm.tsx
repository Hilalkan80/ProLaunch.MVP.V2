import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { signUpSchema } from '../../lib/validation/auth-schemas';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Alert } from '../ui/Alert';
import type { SignUpData } from '../../types/auth';

export const SignUpForm = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<SignUpData>({
    resolver: zodResolver(signUpSchema),
  });

  const password = watch('password');

  const onSubmit = async (data: SignUpData) => {
    try {
      setIsLoading(true);
      setError('');
      // TODO: Implement sign up logic
      console.log('Sign up data:', data);
    } catch (err) {
      setError('An error occurred during sign up');
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
          label="Name"
          {...register('name')}
          error={errors.name?.message}
          disabled={isLoading}
        />
      </div>

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

      <div className="space-y-2">
        <Input
          label="Confirm Password"
          type="password"
          {...register('confirmPassword', {
            validate: value => value === password || 'Passwords do not match',
          })}
          error={errors.confirmPassword?.message}
          disabled={isLoading}
        />
      </div>

      <div className="space-y-2">
        <label className="flex items-start space-x-2">
          <input
            type="checkbox"
            {...register('terms')}
            className="mt-1 h-4 w-4 rounded border-gray-300"
          />
          <span className="text-sm text-gray-600">
            I agree to the{' '}
            <a
              href="/terms"
              className="text-blue-600 hover:text-blue-500"
              target="_blank"
              rel="noopener noreferrer"
            >
              Terms of Service
            </a>{' '}
            and{' '}
            <a
              href="/privacy"
              className="text-blue-600 hover:text-blue-500"
              target="_blank"
              rel="noopener noreferrer"
            >
              Privacy Policy
            </a>
          </span>
        </label>
        {errors.terms && (
          <p className="text-sm text-red-600">{errors.terms.message}</p>
        )}
      </div>

      <Button
        type="submit"
        variant="primary"
        isLoading={isLoading}
        className="w-full"
      >
        Sign up
      </Button>

      <p className="text-center text-sm text-gray-600">
        Already have an account?{' '}
        <a href="/auth/signin" className="text-blue-600 hover:text-blue-500">
          Sign in
        </a>
      </p>
    </form>
  );
};