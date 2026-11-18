"use client";

interface StatusBadgeProps {
  status: string;
}

const statusConfig: Record<
  string,
  { label: string; className: string }
> = {
  pending: { label: "Pending", className: "badge-pending" },
  running: { label: "Running", className: "badge-running" },
  success: { label: "SUCCESS", className: "badge-successful" },
  failed: { label: "Failed", className: "badge-failed" },
  error: { label: "Error", className: "badge-error" },
};

export default function StatusBadge({ status }: StatusBadgeProps) {
  const config = statusConfig[status] || {
    label: status,
    className: "badge-pending",
  };

  return (
    <span className={`badge ${config.className}`}>
      <span className="badge-dot" />
      {config.label}
    </span>
  );
}
