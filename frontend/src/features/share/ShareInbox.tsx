import { useState } from 'react';
import { useShareInbox } from '@/api/hooks/useSharesQueries';
import { Button } from '@/components/ui/button';
import { OpenShareDialog } from './OpenShareDialog';
import { Mail, Clock, LockOpen } from 'lucide-react';
import type { ShareInboxItem } from '@/api/types';

export function ShareInbox() {
  const { data: inboxItems = [], isLoading, error } = useShareInbox();
  const [selectedShare, setSelectedShare] = useState<ShareInboxItem | null>(null);
  
  if (isLoading) return <div className="p-8 text-center text-text-muted">Loading inbox...</div>;
  if (error) return <div className="p-8 text-center text-danger">Failed to load inbox</div>;
  
  return (
    <div className="space-y-4">
      {inboxItems.length === 0 ? (
        <div className="p-12 text-center text-text-muted bg-bg-surface rounded-xl border border-border">
          <Mail size={48} className="mx-auto mb-4 opacity-20" />
          <p>No shares received.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {inboxItems.map(item => (
            <div key={item.share_id} className={`p-5 rounded-xl border ${item.opened_at ? 'border-border bg-bg-surface' : 'border-accent/30 bg-accent/5'} flex flex-col`}>
              <div className="flex justify-between items-start mb-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-accent/20 text-accent font-bold">
                    {item.service.charAt(0).toUpperCase()}
                  </div>
                  <div className="min-w-0">
                    <h3 className="font-semibold text-text-primary truncate">{item.service}</h3>
                    <p className="text-xs text-text-muted">from {item.sender}</p>
                  </div>
                </div>
                {!item.opened_at && <span className="flex h-3 w-3 rounded-full bg-accent shrink-0"></span>}
              </div>
              
              <div className="flex items-center gap-2 text-xs text-text-muted mb-4 mt-auto">
                <Clock size={14} />
                <span>{new Date(item.created_at).toLocaleDateString()}</span>
              </div>
              
              <Button onClick={() => { setSelectedShare(item); }} variant={item.opened_at ? 'outline' : 'default'} className="w-full gap-2">
                <LockOpen size={16} />
                {item.opened_at ? 'View Again' : 'Open Share'}
              </Button>
            </div>
          ))}
        </div>
      )}
      
      {selectedShare && (
        <OpenShareDialog 
          share={selectedShare} 
          open={!!selectedShare} 
          onOpenChange={(open) => { if (!open) setSelectedShare(null); }} 
        />
      )}
    </div>
  );
}
