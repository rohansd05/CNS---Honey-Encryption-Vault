import { BarChart3, RotateCcw, Terminal, ExternalLink } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

interface EvalEmptyStateProps {
  onRetry: () => void;
  onLoadMock?: () => void;
}

export function EvalEmptyState({ onRetry, onLoadMock }: EvalEmptyStateProps) {
  return (
    <Card className="border-border border-dashed bg-bg-surface/50 max-w-2xl mx-auto my-12 text-center p-8 sm:p-12 shadow-card">
      <CardContent className="space-y-6">
        <div className="h-16 w-16 mx-auto rounded-2xl bg-accent/10 border border-accent/20 flex items-center justify-center text-accent shadow-glow">
          <BarChart3 size={32} />
        </div>

        <div className="space-y-2">
          <h2 className="text-xl sm:text-2xl font-bold text-text-primary">
            Evaluation Not Run Yet
          </h2>
          <p className="text-sm text-text-secondary max-w-md mx-auto leading-relaxed">
            The API returned <strong className="text-text-primary font-mono">404</strong> (no evaluation summary exists at <code className="font-mono text-accent">eval/results/latest.json</code>).
          </p>
        </div>

        {/* Command Box */}
        <div className="max-w-md mx-auto p-3.5 rounded-xl bg-bg-elevated/80 border border-border text-left font-mono text-xs text-text-secondary flex items-start gap-3">
          <Terminal size={16} className="text-accent shrink-0 mt-0.5" />
          <div className="space-y-1 overflow-x-auto">
            <div className="text-text-muted"># Run evaluation suite in backend</div>
            <div className="text-text-primary">python -m eval.run_all</div>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
          <Button
            onClick={onRetry}
            variant="default"
            className="bg-accent hover:bg-accent-hover text-bg font-semibold gap-2"
          >
            <RotateCcw size={15} />
            <span>Check Again</span>
          </Button>

          {onLoadMock && (
            <Button
              onClick={onLoadMock}
              variant="outline"
              className="border-border hover:bg-bg-elevated text-text-primary gap-2"
            >
              <span>Load Demonstration Data</span>
            </Button>
          )}

          <Button
            asChild
            variant="ghost"
            className="text-text-secondary hover:text-text-primary gap-2"
          >
            <a
              href="https://github.com/rohansd05/CNS---Honey-Encryption-Vault/blob/dev/docs/eval-report.md"
              target="_blank"
              rel="noopener noreferrer"
            >
              <span>Read Documentation</span>
              <ExternalLink size={14} />
            </a>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
