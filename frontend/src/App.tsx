// owner: Krrish (T3) — app root
import React, { Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';
import { ThemeProvider } from '@/lib/theme';
import { AuthProvider, ProtectedRoute, AdminRoute } from '@/lib/auth';
import { AppShell } from '@/components/layout/AppShell';

// Pages — Krrish owns
const LoginPage = React.lazy(() => import('@/features/auth/LoginPage').then(m => ({ default: m.LoginPage })));
const RegisterPage = React.lazy(() => import('@/features/auth/RegisterPage').then(m => ({ default: m.RegisterPage })));
const VaultPage = React.lazy(() => import('@/features/vault/VaultPage').then(m => ({ default: m.VaultPage })));
const SharePage = React.lazy(() => import('@/features/share/SharePage').then(m => ({ default: m.SharePage })));
const NotFoundPage = React.lazy(() => import('@/features/NotFoundPage').then(m => ({ default: m.NotFoundPage })));

// Pages — Chetan owns
const LandingPage = React.lazy(() => import('@/features/landing/LandingPage').then(m => ({ default: m.LandingPage })));
const AttackLabPage = React.lazy(() => import('@/features/attack/AttackLabPage').then(m => ({ default: m.AttackLabPage })));
const EvaluationPage = React.lazy(() => import('@/features/evaluation/EvaluationPage').then(m => ({ default: m.EvaluationPage })));
const AdminPage = React.lazy(() => import('@/features/admin/AdminPage').then(m => ({ default: m.AdminPage })));
const AboutPage = React.lazy(() => import('@/features/about/AboutPage').then(m => ({ default: m.AboutPage })));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000 },
  },
});

export default function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <BrowserRouter>
            <Suspense fallback={<div className="flex h-screen items-center justify-center text-text-muted">Loading...</div>}>
              <Routes>
                <Route element={<AppShell />}>
                  <Route path="/" element={<LandingPage />} />
                  <Route path="/login" element={<LoginPage />} />
                  <Route path="/register" element={<RegisterPage />} />
                  <Route
                    path="/vault"
                    element={
                      <ProtectedRoute>
                        <VaultPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/share"
                    element={
                      <ProtectedRoute>
                        <SharePage />
                      </ProtectedRoute>
                    }
                  />
                  <Route path="/attack" element={<AttackLabPage />} />
                  <Route path="/evaluation" element={<EvaluationPage />} />
                  <Route
                    path="/admin"
                    element={
                      <AdminRoute>
                        <AdminPage />
                      </AdminRoute>
                    }
                  />
                  <Route path="/about" element={<AboutPage />} />
                  <Route path="*" element={<NotFoundPage />} />
                </Route>
              </Routes>
            </Suspense>
          </BrowserRouter>
          <Toaster
            position="bottom-right"
            toastOptions={{
              style: {
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border)',
                color: 'var(--text-primary)',
              },
            }}
          />
        </AuthProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
