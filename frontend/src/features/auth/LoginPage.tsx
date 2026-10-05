// owner: Krrish (T3) — login page
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { toast } from 'sonner';
import { ShieldCheck, LogIn, Key, User, Eye, EyeOff, Sparkles, Loader2 } from 'lucide-react';

import { useAuth } from '@/lib/auth';
import { authApi } from '@/api/endpoints/auth';
import { ApiError } from '@/api/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { AuthIllustration } from './AuthIllustration';

const loginSchema = z.object({
  username: z
    .string()
    .min(1, 'Username is required')
    .max(32, 'Username must be at most 32 characters'),
  login_password: z
    .string()
    .min(1, 'Login password is required')
    .max(32, 'Password must be at most 32 characters'),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const state = location.state as { from?: { pathname?: string } } | null | undefined;
  const from = state?.from?.pathname ?? '/vault';

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      username: '',
      login_password: '',
    },
  });

  const onSubmit = async (values: LoginFormValues) => {
    setIsSubmitting(true);
    try {
      const res = await authApi.login({
        username: values.username.trim(),
        login_password: values.login_password,
      });

      login(res.access_token, {
        id: res.user.id,
        username: res.user.username,
        is_admin: res.user.is_admin,
        created_at: new Date().toISOString(),
        entry_count: 0,
      });

      toast.success(`Welcome back, ${res.user.username}!`, {
        description: 'Session authenticated. Ready to unlock your honey vault.',
      });

      navigate(from, { replace: true });
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        toast.error('Authentication Failed', {
          description: err.detail || 'Invalid username or password.',
        });
      } else {
        toast.error('Login Error', {
          description: 'Unable to reach the server. Please check your connection.',
        });
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const fillCredentials = (user: string, pass: string) => {
    setValue('username', user, { shouldValidate: true });
    setValue('login_password', pass, { shouldValidate: true });
    toast.info(`Filled credentials for ${user}`);
  };

  return (
    <div className="container mx-auto px-4 py-8 md:py-12 min-h-[calc(100vh-140px)] flex items-center justify-center">
      <div className="grid w-full max-w-5xl grid-cols-1 lg:grid-cols-2 gap-8 items-stretch">
        {/* Left: Login Form Card */}
        <Card className="flex flex-col justify-between border-[var(--border)] bg-[var(--bg-surface)] backdrop-blur-md shadow-2xl">
          <div>
            <CardHeader className="space-y-2 pb-4">
              <div className="flex items-center gap-2">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[var(--accent-muted)] text-[var(--accent)] border border-[var(--accent)]/30">
                  <ShieldCheck className="h-5 w-5" />
                </div>
                <CardTitle className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
                  Sign In
                </CardTitle>
              </div>
              <CardDescription className="text-sm text-[var(--text-secondary)]">
                Authenticate with your account login password to access your encrypted vault.
              </CardDescription>
            </CardHeader>

            <CardContent className="space-y-5">
              {/* Quick Fill Demo Banner */}
              <div className="rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] p-3 space-y-2 text-xs">
                <div className="flex items-center justify-between text-[var(--text-muted)] font-medium">
                  <span className="flex items-center gap-1.5 text-[var(--accent)]">
                    <Sparkles className="h-3.5 w-3.5" /> Demo Accounts
                  </span>
                  <span>Click to auto-fill</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-7 text-xs font-mono border-[var(--border)] hover:bg-[var(--bg-hover)]"
                    onClick={() => {
                      fillCredentials('demo', 'demo-login-pass');
                    }}
                  >
                    User: demo
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-7 text-xs font-mono border-[var(--border)] hover:bg-[var(--bg-hover)]"
                    onClick={() => {
                      fillCredentials('admin', 'admin-pass');
                    }}
                  >
                    Admin: admin
                  </Button>
                </div>
              </div>

              <form
                id="login-form"
                onSubmit={(e) => {
                  void handleSubmit(onSubmit)(e);
                }}
                className="space-y-4"
              >
                {/* Username */}
                <div className="space-y-2">
                  <Label htmlFor="username" className="text-xs font-medium text-[var(--text-secondary)]">
                    Username
                  </Label>
                  <div className="relative">
                    <User className="absolute left-3 top-2.5 h-4 w-4 text-[var(--text-muted)]" />
                    <Input
                      id="username"
                      type="text"
                      placeholder="e.g. demo"
                      autoComplete="username"
                      disabled={isSubmitting}
                      className="pl-9 bg-[var(--bg-elevated)] border-[var(--border)] focus-visible:ring-[var(--accent)]"
                      {...register('username')}
                    />
                  </div>
                  {errors.username && (
                    <p className="text-xs text-[var(--danger)]">{errors.username.message}</p>
                  )}
                </div>

                {/* Login Password */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label
                      htmlFor="login_password"
                      className="text-xs font-medium text-[var(--text-secondary)]"
                    >
                      Login Password
                    </Label>
                    <span className="text-[11px] text-[var(--text-muted)]">Account password</span>
                  </div>
                  <div className="relative">
                    <Key className="absolute left-3 top-2.5 h-4 w-4 text-[var(--text-muted)]" />
                    <Input
                      id="login_password"
                      type={showPassword ? 'text' : 'password'}
                      placeholder="••••••••••••"
                      autoComplete="current-password"
                      disabled={isSubmitting}
                      className="pl-9 pr-10 bg-[var(--bg-elevated)] border-[var(--border)] focus-visible:ring-[var(--accent)]"
                      {...register('login_password')}
                    />
                    <button
                      type="button"
                      tabIndex={-1}
                      onClick={() => {
                        setShowPassword(!showPassword);
                      }}
                      className="absolute right-3 top-2.5 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                  {errors.login_password && (
                    <p className="text-xs text-[var(--danger)]">{errors.login_password.message}</p>
                  )}
                </div>

                <Button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-slate-950 font-semibold shadow-md mt-2"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Authenticating...
                    </>
                  ) : (
                    <>
                      <LogIn className="mr-2 h-4 w-4" />
                      Sign In
                    </>
                  )}
                </Button>
              </form>
            </CardContent>
          </div>

          <CardFooter className="flex flex-col border-t border-[var(--border)] pt-4 text-center text-xs text-[var(--text-muted)] space-y-2">
            <p>
              Don&apos;t have a HoneyVault account yet?{' '}
              <Link
                to="/register"
                className="font-semibold text-[var(--accent)] hover:underline"
              >
                Create one now →
              </Link>
            </p>
            <p className="text-[11px] text-[var(--text-muted)]">
              Protected by Honey Encryption &amp; Honeywords breach detection.
            </p>
          </CardFooter>
        </Card>

        {/* Right: Illustration */}
        <AuthIllustration mode="login" />
      </div>
    </div>
  );
}
