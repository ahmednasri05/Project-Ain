import * as React from "react"
import * as TooltipPrimitive from "@radix-ui/react-tooltip"
import { cn } from "@/lib/utils"

const TooltipProvider = TooltipPrimitive.Provider
const TooltipRoot = TooltipPrimitive.Root
const TooltipTrigger = TooltipPrimitive.Trigger

const TooltipContent = React.forwardRef(({ className, sideOffset = 6, ...props }, ref) => (
    <TooltipPrimitive.Portal>
        <TooltipPrimitive.Content
            ref={ref}
            sideOffset={sideOffset}
            className={cn(
                "z-50 max-w-xs rounded-md bg-popover px-3 py-1.5 text-xs text-popover-foreground shadow-md",
                "animate-in fade-in-0 zoom-in-95",
                "data-[side=bottom]:slide-in-from-top-2 data-[side=top]:slide-in-from-bottom-2",
                className
            )}
            {...props}
        />
    </TooltipPrimitive.Portal>
))
TooltipContent.displayName = TooltipPrimitive.Content.displayName

/** Convenience wrapper: wraps children in a tooltip showing `content`. */
function Tooltip({ content, children, ...props }) {
    if (!content) return children
    return (
        <TooltipRoot delayDuration={300} {...props}>
            <TooltipTrigger asChild>{children}</TooltipTrigger>
            <TooltipContent dir="rtl">{content}</TooltipContent>
        </TooltipRoot>
    )
}

export { TooltipProvider, Tooltip, TooltipContent }
