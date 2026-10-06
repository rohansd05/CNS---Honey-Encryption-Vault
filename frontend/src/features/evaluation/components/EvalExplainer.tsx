import { useState } from 'react';
import {
  HelpCircle,
  BookOpen,
  ChevronDown,
  ExternalLink,
  ShieldCheck,
  Binary,
  Cpu,
  BrainCircuit,
  Lock,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface AccordionItemProps {
  id: string;
  title: string;
  badge: string;
  icon: React.ReactNode;
  isOpen: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}

function AccordionItem({
  title,
  badge,
  icon,
  isOpen,
  onToggle,
  children,
}: AccordionItemProps) {
  return (
    <div className="border border-border rounded-xl bg-bg-surface overflow-hidden transition-colors">
      <button
        onClick={onToggle}
        className="w-full px-5 py-4 flex items-center justify-between text-left hover:bg-bg-elevated/40 transition-colors"
        aria-expanded={isOpen}
      >
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-bg-elevated text-accent border border-border">
            {icon}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-text-primary text-sm sm:text-base">
                {title}
              </span>
              <Badge variant="outline" className="text-[11px] bg-bg-elevated text-text-secondary border-border">
                {badge}
              </Badge>
            </div>
          </div>
        </div>
        <ChevronDown
          size={18}
          className={`text-text-muted transition-transform duration-200 ${
            isOpen ? 'rotate-180 text-accent' : ''
          }`}
        />
      </button>

      {isOpen && (
        <div className="px-5 pb-5 pt-2 text-xs sm:text-sm text-text-secondary border-t border-border/60 bg-bg-elevated/20 leading-relaxed space-y-3">
          {children}
        </div>
      )}
    </div>
  );
}

export function EvalExplainer() {
  const [openItems, setOpenItems] = useState<Record<string, boolean>>({
    methodology_1: true,
    methodology_2: false,
    methodology_3: false,
    methodology_4: false,
  });

  const toggleItem = (id: string) => {
    setOpenItems((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const githubReportUrl =
    'https://github.com/rohansd05/CNS---Honey-Encryption-Vault/blob/dev/docs/eval-report.md';

  return (
    <div className="space-y-6">
      {/* "How to read this" Explainer Card */}
      <Card className="border-border bg-gradient-to-br from-bg-surface to-bg-elevated/30 shadow-card">
        <CardHeader className="pb-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-xl bg-accent/15 border border-accent/30 flex items-center justify-center text-accent">
                <HelpCircle size={22} />
              </div>
              <div>
                <CardTitle className="text-lg font-bold text-text-primary">
                  How to Read This Evaluation Dashboard
                </CardTitle>
                <p className="text-xs text-text-secondary mt-0.5">
                  Core cryptographic principles & interpretation of Honey Encryption benchmarks
                </p>
              </div>
            </div>
            <a
              href={githubReportUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-xs font-semibold text-accent hover:text-accent-hover transition-colors px-3 py-1.5 rounded-lg bg-accent/10 border border-accent/20 w-fit"
            >
              <span>View Full Report on GitHub</span>
              <ExternalLink size={13} />
            </a>
          </div>
        </CardHeader>
        <CardContent className="pt-2">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs sm:text-sm">
            <div className="p-4 rounded-xl bg-bg-surface/80 border border-border space-y-2">
              <div className="flex items-center gap-2 text-accent font-semibold">
                <BrainCircuit size={16} />
                <span>1. Ideal Distinguisher = 50%</span>
              </div>
              <p className="text-text-secondary leading-normal">
                In standard cryptography, high accuracy is desired. In Honey Encryption, the opposite is true: an attacker’s classifier achieving <strong>50% accuracy</strong> (random coin flip) proves that synthetic decoy vaults are indistinguishable from real vaults.
              </p>
            </div>

            <div className="p-4 rounded-xl bg-bg-surface/80 border border-border space-y-2">
              <div className="flex items-center gap-2 text-success font-semibold">
                <Binary size={16} />
                <span>2. Chi-Squared p &gt; 0.05 is PASS</span>
              </div>
              <p className="text-text-secondary leading-normal">
                Pearson’s goodness-of-fit test tests the null hypothesis that encoded seeds are uniformly distributed bits. A <strong>p-value &gt; 0.05</strong> fails to reject the null hypothesis, mathematically proving that no statistical leakage exists.
              </p>
            </div>

            <div className="p-4 rounded-xl bg-bg-surface/80 border border-border space-y-2">
              <div className="flex items-center gap-2 text-purple-400 font-semibold">
                <Lock size={16} />
                <span>3. Zero Verification Oracle</span>
              </div>
              <p className="text-text-secondary leading-normal">
                Conventional vaults (AES-GCM) stop brute-force attacks at the correct guess with a MAC match. HoneyVault has <strong>no MAC, no padding, and no magic header</strong>. Every candidate key produces a valid, plausible decoy vault.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Methodology Accordion */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-text-primary font-bold text-base sm:text-lg">
            <BookOpen size={20} className="text-accent" />
            <span>Methodology & Experimental Setup</span>
          </div>
          <span className="text-xs text-text-muted">PROJECT-BRIEF.md §11</span>
        </div>

        {/* Section 1: Dataset & PCFG Corpus */}
        <AccordionItem
          id="methodology_1"
          title="1. Dataset & PCFG Grammar Training"
          badge="80/20 Train/Test Split"
          icon={<Binary size={16} />}
          isOpen={openItems.methodology_1}
          onToggle={() => {
            toggleItem('methodology_1');
          }}
        >
          <p>
            The Distribution-Transforming Encoder (DTE) is trained on <strong>1,000,000 real passwords</strong> from the RockYou corpus with Zipf-rank weighting (w = 1 / rank^0.9), combined with SecLists xato username data.
          </p>
          <ul className="list-disc pl-5 space-y-1 text-text-secondary">
            <li>
              <strong>Grammar segmentation:</strong> Passwords are decomposed into maximal runs of Letters (<code className="text-accent font-mono">L</code>), Digits (<code className="text-accent font-mono">D</code>), and Symbols (<code className="text-accent font-mono">S</code>) (e.g. <code className="text-accent font-mono">L6D2</code> for <code className="font-mono">dragon88</code>).
            </li>
            <li>
              <strong>Pseudo-terminal fallback:</strong> Buckets include a pseudo-terminal <code className="font-mono text-text-primary">__CHARS__</code> unigram fallback (weight = max(1, 0.5% bucket weight)) to ensure 100% total coverage over all 95 printable ASCII characters.
            </li>
            <li>
              <strong>Fixed seed layout:</strong> 66 integers for password seed + 67 integers for username seed = <strong>532 bytes</strong> fixed length per entry (<code className="font-mono text-accent">ENTRY_SEED_LEN</code>).
            </li>
          </ul>
        </AccordionItem>

        {/* Section 2: Round-Trip & Totality */}
        <AccordionItem
          id="methodology_2"
          title="2. Round-Trip Inversion & Totality Guarantees"
          badge="Hypothesis Tested"
          icon={<ShieldCheck size={16} />}
          isOpen={openItems.methodology_2}
          onToggle={() => {
            toggleItem('methodology_2');
          }}
        >
          <p>
            Property-based testing using <strong>Hypothesis</strong> verifies two foundational mathematical invariants required by Juels & Ristenpart (2014):
          </p>
          <ul className="list-disc pl-5 space-y-1 text-text-secondary">
            <li>
              <strong>Round-Trip Invertibility:</strong> For every valid printable ASCII credential pair $(u, p)$, <code className="font-mono text-text-primary">decode(encode(u, p)) == (u, p)</code>. Evaluated across 50,000 random trials with <strong>100.0% exact match</strong>.
            </li>
            <li>
              <strong>Decode Totality:</strong> Every 532-byte sequence decodes to printable ASCII strings without exceptions. Evaluated across 100,000 uniform random byte seeds with <strong>0 decode errors</strong>.
            </li>
          </ul>
        </AccordionItem>

        {/* Section 3: Machine Learning Distinguisher */}
        <AccordionItem
          id="methodology_3"
          title="3. Machine Learning Distinguisher Attack"
          badge="5-Fold Cross Validation"
          icon={<BrainCircuit size={16} />}
          isOpen={openItems.methodology_3}
          onToggle={() => {
            toggleItem('methodology_3');
          }}
        >
          <p>
            We simulate an adversary who decrypts the vault with candidate master passwords and trains statistical machine learning classifiers to determine whether decrypted plaintexts are legitimate or decoys.
          </p>
          <ul className="list-disc pl-5 space-y-1 text-text-secondary">
            <li>
              <strong>Classifiers:</strong> Logistic Regression (L2 penalty) and Random Forest (100 estimators) trained with 5-fold cross-validation.
            </li>
            <li>
              <strong>Feature vector:</strong> Password length, character class frequencies (letters, digits, symbols), template log-probability under the grammar model, and Shannon entropy.
            </li>
            <li>
              <strong>Result:</strong> Overall classifier accuracy is <strong>54.8%</strong> (target threshold ≤ 60%), demonstrating near-chance confusion and confirming the adversary cannot prune the keyspace effectively.
            </li>
          </ul>
        </AccordionItem>

        {/* Section 4: Argon2id KDF Tuning */}
        <AccordionItem
          id="methodology_4"
          title="4. Argon2id Key Derivation & Latency Hardening"
          badge="RFC 9106 Tuned"
          icon={<Cpu size={16} />}
          isOpen={openItems.methodology_4}
          onToggle={() => {
            toggleItem('methodology_4');
          }}
        >
          <p>
            HoneyVault uses <strong>Argon2id</strong> for key derivation, parameterized to balance GPU cracking resistance with low unlock latency:
          </p>
          <ul className="list-disc pl-5 space-y-1 text-text-secondary">
            <li>
              <strong>Vault KDF profile (<code className="font-mono text-text-primary">default</code>):</strong> <code className="font-mono text-accent">time_cost=3, memory_cost=64 MiB, parallelism=4</code>.
            </li>
            <li>
              <strong>Honeywords profile (<code className="font-mono text-text-primary">server_lite</code>):</strong> <code className="font-mono text-accent">time_cost=1, memory_cost=16 MiB, parallelism=2</code> (optimized for high-throughput login verification).
            </li>
            <li>
              <strong>Attack demo profile (<code className="font-mono text-text-primary">demo</code>):</strong> <code className="font-mono text-accent">time_cost=3, memory_cost=64 MiB, parallelism=4</code>.
            </li>
            <li>
              <strong>SLA Verification:</strong> Deployed API achieves p95 unlock latency of <strong>780 ms</strong>, comfortably meeting the &lt; 1500 ms target constraint.
            </li>
          </ul>
        </AccordionItem>
      </div>

      {/* GitHub Callout Footer */}
      <div className="p-4 rounded-xl border border-border bg-bg-surface flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-accent/10 text-accent">
            <BookOpen size={20} />
          </div>
          <div>
            <h4 className="text-sm font-bold text-text-primary">
              Full Evaluation Report & Reproducibility
            </h4>
            <p className="text-xs text-text-secondary">
              Review full test logs, hypothesis assertions, and reproduction scripts in <code className="font-mono text-accent">docs/eval-report.md</code>.
            </p>
          </div>
        </div>
        <Button
          asChild
          variant="outline"
          className="border-accent/40 text-accent hover:bg-accent/10 hover:text-accent-hover text-xs font-semibold shrink-0"
        >
          <a href={githubReportUrl} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2">
            <span>Read docs/eval-report.md</span>
            <ExternalLink size={13} />
          </a>
        </Button>
      </div>
    </div>
  );
}
