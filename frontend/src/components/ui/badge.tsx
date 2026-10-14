import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center rounded-pill border px-2.5 py-0.5 text-xs font-semibold tracking-wide transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
  {
    variants: {
      variant: {
        default: 'border-transparent bg-[#5865f2] text-white shadow-sm',
        primary: 'border-transparent bg-[#5865f2] text-white shadow-sm',
        magenta: 'border-transparent bg-[#ec48bd] text-white shadow-sm',
        green: 'border-transparent bg-[#35ed7e] text-black font-bold shadow-sm',
        cyan: 'border-transparent bg-[#00b0f4] text-black font-bold shadow-sm',
        secondary: 'border-[#2b305c] bg-[#1e2353] text-[#949ba4]',
        outline: 'border-[#2b305c] bg-transparent text-white',
        destructive: 'border-rose-500/30 bg-rose-500/20 text-rose-300',
        success: 'border-emerald-500/30 bg-[#35ed7e]/20 text-[#35ed7e]',
        warning: 'border-amber-500/30 bg-amber-500/20 text-amber-300',
        hit: 'border-transparent bg-[#00b0f4] text-black font-bold shadow-sm',
        stand: 'border-transparent bg-[#fee75c] text-black font-bold shadow-sm',
        double: 'border-transparent bg-[#ec48bd] text-white font-bold shadow-sm',
        split: 'border-transparent bg-[#35ed7e] text-black font-bold shadow-sm',
        surrender: 'border-transparent bg-[#f04747] text-white font-bold shadow-sm',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
