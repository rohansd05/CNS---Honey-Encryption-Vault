import { useState, useEffect } from 'react';
import { useUnlockVault } from '@/api/hooks/useVaultQueries';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Eye, EyeOff, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import { ApiError } from '@/api/client';
import type { UnlockResponse } from '@/api/types';

interface VaultLockedProps {
  onUnlock: (password: string, data: UnlockResponse) => void;
}

export function VaultLocked({ onUnlock }: VaultLockedProps) {
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [capsLock, setCapsLock] = useState(false);
  const unlock = useUnlockVault();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      setCapsLock(e.getModifierState('CapsLock'));
    };
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyDown);
    };
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!password) return;

    unlock.mutate(
      { master_password: password },
      {
        onSuccess: (data) => {
          onUnlock(password, data);
        },
        onError: (err: unknown) => {
          if (err instanceof ApiError) {
            if (err.status === 429) {
              const wait = err.retryAfter ? `${String(err.retryAfter)}s` : 'a moment';
              toast.error('Too Many Attempts', {
                description: `Rate limit exceeded. Please wait ${wait} before trying again.`,
              });
            } else if (err.status === 401) {
              toast.error('Session Expired', {
                description: 'Please sign in again to unlock your vault.',
              });
            } else if (err.status === 503) {
              toast.error('Service Unavailable', {
                description: 'Security service is temporarily unavailable. Please try again later.',
              });
            } else if (err.status === 422) {
              toast.error('Validation Error', {
                description: err.detail || 'Master password must be between 1 and 128 characters.',
              });
            } else {
              toast.error('Unlock Failed', {
                description: err.detail || 'Failed to unlock vault.',
              });
            }
          } else {
            toast.error('Unlock Error', {
              description: 'Unable to reach the server. Please check your connection.',
            });
          }
        },
      },
    );
  };

  return (
    <div className="flex min-h-[calc(100vh-128px)] items-center justify-center p-4 md:p-8">
      <div className="w-full max-w-md rounded-xl border border-border bg-bg-surface p-6 sm:p-8 shadow-elevated">
        <div className="mb-6 text-center">
          <div className="mb-4 text-4xl" aria-hidden="true">
            🔐
          </div>
          <h1 className="mb-2 text-2xl font-bold text-text-primary">Unlock Vault</h1>
          <p className="text-sm text-text-secondary">
            Enter your master password to access your encrypted entries.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="masterPassword">Master Password</Label>
            <div className="relative">
              <Input
                id="masterPassword"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                }}
                disabled={unlock.isPending}
                className="pr-10 focus-visible:ring-accent"
                autoComplete="current-password"
                required
              />
              <button
                type="button"
                className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary focus:outline-none focus:text-text-primary transition-colors"
                onClick={() => {
                  setShowPassword(!showPassword);
                }}
                aria-label={showPassword ? 'Hide master password' : 'Show master password'}
                title={showPassword ? 'Hide master password' : 'Show master password'}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            {capsLock && (
              <div role="alert" className="flex items-center gap-2 text-sm text-warning mt-1">
                <AlertCircle size={14} />
                <span>Caps Lock is on</span>
              </div>
            )}
          </div>
          <Button
            type="submit"
            className="w-full focus-visible:ring-accent"
            disabled={unlock.isPending}
          >
            {unlock.isPending ? 'Unlocking...' : 'Unlock'}
          </Button>
        </form>
      </div>
    </div>
  );
}
