import React, { useMemo } from "react";
import { AISourceItem } from "@/lib/api";

interface AISourceListProps {
  sources: AISourceItem[];
}

export default function AISourceList({ sources }: AISourceListProps) {
  const uniqueSources = useMemo(() => {
    if (!sources) return [];
    const seen = new Set<string>();
    return sources.filter((source) => {
      const key = `${source.doc_group}::${source.filename}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }, [sources]);

  if (!uniqueSources || uniqueSources.length === 0) {
    return null;
  }

  return (
    <div style={{ marginTop: "var(--spacing-lg)" }}>
      <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: "var(--spacing-sm)", color: "var(--color-text-secondary)" }}>
        참고 문서 ({uniqueSources.length})
      </h3>
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-sm)" }}>
        {uniqueSources.map((source, index) => (
          <div
            key={`${source.source}-${index}`}
            data-testid="ai-source-item"
            style={{
              padding: "var(--spacing-md)",
              backgroundColor: "var(--color-bg-secondary)",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--color-border)",
              fontSize: 13,
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
              <span style={{ fontWeight: 600, color: "var(--color-primary)" }}>
                {source.filename}
              </span>
              <span style={{ color: "var(--color-text-muted)" }}>
                {source.doc_group}
              </span>
            </div>
            <div style={{ color: "var(--color-text-secondary)", whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
              {source.excerpt}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
