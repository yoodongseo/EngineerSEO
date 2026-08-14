"use client";

interface HeaderProps {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}

export default function Header({ title, subtitle, actions }: HeaderProps) {
  return (
    <header className="app-header">
      <div>
        <h1 style={{ fontSize: "18px", fontWeight: 600 }}>{title}</h1>
        {subtitle && (
          <p
            style={{
              fontSize: "13px",
              color: "var(--color-text-muted)",
              marginTop: "2px",
            }}
          >
            {subtitle}
          </p>
        )}
      </div>
      {actions && <div className="flex-center gap-sm">{actions}</div>}
    </header>
  );
}
