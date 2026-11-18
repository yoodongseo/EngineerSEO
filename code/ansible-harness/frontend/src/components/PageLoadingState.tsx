"use client";

import type { CSSProperties, ReactNode } from "react";

interface PageLoadingStateProps {
  label?: ReactNode;
  minHeight?: number;
  className?: string;
  style?: CSSProperties;
}

export default function PageLoadingState({
  label,
  minHeight,
  className,
  style,
}: PageLoadingStateProps) {
  return (
    <div
      className={["flex-center", label ? "gap-md" : "", className ?? ""]
        .filter(Boolean)
        .join(" ")}
      style={{ minHeight, ...style }}
    >
      <div className="spinner" />
      {label ? <span>{label}</span> : null}
    </div>
  );
}
