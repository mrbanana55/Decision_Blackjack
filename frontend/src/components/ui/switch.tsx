import * as React from 'react';
import { cn } from '@/lib/utils';

export interface SwitchProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  checked?: boolean;
  onCheckedChange?: (checked: boolean) => void;
}

const Switch = React.forwardRef<HTMLInputElement, SwitchProps>(
  ({ className, checked = false, onCheckedChange, disabled, ...props }, ref) => {
    return (
      <label
        className={cn(
          'relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-pill transition-colors duration-200 border border-[#2b305c]/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#5865f2]',
          checked ? 'bg-[#5865f2] shadow-sm shadow-[#5865f2]/40' : 'bg-[#23272a]',
          disabled && 'cursor-not-allowed opacity-50',
          className
        )}
      >
        <input
          ref={ref}
          type="checkbox"
          className="sr-only"
          checked={checked}
          disabled={disabled}
          onChange={(e) => onCheckedChange?.(e.target.checked)}
          {...props}
        />
        <span
          className={cn(
            'pointer-events-none block h-5 w-5 rounded-full bg-white shadow-md ring-0 transition-transform duration-200 ease-in-out',
            checked ? 'translate-x-[22px]' : 'translate-x-[2px]'
          )}
        />
      </label>
    );
  }
);
Switch.displayName = 'Switch';

export { Switch };
