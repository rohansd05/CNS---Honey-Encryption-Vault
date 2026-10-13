import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { useOpenShare } from '@/api/hooks/useSharesQueries';
import { copyToClipboard } from '@/lib/clipboard';
import { Copy, ShieldCheck, ShieldAlert, Info, Loader2 } from 'lucide-react';
import { useEffect } from 'react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import type { ShareInboxItem } from '@/api/types';

interface OpenShareDialogProps {
  share: ShareInboxItem;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function OpenShareDialog({ share, open, onOpenChange }: OpenShareDialogProps) {
  const openShare = useOpenShare();
  
  useEffect(() => {
    if (open) {
      openShare.mutate(share.share_id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, share.share_id]);
  
  const data = openShare.data;
  const isPending = openShare.isPending;
  const isError = openShare.isError;
  const error = openShare.error as { detail?: string } | null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Shared Entry</DialogTitle>
          <DialogDescription>
            {share.service} from {share.sender}
          </DialogDescription>
        </DialogHeader>
        
        {isPending && (
          <div className="flex flex-col items-center justify-center py-8 text-text-muted">
            <Loader2 className="h-8 w-8 animate-spin mb-4 text-accent" />
            <p>Decrypting envelope and verifying signatures...</p>
          </div>
        )}
        
        {isError && (
          <div className="p-4 bg-danger/10 border border-danger/20 rounded-lg text-danger">
            <p className="font-semibold mb-1">Failed to open share</p>
            <p className="text-sm opacity-80">{error?.detail || 'An error occurred'}</p>
          </div>
        )}
        
        {data && (
          <div className="space-y-6">
            <div className="flex flex-col gap-2 p-3 bg-bg-elevated rounded-lg border border-border">
              <div className="flex justify-between items-center text-sm">
                <span className="text-text-secondary">Signature</span>
                {data.signature_valid ? (
                  <span className="flex items-center gap-1 text-emerald-400 font-medium"><ShieldCheck size={16} /> Valid</span>
                ) : (
                  <span className="flex items-center gap-1 text-danger font-medium"><ShieldAlert size={16} /> Tampered</span>
                )}
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-text-secondary">Certificate</span>
                {data.certificate_valid ? (
                  <span className="flex items-center gap-1 text-emerald-400 font-medium"><ShieldCheck size={16} /> Valid</span>
                ) : (
                  <span className="flex items-center gap-1 text-danger font-medium"><ShieldAlert size={16} /> Untrusted</span>
                )}
              </div>
              
              <div className="flex items-center justify-between mt-2 pt-2 border-t border-border/50 text-xs text-text-muted">
                <span>Subject: {data.certificate_subject}</span>
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button className="text-accent hover:text-accent/80"><Info size={14} /></button>
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs text-xs">
                      <p className="font-semibold mb-1">Secure Sharing</p>
                      <p>Uses ephemeral ECDH (P-256) + AES-256-GCM. Sender authenticated via ECDSA-P256-SHA256 signature.</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </div>
            </div>
            
            {(data.signature_valid && data.certificate_valid && data.username && data.password) ? (
              <div className="space-y-4">
                <div className="space-y-1">
                  <label className="text-xs text-text-muted">Username</label>
                  <div className="flex items-center justify-between p-3 bg-bg-elevated rounded-lg border border-border">
                    <span className="font-medium truncate mr-2">{data.username}</span>
                    <button onClick={() => { if (data.username) void copyToClipboard(data.username, 'Username copied'); }} className="text-text-secondary hover:text-text-primary p-1">
                      <Copy size={16} />
                    </button>
                  </div>
                </div>
                
                <div className="space-y-1">
                  <label className="text-xs text-text-muted">Password</label>
                  <div className="flex items-center justify-between p-3 bg-bg-elevated rounded-lg border border-border">
                    <span className="font-mono truncate mr-2">{data.password}</span>
                    <button onClick={() => { if (data.password) void copyToClipboard(data.password, 'Password copied'); }} className="text-text-secondary hover:text-text-primary p-1">
                      <Copy size={16} />
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-4 bg-danger/10 border border-danger/20 rounded-lg text-danger text-center">
                <ShieldAlert size={32} className="mx-auto mb-2 opacity-80" />
                <p className="font-semibold">Security Warning</p>
                <p className="text-sm opacity-80 mt-1">
                  Verification failed. The contents have been tampered with or the sender is untrusted. Nothing was decrypted.
                </p>
              </div>
            )}
            
            <div className="flex justify-end">
              <Button variant="outline" onClick={() => { onOpenChange(false); }}>Close</Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
