import * as React from 'react';
import { cn } from '@/lib/utils';

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          'flex h-10 w-full rounded-sm border border-[#2b305c] bg-[#0a0d3a] px-3.5 py-2 text-sm text-white placeholder:text-[#949ba4] transition-all duration-150 focus-visible:outline-none focus-visible:border-[#5865f2] focus-visible:ring-2 focus-visible:ring-[#5865f2]/40 disabled:cursor-not-allowed disabled:opacity-50 font-medium',
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Input.displayName = 'Input';

export { Input };
