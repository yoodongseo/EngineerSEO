"use client";

import type { CSSProperties, ReactNode } from "react";

interface PageErrorStateProps {
  message: ReactNode;
  messageClassName?: string;
  messageStyle?: CSSProperties;
  helper?: ReactNode;
  action?: ReactNode;
  children?: ReactNode;
  className?: string;
  style?: CSSProperties;
}

export default function PageErrorState({
  message,
  messageClassName = "text-error",
  messageStyle,
  helper,
  action,
  children,
  className = "card",
  style,
}: PageErrorStateProps) {
  return (
    <div className={className} style={style}>
      <p className={messageClassName} style={messageStyle}>
        {message}
      </p>
      {helper ? (
        <p className="text-muted text-sm" style={{ marginTop: 8 }}>
          {helper}
        </p>
      ) : null}
      {children}
      {action ? <div style={{ marginTop: 16 }}>{action}</div> : null}
    </div>
  );
}
