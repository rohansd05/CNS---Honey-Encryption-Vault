import { toast } from 'sonner';

let timeoutId: number | null = null;

export async function copyToClipboard(text: string, description: string = 'Copied to clipboard') {
  try {
    await navigator.clipboard.writeText(text);
    toast.success(description);
    
    if (timeoutId) {
      window.clearTimeout(timeoutId);
    }
    
    timeoutId = window.setTimeout(() => {
      void (async () => {
        try {
          await navigator.clipboard.writeText('');
          toast.info('Clipboard cleared automatically');
        } catch {
          // ignore
        }
      })();
    }, 30000);
    
  } catch {
    toast.error('Failed to copy to clipboard');
  }
}
