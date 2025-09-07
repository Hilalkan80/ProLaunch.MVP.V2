import { HTMLAttributes } from 'react';
import { cva, type VariantProps } from 'class-variance-authority';

const alertVariants = cva(
  'relative rounded-lg border p-4 [&>svg~*]:pl-7 [&>svg+div]:translate-y-[-3px] [&>svg]:absolute [&>svg]:left-4 [&>svg]:top-4 [&>svg]:text-foreground',
  {
    variants: {
      variant: {
        default: 'bg-background text-foreground',
        error: 'border-red-500 text-red-900 bg-red-50',
        success: 'border-green-500 text-green-900 bg-green-50',
        warning: 'border-yellow-500 text-yellow-900 bg-yellow-50',
        info: 'border-blue-500 text-blue-900 bg-blue-50',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

interface AlertProps
  extends HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof alertVariants> {}

export const Alert = ({ className, variant, ...props }: AlertProps) => {
  return (
    <div
      role="alert"
      className={alertVariants({ variant, className })}
      {...props}
    />
  );
};