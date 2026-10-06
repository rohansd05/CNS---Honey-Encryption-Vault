import { useState } from 'react';
import {
  ShieldAlert,
  ChevronDown,
  KeyRound,
  Server,
  ZapOff,
  AlertTriangle,
  FileCheck2,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

export function AdminHoneywordsPanel() {
  const [isExpanded, setIsExpanded] = useState<boolean>(true);

  return (
    <Card className="border-border bg-bg-surface shadow-card overflow-hidden">
      <CardHeader className="p-4 sm:p-5 bg-bg-elevated/30 border-b border-border/80">
        <button
          onClick={() => {
            setIsExpanded((prev) => !prev);
          }}
          className="w-full flex items-center justify-between text-left"
          aria-expanded={isExpanded}
        >
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-xl bg-danger/15 border border-danger/35 flex items-center justify-center text-danger shadow-[0_0_12px_rgba(239,68,68,0.15)] shrink-0">
              <ShieldAlert size={20} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <CardTitle className="text-sm sm:text-base font-bold text-text-primary">
                  What This Means: Honeywords Tripwire Telemetry
                </CardTitle>
                <Badge variant="outline" className="text-[10px] bg-danger/10 text-danger border-danger/30 font-semibold">
                  Juels & Rivest 2013
                </Badge>
              </div>
              <p className="text-xs text-text-secondary mt-0.5">
                Understanding offline hash breach detection & silent tripwires
              </p>
            </div>
          </div>

          <ChevronDown
            size={18}
            className={`text-text-muted transition-transform duration-200 shrink-0 ${
              isExpanded ? 'rotate-180 text-accent' : ''
            }`}
          />
        </button>
      </CardHeader>

      {isExpanded && (
        <CardContent className="p-5 space-y-5 text-xs sm:text-sm text-text-secondary leading-relaxed">
          {/* 3 Step Flow Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Step 1: Generation & Storage */}
            <div className="p-4 rounded-xl bg-bg-elevated/50 border border-border space-y-2">
              <div className="flex items-center gap-2 text-accent font-semibold text-xs sm:text-sm">
                <KeyRound size={16} />
                <span>1. k Sweetwords Stored</span>
              </div>
              <p className="text-text-secondary text-xs">
                During registration, HoneyVault creates $k = 10$ sweetwords: the real login password + 5 PCFG lookalikes (<code className="font-mono text-accent">sample_like</code>) + 4 tail-tweaks. The main DB stores Argon2id hashes for all 10.
              </p>
            </div>

            {/* Step 2: Honeychecker Isolation */}
            <div className="p-4 rounded-xl bg-bg-elevated/50 border border-border space-y-2">
              <div className="flex items-center gap-2 text-info font-semibold text-xs sm:text-sm">
                <Server size={16} />
                <span>2. Isolated Honeychecker</span>
              </div>
              <p className="text-text-secondary text-xs">
                Only the isolated Honeychecker service knows which index (0–9) is the real password. The primary API database never stores the index, preventing offline database dump correlation.
              </p>
            </div>

            {/* Step 3: Silent Breach Alarm */}
            <div className="p-4 rounded-xl bg-bg-elevated/50 border border-border space-y-2">
              <div className="flex items-center gap-2 text-danger font-semibold text-xs sm:text-sm">
                <ZapOff size={16} />
                <span>3. Silent Tripwire Alarm</span>
              </div>
              <p className="text-text-secondary text-xs">
                When an attacker cracks the hashes offline and attempts login with any decoy sweetword, Honeychecker flags a breach. The API returns standard <strong>401 Unauthorized</strong>, keeping the attacker in the dark.
              </p>
            </div>
          </div>

          {/* Actionable SOC Playbook */}
          <div className="p-4 rounded-xl bg-danger/10 border border-danger/25 space-y-2 text-xs">
            <div className="flex items-center gap-2 text-danger font-bold text-xs uppercase tracking-wider">
              <AlertTriangle size={15} />
              <span>Recommended Security Incident Response Playbook</span>
            </div>
            <p className="text-text-primary">
              A <code className="font-mono text-danger font-bold">HONEYWORD_LOGIN</code> alert confirms with near certainty that your password hash database was exfiltrated and subjected to offline cracking.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1 text-text-secondary">
              <div className="flex items-start gap-2">
                <FileCheck2 size={14} className="text-accent shrink-0 mt-0.5" />
                <span><strong>Rotate Credentials:</strong> Invalidate all active sessions for the targeted user and force password reset.</span>
              </div>
              <div className="flex items-start gap-2">
                <FileCheck2 size={14} className="text-accent shrink-0 mt-0.5" />
                <span><strong>Quarantine Attacker IP:</strong> Block the source IP at edge firewall and inspect network logs for exfiltration.</span>
              </div>
              <div className="flex items-start gap-2">
                <FileCheck2 size={14} className="text-accent shrink-0 mt-0.5" />
                <span><strong>Audit Database Backups:</strong> Identify unauthorized read access to production databases or snapshot storage.</span>
              </div>
              <div className="flex items-start gap-2">
                <FileCheck2 size={14} className="text-accent shrink-0 mt-0.5" />
                <span><strong>Preserve Evidence:</strong> Archive Honeychecker audit logs for forensic attribution.</span>
              </div>
            </div>
          </div>
        </CardContent>
      )}
    </Card>
  );
}
