import * as React from 'react';
import { cn } from '@/lib/utils';
import { ChevronDown } from 'lucide-react';

export interface SelectProps
  extends React.SelectHTMLAttributes<HTMLSelectElement> {}

const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <div className="relative w-full">
        <select
          ref={ref}
          className={cn(
            'flex h-10 w-full appearance-none items-center justify-between rounded-sm border border-[#2b305c] bg-[#0a0d3a] px-3.5 py-2 text-sm text-white placeholder:text-[#949ba4] transition-all duration-150 focus:outline-none focus:border-[#5865f2] focus:ring-2 focus:ring-[#5865f2]/40 disabled:cursor-not-allowed disabled:opacity-50 pr-9 font-medium',
            className
          )}
          {...props}
        >
          {children}
        </select>
        <ChevronDown className="pointer-events-none absolute right-3 top-3 h-4 w-4 text-[#949ba4]" />
      </div>
    );
  }
);
Select.displayName = 'Select';

export { Select };
