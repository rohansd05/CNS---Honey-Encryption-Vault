// owner: Krrish (T3) — TypeScript types for every API shape in docs/api-contract.md

// ── Error ──────────────────────────────────────────────────────────
export interface ApiErrorDetail {
  loc: string[];
  msg: string;
  type: string;
}
export type ApiErrorBody = { detail: string } | { detail: ApiErrorDetail[] };

// ── Health ─────────────────────────────────────────────────────────
export interface HealthResponse {
  status: 'ok';
  version: string;
  honeycore_impl: 'stub' | 'real';
  honeychecker: 'ok' | 'down' | 'unknown';
}

// ── Auth ───────────────────────────────────────────────────────────
export interface RegisterRequest {
  username: string;
  login_password: string;
  master_password: string;
}
export interface RegisterResponse {
  id: string;
  username: string;
}

export interface LoginRequest {
  username: string;
  login_password: string;
}
export interface LoginResponse {
  access_token: string;
  token_type: 'bearer';
  user: UserPublic;
}

export interface UserPublic {
  id: string;
  username: string;
  is_admin: boolean;
}

export interface MeResponse {
  id: string;
  username: string;
  is_admin: boolean;
  created_at: string;
  entry_count: number;
}

// ── Vault ──────────────────────────────────────────────────────────
export interface Sigil {
  emojis: [string, string, string];
  color: string; // #RRGGBB
}

export interface VaultEntry {
  id: string;
  service: string;
  username: string;
  password: string;
  created_at: string;
  updated_at: string;
}

export interface UnlockRequest {
  master_password: string;
}
export interface UnlockResponse {
  entries: VaultEntry[];
  sigil: Sigil;
}

export interface AddEntryRequest {
  master_password: string;
  service: string;
  username: string;
  password: string;
}
export interface AddEntryResponse {
  id: string;
}

export interface UpdateEntryRequest {
  master_password: string;
  service: string;
  username: string;
  password: string;
}
export interface UpdateEntryResponse {
  id: string;
}

// DELETE /vault/entries/{id} → 204 no body

export interface ExportVaultKdf {
  alg: string;
  profile: string;
  salt: string;
  time_cost: number;
  memory_cost_kib: number;
  parallelism: number;
  hash_len: number;
}
export interface ExportVaultDte {
  password_model: string;
  username_model: string;
  entry_seed_len: number;
}
export interface ExportVaultEntry {
  id: string;
  service: string;
  nonce: string;
  ciphertext: string;
  created_at: string;
  updated_at: string;
}
export interface ExportVaultBlob {
  format: 'honeyvault';
  version: 1;
  scheme: string;
  kdf: ExportVaultKdf;
  dte: ExportVaultDte;
  entries: ExportVaultEntry[];
}

// ── Users ──────────────────────────────────────────────────────────
export interface UserIdentityResponse {
  username: string;
  public_key_pem: string;
  certificate_pem: string;
}

// ── Shares ─────────────────────────────────────────────────────────
export interface CreateShareRequest {
  master_password: string;
  entry_id: string;
  recipient_username: string;
}
export interface CreateShareResponse {
  share_id: string;
}

export interface ShareInboxItem {
  share_id: string;
  sender: string;
  service: string;
  created_at: string;
  opened_at: string | null;
}

export interface ShareSentItem {
  share_id: string;
  recipient: string;
  service: string;
  created_at: string;
  opened_at: string | null;
}

export interface OpenShareResponse {
  service: string;
  username: string | null;
  password: string | null;
  sender: string;
  signature_valid: boolean;
  certificate_valid: boolean;
  certificate_subject: string;
  certificate_issuer: string;
}

// ── Admin ──────────────────────────────────────────────────────────
export interface AdminAlert {
  id: string;
  username: string;
  kind: 'HONEYWORD_LOGIN';
  severity: 'critical' | 'high' | 'medium' | 'low';
  sweetword_index: number;
  source_ip: string;
  user_agent: string;
  created_at: string;
}

// ── Evaluation ─────────────────────────────────────────────────────
// Schema defined by T1 in Phase 2; use unknown for now
export type EvalSummaryResponse = Record<string, unknown>;

// ── Attack Demo ────────────────────────────────────────────────────
export interface AttackStolenVaultResponse {
  honey_blob: ExportVaultBlob;
  baseline_blob: Record<string, unknown>;
  owner: string;
}

export interface DictionaryAttackRequest {
  max_guesses: number;
  custom_guesses?: string[];
}

export interface CrackedEntry {
  id: string;
  service: string;
  username: string;
  password: string;
  created_at: string;
  updated_at: string;
}

export interface DictionaryAttackBaseline {
  cracked: boolean;
  guess_index: number | null;
  elapsed_ms: number;
  recovered_entries: CrackedEntry[];
}

export interface DictionaryAttackHoneySample {
  guess_index: number;
  guess: string;
  entries: CrackedEntry[];
}

export interface DictionaryAttackHoney {
  guesses_tried: number;
  elapsed_ms: number;
  distinct_vaults: number;
  samples: DictionaryAttackHoneySample[];
}

export interface DictionaryAttackResponse {
  baseline: DictionaryAttackBaseline;
  honey: DictionaryAttackHoney;
  reveal: { real_guess_index: number | null };
}

export interface StolenHoneywordsResponse {
  username: string;
  k: number;
  salt: string;
  hashes: string[];
  cracked_sweetwords: string[];
}

export type AttackAlarmsResponse = AdminAlert[];

// ── Utils ──────────────────────────────────────────────────────────
export interface StrengthRequest {
  password: string;
}
export interface StrengthResponse {
  score: 0 | 1 | 2 | 3 | 4;
  entropy_bits: number;
  feedback: string[];
}
