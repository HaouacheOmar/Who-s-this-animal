import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { CheckCircle2, MailCheck } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { api, ApiError } from '@/lib/api'
import { useAuth } from '@/lib/auth'

export function Field({ label, error, ...input }: { label: string; error?: string } & React.ComponentProps<'input'>) {
  const id = input.name
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      <Input id={id} aria-invalid={!!error} aria-describedby={error ? `${id}-err` : undefined} className="h-11" {...input} />
      {error && <p id={`${id}-err`} className="text-sm text-destructive">{error}</p>}
    </div>
  )
}

function AuthCard({ title, description, children }: { title: string; description?: ReactNode; children: ReactNode }) {
  return (
    <Card className="shadow-lg shadow-primary/5">
      <CardHeader>
        <CardTitle className="font-heading text-2xl">{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  )
}

/** Shared submit handling: native validation first, then server field errors (IMPLEMENTATION.md §3.3). */
function useSubmit<T>(fn: (data: Record<string, string>) => Promise<T>) {
  const [errors, setErrors] = useState<ApiError | null>(null)
  const [busy, setBusy] = useState(false)
  const onSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setBusy(true)
    setErrors(null)
    try {
      await fn(Object.fromEntries(new FormData(e.currentTarget)) as Record<string, string>)
    } catch (err) {
      if (err instanceof ApiError) setErrors(err)
      else toast.error('Network error, try again.')
    } finally {
      setBusy(false)
    }
  }
  return { onSubmit, errors, busy }
}

function ResendVerification({ email }: { email?: string }) {
  const resend = async () => {
    const value = email ?? prompt('Your email')
    if (!value) return
    await api('/auth/resend-verification/', { body: { email: value } })
    toast.success('If an unverified account exists, we sent a new link.')
  }
  return <Button type="button" variant="outline" className="w-full" onClick={resend}>Resend email</Button>
}

export function Signup() {
  const [sentTo, setSentTo] = useState<string>()
  const { onSubmit, errors, busy } = useSubmit(async (d) => {
    await api('/auth/register/', { body: d })
    setSentTo(d.email)
  })
  if (sentTo)
    return (
      <AuthCard title="Check your inbox" description={<>We sent a verification link to <b>{sentTo}</b>.</>}>
        <div className="space-y-4">
          <MailCheck className="mx-auto size-12 text-accent" />
          <ResendVerification email={sentTo} />
        </div>
      </AuthCard>
    )
  return (
    <AuthCard title="Create your account" description="Start your pet's care plan in a minute.">
      <form onSubmit={onSubmit} className="space-y-4">
        <Field label="Email" name="email" type="email" autoComplete="email" required error={errors?.field('email')} />
        <Field label="Password" name="password" type="password" autoComplete="new-password" minLength={8} required
               error={errors?.field('password')} />
        <Field label="Confirm password" name="password_confirm" type="password" autoComplete="new-password" required
               error={errors?.field('password_confirm')} />
        <Button className="h-11 w-full" disabled={busy}>Sign up</Button>
        <p className="text-center text-sm text-muted-foreground">
          Already have an account? <Link to="/login" className="font-medium text-primary underline-offset-4 hover:underline">Log in</Link>
        </p>
      </form>
    </AuthCard>
  )
}

export function Login() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const from = (useLocation().state as { from?: string } | null)?.from ?? '/app'
  const [email, setEmail] = useState('')
  useEffect(() => {
    if (user) navigate(from, { replace: true }) // PRD S3 2c
  }, [user, from, navigate])

  const { onSubmit, errors, busy } = useSubmit((d) => login(d.email, d.password))
  const unverified = errors?.data?.code === 'email_not_verified'
  return (
    <AuthCard title="Welcome back" description="Log in to your pet workspace.">
      <form onSubmit={onSubmit} className="space-y-4">
        <Field label="Email" name="email" type="email" autoComplete="email" required value={email}
               onChange={(e) => setEmail(e.target.value)} />
        <Field label="Password" name="password" type="password" autoComplete="current-password" required />
        {errors && <p role="alert" className="text-sm text-destructive">{errors.message}</p>}
        {unverified && <ResendVerification email={email} />}
        <Button className="h-11 w-full" disabled={busy}>Log in</Button>
        <div className="flex justify-between text-sm">
          <Link to="/forgot-password" className="text-muted-foreground hover:text-foreground">Forgot password?</Link>
          <Link to="/signup" className="font-medium text-primary hover:underline">Create account</Link>
        </div>
      </form>
    </AuthCard>
  )
}

export function VerifyEmail() {
  const { uid, token } = useParams()
  const [state, setState] = useState<'loading' | 'verified' | 'already_verified' | 'invalid'>('loading')
  const sent = useRef(false)
  useEffect(() => {
    if (sent.current) return // StrictMode runs effects twice; the 2nd call would report "already verified"
    sent.current = true
    api<{ detail: string }>('/auth/verify-email/', { body: { uid, token } })
      .then((r) => setState(r.detail as 'verified' | 'already_verified'), () => setState('invalid'))
  }, [uid, token])

  if (state === 'loading') return <AuthCard title="Verifying…">{null}</AuthCard>
  if (state === 'invalid')
    return (
      <AuthCard title="Link invalid or expired" description="Verification links last 24 hours. Get a new one below.">
        <ResendVerification />
      </AuthCard>
    )
  return (
    <AuthCard title={state === 'verified' ? 'Email verified' : 'Your email is already verified'}>
      <div className="space-y-4">
        <CheckCircle2 className="mx-auto size-12 text-accent" />
        <Button asChild className="h-11 w-full"><Link to="/login">Log in</Link></Button>
      </div>
    </AuthCard>
  )
}

export function ForgotPassword() {
  const [sent, setSent] = useState(false)
  const { onSubmit, busy } = useSubmit(async (d) => {
    await api('/auth/password-reset/', { body: d })
    setSent(true)
  })
  return (
    <AuthCard title="Forgot password" description="We'll email you a link to set a new one.">
      {sent ? (
        <p className="text-sm">If an account exists, we sent a reset link. Check your inbox.</p>
      ) : (
        <form onSubmit={onSubmit} className="space-y-4">
          <Field label="Email" name="email" type="email" autoComplete="email" required />
          <Button className="h-11 w-full" disabled={busy}>Send reset link</Button>
        </form>
      )}
      <Link to="/login" className="mt-4 block text-center text-sm text-muted-foreground hover:text-foreground">Back to log in</Link>
    </AuthCard>
  )
}

export function ResetPassword() {
  const { uid, token } = useParams()
  const navigate = useNavigate()
  const { onSubmit, errors, busy } = useSubmit(async (d) => {
    await api('/auth/password-reset/confirm/', { body: { ...d, uid, token } })
    toast.success('Password changed. Log in with your new password.')
    navigate('/login')
  })
  const invalid = errors?.status === 400 && !errors.field('password') && !errors.field('password_confirm')
  return (
    <AuthCard title="Set a new password">
      <form onSubmit={onSubmit} className="space-y-4">
        <Field label="New password" name="password" type="password" autoComplete="new-password" minLength={8} required
               error={errors?.field('password')} />
        <Field label="Confirm password" name="password_confirm" type="password" autoComplete="new-password" required
               error={errors?.field('password_confirm')} />
        {invalid && (
          <p role="alert" className="text-sm text-destructive">
            {errors.message} <Link to="/forgot-password" className="underline">Request a new link</Link>
          </p>
        )}
        <Button className="h-11 w-full" disabled={busy}>Change password</Button>
      </form>
    </AuthCard>
  )
}
