import { useState } from 'react';
import {
  ShieldAlert,
  Clock,
  Copy,
  Check,
  Globe,
  Maximize2,
  Terminal,
} from 'lucide-react';
import type { AdminAlert } from '@/api/types';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableHeader,
  TableRow,
  TableHead,
  TableBody,
  TableCell,
} from '@/components/ui/table';
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
  TooltipProvider,
} from '@/components/ui/tooltip';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { formatRelativeTime, formatAbsoluteUtc, getSeverityStyle } from '../utils';

interface AdminAlertsTableProps {
  alerts: AdminAlert[];
}

export function AdminAlertsTable({ alerts }: AdminAlertsTableProps) {
  const [copiedIp, setCopiedIp] = useState<string | null>(null);
  const [selectedAlert, setSelectedAlert] = useState<AdminAlert | null>(null);

  const handleCopyIp = (ip: string) => {
    void navigator.clipboard.writeText(ip);
    setCopiedIp(ip);
    setTimeout(() => {
      setCopiedIp(null);
    }, 1800);
  };

  return (
    <TooltipProvider>
      <div className="rounded-xl border border-border bg-bg-surface overflow-hidden shadow-card">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader className="bg-bg-elevated/40 border-b border-border">
              <TableRow className="hover:bg-transparent border-border">
                <TableHead className="w-[170px] text-xs font-semibold text-text-muted uppercase tracking-wider">
                  Timestamp
                </TableHead>
                <TableHead className="w-[140px] text-xs font-semibold text-text-muted uppercase tracking-wider">
                  Target Account
                </TableHead>
                <TableHead className="w-[180px] text-xs font-semibold text-text-muted uppercase tracking-wider">
                  Breach Event
                </TableHead>
                <TableHead className="w-[110px] text-xs font-semibold text-text-muted uppercase tracking-wider">
                  Severity
                </TableHead>
                <TableHead className="w-[130px] text-xs font-semibold text-text-muted uppercase tracking-wider">
                  Sweetword
                </TableHead>
                <TableHead className="w-[150px] text-xs font-semibold text-text-muted uppercase tracking-wider">
                  Source IP
                </TableHead>
                <TableHead className="min-w-[200px] text-xs font-semibold text-text-muted uppercase tracking-wider">
                  User Agent
                </TableHead>
                <TableHead className="w-[70px] text-right text-xs font-semibold text-text-muted uppercase tracking-wider">
                  Inspect
                </TableHead>
              </TableRow>
            </TableHeader>

            <TableBody>
              {alerts.map((alert) => {
                const severityStyle = getSeverityStyle(alert.severity);
                const relativeTime = formatRelativeTime(alert.created_at);
                const absoluteTime = formatAbsoluteUtc(alert.created_at);

                return (
                  <TableRow
                    key={alert.id}
                    className="border-b border-border/60 hover:bg-bg-elevated/30 transition-colors"
                  >
                    {/* Time (Relative + Absolute Tooltip) */}
                    <TableCell className="py-3.5">
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <div className="flex items-center gap-1.5 cursor-help">
                            <Clock size={13} className="text-text-muted shrink-0" />
                            <span className="text-xs font-medium text-text-primary">
                              {relativeTime}
                            </span>
                          </div>
                        </TooltipTrigger>
                        <TooltipContent side="top" className="text-xs font-mono">
                          {absoluteTime}
                        </TooltipContent>
                      </Tooltip>
                      <div className="text-[11px] text-text-muted font-mono mt-0.5 truncate max-w-[150px]">
                        {new Date(alert.created_at).toLocaleTimeString()}
                      </div>
                    </TableCell>

                    {/* Target Username */}
                    <TableCell className="py-3.5">
                      <div className="flex items-center gap-2">
                        <div className="h-7 w-7 rounded-full bg-accent/15 border border-accent/30 flex items-center justify-center text-accent text-xs font-bold uppercase shrink-0">
                          {alert.username.slice(0, 2)}
                        </div>
                        <span className="text-xs font-semibold text-text-primary font-mono">
                          {alert.username}
                        </span>
                      </div>
                    </TableCell>

                    {/* Kind */}
                    <TableCell className="py-3.5">
                      <div className="flex items-center gap-1.5">
                        <ShieldAlert size={14} className="text-danger shrink-0" />
                        <div>
                          <span className="text-xs font-mono font-semibold text-text-primary">
                            {alert.kind}
                          </span>
                          <p className="text-[10px] text-text-muted leading-tight">
                            Decoy tripwire triggered
                          </p>
                        </div>
                      </div>
                    </TableCell>

                    {/* Severity Badge (Critical = Red) */}
                    <TableCell className="py-3.5">
                      <Badge
                        variant="outline"
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-md uppercase tracking-wider ${severityStyle.badgeClass}`}
                      >
                        {severityStyle.label}
                      </Badge>
                    </TableCell>

                    {/* Sweetword Index */}
                    <TableCell className="py-3.5">
                      <div className="flex items-center gap-1.5">
                        <Badge
                          variant="outline"
                          className="bg-accent/15 text-accent border-accent/30 font-mono text-xs px-2 py-0.5"
                        >
                          Index #{String(alert.sweetword_index)}
                        </Badge>
                        <span className="text-[10px] text-text-muted">/ k=10</span>
                      </div>
                    </TableCell>

                    {/* Source IP (Copyable) */}
                    <TableCell className="py-3.5">
                      <div className="flex items-center gap-1.5 font-mono text-xs text-text-primary">
                        <span>{alert.source_ip}</span>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <button
                              onClick={() => {
                                handleCopyIp(alert.source_ip);
                              }}
                              className="text-text-muted hover:text-text-primary p-1 rounded transition-colors"
                              aria-label="Copy IP"
                            >
                              {copiedIp === alert.source_ip ? (
                                <Check size={12} className="text-success" />
                              ) : (
                                <Copy size={12} />
                              )}
                            </button>
                          </TooltipTrigger>
                          <TooltipContent side="top">
                            {copiedIp === alert.source_ip ? 'Copied!' : 'Copy IP'}
                          </TooltipContent>
                        </Tooltip>
                      </div>
                    </TableCell>

                    {/* User Agent (Truncated + Tooltip) */}
                    <TableCell className="py-3.5">
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <div className="flex items-center gap-1.5 max-w-[260px] cursor-help">
                            <Globe size={13} className="text-text-muted shrink-0" />
                            <span className="text-xs text-text-secondary truncate font-mono">
                              {alert.user_agent}
                            </span>
                          </div>
                        </TooltipTrigger>
                        <TooltipContent side="top" className="max-w-md text-xs font-mono break-all">
                          {alert.user_agent}
                        </TooltipContent>
                      </Tooltip>
                    </TableCell>

                    {/* Action / Inspect */}
                    <TableCell className="py-3.5 text-right">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => {
                          setSelectedAlert(alert);
                        }}
                        className="h-7 w-7 text-text-muted hover:text-text-primary hover:bg-bg-elevated"
                        aria-label="Inspect Alert Payload"
                      >
                        <Maximize2 size={13} />
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      </div>

      {/* Inspect Alert Dialog */}
      <Dialog
        open={Boolean(selectedAlert)}
        onOpenChange={(open) => {
          if (!open) setSelectedAlert(null);
        }}
      >
        <DialogContent className="max-w-lg bg-bg-surface border-border text-text-primary">
          <DialogHeader>
            <DialogTitle className="text-base font-bold flex items-center gap-2">
              <ShieldAlert size={18} className="text-danger" />
              <span>Breach Alert Incident Details</span>
            </DialogTitle>
            <DialogDescription className="text-xs text-text-secondary">
              Raw telemetry logged by Honeychecker on unauthorized tripwire hit.
            </DialogDescription>
          </DialogHeader>

          {selectedAlert && (
            <div className="space-y-4 pt-2">
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded-lg bg-bg-elevated border border-border">
                  <div className="text-text-muted uppercase text-[10px] font-semibold">Incident ID</div>
                  <div className="font-mono text-text-primary mt-0.5">{selectedAlert.id}</div>
                </div>
                <div className="p-3 rounded-lg bg-bg-elevated border border-border">
                  <div className="text-text-muted uppercase text-[10px] font-semibold">Target Account</div>
                  <div className="font-mono text-accent mt-0.5 font-bold">{selectedAlert.username}</div>
                </div>
                <div className="p-3 rounded-lg bg-bg-elevated border border-border">
                  <div className="text-text-muted uppercase text-[10px] font-semibold">Triggered Sweetword</div>
                  <div className="font-mono text-text-primary mt-0.5">
                    Position #{String(selectedAlert.sweetword_index)} (Decoy)
                  </div>
                </div>
                <div className="p-3 rounded-lg bg-bg-elevated border border-border">
                  <div className="text-text-muted uppercase text-[10px] font-semibold">Attacker IP</div>
                  <div className="font-mono text-text-primary mt-0.5">{selectedAlert.source_ip}</div>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-bg-elevated border border-border space-y-1">
                <div className="text-text-muted uppercase text-[10px] font-semibold">Client User Agent</div>
                <div className="font-mono text-xs text-text-secondary break-all">
                  {selectedAlert.user_agent}
                </div>
              </div>

              <div className="space-y-1.5">
                <div className="text-text-muted text-[11px] font-semibold flex items-center gap-1.5">
                  <Terminal size={12} className="text-accent" />
                  <span>Raw Telemetry JSON</span>
                </div>
                <pre className="p-3 rounded-lg bg-bg-overlay/80 border border-border text-[11px] font-mono text-text-primary overflow-x-auto">
                  {JSON.stringify(selectedAlert, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </TooltipProvider>
  );
}
