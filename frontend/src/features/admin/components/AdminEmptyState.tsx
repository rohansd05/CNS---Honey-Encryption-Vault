import { ShieldCheck, X, Flame } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

interface AdminEmptyStateProps {
  hasFilters: boolean;
  onResetFilters: () => void;
  onSimulate?: () => void;
}

export function AdminEmptyState({
  hasFilters,
  onResetFilters,
  onSimulate,
}: AdminEmptyStateProps) {
  return (
    <Card className="border-border border-dashed bg-bg-surface/60 max-w-xl mx-auto my-10 text-center p-8 sm:p-10 shadow-card">
      <CardContent className="space-y-5">
        <div className="h-16 w-16 mx-auto rounded-2xl bg-success/10 border border-success/20 flex items-center justify-center text-success shadow-[0_0_20px_rgba(34,197,94,0.15)]">
          <ShieldCheck size={32} />
        </div>

        <div className="space-y-1.5">
          <h3 className="text-lg sm:text-xl font-bold text-text-primary">
            {hasFilters ? 'No Alerts Match Your Filters' : 'No Breach Alerts Detected'}
          </h3>
          <p className="text-xs sm:text-sm text-text-secondary max-w-md mx-auto leading-relaxed">
            {hasFilters
              ? 'Try adjusting your search query or severity filter to see more telemetry events.'
              : 'Tripwires are armed and silent. No unauthorized decoy sweetword logins have been registered by Honeychecker.'}
          </p>
        </div>

        <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
          {hasFilters ? (
            <Button
              onClick={onResetFilters}
              variant="outline"
              size="sm"
              className="border-border hover:bg-bg-elevated text-xs font-semibold text-text-primary gap-1.5"
            >
              <X size={14} />
              <span>Clear Active Filters</span>
            </Button>
          ) : (
            onSimulate && (
              <Button
                onClick={onSimulate}
                variant="default"
                size="sm"
                className="bg-danger hover:bg-danger/90 text-white text-xs font-semibold gap-1.5"
              >
                <Flame size={14} />
                <span>Trigger Test Breach Alert</span>
              </Button>
            )
          )}
        </div>
      </CardContent>
    </Card>
  );
}
