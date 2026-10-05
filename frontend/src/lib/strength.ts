// owner: Krrish (T3) — client-side password strength estimator
// Falls back to this when the backend /api/utils/strength endpoint is unavailable

const COMMON_PASSWORDS = new Set([
  '123456', 'password', '12345678', 'qwerty', '123456789', '12345',
  '1234', '111111', '1234567', 'dragon', '123123', 'baseball', 'abc123',
  'football', 'monkey', 'letmein', 'shadow', 'master', '666666', 'qwertyuiop',
  '123321', 'mustang', '1234567890', 'michael', '654321', 'superman',
  'qazwsx', 'trustno1', 'jordan', 'iloveyou', 'password1', 'sunshine',
  'princess', 'welcome', 'charlie', 'passw0rd', 'starwars',
]);

const SEQUENCES = [
  'abcdefghijklmnopqrstuvwxyz',
  'zyxwvutsrqponmlkjihgfedcba',
  '01234567890',
  '9876543210',
  'qwertyuiop',
  'asdfghjkl',
  'zxcvbnm',
];

const YEAR_PATTERN = /(?:19[5-9]\d|20[0-3]\d)/;
const REPEAT_PATTERN = /(.)\1{2,}/;

export interface StrengthResult {
  score: 0 | 1 | 2 | 3 | 4;
  entropy_bits: number;
  feedback: string[];
}

export function estimateStrength(password: string): StrengthResult {
  const feedback: string[] = [];

  if (password.length === 0) {
    return { score: 0, entropy_bits: 0, feedback: ['Enter a password.'] };
  }

  // Pool size based on character classes
  let pool = 0;
  if (/[a-z]/.test(password)) pool += 26;
  if (/[A-Z]/.test(password)) pool += 26;
  if (/[0-9]/.test(password)) pool += 10;
  if (/[^a-zA-Z0-9]/.test(password)) pool += 33;

  let entropy = password.length * Math.log2(pool || 1);

  // Penalties
  if (COMMON_PASSWORDS.has(password.toLowerCase())) {
    feedback.push('This is a commonly used password.');
    return { score: 0, entropy_bits: Math.round(entropy * 10) / 10, feedback };
  }

  if (password.length < 8) {
    feedback.push('Use at least 8 characters.');
    entropy *= 0.6;
  }

  // Sequence check
  const lower = password.toLowerCase();
  for (const seq of SEQUENCES) {
    for (let i = 0; i <= lower.length - 3; i++) {
      const sub = lower.slice(i, i + 3);
      if (seq.includes(sub)) {
        feedback.push('Avoid keyboard or alphabet sequences.');
        entropy *= 0.75;
        break;
      }
    }
    if (feedback.length > 0 && feedback[feedback.length - 1]?.includes('sequences')) break;
  }

  // Repeated chars
  if (REPEAT_PATTERN.test(password)) {
    feedback.push('Avoid repeated characters.');
    entropy *= 0.8;
  }

  // Year pattern
  if (YEAR_PATTERN.test(password)) {
    feedback.push('Avoid including years.');
    entropy *= 0.85;
  }

  // Score thresholds
  let score: 0 | 1 | 2 | 3 | 4;
  if (entropy < 28) {
    score = 0;
    feedback.push('Very weak — try a longer password with mixed characters.');
  } else if (entropy < 36) {
    score = 1;
    feedback.push('Weak — add more character variety or length.');
  } else if (entropy < 60) {
    score = 2;
    if (feedback.length === 0) feedback.push('Fair — consider adding symbols or more length.');
  } else if (entropy < 80) {
    score = 3;
    if (feedback.length === 0) feedback.push('Good password strength.');
  } else {
    score = 4;
    if (feedback.length === 0) feedback.push('Excellent password strength.');
  }

  return {
    score,
    entropy_bits: Math.round(entropy * 10) / 10,
    feedback,
  };
}
