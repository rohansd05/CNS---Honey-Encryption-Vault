// owner: Krrish (T3) — root MSW handlers
import { authHandlers } from './auth';
import { vaultHandlers } from './vault';
import { usersHandlers } from './users';
import { sharesHandlers } from './shares';
import { adminHandlers } from './admin';
import { attackHandlers } from './attack';
import { evalHandlers } from './eval';

export const handlers = [
  ...authHandlers,
  ...vaultHandlers,
  ...usersHandlers,
  ...sharesHandlers,
  ...adminHandlers,
  ...attackHandlers,
  ...evalHandlers,
];
