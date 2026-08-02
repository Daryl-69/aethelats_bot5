import React, { Component, useState, useEffect, Suspense, lazy } from 'react';
import {
  AlertTriangle, AlertCircle, Shield, Users, Activity, BarChart2,
  RefreshCw, XCircle, Play, Bell, HelpCircle, Layers,
  FileText, Clock, Menu, X, LogOut, ChevronRight
} from 'lucide-react';
import { useAppState } from './components/AppLogic';
import { NavItem, FairnessGateModal, getLogColor, LogIcon } from './components/UIHelpers';
import MagneticLensCursor from './components/MagneticLensCursor';
import NeuralWireframe from './components/NeuralWireframe';
import CircuitLoader from './components/CircuitLoader';
import HorseLoader from './components/HorseLoader';
import { useAuth } from './context/AuthContext';

// ── Eager imports (always visible/critical path) ──
import LandingView from './components/LandingView';

// ── Helper to handle Vite chunk load errors gracefully ──
// If a user has a stale session and tries to load a view that was updated,
// Vite will throw a chunk load error. This forces a single reload to get fresh assets.
const lazyWithRetry = (componentImport) =>
  lazy(async () => {
    const pageHasAlreadyBeenForceRefreshed = JSON.parse(
      window.sessionStorage.getItem('page-has-been-force-refreshed') || 'false'
    );
    try {
      const component = await componentImport();
      window.sessionStorage.setItem('page-has-been-force-refreshed', 'false');
      return component;
    } catch (error) {
      if (!pageHasAlreadyBeenForceRefreshed) {
        window.sessionStorage.setItem('page-has-been-force-refreshed', 'true');
        window.location.reload();
        // Return a promise that never resolves while the page reloads
        return new Promise(() => {});
      }
      throw error;
    }
  });

// ── Lazy-loaded route-level components (code-split by Vite) ──
const UploadView = lazyWithRetry(() => import('./components/UploadView'));
const ResultsView = lazyWithRetry(() => import('./components/ResultsView'));
const BiasDashboard = lazyWithRetry(() => import('./components/BiasDashboard'));
const TalentPoolView = lazyWithRetry(() => import('./components/TalentPoolView'));
const BatchUploadView = lazyWithRetry(() => import('./components/BatchUploadView'));
const AuthView = lazyWithRetry(() => import('./components/AuthView'));
const PipelineVisualizer = lazyWithRetry(() => import('./components/PipelineVisualizer'));
const AiCoachView = lazyWithRetry(() => import('./components/AiCoachView'));
const RecruiterVerificationModal = lazyWithRetry(() => import('./components/RecruiterVerificationModal'));

class ErrorBoundary extends Component {
  constructor(props) { super(props); this.state = { error: null }; }
  static getDerivedStateFromError(error) { return { error }; }
  componentDidCatch(error, errorInfo) { console.error(error, errorInfo); }
  render() { 
    if (this.state.error) return <div className="p-4 text-red-500 font-mono text-sm bg-red-500/10 rounded-xl border border-red-500/20 m-4">Error: {this.state.error.message}</div>;
    return this.props.children; 
  }
}

/* ── Minimal loading fallback for lazy-loaded routes ── */
function PageLoader() {
  return (
    <div className="flex items-center justify-center min-h-[60vh] animate-fade-in">
      <div className="flex flex-col items-center gap-4">
        <div className="w-8 h-8 border-2 border-white/20 border-t-white rounded-full animate-spin" />
        <span className="text-xs text-white/30 uppercase tracking-widest font-semibold">Loading</span>
      </div>
    </div>
  );
}



/* ── Compact "Coming Soon" nav item ── */
function ComingSoonNavItem({ icon, label }) {
  return (
    <div className="flex items-center gap-3 px-4 py-2.5 rounded-xl text-white/25 cursor-default select-none overflow-hidden">
      <span className="shrink-0 text-white/20">{icon}</span>
      <span className="text-sm font-medium text-white/25 flex-1 whitespace-nowrap overflow-hidden transition-all duration-300 opacity-0 w-0 group-hover:opacity-100 group-hover:w-auto group-[.is-mobile-open]:opacity-100 group-[.is-mobile-open]:w-auto">{label}</span>
      <span className="text-[8px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-white/[0.04] text-white/25 border border-white/[0.05] transition-all duration-300 opacity-0 w-0 group-hover:opacity-100 group-hover:w-auto group-[.is-mobile-open]:opacity-100 group-[.is-mobile-open]:w-auto">
        Soon
      </span>
    </div>
  );
}

/* ── Auth modal overlay — wraps AuthView as a dismissible overlay ── */
function AuthModal({ onClose }) {
  // Close on Escape key
  useEffect(() => {
    const handler = e => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-[200] overflow-y-auto">
      {/* Backdrop — click to dismiss */}
      <div
        className="fixed inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />
      {/* Scrollable Container */}
      <div className="relative min-h-screen flex items-center justify-center p-4 py-12">
        {/* Modal content — positioned above backdrop */}
        <div className="relative w-full max-w-4xl animate-neural-expand">
        {/* Dismiss button */}
        <button
          onClick={onClose}
          className="absolute -top-4 -right-4 w-9 h-9 rounded-full bg-white/[0.08] border border-white/15
            flex items-center justify-center text-white/60 hover:text-white hover:bg-white/15
            transition-all z-20 shadow-xl"
          title="Back to homepage"
        >
          <X className="w-4 h-4" />
        </button>
        {/* Re-use AuthView but with modal styling */}
        <Suspense fallback={null}>
          <AuthView isModal />
        </Suspense>
      </div>
      </div>
    </div>
  );
}

/* ── User avatar initials ── */
function UserAvatar({ name }) {
  const initials = name
    ? name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
    : 'ME';
  return (
    <div className="w-8 h-8 rounded-full bg-white/10 border border-white/15 flex items-center justify-center text-xs font-bold text-white">
      {initials}
    </div>
  );
}

/* ── User dropdown ── */
function UserMenu({ user, onLogout, onClose }) {
  if (!user) return null;
  return (
    <div className="absolute right-0 top-full mt-2 w-56 glass-card rounded-2xl border border-white/[0.08] shadow-xl z-[100] overflow-hidden animate-fade-in">
      <div className="px-4 py-3 border-b border-white/[0.06]">
        <div className="text-sm font-bold text-white truncate">{user.name}</div>
        <div className="text-xs text-white/40 truncate">{user.email}</div>
        <span className={`mt-1 inline-block text-[10px] px-2 py-0.5 rounded-full border font-bold uppercase tracking-wider ${
          user.role === 'recruiter' ? 'bg-blue-500/10 text-blue-300 border-blue-500/20' : 'bg-purple-500/10 text-purple-300 border-purple-500/20'
        }`}>{user.role}</span>
      </div>
      <button
        onClick={() => { onLogout(); onClose(); }}
        className="w-full px-4 py-3 flex items-center gap-3 text-sm text-white/60 hover:text-white hover:bg-white/[0.04] transition-colors"
      >
        <LogOut className="w-4 h-4" /> Sign out
      </button>
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════
   PUBLIC LANDING — shown to everyone, no auth required
══════════════════════════════════════════════════════════════ */
function PublicLanding({ onSignIn, onGetStarted, onLoadDemo, s }) {
  return (
    <div className="min-h-screen bg-transparent relative w-full">
      <MagneticLensCursor />
      <NeuralWireframe />

      {/* Minimal public topbar */}
      <header className="relative z-10 flex items-center justify-between px-6 py-4 border-b border-white/[0.05]"
        style={{ background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(12px)' }}>
        <div className="flex items-center gap-2.5">
          <img src="/assets/shield_logo.webp" alt="Aethel" style={{ width: 34, height: 34, objectFit: 'contain', filter: 'drop-shadow(0 2px 6px rgba(255,255,255,0.2))' }} />
          <div>
            <div className="text-base font-black text-white tracking-tight">Aethel</div>
            <div className="text-[8px] font-bold uppercase tracking-[0.2em] text-white/40 -mt-0.5">Precision Recruitment</div>
          </div>
        </div>
        <div className="flex items-center gap-2 sm:gap-3">
          {s?.isDemo && (
            <span className="hidden sm:inline-block px-2 py-0.5 rounded-full text-[10px] font-bold bg-white/[0.06] text-white/70 border border-white/[0.08]">Demo</span>
          )}

          <button onClick={onGetStarted}
            className="px-3 py-1.5 sm:px-4 sm:py-2 text-xs sm:text-sm font-bold text-black bg-white rounded-xl hover:bg-white/90 active:scale-95 transition-all whitespace-nowrap">
            Get Started Free
          </button>
        </div>
      </header>

      {/* Demo mode: show results + sign-up nudge */}
      {s?.isDemo && s?.result ? (
        <div className="relative z-10 max-w-7xl mx-auto w-full">
          <div className="px-6 py-3 flex items-center justify-between gap-4 border-b border-white/[0.05]"
            style={{ background: 'rgba(255,255,255,0.03)' }}>
            <p className="text-xs text-white/60">
              👀 You're viewing a <span className="text-white font-semibold">sample demo</span>. Sign up free to audit your own resume.
            </p>
            <button onClick={onGetStarted}
              className="shrink-0 px-4 py-1.5 rounded-xl bg-white text-black text-xs font-bold hover:bg-white/90 transition-all">
              Audit My Resume — Free →
            </button>
          </div>
          <Suspense fallback={<PageLoader />}>
            <ResultsView s={s} />
          </Suspense>
        </div>
      ) : (
        /* Normal landing content */
        <div className="relative z-10 mx-auto w-full">
          <LandingView onGetStarted={onGetStarted} onLoadDemo={onLoadDemo} />
        </div>
      )}
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════
   MAIN APP — shown only when logged in (full sidebar layout)
══════════════════════════════════════════════════════════════ */
function AuthenticatedApp({ s }) {
  const { user, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen]     = useState(false);
  const [showVerificationModal, setShowVerificationModal] = useState(false);
  const [loaderPhase, setLoaderPhase]       = useState('loading'); // 'loading', 'forming', 'complete'
  const scanStartTimeRef = React.useRef(Date.now());

  React.useEffect(() => {
    if (s.step === 'scanning') {
      scanStartTimeRef.current = Date.now();
      setLoaderPhase('loading');

      // Preload the horse SVG image in the background (zero DOM cost)
      const img = new Image();
      img.src = '/assets/horse_animated.svg';
      
      const onReady = () => {
        const elapsed = Date.now() - scanStartTimeRef.current;
        const remainingTime = Math.max(0, 4000 - elapsed);
        
        setTimeout(() => {
          setLoaderPhase('forming');
          // After 3s shield trace, show the horse
          setTimeout(() => setLoaderPhase('complete'), 3000);
        }, remainingTime);
      };

      // If already cached, fire immediately; otherwise wait for load
      if (img.complete) onReady();
      else img.onload = onReady;
    }
  }, [s.step]);

  const biasProxies    = s.result?.bias_proxies || [];
  const recommendation = s.result?.recommendation || 'Schedule Screening Call';

  const goTo = step => { s.setStep(step); setMobileMenuOpen(false); };

  return (
    <div className="h-screen text-white flex relative overflow-hidden bg-transparent w-full">
      <div className="bg-criss-cross fixed inset-0 z-0" />

      {s.showFairnessGate && (
        <FairnessGateModal biasProxies={biasProxies} recommendation={recommendation}
          onConfirm={s.handleFairnessConfirm} onCancel={() => s.setShowFairnessGate(false)} />
      )}

      {showVerificationModal && (
        <Suspense fallback={null}>
          <RecruiterVerificationModal onClose={() => setShowVerificationModal(false)} />
        </Suspense>
      )}

      {mobileMenuOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[60] md:hidden" onClick={() => setMobileMenuOpen(false)} />
      )}

      {/* SIDEBAR - Mobile drawer with backdrop */}
      <aside className={`group shrink-0 glass-sidebar flex flex-col m-0 z-[70] fixed md:sticky top-0 h-screen border-r border-white/[0.06] transition-all duration-300 overflow-hidden ${mobileMenuOpen ? 'translate-x-0 w-[260px]' : '-translate-x-full md:translate-x-0 w-[88px] hover:w-[260px]'}`}>
        <div className="px-5 py-6 border-b border-white/[0.06] flex items-center justify-between">
          <div className="flex items-center gap-2 relative">
            <div className="absolute inset-0 bg-white/20 blur-xl rounded-full scale-[1.5]" />
            <img src="/assets/shield_logo.webp" alt="Aethel" className="relative z-10 shrink-0" style={{ width: 40, height: 40, objectFit: 'contain', filter: 'drop-shadow(0 2px 8px rgba(255,255,255,0.2))' }} />
            <div className={`relative z-10 ml-1 transition-all duration-300 whitespace-nowrap overflow-hidden ${mobileMenuOpen ? 'opacity-100 w-auto' : 'opacity-0 w-0 group-hover:opacity-100 group-hover:w-auto'}`}>
              <div className="text-lg font-bold text-white tracking-tight">Aethel</div>
              <div className="text-[8px] font-bold uppercase tracking-[0.25em] text-white/40">Precision Recruitment</div>
            </div>
          </div>
          <button className="md:hidden p-1 text-white/50 hover:text-white" onClick={() => setMobileMenuOpen(false)}>
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="px-3 py-4">
          <button onClick={() => { s.reset(); setMobileMenuOpen(false); }} data-cursor="magnetic"
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl btn-premium magnetic-btn text-sm font-semibold mb-4 overflow-hidden whitespace-nowrap">
            <span className="shrink-0 text-lg">+</span>
            <span className={`transition-all duration-300 ${mobileMenuOpen ? 'opacity-100 w-auto' : 'opacity-0 w-0 group-hover:opacity-100 group-hover:w-auto'}`}>
              {user?.role === 'candidate' ? 'Audit Resume' : 'Add Candidate'}
            </span>
          </button>
        </div>

        <nav className="flex-1 px-3 space-y-0.5">
          <NavItem icon={<img src="/assets/shield_logo.webp" alt="" className="w-4 h-4 object-contain" />}
            label="Home" active={s.step === 'landing'} onClick={() => goTo('landing')} expanded={mobileMenuOpen} />
          <NavItem icon={<Users className="w-4 h-4" />}
            label={user?.role === 'candidate' ? 'My Resumes' : 'Talent Pipeline'} active={s.step === 'talent-pool'} onClick={() => goTo('talent-pool')} expanded={mobileMenuOpen} />
          {user?.role !== 'candidate' && (
            <ComingSoonNavItem icon={<FileText className="w-4 h-4" />} label="JD Matching" expanded={mobileMenuOpen} />
          )}
          {user?.role === 'candidate' && (
            <NavItem icon={<Activity className="w-4 h-4" />}
              label="AI Coach" active={s.step === 'coach'} onClick={() => goTo('coach')} expanded={mobileMenuOpen} />
          )}
          {user?.role !== 'candidate' && (
            <NavItem icon={<Layers className="w-4 h-4" />}
              label="Batch Upload" active={s.step === 'batch'} 
              expanded={mobileMenuOpen}
              onClick={() => {
                if (user?.role === 'recruiter' && !user?.is_recruiter_verified) {
                  setShowVerificationModal(true);
                } else {
                  goTo('batch');
                }
              }} />
          )}
          <NavItem icon={<Shield className="w-4 h-4" />}
            label={user?.role === 'candidate' ? 'New Audit' : 'Audit Trail'} active={s.step === 'upload' || s.step === 'scanning'} onClick={() => goTo('upload')} expanded={mobileMenuOpen} />
          {user?.role !== 'candidate' && (
            <NavItem icon={<BarChart2 className="w-4 h-4" />}
              label="Analytics" active={s.step === 'analytics'} onClick={() => goTo('analytics')} expanded={mobileMenuOpen} />
          )}
        </nav>

        <div className="px-3 pb-4 space-y-0.5">
          <button onClick={() => { window.open('mailto:support@aethel.ai', '_blank'); setMobileMenuOpen(false); }}
            className="w-full flex items-center gap-3 px-3 py-2 text-sm text-white/80 hover:text-white transition-colors rounded-xl hover:bg-white/[0.04] overflow-hidden">
            <div className="shrink-0"><HelpCircle className="w-4 h-4" /></div>
            <span className={`whitespace-nowrap overflow-hidden transition-all duration-300 ${mobileMenuOpen ? 'opacity-100 w-auto' : 'opacity-0 w-0 group-hover:opacity-100 group-hover:w-auto'}`}>Support</span>
          </button>
          <div className="flex items-center gap-3 px-3 py-2 overflow-hidden">
            <div className="shrink-0 w-7 h-7 rounded-full bg-white/10 border border-white/15 flex items-center justify-center text-xs font-bold text-white">
              {user?.name ? user.name.split(' ').map(w => w[0]).join('').slice(0,2).toUpperCase() : 'ME'}
            </div>
            <div className={`flex-1 min-w-0 transition-all duration-300 whitespace-nowrap overflow-hidden ${mobileMenuOpen ? 'opacity-100 w-auto' : 'opacity-0 w-0 group-hover:opacity-100 group-hover:w-auto'}`}>
              <div className="text-xs font-semibold text-white truncate">{user?.name}</div>
              <div className="text-[10px] text-white/40 truncate">{user?.role}</div>
            </div>
            <button onClick={() => { logout(); setMobileMenuOpen(false); }} className={`shrink-0 transition-all duration-300 text-white/30 hover:text-white/70 ${mobileMenuOpen ? 'opacity-100 w-auto' : 'opacity-0 w-0 group-hover:opacity-100 group-hover:w-auto'}`} title="Sign out">
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </aside>

      {/* MAIN */}
      <div className="flex-1 flex flex-col h-full min-w-0 w-full relative">
        {/* TOPBAR - Flush Gradient Fade */}
        <header className="h-20 shrink-0 z-50 flex items-start justify-between px-4 sm:px-6 pt-4 pointer-events-none"
          style={{ 
            background: 'linear-gradient(to bottom, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.5) 40%, transparent 100%)',
            transform: 'translateZ(0)',
            willChange: 'transform'
          }}>
          <div className="flex items-center gap-3 pointer-events-auto">
            <button className="md:hidden text-white hover:text-white/80" onClick={() => setMobileMenuOpen(true)}>
              <Menu className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-2">
              <img src="/assets/shield_logo.webp" alt="Aethel Logo" className="w-6 h-6 object-contain" />
              <span className="text-sm font-bold text-white tracking-tight">Aethel ATS</span>
            </div>
          </div>
          <div className="flex items-center gap-3 relative pointer-events-auto">
            {s.isDemo && s.step === 'results' && (
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-white/[0.06] text-white/70 border border-white/[0.08]">Demo</span>
            )}
            <button onClick={() => alert('No new notifications.')}
              className="w-8 h-8 rounded-lg bg-white/[0.04] border border-white/[0.06] flex items-center justify-center hover:bg-white/[0.08] transition-all">
              <Bell className="w-4 h-4 text-white/60" />
            </button>
            <div className="relative">
              <button onClick={() => setUserMenuOpen(v => !v)}>
                <UserAvatar name={user?.name} />
              </button>
              {userMenuOpen && <UserMenu user={user} onLogout={logout} onClose={() => setUserMenuOpen(false)} />}
            </div>
          </div>
        </header>
        {userMenuOpen && <div className="fixed inset-0 z-40" onClick={() => setUserMenuOpen(false)} />}

        {/* VERIFICATION BANNER */}
        {user?.role === 'recruiter' && !user?.is_recruiter_verified && (
          <div className="bg-yellow-500/10 border-b border-yellow-500/20 px-6 py-2.5 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-3">
              <AlertCircle className="w-4 h-4 text-yellow-500" />
              <span className="text-xs text-yellow-200">
                Verify your company email to unlock premium features like batch processing.
              </span>
            </div>
            <button 
              onClick={() => setShowVerificationModal(true)}
              className="text-xs font-bold text-yellow-500 hover:text-yellow-400 bg-yellow-500/10 hover:bg-yellow-500/20 px-3 py-1.5 rounded-lg transition-colors"
            >
              Verify Now
            </button>
          </div>
        )}

        {/* PAGE CONTENT */}
        <main className="flex-1 overflow-y-auto overflow-x-hidden relative z-10 w-full flex flex-col">
          <Suspense fallback={<PageLoader />}>
            {s.step === 'coach' ? (
              <AiCoachView s={s} />
            ) : (
              <div className={`mx-auto w-full px-4 sm:px-8 py-6 flex-1 ${s.step === 'talent-pool' ? 'max-w-none' : 'max-w-[1600px]'}`}>
                {s.step === 'landing' && <LandingView onGetStarted={() => goTo('upload')} onLoadDemo={s.loadDemo} />}

              {s.step === 'upload' && <UploadView s={s} />}

              {s.step === 'scanning' && (
                <>
                  <div className="flex flex-col items-center justify-center min-h-[calc(100vh-8rem)] p-8 animate-fade-in relative z-10">
                    {/* Central 160x160 area for the loaders */}
                    <div className="relative w-40 h-40 mb-10 flex items-center justify-center">
                      
                      {/* SVG Circuit Loader / Shield Trace */}
                      <CircuitLoader phase={loaderPhase} />

                      {/* Actual HorseLoader — only mounted AFTER shield animation completes */}
                      <div 
                        className={`absolute inset-0 flex items-center justify-center transition-all duration-500 ${loaderPhase === 'complete' ? 'scale-100 opacity-100' : 'scale-90 opacity-0'}`}
                        style={{ willChange: 'transform, opacity', transform: 'translateZ(0)' }}
                      >
                        <HorseLoader />
                      </div>
                    </div>
                    <h2 className="text-2xl font-bold text-white mb-6">Analyzing Candidate Profile</h2>
                  
                  <div className="w-full max-w-lg bento-box p-6 scan-container shadow-[0_0_80px_rgba(255,255,255,0.03)] border border-white/[0.08]">
                    <div className="flex justify-between items-end mb-3">
                      <span className="text-xs font-bold uppercase tracking-widest text-white/50 flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-[#00f0ff] animate-pulse shadow-[0_0_10px_#00f0ff]" /> Live Audit Trail
                      </span>
                      <span className="text-lg font-black text-white font-mono">{s.progress}%</span>
                    </div>
                    <div className="h-1.5 w-full bg-white/[0.06] rounded-full overflow-hidden mb-6">
                      <div className="h-full bg-white rounded-full transition-all duration-300 ease-out shadow-[0_0_10px_rgba(255,255,255,0.5)]" style={{ width: s.progress + '%' }} />
                    </div>
                    
                    {/* Vertical Text Animation Container */}
                    <div className="space-y-3 font-mono text-xs h-48 overflow-hidden relative">
                      {s.logs.filter(Boolean).map(log => (
                        <div key={log.id} className={'flex items-start gap-3 animate-fade-in-up ' + getLogColor(log.type)}>
                          <div className="mt-0.5"><LogIcon type={log.type} /></div>
                          <div className="leading-relaxed">{log.text}</div>
                        </div>
                      ))}
                      <div className="absolute bottom-0 left-0 right-0 h-16 bg-gradient-to-t from-transparent to-transparent pointer-events-none" />
                    </div>
                  </div>
                </div>
                </>
              )}

              {s.step === 'error' && (
                <div className="flex flex-col items-center justify-center min-h-[calc(100vh-8rem)] p-8 animate-fade-in">
                  <div className="max-w-md w-full glass-card rounded-2xl p-8 text-center">
                    <XCircle className="w-12 h-12 text-white/80 mx-auto mb-4" />
                    <h2 className="text-xl font-bold text-white mb-2">Analysis Failed</h2>
                    <p className="text-white/60 text-sm mb-6 font-mono leading-relaxed">
                      {typeof s.apiError === 'object' ? (s.apiError?.message || s.apiError?.detail || JSON.stringify(s.apiError)) : s.apiError}
                    </p>
                    <div className="flex justify-center gap-3">
                      <button onClick={s.reset} className="px-6 py-2.5 rounded-xl text-sm font-semibold flex items-center gap-2 btn-premium"><RefreshCw className="w-4 h-4" />Retry</button>
                      <button onClick={s.loadDemo} className="px-6 py-2.5 rounded-xl text-sm font-semibold flex items-center gap-2 btn-premium"><Play className="w-4 h-4" />Demo</button>
                    </div>
                  </div>
                </div>
              )}

              {s.step === 'results' && s.result && <ResultsView s={s} onOpenCoach={() => goTo('coach')} />}
              {s.step === 'analytics' && user?.role !== 'candidate' && (
                <>
                  {/* Mobile restriction for recruiter dashboard */}
                  <div className="block lg:hidden">
                    <div className="flex flex-col items-center justify-center min-h-[60vh] px-6 py-12">
                      <div className="glass-card rounded-2xl p-8 max-w-md text-center border border-white/[0.08]">
                        <div className="w-16 h-16 rounded-full bg-white/[0.06] border border-white/[0.1] flex items-center justify-center mx-auto mb-6">
                          <BarChart2 className="w-8 h-8 text-white/60" />
                        </div>
                        <h2 className="text-xl font-bold text-white mb-3">Desktop Required</h2>
                        <p className="text-sm text-white/60 leading-relaxed mb-6">
                          The Analytics Dashboard is optimized for desktop viewing. Please access this page from a laptop or PC for the best experience.
                        </p>
                        <button
                          onClick={() => goTo('talent-pool')}
                          className="px-6 py-2.5 rounded-xl text-sm font-semibold btn-premium flex items-center gap-2 mx-auto"
                        >
                          <Users className="w-4 h-4" />
                          Go to Talent Pipeline
                        </button>
                      </div>
                    </div>
                  </div>
                  {/* Desktop view */}
                  <div className="hidden lg:block">
                    <BiasDashboard />
                  </div>
                </>
              )}
              {s.step === 'talent-pool' && (
                user?.role !== 'candidate' ? (
                  <>
                    <div className="block lg:hidden">
                      <div className="flex flex-col items-center justify-center min-h-[60vh] px-6 py-12">
                        <div className="glass-card rounded-2xl p-8 max-w-md text-center border border-white/[0.08]">
                          <div className="w-16 h-16 rounded-full bg-white/[0.06] border border-white/[0.1] flex items-center justify-center mx-auto mb-6">
                            <Users className="w-8 h-8 text-white/60" />
                          </div>
                          <h2 className="text-xl font-bold text-white mb-3">Desktop Required</h2>
                          <p className="text-sm text-white/60 leading-relaxed mb-6">
                            The Recruiter Dashboard is optimized for desktop viewing. Please access this page from a laptop or PC for the best experience.
                          </p>
                          <button
                            onClick={() => goTo('upload')}
                            className="px-6 py-2.5 rounded-xl text-sm font-semibold btn-premium flex items-center gap-2 mx-auto"
                          >
                            <Shield className="w-4 h-4" />
                            Go to New Audit
                          </button>
                        </div>
                      </div>
                    </div>
                    <div className="hidden lg:block">
                      <TalentPoolView />
                    </div>
                  </>
                ) : (
                  <TalentPoolView />
                )
              )}
              {s.step === 'batch' && user?.role !== 'candidate' && (
                <BatchUploadView
                  s={s}
                  jobs={s.batchJobs}
                  setJobs={s.setBatchJobs}
                  batchId={s.batchId}
                  setBatchId={s.setBatchId}
                  ws={s.batchWs}
                  setWs={s.setBatchWs}
                  onViewResult={(job) => {
                    s.setResult(job.result);
                    s.setStep('results');
                  }}
                />
              )}
            </div>
            )}
          </Suspense>
        </main>
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════
   ROOT APP — decides what to render based on auth state
══════════════════════════════════════════════════════════════ */
export default function App() {
  const { isLoggedIn } = useAuth();
  const s = useAppState();
  const [showAuth, setShowAuth]     = useState(false);  // auth modal open?
  const [authIntent, setAuthIntent] = useState(null);   // where to go after login

  // When user logs in → close modal and act on intent
  const prevLoggedIn = React.useRef(isLoggedIn);
  useEffect(() => {
    if (!prevLoggedIn.current && isLoggedIn) {
      setShowAuth(false);
      if (authIntent === 'scan') s.setStep('upload');
      else if (authIntent === 'demo') s.loadDemo();
      setAuthIntent(null);
    }
    prevLoggedIn.current = isLoggedIn;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoggedIn]);

  const handleGetStarted = () => {
    if (isLoggedIn) { s.setStep('upload'); }
    else { setAuthIntent('scan'); setShowAuth(true); }
  };

  const handleLoadDemo = () => {
    s.loadDemo();
    setShowAuth(false);
  };

  const handleSignIn = () => {
    setAuthIntent(null);
    setShowAuth(true);
  };

  // A demo user (not logged in) sees results inside a stripped-down shell
  const showApp = isLoggedIn || s.isDemo;


  return (
    <ErrorBoundary>
      {/* ── LOGGED IN: full authenticated app ── */}
      {isLoggedIn && <AuthenticatedApp s={s} />}

      {/* ── NOT LOGGED IN: public landing (handles demo state internally) ── */}
      {!isLoggedIn && (
        <PublicLanding
          onSignIn={handleSignIn}
          onGetStarted={handleGetStarted}
          onLoadDemo={handleLoadDemo}
          s={s}
        />
      )}

      {/* ── Auth modal ── */}
      {showAuth && !isLoggedIn && (
        <Suspense fallback={null}>
          <AuthModal onClose={() => setShowAuth(false)} />
        </Suspense>
      )}
    </ErrorBoundary>
  );
}
