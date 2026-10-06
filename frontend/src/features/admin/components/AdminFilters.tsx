import { useState, useEffect } from 'react';
import {
  Search,
  X,
  RotateCcw,
  Flame,
} from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

interface AdminFiltersProps {
  searchTerm: string;
  onSearchChange: (value: string) => void;
  severityFilter: string;
  onSeverityChange: (severity: string) => void;
  totalAlerts: number;
  filteredAlerts: number;
  isFetching: boolean;
  onRefresh: () => void;
  dataUpdatedAt?: number;
  onSimulate?: () => void;
}

export function AdminFilters({
  searchTerm,
  onSearchChange,
  severityFilter,
  onSeverityChange,
  totalAlerts,
  filteredAlerts,
  isFetching,
  onRefresh,
  dataUpdatedAt,
  onSimulate,
}: AdminFiltersProps) {
  const [secondsAgo, setSecondsAgo] = useState<number>(0);

  useEffect(() => {
    if (!dataUpdatedAt) return;
    const interval = setInterval(() => {
      const diff = Math.floor((Date.now() - dataUpdatedAt) / 1000);
      setSecondsAgo(Math.max(0, diff));
    }, 1000);

    return () => {
      clearInterval(interval);
    };
  }, [dataUpdatedAt]);

  const severityOptions = [
    { value: 'all', label: 'All Severities' },
    { value: 'critical', label: 'Critical' },
    { value: 'high', label: 'High' },
    { value: 'medium', label: 'Medium' },
    { value: 'low', label: 'Low' },
  ];

  return (
    <div className="space-y-3">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 bg-bg-surface p-3.5 rounded-xl border border-border">
        {/* Search by username */}
        <div className="flex flex-1 items-center gap-2">
          <div className="relative flex-1 max-w-sm">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted"
            />
            <Input
              type="text"
              placeholder="Filter by target username..."
              value={searchTerm}
              onChange={(e) => {
                onSearchChange(e.target.value);
              }}
              className="pl-8 pr-8 h-9 text-xs bg-bg-elevated/70 border-border text-text-primary placeholder:text-text-muted"
            />
            {searchTerm && (
              <button
                onClick={() => {
                  onSearchChange('');
                }}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary"
                aria-label="Clear search"
              >
                <X size={13} />
              </button>
            )}
          </div>

          {/* Severity selector pills */}
          <div className="hidden sm:flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
            {severityOptions.map((opt) => {
              const active = severityFilter === opt.value;
              return (
                <button
                  key={opt.value}
                  onClick={() => {
                    onSeverityChange(opt.value);
                  }}
                  className={`text-xs px-2.5 py-1 rounded-lg border font-medium transition-all ${
                    active
                      ? 'bg-accent/15 border-accent/40 text-accent font-semibold shadow-sm'
                      : 'bg-bg-elevated/40 border-border/80 text-text-secondary hover:text-text-primary hover:border-border'
                  }`}
                >
                  {opt.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Right action controls: Live status & refresh */}
        <div className="flex items-center gap-3 justify-between md:justify-end">
          {/* Live 10s auto-refresh indicator */}
          <div className="flex items-center gap-2 px-2.5 py-1 rounded-lg bg-bg-elevated border border-border text-xs text-text-secondary">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-success" />
            </span>
            <span className="font-semibold text-text-primary">LIVE</span>
            <span className="text-[11px] text-text-muted">
              {isFetching ? 'polling...' : `${String(secondsAgo)}s ago`}
            </span>
          </div>

          {/* Refresh Button */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              onRefresh();
            }}
            disabled={isFetching}
            className="h-9 px-3 border-border hover:bg-bg-elevated text-xs text-text-primary gap-1.5"
          >
            <RotateCcw
              size={13}
              className={isFetching ? 'animate-spin text-accent' : ''}
            />
            <span>Refresh</span>
          </Button>

          {onSimulate && (
            <Button
              variant="default"
              size="sm"
              onClick={() => {
                onSimulate();
              }}
              className="h-9 px-3 bg-danger hover:bg-danger/90 text-white text-xs font-semibold gap-1.5 shadow-sm"
            >
              <Flame size={13} />
              <span className="hidden sm:inline">Simulate Alarm</span>
            </Button>
          )}
        </div>
      </div>

      {/* Filter summary status strip */}
      <div className="flex items-center justify-between text-xs text-text-muted px-1">
        <div>
          Showing <strong className="text-text-primary">{String(filteredAlerts)}</strong> of{' '}
          <strong className="text-text-primary">{String(totalAlerts)}</strong> total breach alerts
          {searchTerm && (
            <span>
              {' '}
              matching &quot;<span className="text-accent">{searchTerm}</span>&quot;
            </span>
          )}
          {severityFilter !== 'all' && (
            <span>
              {' '}
              with severity <strong className="text-text-primary">{severityFilter}</strong>
            </span>
          )}
        </div>

        {(searchTerm || severityFilter !== 'all') && (
          <button
            onClick={() => {
              onSearchChange('');
              onSeverityChange('all');
            }}
            className="text-accent hover:underline text-xs flex items-center gap-1"
          >
            <X size={12} />
            <span>Reset filters</span>
          </button>
        )}
      </div>
    </div>
  );
}
