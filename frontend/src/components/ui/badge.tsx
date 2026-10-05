import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2',
  {
    variants: {
      variant: {
        default: 'border-transparent bg-accent text-black shadow hover:bg-accent-hover font-semibold',
        secondary: 'border-border-subtle bg-bg-elevated text-text-primary hover:bg-bg-overlay',
        destructive: 'border-transparent bg-danger/20 text-danger border-danger/30 hover:bg-danger/30',
        outline: 'text-text-primary border-border',
        success: 'border-success/30 bg-success/20 text-success',
        warning: 'border-warning/30 bg-warning/20 text-warning',
        info: 'border-info/30 bg-info/20 text-info',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
