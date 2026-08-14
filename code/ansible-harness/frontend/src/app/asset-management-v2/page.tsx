'use client';

import HostEditPanel from './components/HostEditPanel/HostEditPanel';
import './asset-management-v2.css';

export default function AssetManagementPage() {
  return (
    <div className="asset-management-container">
      <h1>자산관리2</h1>
      <HostEditPanel hostId="test-1" title="my-server-01" />
    </div>
  );
}
