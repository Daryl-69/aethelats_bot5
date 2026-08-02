import React, { useState, useRef, useEffect } from 'react';
import {
  Mail, Lock, User, Building2, ChevronRight, Eye, EyeOff,
  AlertCircle, Zap, Shield, GitBranch, RefreshCw, CheckCircle2,
  ArrowLeft
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

/* ─────────────────────────────────────────────────────────────
   Reusable input field
───────────────────────────────────────────────────────────── */
function AuthInput({ id, label, type = 'text', value, onChange, icon: Icon, autoComplete, required, disabled }) {
  const [showPw, setShowPw] = useState(false);
  const isPassword = type === 'password';
  const inputType  = isPassword ? (showPw ? 'text' : 'password') : type;

  return (
    <div className="relative">
      <div className="absolute left-3.5 top-1/2 -translate-y-1/2 text-white/30 pointer-events-none">
        <Icon className="w-4 h-4" />
      </div>
      <input
        id={id}
        type={inputType}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={label}
        autoComplete={autoComplete}
        required={required}
        disabled={disabled}
        className="w-full bg-white/[0.04] border border-white/[0.08] rounded-xl px-4 py-3 pl-10 text-sm text-white
          placeholder-white/25 focus:outline-none focus:border-white/30 focus:bg-white/[0.06]
          transition-all duration-200 disabled:opacity-40"
      />
      {isPassword && (
        <button type="button" onClick={() => setShowPw(v => !v)} tabIndex={-1}
          className="absolute right-3.5 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/60 transition-colors">
          {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
        </button>
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────
   Role selector
───────────────────────────────────────────────────────────── */
function RoleSelector({ value, onChange }) {
  return (
    <div className="grid grid-cols-2 gap-2">
      {[
        { key: 'recruiter', label: 'Recruiter / HR',   desc: 'Screen and evaluate candidates' },
        { key: 'candidate', label: 'Candidate',         desc: 'Improve and share your resume' },
      ].map(r => (
        <button key={r.key} type="button" onClick={() => onChange(r.key)}
          className={`p-3 rounded-xl border text-left transition-all ${
            value === r.key
              ? 'border-white/30 bg-white/[0.08]'
              : 'border-white/[0.06] bg-white/[0.02] hover:border-white/15 hover:bg-white/[0.04]'
          }`}>
          <div className="text-xs font-bold text-white mb-0.5">{r.label}</div>
          <div className="text-[10px] text-white/40">{r.desc}</div>
        </button>
      ))}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────
   Error banner
───────────────────────────────────────────────────────────── */
function ErrorBanner({ message }) {
  if (!message) return null;
  return (
    <div className="flex items-start gap-2 p-3 rounded-xl bg-red-500/[0.08] border border-red-500/20 animate-fade-in">
      <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
      <p className="text-xs text-red-300">{message}</p>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────
   OTP Input — 6 individual digit boxes
───────────────────────────────────────────────────────────── */
function OTPInput({ value, onChange, disabled }) {
  const digits  = (value + '      ').slice(0, 6).split('');
  const refs    = Array.from({ length: 6 }, () => useRef(null));

  const handleKey = (i, e) => {
    if (e.key === 'Backspace') {
      const next = [...digits];
      if (next[i] && next[i].trim()) {
        next[i] = '';
      } else if (i > 0) {
        next[i - 1] = '';
        refs[i - 1].current?.focus();
      }
      onChange(next.join('').trimEnd());
      return;
    }
    if (!/^\d$/.test(e.key)) return;
    const next = [...digits];
    next[i] = e.key;
    onChange(next.join('').trimEnd());
    if (i < 5) refs[i + 1].current?.focus();
  };

  const handlePaste = e => {
    e.preventDefault();
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    onChange(pasted);
    const focusIdx = Math.min(pasted.length, 5);
    refs[focusIdx].current?.focus();
  };

  return (
    <div className="flex gap-2 justify-center">
      {Array.from({ length: 6 }).map((_, i) => (
        <input
          key={i}
          ref={refs[i]}
          type="text"
          inputMode="numeric"
          maxLength={1}
          value={digits[i]?.trim() || ''}
          onChange={() => {}}
          onKeyDown={e => handleKey(i, e)}
          onPaste={handlePaste}
          disabled={disabled}
          className={`w-11 h-14 text-center text-xl font-black text-white rounded-xl border
            bg-white/[0.04] focus:outline-none focus:bg-white/[0.07] transition-all
            caret-transparent select-none disabled:opacity-40
            ${digits[i]?.trim() ? 'border-white/40' : 'border-white/[0.10] focus:border-white/35'}`}
        />
      ))}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────
   Step 3 — OTP Verification screen
───────────────────────────────────────────────────────────── */
function OTPScreen({ email, onBack, onSuccess }) {
  const { verifyOtp, resendOtp, loading, authError, clearAuthError } = useAuth();
  const [otp, setOtp]           = useState('');
  const [resent, setResent]     = useState(false);
  const [countdown, setCountdown] = useState(30);

  // Countdown timer for resend button
  useEffect(() => {
    if (countdown <= 0) return;
    const t = setInterval(() => setCountdown(c => c - 1), 1000);
    return () => clearInterval(t);
  }, [countdown]);

  const handleSubmit = async e => {
    e.preventDefault();
    clearAuthError();
    const result = await verifyOtp({ email, otp: otp.replace(/\s/g, '') });
    if (result.ok) onSuccess();
  };

  const handleResend = async () => {
    clearAuthError();
    const result = await resendOtp(email);
    if (result.ok) {
      setResent(true);
      setOtp('');
      setCountdown(30);
      setTimeout(() => setResent(false), 3000);
    }
  };

  const isComplete = otp.replace(/\s/g, '').length === 6;

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Header */}
      <div className="text-center">
        <div className="w-14 h-14 rounded-2xl bg-white/[0.04] border border-white/[0.08] flex items-center justify-center mx-auto mb-4">
          <Mail className="w-6 h-6 text-white/60" />
        </div>
        <h2 className="text-lg font-bold text-white mb-1">Check your inbox</h2>
        <p className="text-xs text-white/40 leading-relaxed">
          We emailed a 6-digit code to<br />
          <span className="text-white/70 font-medium">{email}</span>
        </p>
      </div>

      {/* OTP boxes */}
      <OTPInput value={otp} onChange={setOtp} disabled={loading} />

      <ErrorBanner message={authError} />

      {resent && (
        <div className="flex items-center justify-center gap-2 text-xs text-emerald-400 animate-fade-in">
          <CheckCircle2 className="w-3.5 h-3.5" /> New code sent!
        </div>
      )}

      {/* Verify button */}
      <button
        type="submit"
        disabled={!isComplete || loading}
        id="auth-verify-otp-btn"
        className="w-full flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-white text-black
          text-sm font-bold hover:bg-white/90 active:scale-[0.98] transition-all
          disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {loading
          ? <><span className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" /> Verifying…</>
          : <><ChevronRight className="w-4 h-4" /> Verify & Sign In</>
        }
      </button>

      {/* Resend + back */}
      <div className="flex items-center justify-between text-xs">
        <button type="button" onClick={onBack}
          className="flex items-center gap-1.5 text-white/30 hover:text-white/60 transition-colors">
          <ArrowLeft className="w-3.5 h-3.5" /> Back
        </button>
        <button type="button" onClick={handleResend}
          disabled={countdown > 0 || loading}
          className="flex items-center gap-1.5 text-white/40 hover:text-white/70 transition-colors disabled:opacity-40 disabled:cursor-not-allowed">
          <RefreshCw className="w-3 h-3" />
          {countdown > 0 ? `Resend in ${countdown}s` : 'Resend code'}
        </button>
      </div>

      <p className="text-[10px] text-white/20 text-center">
        Code expires in 10 minutes. Check spam if you don't see it.
      </p>
    </form>
  );
}

/* ─────────────────────────────────────────────────────────────
   Login form
───────────────────────────────────────────────────────────── */
function LoginForm({ onSwitch }) {
  const { login, loading, authError, clearAuthError } = useAuth();
  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = async e => {
    e.preventDefault();
    clearAuthError();
    await login({ email, password });
    // AuthContext sets user on success — App rerenders automatically
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <AuthInput id="login-email"    label="Email address"  type="email"    value={email}    onChange={setEmail}    icon={Mail} autoComplete="email"            required />
      <AuthInput id="login-password" label="Password"       type="password" value={password} onChange={setPassword} icon={Lock} autoComplete="current-password" required />

      <ErrorBanner message={authError} />

      <button type="submit" disabled={loading} id="auth-login-btn"
        className="w-full flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-white text-black
          text-sm font-bold hover:bg-white/90 active:scale-[0.98] transition-all disabled:opacity-50 disabled:cursor-wait">
        {loading
          ? <><span className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" /> Signing in…</>
          : <><ChevronRight className="w-4 h-4" /> Sign In</>
        }
      </button>

      <p className="text-center text-xs text-white/30">
        No account?{' '}
        <button type="button" onClick={onSwitch} className="text-white/70 hover:text-white underline underline-offset-2 transition-colors">
          Create one free
        </button>
      </p>
    </form>
  );
}

/* ─────────────────────────────────────────────────────────────
   Register form
───────────────────────────────────────────────────────────── */
function RegisterForm({ onSwitch, onOTPRequired }) {
  const { register, loading, authError, clearAuthError } = useAuth();
  const [name, setName]         = useState('');
  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');
  const [org, setOrg]           = useState('');
  const [role, setRole]         = useState('recruiter');

  const handleSubmit = async e => {
    e.preventDefault();
    clearAuthError();
    const result = await register({ name, email, password, role, org: org || undefined });
    if (result.ok && result.loggedIn) {
      // SKIP_EMAIL_VERIFY: already logged in — nothing to do, App rerenders automatically
    } else if (result.ok && result.pendingEmail) {
      onOTPRequired(result.pendingEmail);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <AuthInput id="reg-name"     label="Full name"                value={name}     onChange={setName}     icon={User}      autoComplete="name"         required />
      <AuthInput id="reg-email"    label="Work email"  type="email" value={email}    onChange={setEmail}    icon={Mail}      autoComplete="email"         required />
      <AuthInput id="reg-password" label="Password (min. 6 chars)"  type="password"
        value={password} onChange={setPassword} icon={Lock} autoComplete="new-password" required />
      <AuthInput id="reg-org"      label="Organisation (optional)"  value={org}      onChange={setOrg}      icon={Building2} autoComplete="organization"          />

      <div>
        <div className="text-[10px] font-bold uppercase tracking-widest text-white/30 mb-2">I am a…</div>
        <RoleSelector value={role} onChange={setRole} />
      </div>

      <ErrorBanner message={authError} />

      <button type="submit" disabled={loading} id="auth-register-btn"
        className="w-full flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-white text-black
          text-sm font-bold hover:bg-white/90 active:scale-[0.98] transition-all disabled:opacity-50 disabled:cursor-wait">
        {loading
          ? <><span className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" /> Creating account…</>
          : <><Zap className="w-4 h-4" /> Create Free Account</>
        }
      </button>

      <p className="text-center text-xs text-white/30">
        Already have an account?{' '}
        <button type="button" onClick={onSwitch} className="text-white/70 hover:text-white underline underline-offset-2 transition-colors">
          Sign in
        </button>
      </p>
    </form>
  );
}

/* ─────────────────────────────────────────────────────────────
   Left branding panel
───────────────────────────────────────────────────────────── */
function BrandPanel() {
  const features = [
    { icon: <Shield className="w-3.5 h-3.5" />,    text: 'Bias-free resume scoring' },
    { icon: <GitBranch className="w-3.5 h-3.5" />, text: 'Counterfactual bias tests' },
    { icon: <Zap className="w-3.5 h-3.5" />,       text: 'JD bias detector' },
    { icon: <Lock className="w-3.5 h-3.5" />,      text: 'PII stripped before scoring' },
  ];

  return (
    <div className="hidden lg:flex flex-col justify-center p-10 border border-white/[0.06] border-r-0
      rounded-l-2xl bg-white/[0.02] backdrop-blur-sm">
      <div className="flex items-center gap-3 mb-8">
        <img src="/assets/shield_logo.png" alt="Aethel"
          style={{ width: 40, height: 40, objectFit: 'contain', filter: 'drop-shadow(0 2px 8px rgba(255,255,255,0.2))' }} />
        <div>
          <div className="text-xl font-black text-white tracking-tight">Aethel</div>
          <div className="text-[9px] font-bold uppercase tracking-[0.25em] text-white/40">Precision Recruitment</div>
        </div>
      </div>

      <h1 className="text-3xl font-black text-white leading-tight mb-3">
        Hire on skills.<br /><span className="text-white/50">Not on bias.</span>
      </h1>
      <p className="text-sm text-white/40 leading-relaxed mb-8">
        India's first bias-aware ATS. Strips IIT/NIT prestige, name-caste signals,
        and career gap penalties before scoring.
      </p>

      <div className="space-y-3 mb-10">
        {features.map((f, i) => (
          <div key={i} className="flex items-center gap-3 text-sm text-white/50">
            <div className="w-6 h-6 rounded-lg bg-white/[0.04] border border-white/[0.06] flex items-center justify-center text-white/40">
              {f.icon}
            </div>
            {f.text}
          </div>
        ))}
      </div>

      <div className="pt-6 border-t border-white/[0.05] flex flex-wrap gap-2">
        {['₹0 always', 'No data stored', 'Open source model'].map(t => (
          <span key={t} className="text-[10px] px-2 py-1 rounded-full border border-white/[0.06] text-white/30">{t}</span>
        ))}
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────
   Main AuthView — manages tab + OTP step state
───────────────────────────────────────────────────────────── */
/* ─────────────────────────────────────────────────────────────
   Main AuthView — manages tab + OTP step state
   isModal: when true, skips the full-screen bg wrapper
   (the AuthModal overlay in App.jsx provides the backdrop)
───────────────────────────────────────────────────────────── */
export default function AuthView({ isModal = false }) {
  const [tab, setTab]                   = useState('login');
  const [pendingEmail, setPendingEmail] = useState('');
  const { clearAuthError }              = useAuth();

  const switchTab = next => { clearAuthError(); setTab(next); };
  const handleOTPRequired = email => { setPendingEmail(email); setTab('otp'); };

  /* ── Inner card (shared between modal and standalone) ── */
  const cardContent = (
    <div className="w-full max-w-4xl grid grid-cols-1 lg:grid-cols-2 gap-0">
      {/* Left branding panel — hidden on mobile */}
      <BrandPanel />

      {/* Right form card */}
      <div className="glass-card rounded-2xl lg:rounded-l-none lg:rounded-r-2xl p-8 lg:p-10 border border-white/[0.08]">
        {/* Mobile logo (shown only when BrandPanel is hidden) */}
        <div className="flex lg:hidden items-center gap-2 mb-6">
          <img src="/assets/shield_logo.png" alt="Aethel"
            style={{ width: 32, height: 32, objectFit: 'contain' }} />
          <span className="text-lg font-black text-white">Aethel</span>
        </div>

        {/* OTP verification step */}
        {tab === 'otp' && (
          <OTPScreen
            email={pendingEmail}
            onBack={() => switchTab('register')}
            onSuccess={() => { /* AuthContext sets user → App auto-rerenders */ }}
          />
        )}

        {/* Login / Register tabs */}
        {tab !== 'otp' && (
          <>
            <div className="flex gap-1 p-1 rounded-xl bg-white/[0.04] border border-white/[0.06] mb-7">
              {[['login', 'Sign In'], ['register', 'Create Account']].map(([key, label]) => (
                <button key={key} onClick={() => switchTab(key)}
                  className={`flex-1 py-2 rounded-lg text-xs font-bold transition-all ${
                    tab === key ? 'bg-white text-black shadow-sm' : 'text-white/60 hover:text-white/90'
                  }`}>
                  {label}
                </button>
              ))}
            </div>

            <div className="mb-5">
              <h2 className="text-lg font-bold text-white mb-1">
                {tab === 'login' ? 'Welcome back' : 'Get started free'}
              </h2>
              <p className="text-xs text-white/40">
                {tab === 'login'
                  ? 'Sign in to your Aethel workspace.'
                  : 'Create your account in under 30 seconds.'}
              </p>
            </div>

            <div className="animate-fade-in" key={tab}>
              {tab === 'login'
                ? <LoginForm onSwitch={() => switchTab('register')} />
                : <RegisterForm onSwitch={() => switchTab('login')} onOTPRequired={handleOTPRequired} />
              }
            </div>
          </>
        )}
      </div>
    </div>
  );

  /* ── Modal mode: no full-screen wrapper (App.jsx provides overlay) ── */
  if (isModal) {
    return <div className="w-full">{cardContent}</div>;
  }

  /* ── Standalone mode: full-screen centered page ── */
  return (
    <div className="min-h-screen bg-black flex items-center justify-center p-4 relative overflow-hidden">
      <div className="fixed inset-0 pointer-events-none"
        style={{ background: 'radial-gradient(ellipse at 50% 0%, rgba(255,255,255,0.04) 0%, transparent 60%)' }} />
      <div className="bg-grid-pattern fixed z-0" />
      <div className="relative z-10 w-full flex justify-center">
        {cardContent}
      </div>
    </div>
  );
}

