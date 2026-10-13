// owner: Krrish (T3) — password strength meter with backend check + client fallback
import { useEffect, useState } from 'react';
import { estimateStrength, type StrengthResult } from '@/lib/strength';
import { utilsApi } from '@/api/endpoints/utils';

interface PasswordStrengthMeterProps {
  password: string;
  showFeedback?: boolean;
  className?: string;
}

const SCORE_LABELS: Record<number, { label: string; color: string; bg: string }> = {
  0: { label: 'Very Weak', color: 'text-red-400', bg: 'bg-red-500' },
  1: { label: 'Weak', color: 'text-orange-400', bg: 'bg-orange-500' },
  2: { label: 'Fair', color: 'text-amber-400', bg: 'bg-amber-500' },
  3: { label: 'Strong', color: 'text-blue-400', bg: 'bg-blue-500' },
  4: { label: 'Very Strong', color: 'text-emerald-400', bg: 'bg-emerald-500' },
};

export function PasswordStrengthMeter({
  password,
  showFeedback = true,
  className = '',
}: PasswordStrengthMeterProps) {
  const [strength, setStrength] = useState<StrengthResult>(() => estimateStrength(password));

  useEffect(() => {
    if (!password) {
      setStrength({ score: 0, entropy_bits: 0, feedback: [] });
      return;
    }

    // Immediately calculate client-side estimate for zero latency
    const localResult = estimateStrength(password);
    setStrength(localResult);

    // Try backend if available, fallback gracefully
    let isCancelled = false;
    const timer = setTimeout(() => {
      void (async () => {
        try {
          const remote = await utilsApi.estimateStrength({ password });
          if (!isCancelled) {
            setStrength(remote);
          }
        } catch {
          // Silently keep local estimate as per brief
        }
      })();
    }, 250);

    return () => {
      isCancelled = true;
      clearTimeout(timer);
    };
  }, [password]);

  if (!password) return null;

  const currentScore = strength.score;
  const config = SCORE_LABELS[currentScore];

  return (
    <div className={`space-y-1.5 pt-1 text-xs ${className}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-[var(--text-secondary)]">Strength:</span>
          <span className={`font-semibold ${config.color}`}>{config.label}</span>
        </div>
        {strength.entropy_bits > 0 && (
          <span className="font-mono text-[11px] text-[var(--text-muted)]">
            ~{strength.entropy_bits} bits entropy
          </span>
        )}
      </div>

      {/* 4-bar indicator */}
      <div className="grid grid-cols-4 gap-1.5 h-1.5 w-full">
        {[1, 2, 3, 4].map((step) => (
          <div
            key={step}
            className={`h-full rounded-full transition-all duration-300 ${
              currentScore >= step
                ? config.bg
                : 'bg-[var(--border)] opacity-40'
            }`}
          />
        ))}
      </div>

      {/* Feedback hints */}
      {showFeedback && strength.feedback.length > 0 && (
        <ul className="text-[11px] text-[var(--text-muted)] space-y-0.5 pt-0.5 list-disc list-inside">
          {strength.feedback.slice(0, 2).map((item, idx) => (
            <li key={idx}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
