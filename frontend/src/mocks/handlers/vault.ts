// owner: Krrish (T3) — mock handlers for Vault API (honey encryption simulation)
import { http, HttpResponse } from 'msw';
import type {
  AddEntryRequest,
  ExportVaultBlob,
  Sigil,
  UnlockRequest,
  UnlockResponse,
  UpdateEntryRequest,
  VaultEntry,
} from '@/api/types';

// The canonical real vault entries when master password == "correct horse"
const REAL_ENTRIES: VaultEntry[] = [
  {
    id: 'ent-1',
    service: 'github.com',
    username: 'krrish.dev@gmail.com',
    password: 'ghp_k92Jsh8921NksA91j2s',
    created_at: '2026-09-01T10:00:00Z',
    updated_at: '2026-09-01T10:00:00Z',
  },
  {
    id: 'ent-2',
    service: 'google.com',
    username: 'krrishg@gmail.com',
    password: 'P@ssw0rd!Secure2026#',
    created_at: '2026-09-02T11:15:00Z',
    updated_at: '2026-09-02T11:15:00Z',
  },
  {
    id: 'ent-3',
    service: 'aws.amazon.com',
    username: 'krrish-admin',
    password: 'AKIAIOSFODNN7EXAMPLE',
    created_at: '2026-09-05T14:30:00Z',
    updated_at: '2026-09-05T14:30:00Z',
  },
  {
    id: 'ent-4',
    service: 'netflix.com',
    username: 'krrish.family',
    password: 'StrangerThings2026!',
    created_at: '2026-09-10T19:00:00Z',
    updated_at: '2026-09-10T19:00:00Z',
  },
  {
    id: 'ent-5',
    service: 'proton.me',
    username: 'krrish_secure',
    password: 'Quant-Vault-9912-Key',
    created_at: '2026-09-15T08:45:00Z',
    updated_at: '2026-09-15T08:45:00Z',
  },
  {
    id: 'ent-6',
    service: 'slack.com',
    username: 'krrish@spit.ac.in',
    password: 'Workspace#SPIT#2026',
    created_at: '2026-09-18T12:00:00Z',
    updated_at: '2026-09-18T12:00:00Z',
  },
  {
    id: 'ent-7',
    service: 'spotify.com',
    username: 'krrish.beats',
    password: 'LofiVibesEveryday#1',
    created_at: '2026-09-20T16:20:00Z',
    updated_at: '2026-09-20T16:20:00Z',
  },
  {
    id: 'ent-8',
    service: 'bankofamerica.com',
    username: 'kgadekar_fin',
    password: 'BlueOak$9182*PaloAlto',
    created_at: '2026-09-25T09:10:00Z',
    updated_at: '2026-09-25T09:10:00Z',
  },
];

const REAL_SIGIL: Sigil = {
  emojis: ['🍯', '🐝', '🛡️'],
  color: '#f5a524',
};

// Deterministic decoy generation pools
const DECOY_SIGIL_EMOJIS = [
  '🦁', '🦊', '🦉', '⚡', '🌙', '🌊', '🔥', '💎',
  '🌲', '🍄', '🪐', '⚓', '🎲', '🧩', '🚀', '🔮',
  '🦅', '🐺', '🐉', '🍀', '🍎', '🍇', '🍒', '🎯',
];

const DECOY_SIGIL_COLORS = [
  '#3b82f6', '#10b981', '#8b5cf6', '#ec4899', '#06b6d4',
  '#f97316', '#6366f1', '#14b8a6', '#e11d48', '#84cc16',
];

const DECOY_USERNAMES = [
  'shadow_runner88', 'cipher_knight', 'neon_voyager', 'alex_morgan_99',
  'skywalker_2024', 'pixel_master', 'silver_hawk', 'storm_weaver',
  'quiet_coder', 'echo_wanderer', 'cosmic_drift', 'lunar_spark',
];

const DECOY_PASSWORDS = [
  'SummerBreeze2025!', 'DragonSlayer#99', 'BlueHorizon$82', 'GoldenSun*44',
  'WinterStorm!19', 'SilverLight#77', 'CyberShield$21', 'QuietRiver*88',
  'CrimsonDawn#12', 'VelvetNight!63', 'StarlightWay$55', 'ShadowHawk*31',
];

function simpleHash(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash + char) | 0;
  }
  return Math.abs(hash);
}

function generateDecoyVault(password: string): UnlockResponse {
  const seed = simpleHash(password);

  const entries: VaultEntry[] = REAL_ENTRIES.map((entry, idx) => {
    const userIdx = (seed + idx * 7) % DECOY_USERNAMES.length;
    const passIdx = (seed + idx * 13) % DECOY_PASSWORDS.length;
    return {
      ...entry,
      username: DECOY_USERNAMES[userIdx] ?? `user_${String(idx)}`,
      password: DECOY_PASSWORDS[passIdx] ?? `pass_${String(idx)}`,
    };
  });

  const e1 = DECOY_SIGIL_EMOJIS[seed % DECOY_SIGIL_EMOJIS.length] ?? '🎲';
  const e2 = DECOY_SIGIL_EMOJIS[(seed >> 3) % DECOY_SIGIL_EMOJIS.length] ?? '🧩';
  const e3 = DECOY_SIGIL_EMOJIS[(seed >> 6) % DECOY_SIGIL_EMOJIS.length] ?? '🚀';
  const color = DECOY_SIGIL_COLORS[(seed >> 2) % DECOY_SIGIL_COLORS.length] ?? '#3b82f6';

  return {
    entries,
    sigil: { emojis: [e1, e2, e3], color },
  };
}

export const vaultHandlers = [
  // POST /api/vault/unlock — NEVER fails, returns real or deterministic decoy vault
  http.post('/api/vault/unlock', async ({ request }) => {
    const body = (await request.json()) as UnlockRequest;

    if (body.master_password === 'correct horse') {
      return HttpResponse.json<UnlockResponse>({
        entries: REAL_ENTRIES,
        sigil: REAL_SIGIL,
      });
    }

    // Honey encryption: wrong password generates plausible decoy vault
    const decoy = generateDecoyVault(body.master_password);
    return HttpResponse.json<UnlockResponse>(decoy);
  }),

  // POST /api/vault/entries
  http.post('/api/vault/entries', async ({ request }) => {
    const body = (await request.json()) as AddEntryRequest;
    if (!body.service || !body.username || !body.password) {
      return HttpResponse.json({ detail: 'Missing required fields' }, { status: 422 });
    }
    return HttpResponse.json({ id: `ent-${Date.now().toString()}` }, { status: 201 });
  }),

  // PUT /api/vault/entries/:id
  http.put('/api/vault/entries/:id', async ({ params, request }) => {
    const body = (await request.json()) as UpdateEntryRequest;
    if (!body.service || !body.username || !body.password) {
      return HttpResponse.json({ detail: 'Missing required fields' }, { status: 422 });
    }
    return HttpResponse.json({ id: params.id as string });
  }),

  // DELETE /api/vault/entries/:id
  http.delete('/api/vault/entries/:id', () => {
    return new HttpResponse(null, { status: 204 });
  }),

  // GET /api/vault/export
  http.get('/api/vault/export', () => {
    const blob: ExportVaultBlob = {
      format: 'honeyvault',
      version: 1,
      scheme: 'HE-PCFG-v1/AES-256-CTR/argon2id',
      kdf: {
        alg: 'argon2id',
        profile: 'default',
        salt: 'dGVzdC1zYWx0LTE2Ynl0ZXM=',
        time_cost: 3,
        memory_cost_kib: 65536,
        parallelism: 4,
        hash_len: 32,
      },
      dte: {
        password_model: 'pcfg-password-v1',
        username_model: 'pcfg-username-v1',
        entry_seed_len: 532,
      },
      entries: REAL_ENTRIES.map((e) => ({
        id: e.id,
        service: e.service,
        nonce: 'YWVzLWN0ci1ub25jZS0xNg==',
        ciphertext: 'aG9uZXl2YXVsdC1jaXBoZXJ0ZXh0LXNlZWQtNTMyYnl0ZXM=',
        created_at: e.created_at,
        updated_at: e.updated_at,
      })),
    };
    return HttpResponse.json(blob);
  }),
];
