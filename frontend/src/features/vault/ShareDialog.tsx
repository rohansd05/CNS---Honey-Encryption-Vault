import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { useCreateShare } from '@/api/hooks/useSharesQueries';
import { usersApi } from '@/api/endpoints/users';
import { toast } from 'sonner';
import type { VaultEntry, UserIdentityResponse } from '@/api/types';
import { ShieldCheck } from 'lucide-react';

const shareSchema = z.object({
  recipient_username: z.string().min(3, 'Username required').max(32, 'Max 32 characters'),
});

type ShareFormValues = z.infer<typeof shareSchema>;

interface ShareDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  entry: VaultEntry;
  masterPassword: string;
}

export function ShareDialog({ open, onOpenChange, entry, masterPassword }: ShareDialogProps) {
  const [identity, setIdentity] = useState<UserIdentityResponse | null>(null);
  const [isFetchingIdentity, setIsFetchingIdentity] = useState(false);
  const [fingerprint, setFingerprint] = useState<string>('');
  const createShare = useCreateShare();
  
  const form = useForm<ShareFormValues>({
    resolver: zodResolver(shareSchema),
    defaultValues: {
      recipient_username: '',
    },
  });

  // Reset when dialog opens
  useEffect(() => {
    if (open) {
      setIdentity(null);
      setFingerprint('');
      form.reset();
    }
  }, [open, form]);

  useEffect(() => {
    if (identity?.certificate_pem) {
      void (async () => {
        try {
          const encoder = new TextEncoder();
          const data = encoder.encode(identity.certificate_pem);
          const hashBuffer = await crypto.subtle.digest('SHA-256', data);
          const hashArray = Array.from(new Uint8Array(hashBuffer));
          const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join(':').toUpperCase();
          setFingerprint(hashHex);
        } catch {
          setFingerprint('Unavailable');
        }
      })();
    }
  }, [identity]);

  const handleVerify = async () => {
    const username = form.getValues('recipient_username');
    if (!username) {
      void form.trigger('recipient_username');
      return;
    }
    
    setIsFetchingIdentity(true);
    setIdentity(null);
    try {
      const res = await usersApi.getIdentity(username);
      setIdentity(res);
    } catch (err: unknown) {
      toast.error(((err as Record<string, unknown>).detail as string) || 'User not found');
    } finally {
      setIsFetchingIdentity(false);
    }
  };

  const onSubmit = () => {
    if (!identity) return;
    
    createShare.mutate({
      master_password: masterPassword,
      entry_id: entry.id,
      recipient_username: identity.username
    }, {
      onSuccess: () => {
        toast.success(`Shared with ${identity.username}`);
        onOpenChange(false);
      },
      onError: (err: unknown) => {
        toast.error(((err as Record<string, unknown>).detail as string) || 'Failed to share');
      }
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Share Entry</DialogTitle>
          <DialogDescription>
            Sharing {entry.service} with another user.
          </DialogDescription>
        </DialogHeader>
        
        {!identity ? (
          <Form {...form}>
            <form onSubmit={(e) => { e.preventDefault(); void handleVerify(); }} className="space-y-4">
              <FormField
                control={form.control}
                name="recipient_username"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Recipient Username</FormLabel>
                    <FormControl>
                      <Input placeholder="bob" {...field} disabled={isFetchingIdentity} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => { onOpenChange(false); }}>Cancel</Button>
                <Button type="submit" disabled={isFetchingIdentity}>
                  {isFetchingIdentity ? 'Finding User...' : 'Find User'}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        ) : (
          <div className="space-y-4">
            <div className="rounded-lg border border-border p-4 space-y-3 bg-bg-elevated">
              <div className="flex items-center gap-2 text-accent font-semibold">
                <ShieldCheck size={18} />
                User Verified
              </div>
              <div className="text-sm space-y-1">
                <p><span className="text-text-muted">Username:</span> {identity.username}</p>
                <p><span className="text-text-muted">Subject:</span> CN={identity.username}</p>
                <p><span className="text-text-muted">Issuer:</span> CN=HoneyVault Issuing CA</p>
                <p className="font-mono text-[10px] break-all"><span className="text-text-muted font-sans text-sm block md:inline">Fingerprint (SHA-256):</span> {fingerprint}</p>
                <p className="text-xs text-warning mt-2 border-t border-border pt-2 font-medium">
                  Verify this fingerprint with your friend before confirming!
                </p>
              </div>
            </div>
            
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => { setIdentity(null); }}>Back</Button>
              <Button onClick={() => { onSubmit(); }} disabled={createShare.isPending}>
                {createShare.isPending ? 'Sharing...' : 'Confirm & Share'}
              </Button>
            </DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
