import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { useAddVaultEntry, useUpdateVaultEntry } from '@/api/hooks/useVaultQueries';
import { toast } from 'sonner';
import { generatePassword } from '@/lib/password-generator';
import { PasswordStrengthMeter } from '@/components/PasswordStrengthMeter';
import type { VaultEntry } from '@/api/types';
import { RefreshCw } from 'lucide-react';

const entrySchema = z.object({
  service: z.string().min(1, 'Service is required').max(128, 'Max 128 characters'),
  username: z.string().min(1, 'Username is required').max(32, 'Max 32 characters'),
  password: z.string().min(1, 'Password is required').max(32, 'Max 32 characters'),
});

type EntryFormValues = z.infer<typeof entrySchema>;

interface EntryDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  entry: VaultEntry | null;
  masterPassword: string;
  onSuccess: () => void;
}

export function EntryDialog({ open, onOpenChange, entry, masterPassword, onSuccess }: EntryDialogProps) {
  const addMutation = useAddVaultEntry();
  const updateMutation = useUpdateVaultEntry();
  const isEditing = !!entry;
  
  const form = useForm<EntryFormValues>({
    resolver: zodResolver(entrySchema),
    defaultValues: {
      service: entry?.service || '',
      username: entry?.username || '',
      password: entry?.password || '',
    },
  });

  useEffect(() => {
    if (open) {
      form.reset({
        service: entry?.service || '',
        username: entry?.username || '',
        password: entry?.password || '',
      });
    }
  }, [open, entry, form]);

  const onSubmit = (values: EntryFormValues) => {
    if (isEditing) {
      updateMutation.mutate({
        id: entry.id,
        data: { ...values, master_password: masterPassword }
      }, {
        onSuccess: () => {
          toast.success('Entry updated');
          onSuccess();
          onOpenChange(false);
        },
        onError: (err: unknown) => { toast.error(((err as Record<string, unknown>).detail as string) || 'Failed to update entry'); }
      });
    } else {
      addMutation.mutate({
        ...values,
        master_password: masterPassword
      }, {
        onSuccess: () => {
          toast.success('Entry added');
          onSuccess();
          onOpenChange(false);
        },
        onError: (err: unknown) => { toast.error(((err as Record<string, unknown>).detail as string) || 'Failed to add entry'); }
      });
    }
  };

  const handleGeneratePassword = () => {
    const pw = generatePassword({
      length: 16,
      uppercase: true,
      lowercase: true,
      numbers: true,
      symbols: true
    });
    form.setValue('password', pw, { shouldValidate: true });
  };

  const isPending = addMutation.isPending || updateMutation.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{isEditing ? 'Edit Entry' : 'Add Entry'}</DialogTitle>
        </DialogHeader>
        
        <Form {...form}>
          <form onSubmit={(e) => { void form.handleSubmit(onSubmit)(e); }} className="space-y-4">
            <FormField
              control={form.control}
              name="service"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Service</FormLabel>
                  <FormControl>
                    <Input placeholder="github.com" {...field} disabled={isPending} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            
            <FormField
              control={form.control}
              name="username"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Username</FormLabel>
                  <FormControl>
                    <Input placeholder="alice@example.com" {...field} disabled={isPending} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            
            <FormField
              control={form.control}
              name="password"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Password</FormLabel>
                  <div className="flex gap-2">
                    <FormControl>
                      <Input type="text" {...field} disabled={isPending} />
                    </FormControl>
                    <Button type="button" variant="outline" size="icon" onClick={() => { handleGeneratePassword(); }} disabled={isPending} title="Generate Password">
                      <RefreshCw size={16} />
                    </Button>
                  </div>
                  <PasswordStrengthMeter password={field.value} />
                  <FormMessage />
                </FormItem>
              )}
            />
            
            <div className="flex justify-end gap-2 pt-4">
              <Button type="button" variant="outline" onClick={() => { onOpenChange(false); }} disabled={isPending}>
                Cancel
              </Button>
              <Button type="submit" disabled={isPending}>
                {isPending ? 'Saving...' : 'Save Entry'}
              </Button>
            </div>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
