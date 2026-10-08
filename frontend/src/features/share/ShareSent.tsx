import { useShareSent } from '@/api/hooks/useSharesQueries';
import { Send, User } from 'lucide-react';

export function ShareSent() {
  const { data: sentItems = [], isLoading, error } = useShareSent();
  
  if (isLoading) return <div className="p-8 text-center text-text-muted">Loading sent shares...</div>;
  if (error) return <div className="p-8 text-center text-danger">Failed to load sent shares</div>;
  
  return (
    <div className="space-y-4">
      {sentItems.length === 0 ? (
        <div className="p-12 text-center text-text-muted bg-bg-surface rounded-xl border border-border">
          <Send size={48} className="mx-auto mb-4 opacity-20" />
          <p>No shares sent.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {sentItems.map(item => (
            <div key={item.share_id} className="p-5 rounded-xl border border-border bg-bg-surface flex flex-col">
              <div className="flex justify-between items-start mb-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-accent/10 text-accent font-bold">
                    {item.service.charAt(0).toUpperCase()}
                  </div>
                  <div className="min-w-0">
                    <h3 className="font-semibold text-text-primary truncate">{item.service}</h3>
                    <p className="text-xs text-text-muted flex items-center gap-1 mt-1">
                      <User size={12} /> to {item.recipient}
                    </p>
                  </div>
                </div>
              </div>
              
              <div className="flex flex-col gap-2 mt-auto pt-4 border-t border-border text-xs">
                <div className="flex items-center justify-between text-text-secondary">
                  <span className="flex items-center gap-1"><Send size={14} /> Sent</span>
                  <span>{new Date(item.created_at).toLocaleDateString()}</span>
                </div>
                {item.opened_at ? (
                  <div className="flex items-center justify-between text-emerald-400">
                    <span>Opened</span>
                    <span>{new Date(item.opened_at).toLocaleDateString()}</span>
                  </div>
                ) : (
                  <div className="flex items-center justify-between text-text-muted">
                    <span>Status</span>
                    <span>Unopened</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
