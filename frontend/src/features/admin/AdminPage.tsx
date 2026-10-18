import { useState, useMemo } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import {
  ShieldAlert,
  UserCheck,
  AlertCircle,
  RotateCcw,
} from 'lucide-react';
import { useAdminAlerts } from '@/api/hooks/useAdminQueries';
import type { AdminAlert } from '@/api/types';
import { useAuth } from '@/lib/auth';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { AdminStatsHeader } from './components/AdminStatsHeader';
import { AdminFilters } from './components/AdminFilters';
import { AdminAlertsTable } from './components/AdminAlertsTable';
import { AdminHoneywordsPanel } from './components/AdminHoneywordsPanel';
import { AdminEmptyState } from './components/AdminEmptyState';

export function AdminPage() {
  const shouldReduceMotion = useReducedMotion();
  const { user } = useAuth();
  const { data, isLoading, isError, refetch, isFetching, dataUpdatedAt } =
    useAdminAlerts();

  const [searchTerm, setSearchTerm] = useState<string>('');
  const [severityFilter, setSeverityFilter] = useState<string>('all');

  const allAlerts: AdminAlert[] = useMemo(() => data ?? [], [data]);

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
        />
      </section>

      {/* Alerts Table or Empty/Loading/Error State */}
      <section aria-label="Breach Telemetry Incidents">
        {isError ? (
          <Card className="border-border border-dashed bg-bg-surface/60 max-w-xl mx-auto my-10 text-center p-8 sm:p-10 shadow-card">
            <CardContent className="space-y-5">
              <div className="h-16 w-16 mx-auto rounded-2xl bg-danger/10 border border-danger/20 flex items-center justify-center text-danger shadow-[0_0_20px_rgba(239,68,68,0.15)]">
                <AlertCircle size={32} />
              </div>
              <div className="space-y-1.5">
                <h3 className="text-lg sm:text-xl font-bold text-text-primary">
                  Couldn't load alerts
                </h3>
                <p className="text-xs sm:text-sm text-text-secondary max-w-md mx-auto leading-relaxed">
                  Failed to fetch breach telemetry from the Honeychecker service.
                </p>
              </div>
              <div className="flex items-center justify-center pt-2">
                <Button
                  onClick={() => {
                    void refetch();
                  }}
                  variant="outline"
                  size="sm"
                  className="border-border hover:bg-bg-elevated text-xs font-semibold text-text-primary gap-1.5"
                >
                  <RotateCcw size={14} />
                  <span>Retry</span>
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : isLoading && allAlerts.length === 0 ? (
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
