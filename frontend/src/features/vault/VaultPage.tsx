import { useState, useEffect } from 'react';
import { VaultLocked } from './VaultLocked';
import { VaultUnlocked } from './VaultUnlocked';
import type { UnlockResponse } from '@/api/types';

export function VaultPage() {
  const [masterPassword, setMasterPassword] = useState<string | null>(null);
  const [vaultData, setVaultData] = useState<UnlockResponse | null>(null);
  
  useEffect(() => {
    return () => {
      // Clear password on unmount
      setMasterPassword(null);
      setVaultData(null);
    };
  }, []);
  
  const handleUnlock = (password: string, data: UnlockResponse) => {
    setMasterPassword(password);
    setVaultData(data);
  };
  
  const handleLock = () => {
    setMasterPassword(null);
    setVaultData(null);
  };
  
  if (masterPassword && vaultData) {
    return (
      <VaultUnlocked 
        masterPassword={masterPassword} 
        initialData={vaultData} 
        onLock={handleLock} 
      />
    );
  }
  
  return <VaultLocked onUnlock={handleUnlock} />;
}
