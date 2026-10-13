// owner: Chetan (T3) — Admin utilities & formatters (feat/t3-evaluation-admin)

export function formatRelativeTime(dateString: string): string {
  try {
    const date = new Date(dateString);
    const now = new Date();
    const diffSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diffSeconds < 5) return 'Just now';
    if (diffSeconds < 60) return `${String(diffSeconds)}s ago`;

    const diffMinutes = Math.floor(diffSeconds / 60);
    if (diffMinutes < 60) return `${String(diffMinutes)}m ago`;

    const diffHours = Math.floor(diffMinutes / 60);
    if (diffHours < 24) return `${String(diffHours)}h ago`;

    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `${String(diffDays)}d ago`;

    return date.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return dateString;
  }
}

export function formatAbsoluteUtc(dateString: string): string {
  try {
    const date = new Date(dateString);
    return date.toUTCString();
  } catch {
    return dateString;
  }
}

export function getSeverityStyle(severity: string) {
  switch (severity.toLowerCase()) {
    case 'critical':
      return {
        badgeClass: 'bg-danger/15 text-danger border-danger/40 shadow-[0_0_12px_rgba(239,68,68,0.2)]',
        indicatorClass: 'bg-danger',
        label: 'CRITICAL',
      };
    case 'high':
      return {
        badgeClass: 'bg-amber-500/15 text-amber-400 border-amber-500/40',
        indicatorClass: 'bg-amber-500',
        label: 'HIGH',
      };
    case 'medium':
      return {
        badgeClass: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/40',
        indicatorClass: 'bg-yellow-500',
        label: 'MEDIUM',
      };
    case 'low':
    default:
      return {
        badgeClass: 'bg-info/15 text-info border-info/40',
        indicatorClass: 'bg-info',
        label: 'LOW',
      };
  }
}
