import { z } from 'zod';
import { signInSchema, signUpSchema, forgotPasswordSchema } from '../lib/validation/auth-schemas';

export type SignInData = z.infer<typeof signInSchema>;
export type SignUpData = z.infer<typeof signUpSchema>;
export type ForgotPasswordData = z.infer<typeof forgotPasswordSchema>;