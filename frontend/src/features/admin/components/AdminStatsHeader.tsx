import { motion } from 'framer-motion';
import {
  ShieldAlert,
  Flame,
  Users,
  Radio,
} from 'lucide-react';
import type { AdminAlert } from '@/api/types';
import { Card, CardContent } from '@/components/ui/card';

interface AdminStatsHeaderProps {
  alerts: AdminAlert[];
}

export function AdminStatsHeader({ alerts }: AdminStatsHeaderProps) {
  const total = alerts.length;
  const critical = alerts.filter((a) => a.severity === 'critical').length;
  const uniqueUsers = new Set(alerts.map((a) => a.username)).size;

  const cardVariants = {
    hidden: { opacity: 0, y: 12 },
    visible: (i: number) => ({
      opacity: 1,
      y: 0,
      transition: { duration: 0.3, delay: i * 0.06 },
    }),
  };

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
      {/* Stat 1: Total Alerts */}
      <motion.div custom={0} variants={cardVariants} initial="hidden" animate="visible">
        <Card className="border-border bg-bg-surface shadow-card p-4">
          <CardContent className="p-0 flex items-center justify-between">
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-wider text-text-muted">
                Total Breach Alarms
              </div>
              <div className="text-2xl font-extrabold text-text-primary font-mono mt-1">
                {total}
              </div>
              <div className="text-[11px] text-text-secondary mt-0.5">
                Logged by Honeychecker
              </div>
            </div>
            <div className="h-10 w-10 rounded-xl bg-accent/10 border border-accent/25 flex items-center justify-center text-accent shrink-0">
              <ShieldAlert size={20} />
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Stat 2: Critical Breaches */}
      <motion.div custom={1} variants={cardVariants} initial="hidden" animate="visible">
        <Card className="border-border bg-bg-surface shadow-card p-4">
          <CardContent className="p-0 flex items-center justify-between">
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-wider text-text-muted">
                Critical Severity
              </div>
              <div className="text-2xl font-extrabold text-danger font-mono mt-1">
                {critical}
              </div>
              <div className="text-[11px] text-text-secondary mt-0.5">
                Decoy honeyword hits
              </div>
            </div>
            <div className="h-10 w-10 rounded-xl bg-danger/10 border border-danger/25 flex items-center justify-center text-danger shrink-0">
              <Flame size={20} />
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Stat 3: Unique Users Targeted */}
      <motion.div custom={2} variants={cardVariants} initial="hidden" animate="visible">
        <Card className="border-border bg-bg-surface shadow-card p-4">
          <CardContent className="p-0 flex items-center justify-between">
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-wider text-text-muted">
                Target Accounts
              </div>
              <div className="text-2xl font-extrabold text-text-primary font-mono mt-1">
                {uniqueUsers}
              </div>
              <div className="text-[11px] text-text-secondary mt-0.5">
                Victim user accounts
              </div>
            </div>
            <div className="h-10 w-10 rounded-xl bg-info/10 border border-info/25 flex items-center justify-center text-info shrink-0">
              <Users size={20} />
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Stat 4: Tripwire Status */}
      <motion.div custom={3} variants={cardVariants} initial="hidden" animate="visible">
        <Card className="border-border bg-bg-surface shadow-card p-4">
          <CardContent className="p-0 flex items-center justify-between">
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-wider text-text-muted">
                Tripwire Network
              </div>
              <div className="text-base font-bold text-success flex items-center gap-1.5 mt-1">
                <span className="h-2 w-2 rounded-full bg-success animate-pulse" />
                <span>ARMED & ACTIVE</span>
              </div>
              <div className="text-[11px] text-text-secondary mt-0.5">
                k=10 Sweetwords/User
              </div>
            </div>
            <div className="h-10 w-10 rounded-xl bg-success/10 border border-success/25 flex items-center justify-center text-success shrink-0">
              <Radio size={20} />
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
