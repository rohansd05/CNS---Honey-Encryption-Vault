import { Skeleton } from '@/components/ui/skeleton';
import { Card } from '@/components/ui/card';

export function EvalSkeletons() {
  return (
    <div className="space-y-8 animate-in fade-in-50 duration-300">
      {/* Header Skeleton */}
      <div className="space-y-3">
        <Skeleton className="h-8 w-64 rounded-lg" />
        <Skeleton className="h-4 w-96 rounded-md" />
      </div>

      {/* KPI Tiles Skeleton */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i} className="border-border bg-bg-surface p-5 space-y-3">
            <div className="flex justify-between items-center">
              <Skeleton className="h-3 w-28 rounded" />
              <Skeleton className="h-7 w-7 rounded-lg" />
            </div>
            <div className="space-y-2">
              <Skeleton className="h-8 w-24 rounded" />
              <Skeleton className="h-3 w-40 rounded" />
            </div>
            <div className="pt-2 border-t border-border/50 flex justify-between">
              <Skeleton className="h-3 w-20 rounded" />
              <Skeleton className="h-3 w-24 rounded" />
            </div>
          </Card>
        ))}
      </div>

      {/* Charts Skeleton */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i} className="border-border bg-bg-surface p-5 space-y-4">
            <div className="space-y-1">
              <Skeleton className="h-5 w-48 rounded" />
              <Skeleton className="h-3 w-64 rounded" />
            </div>
            <Skeleton className="h-[280px] w-full rounded-xl" />
          </Card>
        ))}
      </div>
    </div>
  );
}
