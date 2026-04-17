/**
 * Reusable Material 3 primitives: Surface card, FilledTonalButton, FilledButton,
 * TextField, Chip, StatusPill.
 */
import { cn } from "@/lib/utils";
import { forwardRef } from "react";

export const Surface = forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & { tone?: "base" | "container" | "high" | "highest" }
>(({ className, tone = "container", ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "rounded-3xl border border-outline-variant",
      tone === "base" && "bg-surface",
      tone === "container" && "bg-surface-container",
      tone === "high" && "bg-surface-container-high",
      tone === "highest" && "bg-surface-container-highest",
      className,
    )}
    {...props}
  />
));
Surface.displayName = "Surface";

type BtnVariant = "filled" | "tonal" | "outlined" | "text" | "danger";
type BtnSize = "sm" | "md" | "lg";

export const M3Button = forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: BtnVariant; size?: BtnSize }
>(({ className, variant = "filled", size = "md", ...props }, ref) => {
  const sizeCls =
    size === "sm" ? "h-9 px-4 text-sm" : size === "lg" ? "h-12 px-6 text-base" : "h-10 px-5 text-sm";
  const variantCls =
    variant === "filled"
      ? "bg-primary text-primary-foreground hover:m3-elev-2"
      : variant === "tonal"
        ? "bg-secondary text-secondary-foreground"
        : variant === "outlined"
          ? "border border-outline text-primary bg-transparent"
          : variant === "danger"
            ? "bg-destructive text-destructive-foreground"
            : "text-primary bg-transparent";
  return (
    <button
      ref={ref}
      className={cn(
        "m3-state inline-flex select-none items-center justify-center gap-2 rounded-full font-semibold tracking-tight transition-shadow disabled:pointer-events-none disabled:opacity-50",
        sizeCls,
        variantCls,
        className,
      )}
      {...props}
    />
  );
});
M3Button.displayName = "M3Button";

export const TextField = forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement> & { label?: string; hint?: string; error?: string }
>(({ className, label, hint, error, id, ...props }, ref) => {
  const inputId = id || props.name || label?.replace(/\s+/g, "-").toLowerCase();
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label htmlFor={inputId} className="text-xs font-semibold text-on-surface-variant">
          {label}
        </label>
      )}
      <input
        id={inputId}
        ref={ref}
        className={cn(
          "h-11 rounded-xl border border-outline bg-surface px-3.5 text-sm text-on-surface outline-none transition-all placeholder:text-on-surface-variant focus:border-primary focus:ring-2 focus:ring-primary/20",
          error && "border-destructive focus:border-destructive focus:ring-destructive/20",
          className,
        )}
        {...props}
      />
      {(error || hint) && (
        <span className={cn("text-xs", error ? "text-destructive" : "text-on-surface-variant")}>
          {error || hint}
        </span>
      )}
    </div>
  );
});
TextField.displayName = "TextField";

export function Chip({
  children,
  tone = "neutral",
  className,
}: {
  children: React.ReactNode;
  tone?: "neutral" | "success" | "warning" | "danger" | "info" | "primary";
  className?: string;
}) {
  const toneCls =
    tone === "success"
      ? "bg-success/15 text-success border-success/30"
      : tone === "warning"
        ? "bg-warning/20 text-warning-foreground border-warning/40"
        : tone === "danger"
          ? "bg-destructive/15 text-destructive border-destructive/30"
          : tone === "info"
            ? "bg-info/15 text-info border-info/30"
            : tone === "primary"
              ? "bg-primary/12 text-primary border-primary/30"
              : "bg-surface-container-highest text-on-surface-variant border-outline-variant";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wider",
        toneCls,
        className,
      )}
    >
      {children}
    </span>
  );
}

export function PageHeader({
  eyebrow,
  title,
  subtitle,
  actions,
}: {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
      <div>
        {eyebrow && <div className="m3-label text-on-surface-variant">{eyebrow}</div>}
        <h1 className="m3-headline mt-1 text-on-surface">{title}</h1>
        {subtitle && <p className="mt-2 max-w-2xl text-on-surface-variant">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <Surface tone="container" className="grid place-items-center px-6 py-16 text-center">
      <Icon className="mb-3 h-10 w-10 text-on-surface-variant" />
      <div className="m3-title text-on-surface">{title}</div>
      {description && (
        <p className="mt-1 max-w-md text-sm text-on-surface-variant">{description}</p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </Surface>
  );
}
