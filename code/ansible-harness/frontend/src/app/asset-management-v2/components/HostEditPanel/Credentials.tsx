import type { HostDraft } from './types';

interface CredentialsProps {
  draft: HostDraft;
  onChange: (updates: Partial<HostDraft>) => void;
  options: Array<{ ref: string; label: string; isUnavailable?: boolean }>;
  onAddCredential: () => void;
  onManageCredentials: () => void;
}

export default function Credentials({ 
  draft, 
  onChange, 
  options, 
  onAddCredential, 
  onManageCredentials 
}: CredentialsProps) {
  return (
    <div className="info-form-grid">
      <label className="info-form-field">
        <span>로그인 자격 증명</span>
        <select 
          className="form-select" 
          value={draft.loginCredentialRef} 
          onChange={(e) => onChange({ loginCredentialRef: e.target.value })}
        >
          <option value="">선택 안 함</option>
          {options.map(opt => <option key={opt.ref} value={opt.ref}>{opt.label}</option>)}
        </select>
      </label>
      
      <div className="info-form-field host-become-toggle-field">
        <span>권한 상승</span>
        <label className="inv-checkbox-label inventory-library-membership-item host-become-toggle">
          <input 
            type="checkbox" 
            checked={draft.becomeEnabled} 
            onChange={(e) => onChange({ becomeEnabled: e.target.checked })} 
          />
          <span>become 사용</span>
        </label>
      </div>

      <div className="host-credential-actions">
        <button className="btn btn-primary" onClick={onAddCredential}>+ 자격 증명 추가</button>
        <button className="btn btn-secondary" onClick={onManageCredentials}>자격 증명 관리</button>
      </div>
    </div>
  );
}
