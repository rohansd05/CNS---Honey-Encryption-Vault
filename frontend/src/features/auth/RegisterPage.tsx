// owner: Krrish (T3) — register page with dual-password validation & strength meter
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Link, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import {
  UserPlus,
  Key,
  Shield,
  User,
  Eye,
  EyeOff,
  AlertTriangle,
  Info,
  Loader2,
  Lock,
} from 'lucide-react';

import { useAuth } from '@/lib/auth';
import { authApi } from '@/api/endpoints/auth';
import { ApiError } from '@/api/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { PasswordStrengthMeter } from '@/components/PasswordStrengthMeter';
import { AuthIllustration } from './AuthIllustration';

// Contract validation rules:
// username: 3-32 characters, lowercase alphanumeric, underscore, dot, hyphen
// login_password: 1-32 printable ASCII chars
// master_password: 1-32 printable ASCII chars
// Invariant: login_password !== master_password
const registerSchema = z
  .object({
    username: z
      .string()
      .min(3, 'Username must be at least 3 characters')
      .max(32, 'Username cannot exceed 32 characters')
      .regex(
        /^[a-z0-9_.-]+$/,
        'Username must use lowercase letters, numbers, dots, hyphens, or underscores',
      ),
    login_password: z
      .string()
      .min(6, 'Login password must be at least 6 characters')
      .max(32, 'Login password cannot exceed 32 characters')
      .regex(/^[\x20-\x7E]+$/, 'Password must contain only printable ASCII characters'),
    confirm_login_password: z.string().min(1, 'Please confirm your login password'),
    master_password: z
      .string()
      .min(8, 'Master password should be at least 8 characters')
      .max(32, 'Master password cannot exceed 32 characters')
      .regex(/^[\x20-\x7E]+$/, 'Password must contain only printable ASCII characters'),
    confirm_master_password: z.string().min(1, 'Please confirm your master password'),
  })
  .superRefine((data, ctx) => {
    // Cryptographic Invariant: Login password !== Master password
    if (data.login_password === data.master_password && data.login_password.length > 0) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['master_password'],
        message:
          'Master password MUST be different from login password to preserve the Honey Encryption security boundary.',
      });
    }

    if (data.login_password !== data.confirm_login_password) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['confirm_login_password'],
        message: 'Login passwords do not match.',
      });
    }

    if (data.master_password !== data.confirm_master_password) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['confirm_master_password'],
        message: 'Master passwords do not match.',
      });
    }
  });

type RegisterFormValues = z.infer<typeof registerSchema>;

export function RegisterPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [showLoginPass, setShowLoginPass] = useState(false);
  const [showMasterPass, setShowMasterPass] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    mode: 'onChange',
    defaultValues: {
      username: '',
      login_password: '',
      confirm_login_password: '',
      master_password: '',
      confirm_master_password: '',
    },
  });

  const watchLoginPassword = watch('login_password');
  const watchMasterPassword = watch('master_password');

  const onSubmit = async (values: RegisterFormValues) => {
    setIsSubmitting(true);
    try {
      // 1. Call register endpoint
      await authApi.register({
        username: values.username.trim().toLowerCase(),
        login_password: values.login_password,
        master_password: values.master_password,
      });

      toast.success('Account created successfully!', {
        description: 'Logging you in automatically...',
      });

      // 2. Auto-login immediately to streamline the onboarding flow
      try {
        const loginRes = await authApi.login({
          username: values.username.trim().toLowerCase(),
          login_password: values.login_password,
        });

        login(loginRes.access_token, {
          id: loginRes.user.id,
          username: loginRes.user.username,
          is_admin: loginRes.user.is_admin,
          created_at: new Date().toISOString(),
          entry_count: 0,
        });

        navigate('/vault', { replace: true });
      } catch {
        // If auto-login fails, redirect to login page
        navigate('/login', { replace: true });
      }
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        toast.error('Registration Failed', {
          description: err.detail || 'Could not complete registration.',
        });
      } else {
        toast.error('Registration Error', {
          description: 'Network error or server unreachable. Please try again.',
        });
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 md:py-12 min-h-[calc(100vh-140px)] flex items-center justify-center">
      <div className="grid w-full max-w-5xl grid-cols-1 lg:grid-cols-2 gap-8 items-stretch">
        {/* Left: Register Form */}
        <Card className="flex flex-col justify-between border-[var(--border)] bg-[var(--bg-surface)] backdrop-blur-md shadow-2xl">
          <div>
            <CardHeader className="space-y-2 pb-4">
              <div className="flex items-center gap-2">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[var(--accent-muted)] text-[var(--accent)] border border-[var(--accent)]/30">
                  <UserPlus className="h-5 w-5" />
                </div>
                <CardTitle className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
                  Create Vault
                </CardTitle>
              </div>
              <CardDescription className="text-sm text-[var(--text-secondary)]">
                Initialize your account with separate login and honey vault master credentials.
              </CardDescription>
            </CardHeader>

            <CardContent className="space-y-4">
              {/* Dual-Password Concept Callout */}
              <Alert className="border-amber-500/30 bg-amber-500/10 text-amber-300">
                <Info className="h-4 w-4 text-amber-400" />
                <AlertTitle className="text-xs font-semibold text-amber-200">
                  Dual-Password Security Architecture
                </AlertTitle>
                <AlertDescription className="text-[11px] text-amber-200/90 leading-relaxed mt-1">
                  <strong>Login password</strong> = verifies your account at the server.
                  <br />
                  <strong>Master password</strong> = encrypts your vault locally; a typo shows a
                  decoy vault — watch your sigil!
                </AlertDescription>
              </Alert>

              <form
                id="register-form"
                onSubmit={(e) => {
                  void handleSubmit(onSubmit)(e);
                }}
                className="space-y-4"
              >
                {/* Username */}
                <div className="space-y-1.5">
                  <Label htmlFor="reg-username" className="text-xs font-medium text-[var(--text-secondary)]">
                    Username
                  </Label>
                  <div className="relative">
                    <User className="absolute left-3 top-2.5 h-4 w-4 text-[var(--text-muted)]" />
                    <Input
                      id="reg-username"
                      type="text"
                      placeholder="e.g. alice_spit"
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

                {/* Section: 1. Login Password */}
                <div className="pt-2 border-t border-[var(--border)] space-y-3">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-[var(--text-primary)]">
                    <Key className="h-3.5 w-3.5 text-[var(--text-muted)]" />
                    <span>1. Account Login Password</span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div className="space-y-1.5">
                      <Label htmlFor="reg-login-pass" className="text-[11px] text-[var(--text-secondary)]">
                        Login Password
                      </Label>
                      <div className="relative">
                        <Input
                          id="reg-login-pass"
                          type={showLoginPass ? 'text' : 'password'}
                          placeholder="••••••••••••"
                          autoComplete="new-password"
                          disabled={isSubmitting}
                          className="pr-9 bg-[var(--bg-elevated)] border-[var(--border)] focus-visible:ring-[var(--accent)]"
                          {...register('login_password')}
                        />
                        <button
                          type="button"
                          tabIndex={-1}
                          onClick={() => {
                            setShowLoginPass(!showLoginPass);
                          }}
                          className="absolute right-2.5 top-2.5 text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                          aria-label={showLoginPass ? 'Hide password' : 'Show password'}
                        >
                          {showLoginPass ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                        </button>
                      </div>
                      {errors.login_password && (
                        <p className="text-[11px] text-[var(--danger)]">
                          {errors.login_password.message}
                        </p>
                      )}
                    </div>

                    <div className="space-y-1.5">
                      <Label htmlFor="reg-confirm-login" className="text-[11px] text-[var(--text-secondary)]">
                        Confirm Login Password
                      </Label>
                      <Input
                        id="reg-confirm-login"
                        type={showLoginPass ? 'text' : 'password'}
                        placeholder="••••••••••••"
                        autoComplete="new-password"
                        disabled={isSubmitting}
                        className="bg-[var(--bg-elevated)] border-[var(--border)] focus-visible:ring-[var(--accent)]"
                        {...register('confirm_login_password')}
                      />
                      {errors.confirm_login_password && (
                        <p className="text-[11px] text-[var(--danger)]">
                          {errors.confirm_login_password.message}
                        </p>
                      )}
                    </div>
                  </div>

                  {watchLoginPassword && (
                    <PasswordStrengthMeter password={watchLoginPassword} showFeedback={false} />
                  )}
                </div>

                {/* Section: 2. Master Password */}
                <div className="pt-2 border-t border-[var(--border)] space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5 text-xs font-semibold text-[var(--accent)]">
                      <Shield className="h-3.5 w-3.5" />
                      <span>2. Vault Master Password (Encryption Key)</span>
                    </div>
                    <span className="text-[11px] font-mono text-[var(--text-muted)]">Argon2id KDF</span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div className="space-y-1.5">
                      <Label htmlFor="reg-master-pass" className="text-[11px] text-[var(--text-secondary)]">
                        Master Password
                      </Label>
                      <div className="relative">
                        <Input
                          id="reg-master-pass"
                          type={showMasterPass ? 'text' : 'password'}
                          placeholder="••••••••••••"
                          autoComplete="new-password"
                          disabled={isSubmitting}
                          className="pr-9 bg-[var(--bg-elevated)] border-[var(--border)] focus-visible:ring-[var(--accent)]"
                          {...register('master_password')}
                        />
                        <button
                          type="button"
                          tabIndex={-1}
                          onClick={() => {
                            setShowMasterPass(!showMasterPass);
                          }}
                          className="absolute right-2.5 top-2.5 text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                          aria-label={showMasterPass ? 'Hide password' : 'Show password'}
                        >
                          {showMasterPass ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                        </button>
                      </div>
                      {errors.master_password && (
                        <p className="text-[11px] text-[var(--danger)] leading-tight">
                          {errors.master_password.message}
                        </p>
                      )}
                    </div>

                    <div className="space-y-1.5">
                      <Label htmlFor="reg-confirm-master" className="text-[11px] text-[var(--text-secondary)]">
                        Confirm Master Password
                      </Label>
                      <Input
                        id="reg-confirm-master"
                        type={showMasterPass ? 'text' : 'password'}
                        placeholder="••••••••••••"
                        autoComplete="new-password"
                        disabled={isSubmitting}
                        className="bg-[var(--bg-elevated)] border-[var(--border)] focus-visible:ring-[var(--accent)]"
                        {...register('confirm_master_password')}
                      />
                      {errors.confirm_master_password && (
                        <p className="text-[11px] text-[var(--danger)]">
                          {errors.confirm_master_password.message}
                        </p>
                      )}
                    </div>
                  </div>

                  {watchMasterPassword && (
                    <PasswordStrengthMeter password={watchMasterPassword} showFeedback={true} />
                  )}

                  {/* Warning if login == master */}
                  {watchLoginPassword &&
                    watchMasterPassword &&
                    watchLoginPassword === watchMasterPassword && (
                      <div className="flex items-center gap-2 rounded-md bg-red-500/15 border border-red-500/30 p-2 text-[11px] text-red-300">
                        <AlertTriangle className="h-4 w-4 shrink-0 text-red-400" />
                        <span>
                          Login password and master password cannot match. If an attacker cracks
                          your login hash, they must not gain your master key.
                        </span>
                      </div>
                    )}
                </div>

                <Button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-slate-950 font-semibold shadow-md mt-4"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Generating Key &amp; Vault...
                    </>
                  ) : (
                    <>
                      <Lock className="mr-2 h-4 w-4" />
                      Register &amp; Initialize Vault
                    </>
                  )}
                </Button>
              </form>
            </CardContent>
          </div>

          <CardFooter className="flex flex-col border-t border-[var(--border)] pt-4 text-center text-xs text-[var(--text-muted)] space-y-2">
            <p>
              Already have an account?{' '}
              <Link to="/login" className="font-semibold text-[var(--accent)] hover:underline">
                Sign in here →
              </Link>
            </p>
            <p className="text-[11px] text-[var(--text-muted)]">
              Your master key is never stored on the server or in browser storage.
            </p>
          </CardFooter>
        </Card>

        {/* Right: Illustration */}
        <AuthIllustration mode="register" />
      </div>
    </div>
  );
}
