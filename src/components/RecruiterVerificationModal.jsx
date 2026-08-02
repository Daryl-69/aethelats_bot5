import React, { useState, useRef, useEffect } from 'react';
import { Mail, CheckCircle2, ChevronRight, AlertCircle, ArrowLeft, Building2, Linkedin, Lock } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

/* ─────────────────────────────────────────────────────────────
   OTP Input — 6 individual digit boxes (Copied from AuthView)
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

export default function RecruiterVerificationModal({ onClose }) {
  const { user, requestRecruiterVerification, verifyRecruiterOTP } = useAuth();
  
  const [step, setStep] = useState('request'); // 'request' | 'otp'
  const [email, setEmail] = useState('');
  const [linkedin, setLinkedin] = useState('');
  const [otp, setOtp] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleRequest = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    
    // Simple validation
    if (!email || !email.includes('@')) {
      setError('Please enter a valid company email.');
      setLoading(false);
      return;
    }
    
    // Check if it's a common free email provider
    const freeProviders = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com'];
    const domain = email.split('@')[1]?.toLowerCase();
    if (freeProviders.includes(domain)) {
      setError('Please use your work/company email, not a personal one.');
      setLoading(false);
      return;
    }

    const res = await requestRecruiterVerification({ company_email: email, linkedin_url: linkedin });
    if (res.ok) {
      if (res.auto_verified) {
        if (onClose) onClose();
      } else {
        setStep('otp');
      }
    } else {
      setError('Failed to send verification code. Please try again.');
    }
    setLoading(false);
  };

  const handleVerify = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    
    const res = await verifyRecruiterOTP({ company_email: email, otp: otp.replace(/\s/g, '') });
    if (res.ok) {
      if (onClose) onClose();
    } else {
      setError('Invalid or expired code.');
    }
    setLoading(false);
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" />
      
      <div className="relative w-full max-w-md glass-card rounded-2xl border border-white/[0.08] overflow-hidden shadow-2xl animate-fade-in">
        <div className="p-8">
          {/* Header */}
          <div className="text-center mb-6">
            <div className="w-14 h-14 rounded-2xl bg-white/[0.04] border border-white/[0.08] flex items-center justify-center mx-auto mb-4">
              <Lock className="w-6 h-6 text-white/60" />
            </div>
            <h2 className="text-xl font-bold text-white mb-2">Recruiter Verification</h2>
            <p className="text-sm text-white/50">
              {step === 'request' 
                ? 'Verify your workplace to access premium features like batch processing and resume matching.' 
                : `We sent a code to ${email}`}
            </p>
          </div>

          {error && (
            <div className="mb-4 flex items-start gap-2 p-3 rounded-xl bg-red-500/[0.08] border border-red-500/20 animate-fade-in">
              <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
              <p className="text-xs text-red-300">{error}</p>
            </div>
          )}

          {step === 'request' ? (
            <form onSubmit={handleRequest} className="space-y-4">
              <div className="relative">
                <div className="absolute left-3.5 top-1/2 -translate-y-1/2 text-white/30">
                  <Mail className="w-4 h-4" />
                </div>
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="Work Email (e.g. you@company.com)"
                  required
                  className="w-full bg-white/[0.04] border border-white/[0.08] rounded-xl px-4 py-3 pl-10 text-sm text-white placeholder-white/25 focus:outline-none focus:border-white/30 focus:bg-white/[0.06] transition-all"
                />
              </div>

              <div className="relative">
                <div className="absolute left-3.5 top-1/2 -translate-y-1/2 text-white/30">
                  <Linkedin className="w-4 h-4" />
                </div>
                <input
                  type="url"
                  value={linkedin}
                  onChange={e => setLinkedin(e.target.value)}
                  placeholder="LinkedIn Profile URL (Optional)"
                  className="w-full bg-white/[0.04] border border-white/[0.08] rounded-xl px-4 py-3 pl-10 text-sm text-white placeholder-white/25 focus:outline-none focus:border-white/30 focus:bg-white/[0.06] transition-all"
                />
              </div>

              <button
                type="submit"
                disabled={loading || !email}
                className="w-full mt-2 flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-white text-black text-sm font-bold hover:bg-white/90 active:scale-[0.98] transition-all disabled:opacity-50"
              >
                {loading ? <span className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" /> : 'Send Verification Code'}
              </button>
            </form>
          ) : (
            <form onSubmit={handleVerify} className="space-y-6">
              <OTPInput value={otp} onChange={setOtp} disabled={loading} />

              <button
                type="submit"
                disabled={loading || otp.replace(/\s/g, '').length !== 6}
                className="w-full flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-white text-black text-sm font-bold hover:bg-white/90 active:scale-[0.98] transition-all disabled:opacity-50"
              >
                {loading ? <span className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" /> : 'Verify Account'}
              </button>

              <button
                type="button"
                onClick={() => setStep('request')}
                className="w-full text-xs text-white/40 hover:text-white/70 transition-colors"
              >
                Use a different email
              </button>
            </form>
          )}
          
          <div className="mt-6 pt-4 border-t border-white/[0.06] text-center">
            {onClose && (
              <button onClick={onClose} className="text-xs text-white/30 hover:text-white/60">
                Skip for now (some features will be locked)
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
