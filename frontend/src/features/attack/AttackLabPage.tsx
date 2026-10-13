// owner: Chetan (T3) — Attack Lab Interactive Simulation Page
import { useState } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import {
  FlaskConical,
  Database,
  Zap,
  KeyRound,
  CheckCircle2,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Step1StealVault } from './Step1StealVault';
import { Step2DictionaryAttack } from './Step2DictionaryAttack';
import { Step3HoneywordsLogin } from './Step3HoneywordsLogin';

type AttackStep = 1 | 2 | 3;

interface StepMeta {
  number: AttackStep;
  title: string;
  subtitle: string;
  icon: React.ReactNode;
}

const STEPS: StepMeta[] = [
  {
    number: 1,
    title: 'Steal the Vault',
    subtitle: 'Database exfiltration & ciphertext inspection',
    icon: <Database size={16} />,
  },
  {
    number: 2,
    title: 'Dictionary Attack',
    subtitle: 'Conventional (AES-GCM) vs Honey Vault (HE-PCFG)',
    icon: <Zap size={16} />,
  },
  {
    number: 3,
    title: 'Honeywords & Breach Alarm',
    subtitle: 'Tripwire authentication & Honeychecker alarm',
    icon: <KeyRound size={16} />,
  },
];

export function AttackLabPage() {
  const shouldReduceMotion = useReducedMotion();
  const [currentStep, setCurrentStep] = useState<AttackStep>(1);
  const [completedSteps, setCompletedSteps] = useState<AttackStep[]>([]);

  const markCompleted = (step: AttackStep) => {
    if (!completedSteps.includes(step)) {
      setCompletedSteps((prev) => [...prev, step]);
    }
  };

  const handleGoToStep = (step: AttackStep) => {
    setCurrentStep(step);
  };

  const handleStep1Next = () => {
    markCompleted(1);
    setCurrentStep(2);
  };

  const handleStep2Next = () => {
    markCompleted(2);
    setCurrentStep(3);
  };

  const handleStep2Prev = () => {
    setCurrentStep(1);
  };

  const handleStep3Prev = () => {
    setCurrentStep(2);
  };

  const handleResetFlow = () => {
    setCompletedSteps([]);
    setCurrentStep(1);
  };

  return (
    <div className="min-h-screen py-8 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto space-y-8">
      {/* Cinematic Hero Header */}
      <motion.div
        initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="space-y-4"
      >
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <div className="h-12 w-12 rounded-xl bg-accent/15 border border-accent/30 flex items-center justify-center text-accent shadow-glow">
              <FlaskConical size={26} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl sm:text-3xl font-extrabold text-text-primary tracking-tight">
                  Attack Lab
                </h1>
                <Badge className="bg-accent/20 text-accent border border-accent/40 font-mono text-xs font-semibold">
                  Interactive Simulator
                </Badge>
              </div>
              <p className="text-xs sm:text-sm text-text-secondary mt-0.5">
                Demonstrating the impotence of offline dictionary attacks against Honey Encryption
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 self-start md:self-auto">
            <div className="rounded-lg bg-bg-surface border border-border px-3 py-1.5 flex items-center gap-2 text-xs font-mono">
              <span className="h-2 w-2 rounded-full bg-success animate-pulse" />
              <span className="text-text-secondary">Demo Target:</span>
              <span className="font-bold text-text-primary">@demo</span>
            </div>
          </div>
        </div>

        <p className="text-sm text-text-secondary max-w-3xl leading-relaxed">
          Step into an attacker’s shoes. Walk through database exfiltration, offline dictionary cracking,
          and online sweetword authentication to experience firsthand how HoneyVault deprives attackers
          of verification oracles and sounds silent alarms upon breach attempts.
        </p>
      </motion.div>

      {/* 3-Step Stepper Navigation */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {STEPS.map((step) => {
          const isActive = currentStep === step.number;
          const isDone = completedSteps.includes(step.number);

          return (
            <button
              key={step.number}
              type="button"
              onClick={() => {
                handleGoToStep(step.number);
              }}
              className={`text-left rounded-xl p-4 transition-all duration-200 border relative overflow-hidden flex items-start gap-3 ${
                isActive
                  ? 'border-accent bg-accent/10 shadow-[0_0_20px_rgba(245,165,36,0.15)] ring-1 ring-accent'
                  : isDone
                    ? 'border-border bg-bg-surface hover:border-accent/40 hover:bg-bg-elevated'
                    : 'border-border bg-bg-surface/60 opacity-80 hover:opacity-100 hover:bg-bg-surface'
              }`}
            >
              <div
                className={`mt-0.5 h-8 w-8 rounded-lg flex items-center justify-center font-bold text-xs shrink-0 transition-colors ${
                  isActive
                    ? 'bg-accent text-black shadow-sm'
                    : isDone
                      ? 'bg-success/20 text-success border border-success/30'
                      : 'bg-bg-elevated text-text-muted border border-border'
                }`}
              >
                {isDone ? <CheckCircle2 size={16} /> : step.number}
              </div>

              <div className="space-y-0.5 min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className={`text-xs font-mono font-semibold ${isActive ? 'text-accent' : 'text-text-muted'}`}>
                    STEP 0{step.number}
                  </span>
                  {isDone && (
                    <Badge variant="outline" className="text-[9px] py-0 px-1 border-success/40 text-success">
                      Done
                    </Badge>
                  )}
                </div>
                <h3 className={`text-sm font-bold truncate ${isActive ? 'text-text-primary' : 'text-text-secondary'}`}>
                  {step.title}
                </h3>
                <p className="text-[11px] text-text-muted line-clamp-1">
                  {step.subtitle}
                </p>
              </div>

              {isActive && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-accent" />
              )}
            </button>
          );
        })}
      </div>

      {/* Step Content Container */}
      <div className="relative">
        {currentStep === 1 && (
          <Step1StealVault onNext={handleStep1Next} />
        )}

        {currentStep === 2 && (
          <Step2DictionaryAttack onNext={handleStep2Next} onPrev={handleStep2Prev} />
        )}

        {currentStep === 3 && (
          <Step3HoneywordsLogin onPrev={handleStep3Prev} onResetFlow={handleResetFlow} />
        )}
      </div>
    </div>
  );
}
