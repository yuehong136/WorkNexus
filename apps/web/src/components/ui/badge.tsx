import { cva, type VariantProps } from 'class-variance-authority'
import type { ComponentProps } from 'react'

import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium whitespace-nowrap',
  {
    variants: {
      variant: {
        default: 'border-transparent bg-brand-primary text-brand-primary-foreground',
        secondary: 'border-transparent bg-surface-secondary text-text-secondary',
        outline: 'border-border-default text-text-secondary',
        success: 'border-transparent bg-status-success text-text-inverse',
        warning: 'border-transparent bg-status-warning text-text-inverse',
        error: 'border-transparent bg-status-error text-text-inverse',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
)

export function Badge({
  className,
  variant,
  ...props
}: ComponentProps<'span'> & VariantProps<typeof badgeVariants>) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />
}
