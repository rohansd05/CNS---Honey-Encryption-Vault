import { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Sigil } from '@/components/Sigil';
import { Input } from '@/components/ui/input';
import {
  AlertCircle,
  Download,
  Plus,
  Search,
  Lock,
  Copy,
  Eye,
  EyeOff,
  Share2,
  Edit,
  Trash2,
} from 'lucide-react';
import { useUnlockVault, useDeleteVaultEntry } from '@/api/hooks/useVaultQueries';
import { vaultApi } from '@/api/endpoints/vault';
import { copyToClipboard } from '@/lib/clipboard';
import type { UnlockResponse, VaultEntry } from '@/api/types';
import { toast } from 'sonner';
import { ApiError } from '@/api/client';
import { EntryDialog } from './EntryDialog';
import { ShareDialog } from './ShareDialog';

interface VaultUnlockedProps {
  masterPassword: string;
  initialData: UnlockResponse;
  onLock: () => void;
}

export function VaultUnlocked({ masterPassword, initialData, onLock }: VaultUnlockedProps) {
  const [data, setData] = useState<UnlockResponse>(initialData);
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState<'service' | 'created_at'>('created_at');
  const [revealedPasswords, setRevealedPasswords] = useState<Set<string>>(new Set());

  const [entryToEdit, setEntryToEdit] = useState<VaultEntry | null>(null);
  const [isEntryDialogOpen, setIsEntryDialogOpen] = useState(false);

  const [entryToShare, setEntryToShare] = useState<VaultEntry | null>(null);
  const [isShareDialogOpen, setIsShareDialogOpen] = useState(false);

  const unlock = useUnlockVault();
  const deleteEntry = useDeleteVaultEntry();

  const idleTimeout = useRef<number | null>(null);
  const hiddenTimeout = useRef<number | null>(null);

  useEffect(() => {
    const resetIdleTimer = () => {
      if (idleTimeout.current) window.clearTimeout(idleTimeout.current);
      idleTimeout.current = window.setTimeout(onLock, 5 * 60 * 1000); // 5 mins
    };

    resetIdleTimer();
    const events = ['mousemove', 'keydown', 'click', 'scroll'];
    events.forEach((e) => {
      window.addEventListener(e, resetIdleTimer);
    });

    const handleVisibilityChange = () => {
      if (document.hidden) {
        hiddenTimeout.current = window.setTimeout(onLock, 2 * 60 * 1000); // 2 mins hidden
      } else {
        if (hiddenTimeout.current) window.clearTimeout(hiddenTimeout.current);
      }
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      events.forEach((e) => {
        window.removeEventListener(e, resetIdleTimer);
      });
      if (idleTimeout.current) window.clearTimeout(idleTimeout.current);
      if (hiddenTimeout.current) window.clearTimeout(hiddenTimeout.current);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [onLock]);

  const refreshVault = () => {
    unlock.mutate(
      { master_password: masterPassword },
      {
        onSuccess: (newData) => {
          setData(newData);
        },
      },
    );
  };

  const handleExport = async () => {
    try {
      const blobData = await vaultApi.exportVault();
      const blob = new Blob([JSON.stringify(blobData, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'honeyvault_export.json';
      a.click();
      URL.revokeObjectURL(url);
      toast.info('Export downloaded. This is exactly what an attacker would steal.');
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        toast.error('Export Failed', { description: err.detail });
      } else {
        toast.error('Failed to export vault');
      }
    }
  };

  const handleDelete = (id: string) => {
    if (window.confirm('Are you sure you want to delete this entry?')) {
      deleteEntry.mutate(id, {
        onSuccess: () => {
          toast.success('Entry deleted');
          refreshVault();
        },
        onError: (err: unknown) => {
          if (err instanceof ApiError) {
            toast.error('Delete Failed', { description: err.detail });
          } else {
            toast.error('Failed to delete entry');
          }
        },
      });
    }
  };

  const togglePasswordReveal = (id: string) => {
    const newRevealed = new Set(revealedPasswords);
    if (newRevealed.has(id)) newRevealed.delete(id);
    else newRevealed.add(id);
    setRevealedPasswords(newRevealed);
  };

  const filteredEntries = data.entries
    .filter(
      (e) =>
        e.service.toLowerCase().includes(search.toLowerCase()) ||
        e.username.toLowerCase().includes(search.toLowerCase()),
    )
    .sort((a, b) => {
      if (sortBy === 'service') return a.service.localeCompare(b.service);
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });

  return (
    <div className="container mx-auto p-4 md:p-8 space-y-8 max-w-6xl">
      {/* Header */}
      <div className="flex flex-col md:flex-row items-center justify-between gap-6 rounded-xl border border-border bg-bg-surface p-6 shadow-elevated">
        <div className="flex flex-col md:flex-row items-center gap-6 text-center md:text-left">
          <Sigil sigil={data.sigil} size="md" />
          <div>
            <h2 className="text-xl font-bold text-text-primary mb-2">Vault Unlocked</h2>
            <div className="flex items-center gap-2 text-sm text-warning bg-warning/10 p-2 rounded-lg border border-warning/20 max-w-md">
              <AlertCircle size={20} className="shrink-0" />
              <p>
                Is this your usual sigil? If not, you probably mistyped — this may be a decoy vault.
              </p>
            </div>
          </div>
        </div>
        <div className="flex flex-wrap justify-center md:justify-end items-center gap-4">
          <div className="text-sm font-medium text-text-secondary">
            {data.entries.length} entries
          </div>
          <Button
            variant="outline"
            onClick={() => {
              void handleExport();
            }}
            className="gap-2"
          >
            <Download size={16} /> Export
          </Button>
          <Button
            variant="destructive"
            onClick={() => {
              onLock();
            }}
            className="gap-2"
          >
            <Lock size={16} /> Lock
          </Button>
        </div>
      </div>

      {/* Controls */}
      <div className="flex flex-col md:flex-row gap-4 justify-between items-center">
        <div className="relative w-full md:w-96">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" size={16} />
          <Input
            placeholder="Search entries..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
            }}
            className="pl-9"
          />
        </div>
        <div className="flex items-center gap-4 w-full md:w-auto">
          <select
            className="flex h-10 w-full md:w-auto items-center justify-between rounded-md border border-border bg-bg-surface px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-1 focus:border-accent"
            value={sortBy}
            onChange={(e) => {
              setSortBy(e.target.value as 'service' | 'created_at');
            }}
          >
            <option value="created_at">Sort by Date</option>
            <option value="service">Sort by Service</option>
          </select>
          <Button
            onClick={() => {
              setEntryToEdit(null);
              setIsEntryDialogOpen(true);
            }}
            className="w-full md:w-auto gap-2"
          >
            <Plus size={16} /> Add Entry
          </Button>
        </div>
      </div>

      {/* Entries List Mobile */}
      <div className="grid grid-cols-1 gap-4 md:hidden">
        {filteredEntries.map((entry) => (
          <div
            key={entry.id}
            className="rounded-lg border border-border bg-bg-surface p-4 space-y-4 shadow-sm"
          >
            <div className="flex items-center gap-3 border-b border-border pb-3">
              <div
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent/10 text-accent font-bold"
                aria-hidden="true"
              >
                {entry.service.charAt(0).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-semibold text-text-primary truncate">{entry.service}</div>
                <div className="text-xs text-text-muted">
                  Updated {new Date(entry.updated_at).toLocaleDateString()}
                </div>
              </div>
            </div>

            <div className="space-y-3 text-sm">
              <div>
                <span className="text-text-muted text-xs block mb-1">Username</span>
                <div className="flex items-center justify-between bg-bg-elevated p-2 rounded">
                  <span className="truncate mr-2 font-medium">{entry.username}</span>
                  <button
                    onClick={() => {
                      void copyToClipboard(entry.username, 'Username copied');
                    }}
                    className="text-text-secondary hover:text-text-primary p-1 shrink-0 focus-visible:ring-1 focus-visible:ring-accent rounded"
                    aria-label={`Copy username for ${entry.service}`}
                    title="Copy username"
                  >
                    <Copy size={14} />
                  </button>
                </div>
              </div>
              <div>
                <span className="text-text-muted text-xs block mb-1">Password</span>
                <div className="flex items-center justify-between bg-bg-elevated p-2 rounded">
                  <span className="truncate mr-2 font-mono">
                    {revealedPasswords.has(entry.id) ? entry.password : '••••••••'}
                  </span>
                  <div className="flex items-center gap-1 shrink-0">
                    <button
                      onClick={() => {
                        togglePasswordReveal(entry.id);
                      }}
                      className="text-text-secondary hover:text-text-primary p-1 focus-visible:ring-1 focus-visible:ring-accent rounded"
                      aria-label={
                        revealedPasswords.has(entry.id)
                          ? `Hide password for ${entry.service}`
                          : `Reveal password for ${entry.service}`
                      }
                      title={revealedPasswords.has(entry.id) ? 'Hide password' : 'Show password'}
                    >
                      {revealedPasswords.has(entry.id) ? <EyeOff size={14} /> : <Eye size={14} />}
                    </button>
                    <button
                      onClick={() => {
                        void copyToClipboard(entry.password, 'Password copied');
                      }}
                      className="text-text-secondary hover:text-text-primary p-1 focus-visible:ring-1 focus-visible:ring-accent rounded"
                      aria-label={`Copy password for ${entry.service}`}
                      title="Copy password"
                    >
                      <Copy size={14} />
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between pt-3 border-t border-border">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setEntryToShare(entry);
                  setIsShareDialogOpen(true);
                }}
                className="text-text-secondary hover:text-accent gap-2 focus-visible:ring-accent"
                aria-label={`Share ${entry.service} entry`}
              >
                <Share2 size={16} /> Share
              </Button>
              <div className="flex gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => {
                    setEntryToEdit(entry);
                    setIsEntryDialogOpen(true);
                  }}
                  className="text-text-secondary hover:text-primary focus-visible:ring-accent"
                  aria-label={`Edit ${entry.service} entry`}
                  title="Edit entry"
                >
                  <Edit size={16} />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => {
                    handleDelete(entry.id);
                  }}
                  className="text-text-secondary hover:text-danger focus-visible:ring-accent"
                  aria-label={`Delete ${entry.service} entry`}
                  title="Delete entry"
                >
                  <Trash2 size={16} />
                </Button>
              </div>
            </div>
          </div>
        ))}
        {filteredEntries.length === 0 && (
          <div className="rounded-lg border border-border bg-bg-surface p-8 text-center text-text-muted">
            {search ? (
              <p>No entries matching &ldquo;{search}&rdquo;</p>
            ) : (
              <div className="space-y-3">
                <p>Your vault is currently empty.</p>
                <Button
                  size="sm"
                  onClick={() => {
                    setEntryToEdit(null);
                    setIsEntryDialogOpen(true);
                  }}
                  className="gap-2"
                >
                  <Plus size={14} /> Add your first entry
                </Button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Entries List Desktop */}
      <div className="hidden md:block rounded-xl border border-border bg-bg-surface overflow-hidden shadow-sm">
        <table className="w-full text-sm text-left whitespace-nowrap">
          <thead className="bg-bg-elevated text-text-secondary border-b border-border">
            <tr>
              <th className="px-6 py-4 font-medium" scope="col">
                Service
              </th>
              <th className="px-6 py-4 font-medium" scope="col">
                Username
              </th>
              <th className="px-6 py-4 font-medium" scope="col">
                Password
              </th>
              <th className="px-6 py-4 font-medium" scope="col">
                Updated
              </th>
              <th className="px-6 py-4 font-medium text-right" scope="col">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {filteredEntries.map((entry) => (
              <tr key={entry.id} className="hover:bg-bg-elevated/50 transition-colors group">
                <td className="px-6 py-4 max-w-[200px]">
                  <div className="flex items-center gap-3 overflow-hidden">
                    <div
                      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent/10 text-accent font-bold text-xs"
                      aria-hidden="true"
                    >
                      {entry.service.charAt(0).toUpperCase()}
                    </div>
                    <span className="font-medium text-text-primary truncate">{entry.service}</span>
                  </div>
                </td>
                <td className="px-6 py-4 max-w-[200px]">
                  <div className="flex items-center gap-2 overflow-hidden">
                    <span className="truncate">{entry.username}</span>
                    <button
                      onClick={() => {
                        void copyToClipboard(entry.username, 'Username copied');
                      }}
                      className="opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 focus:opacity-100 text-text-muted hover:text-text-primary transition-opacity shrink-0 focus-visible:ring-1 focus-visible:ring-accent rounded p-0.5"
                      aria-label={`Copy username for ${entry.service}`}
                      title="Copy username"
                    >
                      <Copy size={14} />
                    </button>
                  </div>
                </td>
                <td className="px-6 py-4 max-w-[200px]">
                  <div className="flex items-center gap-2 overflow-hidden">
                    <span className="font-mono truncate">
                      {revealedPasswords.has(entry.id) ? entry.password : '••••••••'}
                    </span>
                    <div className="flex gap-1 shrink-0 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 focus-within:opacity-100 transition-opacity">
                      <button
                        onClick={() => {
                          togglePasswordReveal(entry.id);
                        }}
                        className="text-text-muted hover:text-text-primary p-1 focus-visible:ring-1 focus-visible:ring-accent rounded"
                        aria-label={
                          revealedPasswords.has(entry.id)
                            ? `Hide password for ${entry.service}`
                            : `Reveal password for ${entry.service}`
                        }
                        title={revealedPasswords.has(entry.id) ? 'Hide password' : 'Show password'}
                      >
                        {revealedPasswords.has(entry.id) ? <EyeOff size={14} /> : <Eye size={14} />}
                      </button>
                      <button
                        onClick={() => {
                          void copyToClipboard(entry.password, 'Password copied');
                        }}
                        className="text-text-muted hover:text-text-primary p-1 focus-visible:ring-1 focus-visible:ring-accent rounded"
                        aria-label={`Copy password for ${entry.service}`}
                        title="Copy password"
                      >
                        <Copy size={14} />
                      </button>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 text-text-muted">
                  {new Date(entry.updated_at).toLocaleDateString()}
                </td>
                <td className="px-6 py-4 text-right">
                  <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 focus-within:opacity-100 transition-opacity">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => {
                        setEntryToShare(entry);
                        setIsShareDialogOpen(true);
                      }}
                      className="text-text-muted hover:text-accent focus-visible:ring-accent"
                      aria-label={`Share ${entry.service} entry`}
                      title="Share"
                    >
                      <Share2 size={16} />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => {
                        setEntryToEdit(entry);
                        setIsEntryDialogOpen(true);
                      }}
                      className="text-text-muted hover:text-primary focus-visible:ring-accent"
                      aria-label={`Edit ${entry.service} entry`}
                      title="Edit"
                    >
                      <Edit size={16} />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => {
                        handleDelete(entry.id);
                      }}
                      className="text-text-muted hover:text-danger focus-visible:ring-accent"
                      aria-label={`Delete ${entry.service} entry`}
                      title="Delete"
                    >
                      <Trash2 size={16} />
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
            {filteredEntries.length === 0 && (
              <tr>
                <td colSpan={5} className="px-6 py-12 text-center text-text-muted">
                  {search ? (
                    <p>No entries matching &ldquo;{search}&rdquo;</p>
                  ) : (
                    <div className="space-y-3">
                      <p>Your vault is currently empty.</p>
                      <Button
                        size="sm"
                        onClick={() => {
                          setEntryToEdit(null);
                          setIsEntryDialogOpen(true);
                        }}
                        className="gap-2"
                      >
                        <Plus size={14} /> Add your first entry
                      </Button>
                    </div>
                  )}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {isEntryDialogOpen && (
        <EntryDialog
          open={isEntryDialogOpen}
          onOpenChange={setIsEntryDialogOpen}
          entry={entryToEdit}
          masterPassword={masterPassword}
          onSuccess={refreshVault}
        />
      )}

      {isShareDialogOpen && entryToShare && (
        <ShareDialog
          open={isShareDialogOpen}
          onOpenChange={setIsShareDialogOpen}
          entry={entryToShare}
          masterPassword={masterPassword}
        />
      )}
    </div>
  );
}
