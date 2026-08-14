import type { HostDraft } from './types';

interface BasicInfoProps {
  draft: HostDraft;
  onChange: (updates: Partial<HostDraft>) => void;
}

export default function BasicInfo({ draft, onChange }: BasicInfoProps) {
  return (
    <div className="info-form-grid">
      <label className="info-form-field">
        <span>호스트 이름</span>
        <input 
          className="form-input" 
          value={draft.name} 
          onChange={(e) => onChange({ name: e.target.value })} 
        />
      </label>
      <label className="info-form-field">
        <span>주소</span>
        <input 
          className="form-input" 
          value={draft.address} 
          onChange={(e) => onChange({ address: e.target.value })} 
        />
      </label>
      <label className="info-form-field">
        <span>플랫폼</span>
        <input 
          className="form-input" 
          value={draft.platform} 
          onChange={(e) => onChange({ platform: e.target.value })} 
        />
      </label>
      <label className="info-form-field">
        <span>포트</span>
        <input 
          className="form-input" 
          value={draft.port} 
          onChange={(e) => onChange({ port: e.target.value })} 
        />
      </label>
    </div>
  );
}
