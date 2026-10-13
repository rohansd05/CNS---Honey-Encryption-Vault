// owner: Chetan (T3) — attack lab mock handlers (feat/t3-attack-lab)
import { http, HttpResponse } from 'msw';
import type {
  AdminAlert,
  AttackAlarmsResponse,
  AttackStolenVaultResponse,
  CrackedEntry,
  DictionaryAttackHoneySample,
  DictionaryAttackRequest,
  DictionaryAttackResponse,
  ExportVaultBlob,
  StolenHoneywordsResponse,
} from '@/api/types';

// Real vault entries stored under demo's master key (matching DEMO_ENTRIES in backend/scripts/seed_demo.py)
const REAL_RECOVERED_ENTRIES: CrackedEntry[] = [
  {
    id: 'ent-demo-1',
    service: 'github.com',
    username: 'alex.mercer',
    password: 'GitDev#2024!Safe',
    created_at: '2026-09-15T08:30:00Z',
    updated_at: '2026-09-15T08:30:00Z',
  },
  {
    id: 'ent-demo-2',
    service: 'gmail.com',
    username: 'alex.mercer@gmail.com',
    password: 'P@ssw0rdSecure48',
    created_at: '2026-09-16T09:12:00Z',
    updated_at: '2026-09-16T09:12:00Z',
  },
  {
    id: 'ent-demo-3',
    service: 'netflix.com',
    username: 'alex.mercer@gmail.com',
    password: 'SummerSunset!2024',
    created_at: '2026-09-20T14:45:00Z',
    updated_at: '2026-09-20T14:45:00Z',
  },
  {
    id: 'ent-demo-4',
    service: 'amazon.in',
    username: 'alex.mercer@gmail.com',
    password: 'SummerSunset!2024',
    created_at: '2026-09-22T11:05:00Z',
    updated_at: '2026-09-22T11:05:00Z',
  },
  {
    id: 'ent-demo-5',
    service: 'linkedin.com',
    username: 'alex-mercer-pro',
    password: 'WorkCareer$2025',
    created_at: '2026-09-25T16:20:00Z',
    updated_at: '2026-09-25T16:20:00Z',
  },
  {
    id: 'ent-demo-6',
    service: 'spotify.com',
    username: 'alex_beats',
    password: 'MusicGroove#8812',
    created_at: '2026-09-26T10:15:00Z',
    updated_at: '2026-09-26T10:15:00Z',
  },
  {
    id: 'ent-demo-7',
    service: 'instagram.com',
    username: 'alex.snaps',
    password: 'InstaPic%994',
    created_at: '2026-09-27T12:00:00Z',
    updated_at: '2026-09-27T12:00:00Z',
  },
  {
    id: 'ent-demo-8',
    service: 'hdfcbank.com',
    username: 'alex_hdfc_usr',
    password: 'Hdfc$NetBank!2024',
    created_at: '2026-09-28T14:30:00Z',
    updated_at: '2026-09-28T14:30:00Z',
  },
];

// Stolen honey-vault blob v1 conforming strictly to PROJECT-BRIEF.md §7.8
const MOCK_HONEY_BLOB: ExportVaultBlob = {
  format: 'honeyvault',
  version: 1,
  scheme: 'HE-PCFG-v1/AES-256-CTR/argon2id',
  kdf: {
    alg: 'argon2id',
    profile: 'demo',
    salt: 'ZGVtb19rZGZfc2FsdF8xNmJ5dGVz',
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
  entries: [
    {
      id: 'e1a90c42-7b3f-42e1-95df-42b78b021001',
      service: 'github.com',
      nonce: 'oM4zQkX8s7vN1aB3cE5gHj==',
      ciphertext:
        'e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0==',
      created_at: '2026-09-15T08:30:00Z',
      updated_at: '2026-09-15T08:30:00Z',
    },
    {
      id: 'e2b81d53-8c4g-43f2-86eg-53c89c032002',
      service: 'gmail.com',
      nonce: 'pL5aRjY9t8wO2bC4dF6hIk==',
      ciphertext:
        'b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0e8f7a6b5c4d3e2f1a0==',
      created_at: '2026-09-16T09:12:00Z',
      updated_at: '2026-09-16T09:12:00Z',
    },
    {
      id: 'e3c92e64-9d5h-44g3-97fh-64d90d043003',
      service: 'netflix.com',
      nonce: 'qM6bSkZ0u9xP3cD5eG7iJl==',
      ciphertext:
        'f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0b3==',
      created_at: '2026-09-20T14:45:00Z',
      updated_at: '2026-09-20T14:45:00Z',
    },
    {
      id: 'e4d03f75-0e6i-45h4-08gi-75ea1e054004',
      service: 'amazon.in',
      nonce: 'rN7cTlA1v0yQ4dE6fH8jKm==',
      ciphertext:
        'c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7==',
      created_at: '2026-09-22T11:05:00Z',
      updated_at: '2026-09-22T11:05:00Z',
    },
    {
      id: 'e5e14g86-1f7j-46i5-19hj-86fb2f065005',
      service: 'linkedin.com',
      nonce: 'sO8dUmB2w1zR5eF7gI9kLn==',
      ciphertext:
        'd7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8==',
      created_at: '2026-09-25T16:20:00Z',
      updated_at: '2026-09-25T16:20:00Z',
    },
    {
      id: 'e6f25h97-2g8k-57j6-20ik-97gc3g076006',
      service: 'spotify.com',
      nonce: 'tP9eVnC3x2aS6fG8hJ0lMo==',
      ciphertext:
        'a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0e8f7a6b5c4d3e2f1==',
      created_at: '2026-09-26T10:15:00Z',
      updated_at: '2026-09-26T10:15:00Z',
    },
    {
      id: 'e7a36i08-3h9l-68k7-31jl-08hd4h087007',
      service: 'instagram.com',
      nonce: 'uQ0fWoD4y3bT7gH9iK1mNp==',
      ciphertext:
        'b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0e8f7a6b5c4d3e2f1a0==',
      created_at: '2026-09-27T12:00:00Z',
      updated_at: '2026-09-27T12:00:00Z',
    },
    {
      id: 'e8b47j19-4i0m-79l8-42km-19ie5i098008',
      service: 'hdfcbank.com',
      nonce: 'vR1gXpE5z4cU8hI0jL2nOq==',
      ciphertext:
        'c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0e8f7a6b5c4d3e2f1a0b9==',
      created_at: '2026-09-28T14:30:00Z',
      updated_at: '2026-09-28T14:30:00Z',
    },
  ],
};

// Conventional baseline vault blob (matches real ConventionalVault dict shape)
const MOCK_BASELINE_BLOB = {
  format: 'conventional-vault',
  version: 1,
  scheme: 'AES-256-GCM/argon2id',
  kdf: {
    alg: 'argon2id',
    profile: 'demo',
    salt: 'ZGVtb19rZGZfc2FsdF8xNmJ5dGVz',
    time_cost: 3,
    memory_cost_kib: 65536,
    parallelism: 4,
    hash_len: 32,
  },
  nonce: 'oM4zQkX8s7vN1aB3cE5gHj==',
  ciphertext:
    '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',
};

// 25 realistic PCFG decoy vaults sampled across dictionary guesses (8 entries per sample)
const MOCK_SAMPLES: DictionaryAttackHoneySample[] = [
  {
    guess_index: 0,
    guess: '123456',
    entries: [
      { id: 'd0-1', service: 'github.com', username: 'alex_smith92', password: 'dragon88', created_at: '2026-09-15T08:30:00Z', updated_at: '2026-09-15T08:30:00Z' },
      { id: 'd0-2', service: 'gmail.com', username: 'smith_alex@gmail.com', password: 'summer2019!', created_at: '2026-09-16T09:12:00Z', updated_at: '2026-09-16T09:12:00Z' },
      { id: 'd0-3', service: 'netflix.com', username: 'smith_alex@gmail.com', password: 'monkey1234', created_at: '2026-09-20T14:45:00Z', updated_at: '2026-09-20T14:45:00Z' },
      { id: 'd0-4', service: 'amazon.in', username: 'smith_alex@gmail.com', password: 'shadow99#', created_at: '2026-09-22T11:05:00Z', updated_at: '2026-09-22T11:05:00Z' },
      { id: 'd0-5', service: 'linkedin.com', username: 'alex-smith-pro', password: 'football2020', created_at: '2026-09-25T16:20:00Z', updated_at: '2026-09-25T16:20:00Z' },
      { id: 'd0-6', service: 'spotify.com', username: 'alex_groove', password: 'music#2024', created_at: '2026-09-26T10:15:00Z', updated_at: '2026-09-26T10:15:00Z' },
      { id: 'd0-7', service: 'instagram.com', username: 'alex_snaps_real', password: 'camera2025!', created_at: '2026-09-27T12:00:00Z', updated_at: '2026-09-27T12:00:00Z' },
      { id: 'd0-8', service: 'hdfcbank.com', username: 'alex_smith_hdfc', password: 'bankpass#192', created_at: '2026-09-28T14:30:00Z', updated_at: '2026-09-28T14:30:00Z' },
    ],
  },
  {
    guess_index: 1,
    guess: 'password',
    entries: [
      { id: 'd1-1', service: 'github.com', username: 'jordan_dev', password: 'princess8', created_at: '2026-09-15T08:30:00Z', updated_at: '2026-09-15T08:30:00Z' },
      { id: 'd1-2', service: 'gmail.com', username: 'jordan.c@gmail.com', password: 'purple123!', created_at: '2026-09-16T09:12:00Z', updated_at: '2026-09-16T09:12:00Z' },
      { id: 'd1-3', service: 'netflix.com', username: 'jordan.c@gmail.com', password: 'charlie007', created_at: '2026-09-20T14:45:00Z', updated_at: '2026-09-20T14:45:00Z' },
      { id: 'd1-4', service: 'amazon.in', username: 'jordan.c@gmail.com', password: 'sunshine99$', created_at: '2026-09-22T11:05:00Z', updated_at: '2026-09-22T11:05:00Z' },
      { id: 'd1-5', service: 'linkedin.com', username: 'jordan-career', password: 'superman2021', created_at: '2026-09-25T16:20:00Z', updated_at: '2026-09-25T16:20:00Z' },
      { id: 'd1-6', service: 'spotify.com', username: 'jordan_beats', password: 'rhythm77', created_at: '2026-09-26T10:15:00Z', updated_at: '2026-09-26T10:15:00Z' },
      { id: 'd1-7', service: 'instagram.com', username: 'jordan.pic', password: 'sunset#22', created_at: '2026-09-27T12:00:00Z', updated_at: '2026-09-27T12:00:00Z' },
      { id: 'd1-8', service: 'hdfcbank.com', username: 'jordan_netbank', password: 'secure$net99', created_at: '2026-09-28T14:30:00Z', updated_at: '2026-09-28T14:30:00Z' },
    ],
  },
  {
    guess_index: 8,
    guess: '12345678',
    entries: [
      { id: 'd8-1', service: 'github.com', username: 'marcus_code', password: 'trustno1', created_at: '2026-09-15T08:30:00Z', updated_at: '2026-09-15T08:30:00Z' },
      { id: 'd8-2', service: 'gmail.com', username: 'marcus.v@gmail.com', password: 'harley99!', created_at: '2026-09-16T09:12:00Z', updated_at: '2026-09-16T09:12:00Z' },
      { id: 'd8-3', service: 'netflix.com', username: 'marcus.v@gmail.com', password: 'diamond22', created_at: '2026-09-20T14:45:00Z', updated_at: '2026-09-20T14:45:00Z' },
      { id: 'd8-4', service: 'amazon.in', username: 'marcus.v@gmail.com', password: 'mustangGT#1', created_at: '2026-09-22T11:05:00Z', updated_at: '2026-09-22T11:05:00Z' },
      { id: 'd8-5', service: 'linkedin.com', username: 'marcus-pro', password: 'baseball19', created_at: '2026-09-25T16:20:00Z', updated_at: '2026-09-25T16:20:00Z' },
      { id: 'd8-6', service: 'spotify.com', username: 'marcus_tunes', password: 'acoustic2023', created_at: '2026-09-26T10:15:00Z', updated_at: '2026-09-26T10:15:00Z' },
      { id: 'd8-7', service: 'instagram.com', username: 'marcus_photos', password: 'camera99#', created_at: '2026-09-27T12:00:00Z', updated_at: '2026-09-27T12:00:00Z' },
      { id: 'd8-8', service: 'hdfcbank.com', username: 'marcus_bank', password: 'rupeeSafe#1', created_at: '2026-09-28T14:30:00Z', updated_at: '2026-09-28T14:30:00Z' },
    ],
  },
  {
    // The REAL guess index matching real demo wordlist position (index 18)
    guess_index: 18,
    guess: 'demo-master-vault-2026',
    entries: REAL_RECOVERED_ENTRIES,
  },
  {
    guess_index: 24,
    guess: 'dragon',
    entries: [
      { id: 'd24-1', service: 'github.com', username: 'd_chen', password: 'matrix2022', created_at: '2026-09-15T08:30:00Z', updated_at: '2026-09-15T08:30:00Z' },
      { id: 'd24-2', service: 'gmail.com', username: 'david.c@gmail.com', password: 'phantom#4', created_at: '2026-09-16T09:12:00Z', updated_at: '2026-09-16T09:12:00Z' },
      { id: 'd24-3', service: 'netflix.com', username: 'david.c@gmail.com', password: 'silverado9', created_at: '2026-09-20T14:45:00Z', updated_at: '2026-09-20T14:45:00Z' },
      { id: 'd24-4', service: 'amazon.in', username: 'david.c@gmail.com', password: 'whiskey#12', created_at: '2026-09-22T11:05:00Z', updated_at: '2026-09-22T11:05:00Z' },
      { id: 'd24-5', service: 'linkedin.com', username: 'dchen-tech', password: 'phoenix99!', created_at: '2026-09-25T16:20:00Z', updated_at: '2026-09-25T16:20:00Z' },
      { id: 'd24-6', service: 'spotify.com', username: 'dchen_audio', password: 'vibes#2024', created_at: '2026-09-26T10:15:00Z', updated_at: '2026-09-26T10:15:00Z' },
      { id: 'd24-7', service: 'instagram.com', username: 'dchen_snaps', password: 'picsecure!3', created_at: '2026-09-27T12:00:00Z', updated_at: '2026-09-27T12:00:00Z' },
      { id: 'd24-8', service: 'hdfcbank.com', username: 'dchen_fin', password: 'wealth#998', created_at: '2026-09-28T14:30:00Z', updated_at: '2026-09-28T14:30:00Z' },
    ],
  },
  {
    guess_index: 39,
    guess: 'master',
    entries: [
      { id: 'd39-1', service: 'github.com', username: 'vikram_p', password: 'cheetah8', created_at: '2026-09-15T08:30:00Z', updated_at: '2026-09-15T08:30:00Z' },
      { id: 'd39-2', service: 'gmail.com', username: 'vikram.p@gmail.com', password: 'galaxy2020!', created_at: '2026-09-16T09:12:00Z', updated_at: '2026-09-16T09:12:00Z' },
      { id: 'd39-3', service: 'netflix.com', username: 'vikram.p@gmail.com', password: 'rover332', created_at: '2026-09-20T14:45:00Z', updated_at: '2026-09-20T14:45:00Z' },
      { id: 'd39-4', service: 'amazon.in', username: 'vikram.p@gmail.com', password: 'titanium#7', created_at: '2026-09-22T11:05:00Z', updated_at: '2026-09-22T11:05:00Z' },
      { id: 'd39-5', service: 'linkedin.com', username: 'vikram-lead', password: 'wolverine88', created_at: '2026-09-25T16:20:00Z', updated_at: '2026-09-25T16:20:00Z' },
      { id: 'd39-6', service: 'spotify.com', username: 'vik_stream', password: 'lofi_night1', created_at: '2026-09-26T10:15:00Z', updated_at: '2026-09-26T10:15:00Z' },
      { id: 'd39-7', service: 'instagram.com', username: 'vikram_art', password: 'gallery#88', created_at: '2026-09-27T12:00:00Z', updated_at: '2026-09-27T12:00:00Z' },
      { id: 'd39-8', service: 'hdfcbank.com', username: 'vikram_hdfc', password: 'secureNet$5', created_at: '2026-09-28T14:30:00Z', updated_at: '2026-09-28T14:30:00Z' },
    ],
  },
  {
    guess_index: 52,
    guess: 'football',
    entries: [
      { id: 'd52-1', service: 'github.com', username: 'elena_r', password: 'scorpio88', created_at: '2026-09-15T08:30:00Z', updated_at: '2026-09-15T08:30:00Z' },
      { id: 'd52-2', service: 'gmail.com', username: 'elena.r@gmail.com', password: 'jasmine2019!', created_at: '2026-09-16T09:12:00Z', updated_at: '2026-09-16T09:12:00Z' },
      { id: 'd52-3', service: 'netflix.com', username: 'elena.r@gmail.com', password: 'eclipse44', created_at: '2026-09-20T14:45:00Z', updated_at: '2026-09-20T14:45:00Z' },
      { id: 'd52-4', service: 'amazon.in', username: 'elena.r@gmail.com', password: 'monterey#2', created_at: '2026-09-22T11:05:00Z', updated_at: '2026-09-22T11:05:00Z' },
      { id: 'd52-5', service: 'linkedin.com', username: 'elena-sre', password: 'cardinal99', created_at: '2026-09-25T16:20:00Z', updated_at: '2026-09-25T16:20:00Z' },
      { id: 'd52-6', service: 'spotify.com', username: 'elena_sound', password: 'ambient#9', created_at: '2026-09-26T10:15:00Z', updated_at: '2026-09-26T10:15:00Z' },
      { id: 'd52-7', service: 'instagram.com', username: 'elena.snaps', password: 'polaroid!2', created_at: '2026-09-27T12:00:00Z', updated_at: '2026-09-27T12:00:00Z' },
      { id: 'd52-8', service: 'hdfcbank.com', username: 'elena_banking', password: 'hdfcKey#2024', created_at: '2026-09-28T14:30:00Z', updated_at: '2026-09-28T14:30:00Z' },
    ],
  },
  {
    guess_index: 104,
    guess: 'shadow',
    entries: [
      { id: 'd104-1', service: 'github.com', username: 'liam_wright', password: 'falcon22', created_at: '2026-09-15T08:30:00Z', updated_at: '2026-09-15T08:30:00Z' },
      { id: 'd104-2', service: 'gmail.com', username: 'liam.w@gmail.com', password: 'crimson#9', created_at: '2026-09-16T09:12:00Z', updated_at: '2026-09-16T09:12:00Z' },
      { id: 'd104-3', service: 'netflix.com', username: 'liam.w@gmail.com', password: 'pegasus77', created_at: '2026-09-20T14:45:00Z', updated_at: '2026-09-20T14:45:00Z' },
      { id: 'd104-4', service: 'amazon.in', username: 'liam.w@gmail.com', password: 'geneva#44', created_at: '2026-09-22T11:05:00Z', updated_at: '2026-09-22T11:05:00Z' },
      { id: 'd104-5', service: 'linkedin.com', username: 'lwright-fin', password: 'vanguard1', created_at: '2026-09-25T16:20:00Z', updated_at: '2026-09-25T16:20:00Z' },
      { id: 'd104-6', service: 'spotify.com', username: 'liam_beats', password: 'jazzClub!4', created_at: '2026-09-26T10:15:00Z', updated_at: '2026-09-26T10:15:00Z' },
      { id: 'd104-7', service: 'instagram.com', username: 'liam_capture', password: 'shutter77', created_at: '2026-09-27T12:00:00Z', updated_at: '2026-09-27T12:00:00Z' },
      { id: 'd104-8', service: 'hdfcbank.com', username: 'liam_secure', password: 'accountSafe#8', created_at: '2026-09-28T14:30:00Z', updated_at: '2026-09-28T14:30:00Z' },
    ],
  },
  {
    guess_index: 200,
    guess: 'sunshine2023',
    entries: [
      { id: 'd200-1', service: 'github.com', username: 'clara_b', password: 'glacier8', created_at: '2026-09-15T08:30:00Z', updated_at: '2026-09-15T08:30:00Z' },
      { id: 'd200-2', service: 'gmail.com', username: 'clara.b@gmail.com', password: 'orchard2021!', created_at: '2026-09-16T09:12:00Z', updated_at: '2026-09-16T09:12:00Z' },
      { id: 'd200-3', service: 'netflix.com', username: 'clara.b@gmail.com', password: 'neptune101', created_at: '2026-09-20T14:45:00Z', updated_at: '2026-09-20T14:45:00Z' },
      { id: 'd200-4', service: 'amazon.in', username: 'clara.b@gmail.com', password: 'bern#8812', created_at: '2026-09-22T11:05:00Z', updated_at: '2026-09-22T11:05:00Z' },
      { id: 'd200-5', service: 'linkedin.com', username: 'cbecker-eng', password: 'solstice9', created_at: '2026-09-25T16:20:00Z', updated_at: '2026-09-25T16:20:00Z' },
      { id: 'd200-6', service: 'spotify.com', username: 'clara_mixes', password: 'chillhop#3', created_at: '2026-09-26T10:15:00Z', updated_at: '2026-09-26T10:15:00Z' },
      { id: 'd200-7', service: 'instagram.com', username: 'clara_feed', password: 'aesthetic!4', created_at: '2026-09-27T12:00:00Z', updated_at: '2026-09-27T12:00:00Z' },
      { id: 'd200-8', service: 'hdfcbank.com', username: 'cbecker_bank', password: 'safeToken#19', created_at: '2026-09-28T14:30:00Z', updated_at: '2026-09-28T14:30:00Z' },
    ],
  },
  {
    guess_index: 299,
    guess: 'ocean10team',
    entries: [
      { id: 'd299-1', service: 'github.com', username: 'alex_mercer_alt', password: 'cipher77', created_at: '2026-09-15T08:30:00Z', updated_at: '2026-09-15T08:30:00Z' },
      { id: 'd299-2', service: 'gmail.com', username: 'alex.m.dev@gmail.com', password: 'enigma#2026', created_at: '2026-09-16T09:12:00Z', updated_at: '2026-09-16T09:12:00Z' },
      { id: 'd299-3', service: 'netflix.com', username: 'alex.m.dev@gmail.com', password: 'kryptex99', created_at: '2026-09-20T14:45:00Z', updated_at: '2026-09-20T14:45:00Z' },
      { id: 'd299-4', service: 'amazon.in', username: 'alex.m.dev@gmail.com', password: 'swissbank#1', created_at: '2026-09-22T11:05:00Z', updated_at: '2026-09-22T11:05:00Z' },
      { id: 'd299-5', service: 'linkedin.com', username: 'alex-mercer-lead', password: 'finalkey2026', created_at: '2026-09-25T16:20:00Z', updated_at: '2026-09-25T16:20:00Z' },
      { id: 'd299-6', service: 'spotify.com', username: 'alex_favorites', password: 'playlist!2024', created_at: '2026-09-26T10:15:00Z', updated_at: '2026-09-26T10:15:00Z' },
      { id: 'd299-7', service: 'instagram.com', username: 'alex_visuals', password: 'snapshot#88', created_at: '2026-09-27T12:00:00Z', updated_at: '2026-09-27T12:00:00Z' },
      { id: 'd299-8', service: 'hdfcbank.com', username: 'alex_mercer_savings', password: 'vaultKey$2026', created_at: '2026-09-28T14:30:00Z', updated_at: '2026-09-28T14:30:00Z' },
    ],
  },
];

// Stolen sweetwords: 1 real login password + 9 honeywords per Juels & Rivest 2013
const MOCK_SWEETWORDS = [
  'demo-login-pass!7918',
  'demo-login-pass-5850',
  'demo-login-pass>2928',
  'demo-login-pass]4444',
  'demo-login-pass-0421',
  'demo-login-pass-9084',
  'demo-login-pass-2026', // real login password configured in demo environment
  'demo-login-pass}4136',
  'demo-login-pass!1337',
  'demo-login-pass-9843',
];

const MOCK_SWEETWORD_HASHES = [
  'a643731635795225c255484613289faeaaf5d545074006b749fed7859c278d49',
  '7b819f70d2f1d530ee235ef9e51e7075bdfaa0107759a22f48ef53d1e1f13b19',
  '8c92a081e3f2e641ff346fa0f62f8186ceebb121886ab33f59f064e2f2024c20',
  '9d03b192f403f752004570b107309297dffcc232997bc4406a0175f303135d31',
  '0e14c2a305140863115681c218410308e00dd343aa8cd5517b12860414246e42',
  '1f25d3b416251974226792d329521419f11ee454bb9de6628c23971525357f53',
  '2036e4c527362a853378a3e43a63252a022ff565ccaef7739d34a82636468064',
  '3147f5d638473b964489b4f54b74363b13300676ddbf08840e45b93747579175',
  '425806e749584ca75590c5065c85474c24411787eec019951f56ca485868a286',
  '536917f850695db86601d6176d96585d35522898ffd12aa62067db596979b397',
];

// Active breach alarms store
const alarmsStore: AdminAlert[] = [
  {
    id: 'alt-init-1',
    username: 'demo',
    kind: 'HONEYWORD_LOGIN',
    severity: 'critical',
    sweetword_index: 0,
    source_ip: '127.0.0.1',
    user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    created_at: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
  },
];

// Listen for client-side sweetword trigger event to populate real-time alarm in mock mode
if (typeof window !== 'undefined') {
  window.addEventListener('hv:honeyword_attempt', (event: Event) => {
    const customEvent = event as CustomEvent<{ index: number; sweetword: string }>;
    const { index } = customEvent.detail;
    // Index 6 is the real password in MOCK_SWEETWORDS; only mismatches create alarms!
    if (index !== 6) {
      alarmsStore.unshift({
        id: `alt-live-${String(Date.now())}`,
        username: 'demo',
        kind: 'HONEYWORD_LOGIN',
        severity: 'critical',
        sweetword_index: index,
        source_ip: '127.0.0.1',
        user_agent: navigator.userAgent || 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        created_at: new Date().toISOString(),
      });
    }
  });
}

export const attackHandlers = [
  // GET /api/attack/stolen-vault
  http.get('/api/attack/stolen-vault', () => {
    return HttpResponse.json<AttackStolenVaultResponse>({
      honey_blob: MOCK_HONEY_BLOB,
      baseline_blob: MOCK_BASELINE_BLOB,
      owner: 'demo',
    });
  }),

  // POST /api/attack/dictionary
  http.post('/api/attack/dictionary', async ({ request }) => {
    let maxGuesses = 300;
    try {
      const body = (await request.json()) as DictionaryAttackRequest;
      if (typeof body.max_guesses === 'number') {
        maxGuesses = Math.max(1, Math.min(2000, body.max_guesses));
      }
    } catch {
      // fallback to 300 if body cannot be parsed
    }

    // Matches real seeded demo wordlist index (18)
    const CRACK_TARGET_INDEX = 18;
    const isCracked = maxGuesses >= CRACK_TARGET_INDEX;

    // Filter or adjust samples to fit within maxGuesses
    const filteredSamples = MOCK_SAMPLES.filter((s) => s.guess_index < maxGuesses);
    const samples = filteredSamples.slice(0, 25);

    const response: DictionaryAttackResponse = {
      baseline: {
        cracked: isCracked,
        guess_index: isCracked ? CRACK_TARGET_INDEX : null,
        elapsed_ms: isCracked ? 6 : Math.round(maxGuesses * 4.2),
        recovered_entries: isCracked ? REAL_RECOVERED_ENTRIES : [],
      },
      honey: {
        guesses_tried: maxGuesses,
        elapsed_ms: Math.round(maxGuesses * 5.1),
        distinct_vaults: maxGuesses,
        samples,
      },
      reveal: {
        real_guess_index: isCracked ? CRACK_TARGET_INDEX : null,
      },
    };

    return HttpResponse.json<DictionaryAttackResponse>(response);
  }),

  // GET /api/attack/stolen-honeywords
  http.get('/api/attack/stolen-honeywords', () => {
    return HttpResponse.json<StolenHoneywordsResponse>({
      username: 'demo',
      k: 10,
      salt: '7cGvTT2pINbXYOFE0KJsLA==',
      hashes: MOCK_SWEETWORD_HASHES,
      cracked_sweetwords: MOCK_SWEETWORDS,
    });
  }),

  // GET /api/attack/alarms
  http.get('/api/attack/alarms', () => {
    return HttpResponse.json<AttackAlarmsResponse>(alarmsStore.slice(0, 20));
  }),
];
