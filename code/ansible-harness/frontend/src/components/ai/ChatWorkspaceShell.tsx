import type { ReactNode } from "react";

interface ChatWorkspaceShellProps {
  errorBanner?: ReactNode;
  statusCard: ReactNode;
  promptCard: ReactNode;
  answerBody: ReactNode;
  hasTrailingPanels?: boolean;
  lowerPanels?: ReactNode;
  modal?: ReactNode;
  toast?: ReactNode;
}

export default function ChatWorkspaceShell({
  errorBanner,
  statusCard,
  promptCard,
  answerBody,
  hasTrailingPanels = false,
  lowerPanels,
  modal,
  toast,
}: ChatWorkspaceShellProps) {
  return (
    <div className="app-content fade-in">
      {errorBanner}
      {statusCard}
      {promptCard}

      <div className={hasTrailingPanels ? "card mb-lg" : "card"}>
        <div className="card-header">
          <h2 style={{ fontSize: 16, fontWeight: 600 }}>답변</h2>
        </div>
        <div className="card-body" data-testid="ai-answer-panel">
          {answerBody}
        </div>
      </div>

      {lowerPanels ?? null}
      {modal ?? null}
      {toast ?? null}
    </div>
  );
}
