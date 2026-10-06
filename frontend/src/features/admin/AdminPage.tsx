import { useState, useEffect, useMemo } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import {
  ShieldAlert,
  UserCheck,
} from 'lucide-react';
import { toast } from 'sonner';
import { useAdminAlerts } from '@/api/hooks/useAdminQueries';
import type { AdminAlert } from '@/api/types';
import { useAuth } from '@/lib/auth';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { AdminStatsHeader } from './components/AdminStatsHeader';
import { AdminFilters } from './components/AdminFilters';
import { AdminAlertsTable } from './components/AdminAlertsTable';
import { AdminHoneywordsPanel } from './components/AdminHoneywordsPanel';
import { AdminEmptyState } from './components/AdminEmptyState';

export function AdminPage() {
  const shouldReduceMotion = useReducedMotion();
  const { user } = useAuth();
  const { data, isLoading, refetch, isFetching, dataUpdatedAt } =
    useAdminAlerts();

  // Local simulated alerts to allow interactive testing & cross-tab sync
  const [extraAlerts, setExtraAlerts] = useState<AdminAlert[]>([]);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [severityFilter, setSeverityFilter] = useState<string>('all');

  // Listen for honeyword login attempts dispatched across the application
  useEffect(() => {
    const handleHoneywordAttempt = (e: Event) => {
      const customEvent = e as CustomEvent<{ index: number; sweetword: string; username?: string }>;
      const { index, username } = customEvent.detail;

      const targetUsername = typeof username === 'string' && username.length > 0 ? username : 'demo';
      const sweetIndex = typeof index === 'number' ? index : Math.floor(Math.random() * 9);

      const simulatedAlert: AdminAlert = {
        id: `alt-sim-${Date.now().toString()}`,
        username: targetUsername,
        kind: 'HONEYWORD_LOGIN',
        severity: 'critical',
        sweetword_index: sweetIndex,
        source_ip: '198.51.100.42',
        user_agent: navigator.userAgent,
        created_at: new Date().toISOString(),
      };

      setExtraAlerts((prev) => [simulatedAlert, ...prev]);
      toast.error(
        `CRITICAL BREACH ALARM: Decoy sweetword #${String(sweetIndex)} triggered for '${targetUsername}'!`,
        {
          description: `Source IP: ${simulatedAlert.source_ip} (logged by Honeychecker)`,
          duration: 5000,
        },
      );
    };

    window.addEventListener('hv:honeyword_attempt', handleHoneywordAttempt);
    return () => {
      window.removeEventListener('hv:honeyword_attempt', handleHoneywordAttempt);
    };
  }, []);

  // Merge server alerts with any locally simulated alerts, deduping by id
  const allAlerts = useMemo(() => {
    const serverAlerts = data ?? [];
    const merged = [...extraAlerts, ...serverAlerts];
    const seen = new Set<string>();
    return merged.filter((item) => {
      if (seen.has(item.id)) return false;
      seen.add(item.id);
      return true;
    });
  }, [data, extraAlerts]);

  // Filter alerts based on search and severity
  const filteredAlerts = useMemo(() => {
    return allAlerts.filter((alert) => {
      // Username / IP filter
      if (searchTerm.trim()) {
        const query = searchTerm.toLowerCase();
        const matchesUser = alert.username.toLowerCase().includes(query);
        const matchesIp = alert.source_ip.toLowerCase().includes(query);
        if (!matchesUser && !matchesIp) return false;
      }
      // Severity filter
      if (severityFilter !== 'all') {
        if (alert.severity.toLowerCase() !== severityFilter.toLowerCase()) return false;
      }
      return true;
    });
  }, [allAlerts, searchTerm, severityFilter]);

  const handleSimulateAlert = () => {
    const mockUsernames = ['demo', 'alice', 'bob', 'charlie'];
    const randomUser = mockUsernames[Math.floor(Math.random() * mockUsernames.length)] ?? 'demo';
    const randomIndex = Math.floor(Math.random() * 9) + 1;
    const randomIp = `198.51.100.${String(Math.floor(Math.random() * 200) + 10)}`;

    const newAlert: AdminAlert = {
      id: `alt-sim-${Date.now().toString()}`,
      username: randomUser,
      kind: 'HONEYWORD_LOGIN',
      severity: 'critical',
      sweetword_index: randomIndex,
      source_ip: randomIp,
      user_agent: 'curl/8.5.0 (Security Scanner)',
      created_at: new Date().toISOString(),
    };

    setExtraAlerts((prev) => [newAlert, ...prev]);
    toast.error(`Security Breach Alarm Generated`, {
      description: `Honeyword login hit index #${String(randomIndex)} for ${randomUser}. Honeychecker alerted.`,
      duration: 4000,
    });
  };

  return (
    <div className="min-h-screen py-8 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="space-y-4"
      >
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <div className="h-12 w-12 rounded-xl bg-danger/15 border border-danger/35 flex items-center justify-center text-danger shadow-[0_0_16px_rgba(239,68,68,0.2)] shrink-0">
              <ShieldAlert size={26} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl sm:text-3xl font-extrabold text-text-primary tracking-tight">
                  Security Admin Console
                </h1>
                <Badge
                  variant="outline"
                  className="bg-danger/10 text-danger border-danger/30 text-xs font-semibold"
                >
                  AdminRoute Only
                </Badge>
              </div>
              <p className="text-xs sm:text-sm text-text-secondary mt-1">
                Real-time breach telemetry from Honeychecker tripwire authentication alarms.
              </p>
            </div>
          </div>

          {/* Admin User Badge */}
          <div className="flex items-center gap-2.5 px-3 py-1.5 rounded-xl bg-bg-surface border border-border text-xs self-start md:self-auto">
            <UserCheck size={14} className="text-success" />
            <span className="text-text-muted">Operator:</span>
            <span className="font-mono font-bold text-text-primary">
              {user?.username ?? 'admin'}
            </span>
          </div>
        </div>
      </motion.div>

      {/* Stats Header Tiles */}
      <section aria-label="Incident Summary Statistics">
        <AdminStatsHeader alerts={allAlerts} />
      </section>

      {/* Toolbar: Search, Filters, Live Polling Beacon */}
      <section aria-label="Alert Filters and Telemetry Controls">
        <AdminFilters
          searchTerm={searchTerm}
          onSearchChange={setSearchTerm}
          severityFilter={severityFilter}
          onSeverityChange={setSeverityFilter}
          totalAlerts={allAlerts.length}
          filteredAlerts={filteredAlerts.length}
          isFetching={isFetching}
          onRefresh={() => {
            void refetch();
          }}
          dataUpdatedAt={dataUpdatedAt}
          onSimulate={handleSimulateAlert}
        />
      </section>

      {/* Alerts Table or Empty/Loading State */}
      <section aria-label="Breach Telemetry Incidents">
        {isLoading && allAlerts.length === 0 ? (
          <div className="space-y-3">
            <Skeleton className="h-12 w-full rounded-xl" />
            <Skeleton className="h-40 w-full rounded-xl" />
          </div>
        ) : filteredAlerts.length > 0 ? (
          <AdminAlertsTable alerts={filteredAlerts} />
        ) : (
          <AdminEmptyState
            hasFilters={searchTerm.trim() !== '' || severityFilter !== 'all'}
            onResetFilters={() => {
              setSearchTerm('');
              setSeverityFilter('all');
            }}
            onSimulate={handleSimulateAlert}
          />
        )}
      </section>

      {/* Educational & Threat Containment Honeywords Panel */}
      <section aria-label="Educational Guidance">
        <AdminHoneywordsPanel />
      </section>
    </div>
  );
}
