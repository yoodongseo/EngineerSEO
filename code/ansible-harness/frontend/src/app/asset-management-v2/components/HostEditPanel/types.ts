export type HostConnectionType = "ssh" | "winrm" | "local";
export type HostStatus = "success" | "warning" | "danger" | "unknown";

export interface HostDraft {
  name: string;
  address: string;
  platform: string;
  connection: HostConnectionType;
  port: string;
  loginCredentialRef: string;
  becomeEnabled: boolean;
  legacyBecomeUser: string;
  legacyBecomeCredentialRef: string;
  status: HostStatus;
  note: string;
  groups: string[];
}

export interface HostEditPanelProps {
  hostId: string;
  title: string;
}
