import { apiFetch } from '../client';
import type {
  LoginRequest,
  LoginResponse,
  MeResponse,
  RegisterRequest,
  RegisterResponse,
} from '../types';

export const authApi = {
  register: (data: RegisterRequest) =>
    apiFetch<RegisterResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
      noAuth: true,
    }),

  login: (data: LoginRequest) =>
    apiFetch<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
      noAuth: true,
    }),

  me: () => apiFetch<MeResponse>('/auth/me'),
};
