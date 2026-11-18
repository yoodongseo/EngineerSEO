"use client";

import type { ReactNode } from "react";
import Sidebar from "@/components/Sidebar";

interface PageShellProps {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
  contentClassName?: string;
}

export default function PageShell({
  title,
  subtitle,
  actions,
  children,
  contentClassName = "",
}: PageShellProps) {
  return (
    <>
      <Sidebar />
      <div className="main-content">
        <header>
          <div>
            <h1 id="header-title">{title}</h1>
            {subtitle && (
              <p
                id="header-subtitle"
                style={{
                  color: "var(--text-muted)",
                  marginTop: "4px",
                  fontSize: "14px",
                }}
              >
                {subtitle}
              </p>
            )}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "20px" }}>
            {actions}
            <div className="user-profile">
              <span>Admin</span>
              <div className="avatar">A</div>
            </div>
          </div>
        </header>
        <div className={`tab-content active ${contentClassName}`}>
          {children}
        </div>
      </div>
    </>
  );
}
