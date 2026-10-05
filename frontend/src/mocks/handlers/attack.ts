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

// Real vault entries stored under demo's master key
const REAL_RECOVERED_ENTRIES: CrackedEntry[] = [
  {
    id: 'ent-real-1',
    service: 'github.com',
    username: 'demo_developer',
    password: 'ghp_K992jSkA0182mZls9182',
    created_at: '2026-09-15T08:30:00Z',
    updated_at: '2026-09-15T08:30:00Z',
  },
  {
    id: 'ent-real-2',
    service: 'proton.me',
    username: 'demo_secops@proton.me',
    password: 'Tr0ub4dor&3#Priv',
    created_at: '2026-09-16T09:12:00Z',
    updated_at: '2026-09-16T09:12:00Z',
  },
  {
    id: 'ent-real-3',
    service: 'aws.amazon.com',
    username: 'aws_admin_demo',
    password: 'AKIAIOSFODNN7EXAMPLE_SECRET',
    created_at: '2026-09-20T14:45:00Z',
    updated_at: '2026-09-20T14:45:00Z',
  },
  {
    id: 'ent-real-4',
    service: 'banking.swissquote.ch',
    username: 'chetan_c_private',
    password: 'SwissVault#2026!Key',
    created_at: '2026-09-22T11:05:00Z',
    updated_at: '2026-09-22T11:05:00Z',
  },
  {
    id: 'ent-real-5',
    service: 'discord.com',
    username: 'oceans10_lead',
    password: 'HoneyEncryptionVault2026!',
    created_at: '2026-09-25T16:20:00Z',
    updated_at: '2026-09-25T16:20:00Z',
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
      service: 'proton.me',
      nonce: 'pL5aRjY9t8wO2bC4dF6hIk==',
      ciphertext:
        'b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0e8f7a6b5c4d3e2f1a0==',
      created_at: '2026-09-16T09:12:00Z',
      updated_at: '2026-09-16T09:12:00Z',
    },
    {
      id: 'e3c92e64-9d5h-44g3-97fh-64d90d043003',
      service: 'aws.amazon.com',
      nonce: 'qM6bSkZ0u9xP3cD5eG7iJl==',
      ciphertext:
        'f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0b3==',
      created_at: '2026-09-20T14:45:00Z',
      updated_at: '2026-09-20T14:45:00Z',
    },
    {
      id: 'e4d03f75-0e6i-45h4-08gi-75ea1e054004',
      service: 'banking.swissquote.ch',
      nonce: 'rN7cTlA1v0yQ4dE6fH8jKm==',
      ciphertext:
        'c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7==',
      created_at: '2026-09-22T11:05:00Z',
      updated_at: '2026-09-22T11:05:00Z',
    },
    {
      id: 'e5e14g86-1f7j-46i5-19hj-86fb2f065005',
      service: 'discord.com',
      nonce: 'sO8dUmB2w1zR5eF7gI9kLn==',
      ciphertext:
        'd7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8==',
      created_at: '2026-09-25T16:20:00Z',
      updated_at: '2026-09-25T16:20:00Z',
    },
  ],
};

// Conventional baseline vault blob (AES-256-GCM with authentication tag)
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
  tag: '6f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c',
  ciphertext_len_bytes: 1420,
  ciphertext_preview: '9d8f7e6c5b4a3928170f...[AES-GCM encrypted JSON payload]...8b7c6d5e4f3a',
};

// 25 realistic PCFG decoy vaults sampled across dictionary guesses
const MOCK_SAMPLES: DictionaryAttackHoneySample[] = [
  {
    guess_index: 0,
    guess: '123456',
    entries: [
      { id: 'd0-1', service: 'github.com', username: 'alex_smith92', password: 'dragon88', created_at: '2026-09-15T08:30:00Z', updated_at: '2026-09-15T08:30:00Z' },
      { id: 'd0-2', service: 'proton.me', username: 'smith_priv@proton.me', password: 'summer2019!', created_at: '2026-09-16T09:12:00Z', updated_at: '2026-09-16T09:12:00Z' },
      { id: 'd0-3', service: 'aws.amazon.com', username: 'alex_ops', password: 'monkey1234', created_at: '2026-09-20T14:45:00Z', updated_at: '2026-09-20T14:45:00Z' },
      { id: 'd0-4', service: 'banking.swissquote.ch', username: 'asmith92', password: 'shadow99#', created_at: '2026-09-22T11:05:00Z', updated_at: '2026-09-22T11:05:00Z' },
      { id: 'd0-5', service: 'discord.com', username: 'asmith_gamer', password: 'football2020', created_at: '2026-09-25T16:20:00Z', updated_at: '2026-09-25T16:20:00Z' },
    ],
  },
  {
    guess_index: 1,
    guess: 'password',
    entries: [
      { id: 'd1-1', service: 'github.com', username: 'jordan_dev', password: 'princess8', created_at: '2026-09-15T08:30:00Z', updated_at: '2026-09-15T08:30:00Z' },
      { id: 'd1-2', service: 'proton.me', username: 'jordan_sec@proton.me', password: 'purple123!', created_at: '2026-09-16T09:12:00Z', updated_at: '2026-09-16T09:12:00Z' },
      { id: 'd1-3', service: 'aws.amazon.com', username: 'jordan_cloud', password: 'charlie007', created_at: '2026-09-20T14:45:00Z', updated_at: '2026-09-20T14:45:00Z' },
      { id: 'd1-4', service: 'banking.swissquote.ch', username: 'jordan_b', password: 'sunshine99$', created_at: '2026-09-22T11:05:00Z', updated_at: '2026-09-22T11:05:00Z' },
      { id: 'd1-5', service: 'discord.com', username: 'jordan_night', password: 'superman2021', created_at: '2026-09-25T16:20:00Z', updated_at: '2026-09-25T16:20:00Z' },
    ],
  },
  {
    guess_index: 8,
    guess: '12345678',
    entries: [
      { id: 'd8-1', service: 'github.com', username: 'marcus_code', password: 'trustno1', created_at: '2026-09-15T08:30:00Z', updated_at: '2026-09-15T08:30:00Z' },
      { id: 'd8-2', service: 'proton.me', username: 'marcus.v@proton.me', password: 'harley99!', created_at: '2026-09-16T09:12:00Z', updated_at: '2026-09-16T09:12:00Z' },
      { id: 'd8-3', service: 'aws.amazon.com', username: 'admin_marcus', password: 'diamond22', created_at: '2026-09-20T14:45:00Z', updated_at: '2026-09-20T14:45:00Z' },
      { id: 'd8-4', service: 'banking.swissquote.ch', username: 'mv_invest', password: 'mustangGT#1', created_at: '2026-09-22T11:05:00Z', updated_at: '2026-09-22T11:05:00Z' },
      { id: 'd8-5', service: 'discord.com', username: 'marcus_gg', password: 'baseball19', created_at: '2026-09-25T16:20:00Z', updated_at: '2026-09-25T16:20:00Z' },
    ],
  },
  {
    guess_index: 15,
    guess: 'qwerty',
    entries: [
      { id: 'd15-1', service: 'github.com', username: 'sarah_lyn', password: 'butterfly7', created_at: '2026-09-15T08:30:00Z', updated_at: '2026-09-15T08:30:00Z' },
      { id: 'd15-2', service: 'proton.me', username: 'sarah.crypt@proton.me', password: 'cookie2018!', created_at: '2026-09-16T09:12:00Z', updated_at: '2026-09-16T09:12:00Z' },
      { id: 'd15-3', service: 'aws.amazon.com', username: 's_infra', password: 'pepper2020', created_at: '2026-09-20T14:45:00Z', updated_at: '2026-09-20T14:45:00Z' },
      { id: 'd15-4', service: 'banking.swissquote.ch', username: 'slyn_ch', password: 'rosemary#8', created_at: '2026-09-22T11:05:00Z', updated_at: '2026-09-22T11:05:00Z' },
      { id: 'd15-5', service: 'discord.com', username: 'sarah_quest', password: 'starlight88', created_at: '2026-09-25T16:20:00Z', updated_at: '2026-09-25T16:20:00Z' },
    ],
  },
  {
    guess_index: 24,
    guess: 'dragon',
    entries: [
      { id: 'd24-1', service: 'github.com', username: 'd_chen', password: 'matrix2022', created_at: '2026-09-15T08:30:00Z', updated_at: '2026-09-15T08:30:00Z' },
      { id: 'd24-2', service: 'proton.me', username: 'david.c@proton.me', password: 'phantom#4', created_at: '2026-09-16T09:12:00Z', updated_at: '2026-09-16T09:12:00Z' },
      { id: 'd24-3', service: 'aws.amazon.com', username: 'dchen_iam', password: 'silverado9', created_at: '2026-09-20T14:45:00Z', updated_at: '2026-09-20T14:45:00Z' },
      { id: 'd24-4', service: 'banking.swissquote.ch', username: 'dchen_assets', password: 'whiskey#12', created_at: '2026-09-22T11:05:00Z', updated_at: '2026-09-22T11:05:00Z' },
      { id: 'd24-5', service: 'discord.com', username: 'dchen_vr', password: 'phoenix99!', created_at: '2026-09-25T16:20:00Z', updated_at: '2026-09-25T16:20:00Z' },
    ],
  },
  {
    guess_index: 39,
    guess: 'master',
    entries: [
      { id: 'd39-1', service: 'github.com', username: 'vikram_p', password: 'cheetah8', created_at: '2026-09-15T08:30:00Z', updated_at: '2026-09-15T08:30:00Z' },
      { id: 'd39-2', service: 'proton.me', username: 'vikram.p@proton.me', password: 'galaxy2020!', created_at: '2026-09-16T09:12:00Z', updated_at: '2026-09-16T09:12:00Z' },
      { id: 'd39-3', service: 'aws.amazon.com', username: 'vikram_prod', password: 'rover332', created_at: '2026-09-20T14:45:00Z', updated_at: '2026-09-20T14:45:00Z' },
      { id: 'd39-4', service: 'banking.swissquote.ch', username: 'vp_hedge', password: 'titanium#7', created_at: '2026-09-22T11:05:00Z', updated_at: '2026-09-22T11:05:00Z' },
      { id: 'd39-5', service: 'discord.com', username: 'vik_arcade', password: 'wolverine88', created_at: '2026-09-25T16:20:00Z', updated_at: '2026-09-25T16:20:00Z' },
    ],
  },
  {
    guess_index: 52,
    guess: 'football',
    entries: [
      { id: 'd52-1', service: 'github.com', username: 'elena_rodriguez', password: 'scorpio88', created_at: '2026-09-15T08:30:00Z', updated_at: '2026-09-15T08:30:00Z' },
      { id: 'd52-2', service: 'proton.me', username: 'elena.r@proton.me', password: 'jasmine2019!', created_at: '2026-09-16T09:12:00Z', updated_at: '2026-09-16T09:12:00Z' },
      { id: 'd52-3', service: 'aws.amazon.com', username: 'elena_sre', password: 'eclipse44', created_at: '2026-09-20T14:45:00Z', updated_at: '2026-09-20T14:45:00Z' },
      { id: 'd52-4', service: 'banking.swissquote.ch', username: 'erodriguez_ch', password: 'monterey#2', created_at: '2026-09-22T11:05:00Z', updated_at: '2026-09-22T11:05:00Z' },
      { id: 'd52-5', service: 'discord.com', username: 'elena_meta', password: 'cardinal99', created_at: '2026-09-25T16:20:00Z', updated_at: '2026-09-25T16:20:00Z' },
    ],
  },
  {
    guess_index: 68,
    guess: 'baseball',
    entries: [
      { id: 'd68-1', service: 'github.com', username: 'lucas_meyer', password: 'guitar99', created_at: '2026-09-15T08:30:00Z', updated_at: '2026-09-15T08:30:00Z' },
      { id: 'd68-2', service: 'proton.me', username: 'lucas.m@proton.me', password: 'emerald#11', created_at: '2026-09-16T09:12:00Z', updated_at: '2026-09-16T09:12:00Z' },
      { id: 'd68-3', service: 'aws.amazon.com', username: 'lucas_devops', password: 'thunderbolt7', created_at: '2026-09-20T14:45:00Z', updated_at: '2026-09-20T14:45:00Z' },
      { id: 'd68-4', service: 'banking.swissquote.ch', username: 'lmeyer_swiss', password: 'alpine#2024', created_at: '2026-09-22T11:05:00Z', updated_at: '2026-09-22T11:05:00Z' },
      { id: 'd68-5', service: 'discord.com', username: 'lucas_play', password: 'corvette88', created_at: '2026-09-25T16:20:00Z', updated_at: '2026-09-25T16:20:00Z' },
    ],
  },
  {
    guess_index: 85,
    guess: 'superman',
    entries: [
      { id: 'd85-1', service: 'github.com', username: 'maya_t', password: 'panther44', created_at: '2026-09-15T08:30:00Z', updated_at: '2026-09-15T08:30:00Z' },
      { id: 'd85-2', service: 'proton.me', username: 'maya.t@proton.me', password: 'sapphire2023!', created_at: '2026-09-16T09:12:00Z', updated_at: '2026-09-16T09:12:00Z' },
      { id: 'd85-3', service: 'aws.amazon.com', username: 'maya_lead', password: 'avalanche2', created_at: '2026-09-20T14:45:00Z', updated_at: '2026-09-20T14:45:00Z' },
      { id: 'd85-4', service: 'banking.swissquote.ch', username: 'mtaylor_ch', password: 'zurich#99', created_at: '2026-09-22T11:05:00Z', updated_at: '2026-09-22T11:05:00Z' },
      { id: 'd85-5', service: 'discord.com', username: 'maya_synth', password: 'horizon2020', created_at: '2026-09-25T16:20:00Z', updated_at: '2026-09-25T16:20:00Z' },
    ],
  },
  {
    guess_index: 104,
    guess: 'shadow',
    entries: [
      { id: 'd104-1', service: 'github.com', username: 'liam_wright', password: 'falcon22', created_at: '2026-09-15T08:30:00Z', updated_at: '2026-09-15T08:30:00Z' },
      { id: 'd104-2', service: 'proton.me', username: 'liam.w@proton.me', password: 'crimson#9', created_at: '2026-09-16T09:12:00Z', updated_at: '2026-09-16T09:12:00Z' },
      { id: 'd104-3', service: 'aws.amazon.com', username: 'liam_cloud', password: 'pegasus77', created_at: '2026-09-20T14:45:00Z', updated_at: '2026-09-20T14:45:00Z' },
      { id: 'd104-4', service: 'banking.swissquote.ch', username: 'lwright_fin', password: 'geneva#44', created_at: '2026-09-22T11:05:00Z', updated_at: '2026-09-22T11:05:00Z' },
      { id: 'd104-5', service: 'discord.com', username: 'liam_zero', password: 'vanguard1', created_at: '2026-09-25T16:20:00Z', updated_at: '2026-09-25T16:20:00Z' },
    ],
  },
  {
    guess_index: 120,
    guess: 'sunshine',
    entries: [
      { id: 'd120-1', service: 'github.com', username: 'clara_becker', password: 'glacier8', created_at: '2026-09-15T08:30:00Z', updated_at: '2026-09-15T08:30:00Z' },
      { id: 'd120-2', service: 'proton.me', username: 'clara.b@proton.me', password: 'orchard2021!', created_at: '2026-09-16T09:12:00Z', updated_at: '2026-09-16T09:12:00Z' },
      { id: 'd120-3', service: 'aws.amazon.com', username: 'clara_sys', password: 'neptune101', created_at: '2026-09-20T14:45:00Z', updated_at: '2026-09-20T14:45:00Z' },
      { id: 'd120-4', service: 'banking.swissquote.ch', username: 'cbecker_val', password: 'bern#8812', created_at: '2026-09-22T11:05:00Z', updated_at: '2026-09-22T11:05:00Z' },
      { id: 'd120-5', service: 'discord.com', username: 'clara_luna', password: 'solstice9', created_at: '2026-09-25T16:20:00Z', updated_at: '2026-09-25T16:20:00Z' },
    ],
  },
  {
    // The REAL guess index! Decoy matches the real entries perfectly in appearance!
    guess_index: 137,
    guess: 'correct horse battery staple',
    entries: REAL_RECOVERED_ENTRIES,
  },
  {
    guess_index: 155,
    guess: 'charlie',
    entries: [
      { id: 'd155-1', service: 'github.com', username: 'nathan_k', password: 'spitfire1', created_at: '2026-09-15T08:30:00Z', updated_at: '2026-09-15T08:30:00Z' },
      { id: 'd155-2', service: 'proton.me', username: 'nathan.k@proton.me', password: 'velvet2024#', created_at: '2026-09-16T09:12:00Z', updated_at: '2026-09-16T09:12:00Z' },
      { id: 'd155-3', service: 'aws.amazon.com', username: 'nathan_dev', password: 'polaris99', created_at: '2026-09-20T14:45:00Z', updated_at: '2026-09-20T14:45:00Z' },
      { id: 'd155-4', service: 'banking.swissquote.ch', username: 'nk_swiss', password: 'rhine#331', created_at: '2026-09-22T11:05:00Z', updated_at: '2026-09-22T11:05:00Z' },
      { id: 'd155-5', service: 'discord.com', username: 'nathan_stream', password: 'aurora2022', created_at: '2026-09-25T16:20:00Z', updated_at: '2026-09-25T16:20:00Z' },
    ],
  },
  {
    guess_index: 198,
    guess: 'trustno1',
    entries: [
      { id: 'd198-1', service: 'github.com', username: 'hannah_z', password: 'jupiter88', created_at: '2026-09-15T08:30:00Z', updated_at: '2026-09-15T08:30:00Z' },
      { id: 'd198-2', service: 'proton.me', username: 'hannah.z@proton.me', password: 'zenith#2025', created_at: '2026-09-16T09:12:00Z', updated_at: '2026-09-16T09:12:00Z' },
      { id: 'd198-3', service: 'aws.amazon.com', username: 'hannah_sre', password: 'hydra771', created_at: '2026-09-20T14:45:00Z', updated_at: '2026-09-20T14:45:00Z' },
      { id: 'd198-4', service: 'banking.swissquote.ch', username: 'hz_credit', password: 'lucerne#10', created_at: '2026-09-22T11:05:00Z', updated_at: '2026-09-22T11:05:00Z' },
      { id: 'd198-5', service: 'discord.com', username: 'hannah_gg', password: 'centurion5', created_at: '2026-09-25T16:20:00Z', updated_at: '2026-09-25T16:20:00Z' },
    ],
  },
  {
    guess_index: 250,
    guess: 'secret123',
    entries: [
      { id: 'd250-1', service: 'github.com', username: 'owen_reed', password: 'cobalt33', created_at: '2026-09-15T08:30:00Z', updated_at: '2026-09-15T08:30:00Z' },
      { id: 'd250-2', service: 'proton.me', username: 'owen.r@proton.me', password: 'cypress#88', created_at: '2026-09-16T09:12:00Z', updated_at: '2026-09-16T09:12:00Z' },
      { id: 'd250-3', service: 'aws.amazon.com', username: 'owen_cluster', password: 'tornado19', created_at: '2026-09-20T14:45:00Z', updated_at: '2026-09-20T14:45:00Z' },
      { id: 'd250-4', service: 'banking.swissquote.ch', username: 'oreed_ch', password: 'basel#442', created_at: '2026-09-22T11:05:00Z', updated_at: '2026-09-22T11:05:00Z' },
      { id: 'd250-5', service: 'discord.com', username: 'owen_wave', password: 'navigator4', created_at: '2026-09-25T16:20:00Z', updated_at: '2026-09-25T16:20:00Z' },
    ],
  },
  {
    guess_index: 310,
    guess: 'welcome2022',
    entries: [
      { id: 'd310-1', service: 'github.com', username: 'sam_bell', password: 'nebula99', created_at: '2026-09-15T08:30:00Z', updated_at: '2026-09-15T08:30:00Z' },
      { id: 'd310-2', service: 'proton.me', username: 'sam.b@proton.me', password: 'mirage#192', created_at: '2026-09-16T09:12:00Z', updated_at: '2026-09-16T09:12:00Z' },
      { id: 'd310-3', service: 'aws.amazon.com', username: 'sam_node', password: 'vortex42', created_at: '2026-09-20T14:45:00Z', updated_at: '2026-09-20T14:45:00Z' },
      { id: 'd310-4', service: 'banking.swissquote.ch', username: 'sbell_fx', password: 'matterhorn#5', created_at: '2026-09-22T11:05:00Z', updated_at: '2026-09-22T11:05:00Z' },
      { id: 'd310-5', service: 'discord.com', username: 'sam_pixel', password: 'challenger7', created_at: '2026-09-25T16:20:00Z', updated_at: '2026-09-25T16:20:00Z' },
    ],
  },
  {
    guess_index: 380,
    guess: 'iloveyou',
    entries: [
      { id: 'd380-1', service: 'github.com', username: 'zoe_martin', password: 'monarch1', created_at: '2026-09-15T08:30:00Z', updated_at: '2026-09-15T08:30:00Z' },
      { id: 'd380-2', service: 'proton.me', username: 'zoe.m@proton.me', password: 'radiance#4', created_at: '2026-09-16T09:12:00Z', updated_at: '2026-09-16T09:12:00Z' },
      { id: 'd380-3', service: 'aws.amazon.com', username: 'zoe_infra', password: 'cyclone88', created_at: '2026-09-20T14:45:00Z', updated_at: '2026-09-20T14:45:00Z' },
      { id: 'd380-4', service: 'banking.swissquote.ch', username: 'zmartin_swiss', password: 'lugano#101', created_at: '2026-09-22T11:05:00Z', updated_at: '2026-09-22T11:05:00Z' },
      { id: 'd380-5', service: 'discord.com', username: 'zoe_sound', password: 'endeavour9', created_at: '2026-09-25T16:20:00Z', updated_at: '2026-09-25T16:20:00Z' },
    ],
  },
  {
    guess_index: 440,
    guess: 'orange123',
    entries: [
      { id: 'd440-1', service: 'github.com', username: 'aaron_f', password: 'blizzard7', created_at: '2026-09-15T08:30:00Z', updated_at: '2026-09-15T08:30:00Z' },
      { id: 'd440-2', service: 'proton.me', username: 'aaron.f@proton.me', password: 'cascade#99', created_at: '2026-09-16T09:12:00Z', updated_at: '2026-09-16T09:12:00Z' },
      { id: 'd440-3', service: 'aws.amazon.com', username: 'aaron_sec', password: 'tempest33', created_at: '2026-09-20T14:45:00Z', updated_at: '2026-09-20T14:45:00Z' },
      { id: 'd440-4', service: 'banking.swissquote.ch', username: 'afox_bank', password: 'lausanne#8', created_at: '2026-09-22T11:05:00Z', updated_at: '2026-09-22T11:05:00Z' },
      { id: 'd440-5', service: 'discord.com', username: 'aaron_cast', password: 'intrepid2', created_at: '2026-09-25T16:20:00Z', updated_at: '2026-09-25T16:20:00Z' },
    ],
  },
  {
    guess_index: 505,
    guess: 'yellowstone',
    entries: [
      { id: 'd505-1', service: 'github.com', username: 'grace_hopper_fan', password: 'solaris44', created_at: '2026-09-15T08:30:00Z', updated_at: '2026-09-15T08:30:00Z' },
      { id: 'd505-2', service: 'proton.me', username: 'grace.h@proton.me', password: 'tapestry#3', created_at: '2026-09-16T09:12:00Z', updated_at: '2026-09-16T09:12:00Z' },
      { id: 'd505-3', service: 'aws.amazon.com', username: 'ghopper_sys', password: 'miracle77', created_at: '2026-09-20T14:45:00Z', updated_at: '2026-09-20T14:45:00Z' },
      { id: 'd505-4', service: 'banking.swissquote.ch', username: 'ghopper_fund', password: 'interlaken#2', created_at: '2026-09-22T11:05:00Z', updated_at: '2026-09-22T11:05:00Z' },
      { id: 'd505-5', service: 'discord.com', username: 'grace_flow', password: 'meridian9', created_at: '2026-09-25T16:20:00Z', updated_at: '2026-09-25T16:20:00Z' },
    ],
  },
  {
    guess_index: 590,
    guess: 'starwars1',
    entries: [
      { id: 'd590-1', service: 'github.com', username: 'todd_howard', password: 'skyrim99', created_at: '2026-09-15T08:30:00Z', updated_at: '2026-09-15T08:30:00Z' },
      { id: 'd590-2', service: 'proton.me', username: 'todd.h@proton.me', password: 'citadel#2026', created_at: '2026-09-16T09:12:00Z', updated_at: '2026-09-16T09:12:00Z' },
      { id: 'd590-3', service: 'aws.amazon.com', username: 'todd_corp', password: 'oblivion1', created_at: '2026-09-20T14:45:00Z', updated_at: '2026-09-20T14:45:00Z' },
      { id: 'd590-4', service: 'banking.swissquote.ch', username: 'thoward_vault', password: 'zermatt#77', created_at: '2026-09-22T11:05:00Z', updated_at: '2026-09-22T11:05:00Z' },
      { id: 'd590-5', service: 'discord.com', username: 'todd_rpg', password: 'starfield8', created_at: '2026-09-25T16:20:00Z', updated_at: '2026-09-25T16:20:00Z' },
    ],
  },
  {
    guess_index: 680,
    guess: 'pass1234',
    entries: [
      { id: 'd680-1', service: 'github.com', username: 'ruby_stone', password: 'garnet19', created_at: '2026-09-15T08:30:00Z', updated_at: '2026-09-15T08:30:00Z' },
      { id: 'd680-2', service: 'proton.me', username: 'ruby.s@proton.me', password: 'amethyst#5', created_at: '2026-09-16T09:12:00Z', updated_at: '2026-09-16T09:12:00Z' },
      { id: 'd680-3', service: 'aws.amazon.com', username: 'ruby_mesh', password: 'topaz882', created_at: '2026-09-20T14:45:00Z', updated_at: '2026-09-20T14:45:00Z' },
      { id: 'd680-4', service: 'banking.swissquote.ch', username: 'rstone_swiss', password: 'davos#1928', created_at: '2026-09-22T11:05:00Z', updated_at: '2026-09-22T11:05:00Z' },
      { id: 'd680-5', service: 'discord.com', username: 'ruby_live', password: 'obsidian3', created_at: '2026-09-25T16:20:00Z', updated_at: '2026-09-25T16:20:00Z' },
    ],
  },
  {
    guess_index: 775,
    guess: 'letmein2023',
    entries: [
      { id: 'd775-1', service: 'github.com', username: 'felix_k', password: 'copper88', created_at: '2026-09-15T08:30:00Z', updated_at: '2026-09-15T08:30:00Z' },
      { id: 'd775-2', service: 'proton.me', username: 'felix.k@proton.me', password: 'bronze#2024', created_at: '2026-09-16T09:12:00Z', updated_at: '2026-09-16T09:12:00Z' },
      { id: 'd775-3', service: 'aws.amazon.com', username: 'felix_ops', password: 'silver661', created_at: '2026-09-20T14:45:00Z', updated_at: '2026-09-20T14:45:00Z' },
      { id: 'd775-4', service: 'banking.swissquote.ch', username: 'fk_private', password: 'stmoritz#4', created_at: '2026-09-22T11:05:00Z', updated_at: '2026-09-22T11:05:00Z' },
      { id: 'd775-5', service: 'discord.com', username: 'felix_beat', password: 'platinum9', created_at: '2026-09-25T16:20:00Z', updated_at: '2026-09-25T16:20:00Z' },
    ],
  },
  {
    guess_index: 860,
    guess: 'hunter22',
    entries: [
      { id: 'd860-1', service: 'github.com', username: 'amber_davis', password: 'quartz12', created_at: '2026-09-15T08:30:00Z', updated_at: '2026-09-15T08:30:00Z' },
      { id: 'd860-2', service: 'proton.me', username: 'amber.d@proton.me', password: 'chalcedony#1', created_at: '2026-09-16T09:12:00Z', updated_at: '2026-09-16T09:12:00Z' },
      { id: 'd860-3', service: 'aws.amazon.com', username: 'adavis_arch', password: 'jasper77', created_at: '2026-09-20T14:45:00Z', updated_at: '2026-09-20T14:45:00Z' },
      { id: 'd860-4', service: 'banking.swissquote.ch', username: 'adavis_swiss', password: 'verbier#99', created_at: '2026-09-22T11:05:00Z', updated_at: '2026-09-22T11:05:00Z' },
      { id: 'd860-5', service: 'discord.com', username: 'amber_tune', password: 'beryl2022', created_at: '2026-09-25T16:20:00Z', updated_at: '2026-09-25T16:20:00Z' },
    ],
  },
  {
    guess_index: 940,
    guess: 'security2026',
    entries: [
      { id: 'd940-1', service: 'github.com', username: 'nicolas_v', password: 'granite9', created_at: '2026-09-15T08:30:00Z', updated_at: '2026-09-15T08:30:00Z' },
      { id: 'd940-2', service: 'proton.me', username: 'nicolas.v@proton.me', password: 'basalt#81', created_at: '2026-09-16T09:12:00Z', updated_at: '2026-09-16T09:12:00Z' },
      { id: 'd940-3', service: 'aws.amazon.com', username: 'nv_lambda', password: 'marble330', created_at: '2026-09-20T14:45:00Z', updated_at: '2026-09-20T14:45:00Z' },
      { id: 'd940-4', service: 'banking.swissquote.ch', username: 'nvogt_fin', password: 'aarau#102', created_at: '2026-09-22T11:05:00Z', updated_at: '2026-09-22T11:05:00Z' },
      { id: 'd940-5', service: 'discord.com', username: 'nicolas_dev', password: 'slate2025', created_at: '2026-09-25T16:20:00Z', updated_at: '2026-09-25T16:20:00Z' },
    ],
  },
  {
    guess_index: 999,
    guess: 'ocean10team',
    entries: [
      { id: 'd999-1', service: 'github.com', username: 'deepmind_honey', password: 'cipher77', created_at: '2026-09-15T08:30:00Z', updated_at: '2026-09-15T08:30:00Z' },
      { id: 'd999-2', service: 'proton.me', username: 'deepmind.sec@proton.me', password: 'enigma#2026', created_at: '2026-09-16T09:12:00Z', updated_at: '2026-09-16T09:12:00Z' },
      { id: 'd999-3', service: 'aws.amazon.com', username: 'oceans_k8s', password: 'kryptex99', created_at: '2026-09-20T14:45:00Z', updated_at: '2026-09-20T14:45:00Z' },
      { id: 'd999-4', service: 'banking.swissquote.ch', username: 'ocean_vault', password: 'swissbank#1', created_at: '2026-09-22T11:05:00Z', updated_at: '2026-09-22T11:05:00Z' },
      { id: 'd999-5', service: 'discord.com', username: 'oceans10_hub', password: 'finalkey2026', created_at: '2026-09-25T16:20:00Z', updated_at: '2026-09-25T16:20:00Z' },
    ],
  },
];

// Stolen sweetwords: 1 real login password + 9 honeywords per Juels & Rivest 2013
const MOCK_SWEETWORDS = [
  'Tr0ub4dor!3',
  'Tr0ub4dor&4',
  'Tr0ub4dor&9',
  'Tr0ub4d0r#2',
  'Tr0ub4dor&3', // real login password at index 4!
  'Troubador&3',
  'Tr4ub4dor&3',
  'Mat4d0r&8',
  'Gl4di4tor&2',
  'Crus4d0r&5',
];

const MOCK_SWEETWORD_HASHES = [
  '$argon2id$v=19$m=65536,t=3,p=4$ZGVtb19zYWx0XzE2Qg$e9F1a2B3c4D5e6F7a8B9c0D1e2F3a4B5',
  '$argon2id$v=19$m=65536,t=3,p=4$ZGVtb19zYWx0XzE2Qg$a8B9c0D1e2F3a4B5e9F1a2B3c4D5e6F7',
  '$argon2id$v=19$m=65536,t=3,p=4$ZGVtb19zYWx0XzE2Qg$b7C8d9E0f1A2b3C4d5E6f7A8b9C0d1E2',
  '$argon2id$v=19$m=65536,t=3,p=4$ZGVtb19zYWx0XzE2Qg$c6D7e8F9a0B1c2D3e4F5a6B7c8D9e0F1',
  '$argon2id$v=19$m=65536,t=3,p=4$ZGVtb19zYWx0XzE2Qg$d5E6f7A8b9C0d1E2f3A4b5C6d7E8f9A0',
  '$argon2id$v=19$m=65536,t=3,p=4$ZGVtb19zYWx0XzE2Qg$e4F5a6B7c8D9e0F1a2B3c4D5e6F7a8B9',
  '$argon2id$v=19$m=65536,t=3,p=4$ZGVtb19zYWx0XzE2Qg$f3A4b5C6d7E8f9A0b1C2d3E4f5A6b7C8',
  '$argon2id$v=19$m=65536,t=3,p=4$ZGVtb19zYWx0XzE2Qg$a2B3c4D5e6F7a8B9c0D1e2F3a4B5c6D7',
  '$argon2id$v=19$m=65536,t=3,p=4$ZGVtb19zYWx0XzE2Qg$b1C2d3E4f5A6b7C8d9E0f1A2b3C4d5E6',
  '$argon2id$v=19$m=65536,t=3,p=4$ZGVtb19zYWx0XzE2Qg$c0D1e2F3a4B5c6D7e8F9a0B1c2D3e4F5',
];

// Active breach alarms store
const alarmsStore: AdminAlert[] = [
  {
    id: 'alt-init-1',
    username: 'demo',
    kind: 'HONEYWORD_LOGIN',
    severity: 'critical',
    sweetword_index: 7,
    source_ip: '203.0.113.88 (External Threat Actor)',
    user_agent: 'hydra/9.5 (dictionary automated attack)',
    created_at: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
  },
];

// Listen for client-side sweetword trigger event to populate real-time alarm
if (typeof window !== 'undefined') {
  window.addEventListener('hv:honeyword_attempt', (event: Event) => {
    const customEvent = event as CustomEvent<{ index: number; sweetword: string }>;
    const { index } = customEvent.detail;
    alarmsStore.unshift({
      id: `alt-live-${String(Date.now())}`,
      username: 'demo',
      kind: 'HONEYWORD_LOGIN',
      severity: 'critical',
      sweetword_index: index,
      source_ip: '198.51.100.42 (Interactive Attacker Console)',
      user_agent: navigator.userAgent || 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
      created_at: new Date().toISOString(),
    });
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
    let maxGuesses = 1000;
    try {
      const body = (await request.json()) as DictionaryAttackRequest;
      if (typeof body.max_guesses === 'number') {
        maxGuesses = Math.max(1, Math.min(2000, body.max_guesses));
      }
    } catch {
      // fallback to 1000 if body cannot be parsed
    }

    const CRACK_TARGET_INDEX = 137;
    const isCracked = maxGuesses >= CRACK_TARGET_INDEX;

    // Filter or adjust samples to fit within maxGuesses
    const filteredSamples = MOCK_SAMPLES.filter((s) => s.guess_index < maxGuesses);
    // Always include up to 25 samples
    const samples = filteredSamples.slice(0, 25);

    const response: DictionaryAttackResponse = {
      baseline: {
        cracked: isCracked,
        guess_index: isCracked ? CRACK_TARGET_INDEX : null,
        elapsed_ms: isCracked ? 812 : Math.round(maxGuesses * 5.8),
        recovered_entries: isCracked ? REAL_RECOVERED_ENTRIES : [],
      },
      honey: {
        guesses_tried: maxGuesses,
        elapsed_ms: Math.round(maxGuesses * 6.9),
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
      salt: 'ZGVtb19ob25leXdvcmRfc2FsdF8yMDI2',
      hashes: MOCK_SWEETWORD_HASHES,
      cracked_sweetwords: MOCK_SWEETWORDS,
    });
  }),

  // GET /api/attack/alarms
  http.get('/api/attack/alarms', () => {
    return HttpResponse.json<AttackAlarmsResponse>(alarmsStore.slice(0, 20));
  }),
];
