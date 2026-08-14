import type { HostDraft } from './types';

interface InventoryGroupOption {
  id: string;
  name: string;
}

interface AssignmentTargetOption {
  value: string;
  label: string;
}

interface AssignmentProps {
  draft: HostDraft;
  onChange: (updates: Partial<HostDraft>) => void;
  kind: 'host' | 'hostAsset';
  inventoryGroups?: InventoryGroupOption[];
  assignmentTarget?: string;
  onAssignmentTargetChange?: (value: string) => void;
  onAssign?: () => void;
  assignmentOptions?: AssignmentTargetOption[];
}

export default function Assignment({ 
  draft, 
  onChange, 
  kind, 
  inventoryGroups = [],
  assignmentTarget = '',
  onAssignmentTargetChange,
  onAssign,
  assignmentOptions = []
}: AssignmentProps) {
  return (
    <div className="info-section">
      {kind === 'hostAsset' ? (
        <div className="host-asset-assignment-section">
          <div className="host-asset-assignment-control">
            <label className="info-form-field">
              <span>추가할 위치</span>
              <select className="form-input" value={assignmentTarget} onChange={(e) => onAssignmentTargetChange?.(e.target.value)}>
                <option value="">인벤토리 / 그룹 선택</option>
                {assignmentOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </label>
            <button className="btn btn-primary" onClick={onAssign} disabled={!assignmentTarget}>선택한 그룹에 넣기</button>
          </div>
        </div>
      ) : (
        <div className="inventory-library-membership-list host-group-editor-list">
          {inventoryGroups.length > 0 ? inventoryGroups.map(g => (
            <label key={g.id} className="inv-checkbox-label inventory-library-membership-item">
              <input type="checkbox" checked={draft.groups.includes(g.id)} onChange={() => {
                const newGroups = draft.groups.includes(g.id) 
                  ? draft.groups.filter(id => id !== g.id)
                  : [...draft.groups, g.id];
                onChange({ groups: newGroups });
              }} />
              <span>{g.name}</span>
            </label>
          )) : <span>그룹 없음</span>}
        </div>
      )}
    </div>
  );
}
