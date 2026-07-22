import { cn } from "@/lib/utils";

const variants: Record<string, string> = {
  default: "border-transparent bg-primary/20 text-primary-foreground",
  outline: "border-border text-foreground",
  secondary: "border-transparent bg-secondary text-secondary-foreground",
  muted: "border-border/60 bg-muted/40 text-muted-foreground",
};

export function Badge({
  className,
  variant = "default",
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { variant?: keyof typeof variants }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium",
        variants[variant],
        className
      )}
      {...props}
    />
  );
}
