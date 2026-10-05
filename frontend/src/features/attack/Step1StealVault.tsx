// owner: Chetan (T3) — Step 1: Steal the Vault (Exfiltrate Blobs)
import { useState } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import {
  Download,
  Copy,
  Check,
  ShieldAlert,
  ShieldCheck,
  ArrowRight,
  RefreshCw,
  FileCode2,
  Lock,
  Layers,
  Info,
} from 'lucide-react';
import { useStolenVault } from '@/api/hooks/useAttackQueries';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { toast } from 'sonner';

interface Step1StealVaultProps {
  onNext: () => void;
}

export function Step1StealVault({ onNext }: Step1StealVaultProps) {
  const shouldReduceMotion = useReducedMotion();
  const { data: stolenData, isLoading, isError, refetch, isFetching } = useStolenVault();
  const [copiedHoney, setCopiedHoney] = useState(false);
  const [copiedBaseline, setCopiedBaseline] = useState(false);

  const honeyJson = stolenData?.honey_blob
    ? JSON.stringify(stolenData.honey_blob, null, 2)
    : '';

  const baselineJson = stolenData?.baseline_blob
    ? JSON.stringify(stolenData.baseline_blob, null, 2)
    : '';

  const handleCopyHoney = async () => {
    if (!honeyJson) return;
    try {
      await navigator.clipboard.writeText(honeyJson);
      setCopiedHoney(true);
      toast.success('Honey vault JSON copied to clipboard');
      setTimeout(() => {
        setCopiedHoney(false);
      }, 2000);
    } catch {
      toast.error('Failed to copy to clipboard');
    }
  };

  const handleCopyBaseline = async () => {
    if (!baselineJson) return;
    try {
      await navigator.clipboard.writeText(baselineJson);
      setCopiedBaseline(true);
      toast.success('Conventional vault JSON copied to clipboard');
      setTimeout(() => {
        setCopiedBaseline(false);
      }, 2000);
    } catch {
      toast.error('Failed to copy to clipboard');
    }
  };

  const handleDownloadHoney = () => {
    if (!honeyJson) return;
    const blob = new Blob([honeyJson], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `honeyvault-stolen-${stolenData?.owner ?? 'demo'}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success('Downloaded honeyvault-stolen.json');
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="space-y-6"
    >
      {/* Step Context Banner */}
      <div className="rounded-xl border border-border bg-bg-surface p-6 shadow-card">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-accent/20 text-xs font-bold text-accent">
                1
              </span>
              <h2 className="text-xl font-bold text-text-primary">
                Exfiltrate Database Records
              </h2>
              <Badge variant="outline" className="border-accent/40 text-accent font-mono text-[11px]">
                Target: @{stolenData?.owner ?? 'demo'}
              </Badge>
            </div>
            <p className="text-sm text-text-secondary max-w-2xl leading-relaxed">
              In this scenario, an attacker has breached server storage or intercepted a backup file.
              Compare the exfiltrated ciphertext format between a conventional password vault and a
              Honey Encryption vault.
            </p>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              void refetch();
            }}
            disabled={isFetching}
            className="self-start md:self-auto gap-2 border-border hover:border-accent/40 text-text-secondary hover:text-text-primary"
          >
            <RefreshCw size={14} className={isFetching ? 'animate-spin text-accent' : ''} />
            {isFetching ? 'Refreshing...' : 'Re-fetch Stolen Blobs'}
          </Button>
        </div>
      </div>

      {isLoading && (
        <Card className="border-border bg-bg-surface p-12 text-center">
          <div className="flex flex-col items-center justify-center gap-3">
            <RefreshCw size={28} className="animate-spin text-accent" />
            <p className="text-sm text-text-secondary">Simulating database exfiltration...</p>
          </div>
        </Card>
      )}

      {isError && (
        <Card className="border-danger/30 bg-danger/10 p-6 text-center">
          <ShieldAlert className="mx-auto h-8 w-8 text-danger mb-2" />
          <h3 className="font-semibold text-danger">Failed to fetch stolen vault data</h3>
          <p className="text-xs text-text-secondary mt-1 mb-4">Ensure DEMO_MODE is active and MSW mock handlers are loaded.</p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              void refetch();
            }}
          >
            Retry
          </Button>
        </Card>
      )}

      {!isLoading && stolenData && (
        <div className="space-y-6">
          <Tabs defaultValue="honey" className="w-full">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-3">
              <TabsList className="bg-bg-elevated border border-border">
                <TabsTrigger value="honey" className="gap-2">
                  <ShieldCheck size={14} className="text-accent" />
                  <span>Honey Vault Blob (v1)</span>
                  <Badge variant="default" className="text-[10px] py-0 px-1.5 h-4 bg-accent/20 text-accent border border-accent/30">
                    No Oracle
                  </Badge>
                </TabsTrigger>
                <TabsTrigger value="baseline" className="gap-2">
                  <Lock size={14} className="text-danger" />
                  <span>Conventional Vault (AES-GCM)</span>
                  <Badge variant="destructive" className="text-[10px] py-0 px-1.5 h-4">
                    Vulnerable Oracle
                  </Badge>
                </TabsTrigger>
              </TabsList>

              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleDownloadHoney}
                  className="gap-1.5 text-xs border-border hover:border-accent/40"
                >
                  <Download size={13} />
                  Download JSON
                </Button>
              </div>
            </div>

            {/* Tab 1: Honey Vault Blob */}
            <TabsContent value="honey" className="mt-0 space-y-4">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                {/* Monospace Code Viewer */}
                <div className="lg:col-span-2 rounded-xl border border-border bg-bg-surface overflow-hidden shadow-card flex flex-col">
                  <div className="flex items-center justify-between px-4 py-2.5 bg-bg-elevated/80 border-b border-border">
                    <div className="flex items-center gap-2">
                      <FileCode2 size={15} className="text-accent" />
                      <span className="font-mono text-xs text-text-secondary">
                        honeyvault_stolen_blob.json
                      </span>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        void handleCopyHoney();
                      }}
                      className="h-7 px-2 text-xs gap-1.5 text-text-secondary hover:text-text-primary"
                    >
                      {copiedHoney ? <Check size={13} className="text-success" /> : <Copy size={13} />}
                      {copiedHoney ? 'Copied' : 'Copy'}
                    </Button>
                  </div>

                  <div className="relative p-4 overflow-x-auto max-h-[380px] font-mono text-xs text-text-primary bg-[#080d17] leading-relaxed">
                    <pre className="selection:bg-accent/20">
                      <code>{honeyJson}</code>
                    </pre>
                  </div>
                </div>

                {/* Crypto Analysis Card */}
                <div className="space-y-3">
                  <Card className="border-border bg-bg-surface shadow-card">
                    <CardHeader className="pb-3">
                      <CardTitle className="text-base flex items-center gap-2 text-text-primary">
                        <Layers size={16} className="text-accent" />
                        Honey Encryption Properties
                      </CardTitle>
                      <CardDescription className="text-xs">
                        Adheres to Juels & Ristenpart (2014) invariants
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3 text-xs">
                      <div className="rounded-lg bg-bg-elevated p-3 border border-border-subtle space-y-1">
                        <div className="font-semibold text-accent flex items-center gap-1.5">
                          <Check size={13} className="text-accent" />
                          Zero Verification Oracle
                        </div>
                        <p className="text-text-secondary leading-normal">
                          Notice: <strong>no MAC, no auth tag, no padding, and no checksum</strong>.
                          An offline brute-force attacker has 0 bits of feedback on whether a guess was correct.
                        </p>
                      </div>

                      <div className="rounded-lg bg-bg-elevated p-3 border border-border-subtle space-y-1">
                        <div className="font-semibold text-text-primary flex items-center gap-1.5">
                          <Check size={13} className="text-accent" />
                          Fixed Seed Length (532B)
                        </div>
                        <p className="text-text-secondary leading-normal">
                          Every entry seed is exactly 532 bytes (268B username + 264B password).
                          Ciphertext size reveals entry count, but zero information about credential lengths.
                        </p>
                      </div>

                      <div className="rounded-lg bg-bg-elevated p-3 border border-border-subtle space-y-1">
                        <div className="font-semibold text-text-primary flex items-center gap-1.5">
                          <Check size={13} className="text-accent" />
                          Total DTE Decoder
                        </div>
                        <p className="text-text-secondary leading-normal">
                          Every 532-byte plaintext seed decodes to a valid, printable username and password
                          drawn from the PCFG natural distribution.
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </div>
            </TabsContent>

            {/* Tab 2: Baseline Conventional Blob */}
            <TabsContent value="baseline" className="mt-0 space-y-4">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                <div className="lg:col-span-2 rounded-xl border border-border bg-bg-surface overflow-hidden shadow-card flex flex-col">
                  <div className="flex items-center justify-between px-4 py-2.5 bg-bg-elevated/80 border-b border-border">
                    <div className="flex items-center gap-2">
                      <FileCode2 size={15} className="text-danger" />
                      <span className="font-mono text-xs text-text-secondary">
                        conventional_vault_stolen.json
                      </span>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        void handleCopyBaseline();
                      }}
                      className="h-7 px-2 text-xs gap-1.5 text-text-secondary hover:text-text-primary"
                    >
                      {copiedBaseline ? <Check size={13} className="text-success" /> : <Copy size={13} />}
                      {copiedBaseline ? 'Copied' : 'Copy'}
                    </Button>
                  </div>

                  <div className="relative p-4 overflow-x-auto max-h-[380px] font-mono text-xs text-text-primary bg-[#080d17] leading-relaxed">
                    <pre className="selection:bg-danger/20">
                      <code>{baselineJson}</code>
                    </pre>
                  </div>
                </div>

                <div className="space-y-3">
                  <Card className="border-danger/30 bg-bg-surface shadow-card">
                    <CardHeader className="pb-3">
                      <CardTitle className="text-base flex items-center gap-2 text-danger">
                        <ShieldAlert size={16} />
                        The Conventional Flaw
                      </CardTitle>
                      <CardDescription className="text-xs">
                        How standard password managers get cracked offline
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3 text-xs">
                      <div className="rounded-lg bg-danger/10 p-3 border border-danger/20 space-y-1">
                        <div className="font-semibold text-danger">
                          16-Byte Auth Tag Oracle
                        </div>
                        <p className="text-text-secondary leading-normal">
                          The AES-256-GCM scheme includes a 128-bit authentication tag (<code className="text-danger font-mono font-bold">tag</code>).
                          Wrong passwords fail tag validation with 100% precision.
                        </p>
                      </div>

                      <div className="rounded-lg bg-bg-elevated p-3 border border-border-subtle space-y-1">
                        <div className="font-semibold text-text-primary">
                          GPU Dictionary Acceleration
                        </div>
                        <p className="text-text-secondary leading-normal">
                          Tools like Hashcat or John the Ripper iterate through billions of guesses per second,
                          checking only whether the GCM tag verifies. The first matching tag cracks the entire vault.
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </div>
            </TabsContent>
          </Tabs>

          {/* Stepper Navigation Footer */}
          <div className="flex items-center justify-between pt-4 border-t border-border">
            <div className="flex items-center gap-2 text-xs text-text-secondary">
              <Info size={14} className="text-accent" />
              <span>Step 1 of 3: Vault blobs ready for offline dictionary testing.</span>
            </div>

            <Button
              onClick={onNext}
              className="gap-2 bg-accent text-black font-semibold hover:bg-accent-hover shadow-glow"
            >
              Run Dictionary Attack
              <ArrowRight size={16} />
            </Button>
          </div>
        </div>
      )}
    </motion.div>
  );
}
