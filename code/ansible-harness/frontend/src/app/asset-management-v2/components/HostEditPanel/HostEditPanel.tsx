'use client';

import AccordionSection from './AccordionSection';
import BasicInfo from './BasicInfo';
import Credentials from './Credentials';
import Assignment from './Assignment';
import { useState } from 'react';
import type { HostDraft, HostEditPanelProps } from './types';

// Mock draft (in a real app, this would be managed by state in page.tsx)
const initialDraft = {
  name: "my-server-01",
  address: "192.0.2.10",
  platform: "Linux",
  port: "22",
  connection: "ssh" as const,
  loginCredentialRef: "",
  becomeEnabled: false,
  legacyBecomeUser: "",
  legacyBecomeCredentialRef: "",
  status: "success" as const,
  note: "",
  groups: []
};

export default function HostEditPanel(props: HostEditPanelProps) {
  const { title } = props;
  const [draft, setDraft] = useState<HostDraft>(initialDraft);
  const handleUpdate = (updates: Partial<HostDraft>) => setDraft(prev => ({ ...prev, ...updates }));

  return (
    <div className="panel">
      <div className="panel-header">Host: {title}</div>
      <AccordionSection title="기본 정보" defaultOpen>
        <BasicInfo draft={draft} onChange={handleUpdate} />
      </AccordionSection>
      <AccordionSection title="자격 증명">
        <Credentials 
          draft={draft} 
          onChange={handleUpdate} 
          options={[]} 
          onAddCredential={() => {}} 
          onManageCredentials={() => {}} 
        />
      </AccordionSection>
      <AccordionSection title="배정 관리">
        <Assignment 
          draft={draft} 
          onChange={handleUpdate} 
          kind="host" 
          inventoryGroups={[]} 
        />
      </AccordionSection>
    </div>
  );
}
