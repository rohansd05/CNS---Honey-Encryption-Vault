import { ShareInbox } from './ShareInbox';
import { ShareSent } from './ShareSent';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

export function SharePage() {
  return (
    <div className="container mx-auto p-4 md:p-8 space-y-8 max-w-6xl">
      <div className="flex flex-col md:flex-row items-center gap-4 rounded-xl border border-border bg-bg-surface p-6 shadow-elevated">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-accent/20 text-3xl">📬</div>
        <div className="text-center md:text-left">
          <h1 className="text-2xl font-bold text-text-primary mb-1">Secure Share</h1>
          <p className="text-sm text-text-secondary">
            Send and receive encrypted vault entries securely.
          </p>
        </div>
      </div>
      
      <Tabs defaultValue="inbox" className="w-full">
        <TabsList className="grid w-full md:w-[400px] grid-cols-2 mb-6">
          <TabsTrigger value="inbox">Inbox</TabsTrigger>
          <TabsTrigger value="sent">Sent</TabsTrigger>
        </TabsList>
        <TabsContent value="inbox">
          <ShareInbox />
        </TabsContent>
        <TabsContent value="sent">
          <ShareSent />
        </TabsContent>
      </Tabs>
    </div>
  );
}
