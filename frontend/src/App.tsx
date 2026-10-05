// owner: Krrish (T3) — app root
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';
import { ThemeProvider } from '@/lib/theme';
import { AuthProvider, ProtectedRoute, AdminRoute } from '@/lib/auth';
import { AppShell } from '@/components/layout/AppShell';

// Pages — Krrish owns
import { LoginPage } from '@/features/auth/LoginPage';
import { RegisterPage } from '@/features/auth/RegisterPage';
import { VaultPage } from '@/features/vault/VaultPage';
import { SharePage } from '@/features/share/SharePage';
import { NotFoundPage } from '@/features/NotFoundPage';

// Pages — Chetan owns
import { LandingPage } from '@/features/landing/LandingPage';
import { AttackLabPage } from '@/features/attack/AttackLabPage';
import { EvaluationPage } from '@/features/evaluation/EvaluationPage';
import { AdminPage } from '@/features/admin/AdminPage';
import { AboutPage } from '@/features/about/AboutPage';

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
