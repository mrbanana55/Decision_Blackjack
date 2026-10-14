import { Button as ButtonPrimitive } from "@base-ui/react/button"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "group/button inline-flex shrink-0 items-center justify-center rounded-sm text-sm font-semibold whitespace-nowrap transition-all duration-150 outline-none select-none active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default: "bg-[#5865f2] text-white hover:bg-[#4752c4] shadow-md shadow-[#5865f2]/25",
        primary: "bg-[#5865f2] text-white hover:bg-[#4752c4] shadow-md shadow-[#5865f2]/25",
        green: "bg-[#35ed7e] text-black hover:bg-[#2ecc71] font-bold shadow-md shadow-[#35ed7e]/20",
        magenta: "bg-[#ec48bd] text-white hover:bg-[#d93ca8] font-bold shadow-md shadow-[#ec48bd]/25",
        white: "bg-white text-black hover:bg-slate-200 font-semibold",
        outline:
          "border border-[#2b305c] bg-[#1e2353]/70 text-white hover:bg-[#1e2353] hover:border-[#5865f2]/50",
        secondary:
          "bg-[#1e2353] text-white hover:bg-[#262c69] border border-[#2b305c]",
        ghost:
          "bg-[#1e2353]/60 hover:bg-[#1e2353] text-white hover:text-white border border-transparent hover:border-[#2b305c]",
        destructive:
          "bg-rose-500/15 text-rose-300 hover:bg-rose-500/25 border border-rose-500/30",
        link: "text-[#00b0f4] underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 gap-2 px-4 text-sm",
        xs: "h-6 gap-1 rounded-xs px-2 text-xs [&_svg:not([class*='size-'])]:size-3",
        sm: "h-8 gap-1.5 rounded-sm px-3 text-xs [&_svg:not([class*='size-'])]:size-3.5",
        lg: "h-11 gap-2 rounded-sm px-6 text-base font-bold",
        icon: "size-9 rounded-sm",
        "icon-sm": "size-8 rounded-sm",
        "icon-xs": "size-6 rounded-xs",
        "icon-lg": "size-11 rounded-sm",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  ...props
}: ButtonPrimitive.Props & VariantProps<typeof buttonVariants>) {
  return (
    <ButtonPrimitive
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
