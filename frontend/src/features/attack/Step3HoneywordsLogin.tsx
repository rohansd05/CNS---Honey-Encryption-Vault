// owner: Chetan (T3) — Step 3: Honeywords & Online Login Breach (feat/t3-attack-lab)
import { useState } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import {
  KeyRound,
  AlertTriangle,
  Flame,
  Radio,
  ArrowLeft,
  RotateCcw,
  Clock,
  Send,
  BellRing,
} from 'lucide-react';
import { useStolenHoneywords, useAttackAlarms } from '@/api/hooks/useAttackQueries';
import { useLogin } from '@/api/hooks/useAuthQueries';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { toast } from 'sonner';

interface Step3HoneywordsLoginProps {
  onPrev: () => void;
  onResetFlow: () => void;
}

export function Step3HoneywordsLogin({ onPrev, onResetFlow }: Step3HoneywordsLoginProps) {
  const shouldReduceMotion = useReducedMotion();

  // Queries and mutations
  const { data: honeywordsData, isLoading: isLoadingHoneywords } = useStolenHoneywords();
  const { data: alarmsData, refetch: refetchAlarms } = useAttackAlarms(true);
  const loginMutation = useLogin();

  // Last attempted login info
  const [lastAttempt, setLastAttempt] = useState<{
    index: number;
    sweetword: string;
    timestamp: string;
    status: 'alarm' | 'success';
    errorMessage?: string;
  } | null>(null);

  const [testingIndex, setTestingIndex] = useState<number | null>(null);
  const [testedIndices, setTestedIndices] = useState<number[]>([]);

  const formatAlarmTimestamp = (iso: string) => {
    try {
      const str = iso.includes('Z') || iso.includes('+') ? iso : `${iso}Z`;
      return new Date(str).toLocaleTimeString();
    } catch {
      return iso;
    }
  };

  const handleTestLogin = (sweetword: string, index: number) => {
    setTestingIndex(index);

    // 1. Dispatch custom event so the attack mock handler adds a real-time breach alarm
    if (typeof window !== 'undefined') {
      window.dispatchEvent(
        new CustomEvent('hv:honeyword_attempt', {
          detail: { index, sweetword },
        }),
      );
    }

    if (!testedIndices.includes(index)) {
      setTestedIndices((prev) => [...prev, index]);
    }

    // 2. Call the REAL login hook from useLogin
    loginMutation.mutate(
      { username: honeywordsData?.username ?? 'demo', login_password: sweetword },
      {
        onError: (err) => {
          setTestingIndex(null);
          // A 401 is expected and desired: the API does not tip off the attacker!
          const message = err instanceof Error ? err.message : 'Invalid credentials';
          setLastAttempt({
            index,
            sweetword,
            timestamp: new Date().toLocaleTimeString(),
            status: 'alarm',
            errorMessage: message,
          });
          toast.warning(`Login failed with HTTP 401: "${message}"`);
          // 3. Immediately refetch the alarm feed to pull the new Honeychecker alert
          setTimeout(() => {
            void refetchAlarms();
          }, 200);
        },
        onSuccess: () => {
          setTestingIndex(null);
          setLastAttempt({
            index,
            sweetword,
            timestamp: new Date().toLocaleTimeString(),
            status: 'success',
          });
          toast.success('Login accepted — genuine password was tested!');
          setTimeout(() => {
            void refetchAlarms();
          }, 200);
        },
      },
    );
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="space-y-6"
    >
      {/* Step Context Banner */}
      <div className="rounded-xl border border-border bg-bg-surface p-6 shadow-card space-y-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-accent/20 text-xs font-bold text-accent">
                3
              </span>
              <h2 className="text-xl font-bold text-text-primary">
                Crack the Honeywords & Attempt Online Login
              </h2>
            </div>
            <p className="text-sm text-text-secondary max-w-2xl leading-relaxed">
              When an attacker cannot tell which master password was authentic, they target the server's authentication database.
              The database stores <strong>10 cracked sweetwords</strong> (1 real password + 9 decoy honeywords).
              Attempting an online login with a decoy sweetword immediately triggers the isolated <strong>Honeychecker</strong> service!
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={onResetFlow}
              className="gap-1.5 border-border hover:border-accent/40 text-text-secondary hover:text-text-primary"
            >
              <RotateCcw size={14} />
              Reset Lab Flow
            </Button>
          </div>
        </div>

        {/* Juels & Rivest Concept Callout */}
        <div className="rounded-lg bg-bg-elevated p-4 border border-border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 text-xs">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-accent/20 text-accent">
              <Flame size={16} />
            </div>
            <div>
              <span className="font-bold text-text-primary">Juels & Rivest (2013) Honeywords Model:</span>
              <p className="text-text-secondary mt-0.5">
                Target account: <span className="font-mono text-accent font-semibold">@{honeywordsData?.username ?? 'demo'}</span> ·{' '}
                <span className="text-text-primary font-medium">{String(honeywordsData?.k ?? 10)} sweetwords</span> cracked from salt-protected Argon2id hashes.
              </p>
            </div>
          </div>

          <Badge variant="outline" className="border-accent/50 text-accent font-mono text-[11px] shrink-0">
            Isolated Honeychecker: ACTIVE
          </Badge>
        </div>
      </div>

      {/* =========================================================================
          PROMINENT HONEYCHECKER BREACH ALARM / SUCCESS BANNER
         ========================================================================= */}
      <AnimatePresence>
        {lastAttempt && lastAttempt.status === 'alarm' && (
          <motion.div
            initial={{ opacity: 0, y: shouldReduceMotion ? 0 : -12, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="rounded-xl border-2 border-danger bg-danger/10 p-6 shadow-[0_0_30px_rgba(239,68,68,0.25)] space-y-4"
          >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-danger text-white animate-pulse">
                  <BellRing size={24} />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-lg font-black text-danger tracking-wide">
                      HONEYCHECKER RAISED A BREACH ALARM!
                    </h3>
                    <Badge variant="destructive" className="font-mono text-xs">
                      CRITICAL SEVERITY
                    </Badge>
                  </div>
                  <p className="text-xs text-text-secondary mt-0.5">
                    Sweetword candidate #{String(lastAttempt.index)} triggered an active tripwire at the authentication gate
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-xs font-mono text-text-muted flex items-center gap-1">
                  <Clock size={12} /> {lastAttempt.timestamp}
                </span>
              </div>
            </div>

            {/* Alarm Inspection Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-xs pt-1">
              <div className="rounded-lg bg-bg-surface/80 p-3 border border-danger/30 space-y-0.5">
                <div className="text-text-muted text-[11px]">Submitted Sweetword</div>
                <div className="font-mono font-bold text-danger truncate">"{lastAttempt.sweetword}"</div>
                <div className="text-[10px] text-text-muted">Index #{String(lastAttempt.index)} of 10</div>
              </div>

              <div className="rounded-lg bg-bg-surface/80 p-3 border border-danger/30 space-y-0.5">
                <div className="text-text-muted text-[11px]">Honeychecker Verdict</div>
                <div className="font-mono font-bold text-danger">MISMATCH (Alarm Logged)</div>
                <div className="text-[10px] text-text-muted">Tripwire recorded to audit log</div>
              </div>

              <div className="rounded-lg bg-bg-surface/80 p-3 border border-danger/30 space-y-0.5">
                <div className="text-text-muted text-[11px]">Attacker-Facing Response</div>
                <div className="font-mono font-bold text-text-primary">HTTP 401 Unauthorized</div>
                <div className="text-[10px] text-text-muted">"{lastAttempt.errorMessage ?? 'Invalid credentials'}"</div>
              </div>

              <div className="rounded-lg bg-bg-surface/80 p-3 border border-danger/30 space-y-0.5">
                <div className="text-text-muted text-[11px]">Security Posture</div>
                <div className="font-mono font-bold text-success">Zero Attacker Intel</div>
                <div className="text-[10px] text-text-muted">Silent alert dispatched to SecOps</div>
              </div>
            </div>

            <div className="rounded-lg bg-danger/15 p-3 border border-danger/30 text-xs text-text-secondary leading-relaxed flex items-start gap-2">
              <AlertTriangle size={15} className="text-danger mt-0.5 shrink-0" />
              <span>
                <strong>Why this is revolutionary:</strong> In standard systems, testing a wrong password just logs a failed login.
                With Honeywords, any guess of a decoy sweetword is mathematical proof that an attacker cracked the hash database,
                allowing immediate account isolation without the attacker realizing they were detected.
              </span>
            </div>
          </motion.div>
        )}

        {lastAttempt && lastAttempt.status === 'success' && (
          <motion.div
            initial={{ opacity: 0, y: shouldReduceMotion ? 0 : -12, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="rounded-xl border-2 border-accent bg-accent/10 p-6 shadow-glow space-y-4"
          >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-accent text-black font-bold">
                  <KeyRound size={24} />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-lg font-bold text-text-primary">
                      AUTHENTIC PASSWORD TESTED — LOGIN ACCEPTED
                    </h3>
                    <Badge variant="outline" className="border-accent text-accent font-mono text-xs">
                      SUCCESS
                    </Badge>
                  </div>
                  <p className="text-xs text-text-secondary mt-0.5">
                    Sweetword candidate #{String(lastAttempt.index)} was the authentic master password!
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-xs font-mono text-text-muted flex items-center gap-1">
                  <Clock size={12} /> {lastAttempt.timestamp}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-xs pt-1">
              <div className="rounded-lg bg-bg-surface/80 p-3 border border-accent/30 space-y-0.5">
                <div className="text-text-muted text-[11px]">Submitted Password</div>
                <div className="font-mono font-bold text-accent truncate">"{lastAttempt.sweetword}"</div>
                <div className="text-[10px] text-text-muted">Index #{String(lastAttempt.index)} of 10</div>
              </div>

              <div className="rounded-lg bg-bg-surface/80 p-3 border border-accent/30 space-y-0.5">
                <div className="text-text-muted text-[11px]">Honeychecker Verdict</div>
                <div className="font-mono font-bold text-success">MATCH (No Alarm)</div>
                <div className="text-[10px] text-text-muted">Genuine user authentication path</div>
              </div>

              <div className="rounded-lg bg-bg-surface/80 p-3 border border-accent/30 space-y-0.5">
                <div className="text-text-muted text-[11px]">Attacker-Facing Response</div>
                <div className="font-mono font-bold text-success">HTTP 200 OK</div>
                <div className="text-[10px] text-text-muted">Valid JWT Session Issued</div>
              </div>

              <div className="rounded-lg bg-bg-surface/80 p-3 border border-accent/30 space-y-0.5">
                <div className="text-text-muted text-[11px]">Juels & Rivest Implication</div>
                <div className="font-mono font-bold text-text-primary">1 in k Success (10%)</div>
                <div className="text-[10px] text-text-muted">Single lucky guess (unpreventable)</div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* =========================================================================
          SWEETWORD CRACKED CANDIDATES LIST
         ========================================================================= */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <KeyRound size={16} className="text-accent" />
            <h3 className="text-base font-bold text-text-primary">
              Cracked Sweetword Candidates ({String(honeywordsData?.cracked_sweetwords.length ?? 10)})
            </h3>
          </div>
          <span className="text-xs text-text-muted">
            Click any candidate to simulate an attacker login attempt
          </span>
        </div>

        {isLoadingHoneywords ? (
          <div className="p-8 text-center text-text-secondary bg-bg-surface rounded-xl border border-border">
            Loading sweetwords from attack API...
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {honeywordsData?.cracked_sweetwords.map((sweetword, idx) => {
              const isTested = testedIndices.includes(idx);
              const isLast = lastAttempt !== null && lastAttempt.index === idx;
              const isLastAlarm = isLast && lastAttempt.status === 'alarm';
              const isLastSuccess = isLast && lastAttempt.status === 'success';

              return (
                <div
                  key={idx}
                  className={`rounded-xl border p-4 transition-all duration-200 flex flex-col justify-between gap-3 ${
                    isLastAlarm
                      ? 'border-danger bg-danger/10 shadow-[0_0_16px_rgba(239,68,68,0.2)]'
                      : isLastSuccess
                        ? 'border-accent bg-accent/10 shadow-glow'
                        : isTested
                          ? 'border-border bg-bg-elevated/70'
                          : 'border-border bg-bg-surface hover:border-accent/50 hover:bg-bg-elevated'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <Badge
                          variant={
                            isLastAlarm
                              ? 'destructive'
                              : isLastSuccess
                                ? 'default'
                                : isTested
                                  ? 'secondary'
                                  : 'outline'
                          }
                          className="font-mono text-xs px-2 py-0.5"
                        >
                          Sweetword #{String(idx)}
                        </Badge>
                        <span className="font-mono text-sm font-bold text-text-primary">
                          {sweetword}
                        </span>
                      </div>
                      <div className="font-mono text-[11px] text-text-muted truncate max-w-xs">
                        Hash: {honeywordsData.hashes[idx] ?? '$argon2id$v=19$...'}
                      </div>
                    </div>

                    {isTested && (
                      <Badge variant="outline" className="text-[10px] text-danger border-danger/40">
                        Tested
                      </Badge>
                    )}
                  </div>

                  <div className="flex items-center justify-between pt-1">
                    <span className="text-[11px] text-text-muted">
                      Candidate Sweetword #{String(idx)}
                    </span>

                    <Button
                      size="sm"
                      variant={isLastAlarm ? 'destructive' : 'outline'}
                      onClick={() => {
                        handleTestLogin(sweetword, idx);
                      }}
                      disabled={loginMutation.isPending && testingIndex === idx}
                      className="h-8 text-xs gap-1.5 border-border hover:border-accent hover:text-accent"
                    >
                      <Send size={12} className={testingIndex === idx ? 'animate-spin' : ''} />
                      {testingIndex === idx ? 'Testing...' : 'Test Login'}
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* =========================================================================
          REAL-TIME ALARMS MONITOR TABLE
         ========================================================================= */}
      <Card className="border-border bg-bg-surface shadow-card">
        <CardHeader className="pb-3 border-b border-border">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Radio size={16} className="text-danger animate-pulse" />
              <CardTitle className="text-base text-text-primary">
                Honeychecker Live Breach Alarms
              </CardTitle>
            </div>
            <div className="flex items-center gap-2 text-xs font-mono text-text-muted">
              <span className="inline-block h-2 w-2 rounded-full bg-success animate-ping" />
              <span>Polling /api/attack/alarms (3s)</span>
            </div>
          </div>
          <CardDescription className="text-xs">
            Audit log of security trips raised by the Honeychecker daemon
          </CardDescription>
        </CardHeader>

        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader className="bg-bg-elevated/70">
                <TableRow className="border-border">
                  <TableHead className="text-xs text-text-muted h-9">Timestamp</TableHead>
                  <TableHead className="text-xs text-text-muted h-9">Event Type</TableHead>
                  <TableHead className="text-xs text-text-muted h-9">Severity</TableHead>
                  <TableHead className="text-xs text-text-muted h-9">Index</TableHead>
                  <TableHead className="text-xs text-text-muted h-9">Source IP</TableHead>
                  <TableHead className="text-xs text-text-muted h-9">User Agent</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {alarmsData && alarmsData.length > 0 ? (
                  alarmsData.map((alarm) => (
                    <TableRow key={alarm.id} className="border-border/60 font-mono text-xs">
                      <TableCell className="text-text-secondary py-2">
                        {formatAlarmTimestamp(alarm.created_at)}
                      </TableCell>
                      <TableCell className="font-semibold text-danger py-2">
                        {alarm.kind}
                      </TableCell>
                      <TableCell className="py-2">
                        <Badge variant="destructive" className="text-[10px] py-0 px-1.5 uppercase font-mono">
                          {alarm.severity}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-accent font-bold py-2">
                        #{String(alarm.sweetword_index)}
                      </TableCell>
                      <TableCell className="text-text-secondary py-2">
                        {alarm.source_ip}
                      </TableCell>
                      <TableCell className="text-text-muted py-2 max-w-[200px] truncate" title={alarm.user_agent}>
                        {alarm.user_agent}
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-6 text-text-muted text-xs">
                      No alarms recorded yet. Click a sweetword above to trigger the Honeychecker!
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Stepper Navigation Footer */}
      <div className="flex items-center justify-between pt-4 border-t border-border">
        <Button
          variant="outline"
          onClick={onPrev}
          className="gap-2 border-border hover:border-accent/40 text-text-secondary hover:text-text-primary"
        >
          <ArrowLeft size={16} />
          Back to Dictionary Attack
        </Button>

        <Button
          onClick={onResetFlow}
          className="gap-2 bg-accent text-black font-semibold hover:bg-accent-hover shadow-glow"
        >
          <RotateCcw size={15} />
          Restart Lab Simulation
        </Button>
      </div>
    </motion.div>
  );
}
