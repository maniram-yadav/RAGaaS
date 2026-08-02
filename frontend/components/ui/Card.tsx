import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "../../lib/cn";

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  title?: string;
  children: ReactNode;
}

/**
 * Base `components/ui` card primitive: bordered container with optional
 * title, used as the building block for pricing tiles, dashboard panels, etc.
 */
export function Card({ title, className, children, ...rest }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-card border border-neutral-200 bg-background p-6 shadow-sm",
        className,
      )}
      {...rest}
    >
      {title ? (
        <h3 className="mb-2 text-lg font-semibold text-foreground">{title}</h3>
      ) : null}
      {children}
    </div>
  );
}
