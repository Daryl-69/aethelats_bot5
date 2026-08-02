import React, { useState, useEffect } from 'react';
import { Check, ChevronRight, ChevronDown, ChevronUp, AlertTriangle, Shield, CheckCircle } from 'lucide-react';
import { SEVERITY_STYLE, BIAS_TYPE_LABELS } from './constants';

export function useCountUp(target, duration = 1400, trigger = true) {
  const [value, setValue] = useState(0);
  useEffect(() => {
    if (!trigger || !target) return;
    let start = null;
    const step = (ts) => {
      if (!start) start = ts;
      const p = Math.min((ts - start) / duration, 1);
      setValue(Math.round(p * target));
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [target, duration, trigger]);
  return value;
}

export function SectionHeading({ icon, label }) {
  return (
    <div className="flex items-center gap-2 mb-4">
      <span className="text-white/80">{icon}</span>
      <span className="text-[11px] font-bold uppercase tracking-[0.2em] text-white">{label}</span>
    </div>
  );
}

export function Pill({ children, variant }) {
  const m = {
    emerald: 'bg-white/[0.08] text-white border-white/10',
    rose: 'bg-white/[0.05] text-white border-white/10',
    indigo: 'bg-white/[0.08] text-white border-white/10',
    amber: 'bg-white/[0.05] text-white border-white/10',
  };
  return <span className={'inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border ' + (m[variant] || 'bg-white/[0.05] text-white border-white/10')}>{children}</span>;
}

export function NavItem({ icon, label, active, onClick }) {
  return (
    <button onClick={onClick} className={'w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm transition-all duration-400 ease-out ' +
      (active
        ? 'tab-3d-active'
        : 'text-white/90 hover:text-white hover:bg-white/[0.04] border border-transparent hover:border-white/[0.04]')}>
      {icon}
      <span>{label}</span>
    </button>
  );
}

export function ToggleSwitch({ active, onToggle }) {
  return (
    <div className={'toggle-track' + (active ? ' active' : '')} onClick={onToggle} />
  );
}

export function AnimatedBar({ value, delay = 0, color = 'bg-white' }) {
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const t = setTimeout(() => setWidth(value), 100 + delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return (
    <div className="h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
      <div className={color + ' h-full rounded-full'} style={{ width: width + '%', transition: 'width 1.2s cubic-bezier(0.4,0,0.2,1)' }} />
    </div>
  );
}

export function ScoreMeter({ value, size = 160, label }) {
  const displayVal = useCountUp(value, 1500);
  const p = Math.max(0, Math.min(100, displayVal)) / 100;

  return (
    <div style={{ position: 'relative', width: size, height: size, perspective: '1200px' }} className="group">
      {/* 3D Container */}
      <div 
        className="w-full h-full transition-transform duration-700 ease-out"
        style={{ 
          transformStyle: 'preserve-3d', 
          transform: 'rotateX(60deg) rotateZ(45deg)'
        }} 
      >
        {/* Base Layer */}
        <div className="absolute inset-0 border border-white/10 rounded-3xl bg-[#0a0a0a]" style={{ transform: 'translateZ(-10px)', boxShadow: '0 20px 40px rgba(0,0,0,0.9)' }} />
        
        {/* Circuit Layer */}
        <div className="absolute inset-2 border border-white/5 rounded-[20px] bg-black/50 backdrop-blur-sm flex items-center justify-center" style={{ transform: 'translateZ(10px)' }}>
          <div className="w-full h-full rounded-[18px] border-[0.5px] border-white/[0.03]" style={{ background: 'repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(255,255,255,0.02) 10px, rgba(255,255,255,0.02) 20px)' }} />
        </div>

        {/* Dynamic Progress Ring */}
        <div className="absolute inset-4 rounded-full" style={{ 
          transform: 'translateZ(30px)', 
          background: `conic-gradient(from 225deg, #fff ${p * 360}deg, rgba(255,255,255,0.05) ${p * 360}deg)`,
          padding: '4px',
          WebkitMask: 'radial-gradient(transparent 60%, black 62%)'
        }} />

        {/* Floating Glass Prism Core */}
        <div className="absolute inset-8 rounded-2xl bg-white/5 border border-white/20 backdrop-blur-md flex items-center justify-center" style={{ transform: 'translateZ(60px)', boxShadow: 'inset 0 0 20px rgba(255,255,255,0.1), 0 20px 30px rgba(0,0,0,0.8)' }}>
          <div className="absolute w-full h-full bg-white/10 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 blur-xl" />
        </div>
      </div>

      {/* Floating Text Overlay (Faces camera, breaks out of 3D context) */}
      <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none drop-shadow-[0_4px_10px_rgba(0,0,0,0.8)] z-10 transition-transform duration-700 group-hover:-translate-y-2">
        <span className="text-5xl font-black text-white leading-none tracking-tighter" style={{ textShadow: '0 0 20px rgba(255,255,255,0.2)' }}>{displayVal}</span>
        <span className="text-[10px] text-white mt-1.5 font-bold tracking-[0.2em] uppercase">Score</span>
      </div>
    </div>
  );
}

export function FairnessGateModal({ biasProxies, recommendation, onConfirm, onCancel }) {
  const [checked, setChecked] = useState(false);
  const high = biasProxies.filter(p => p.severity === 'high').length;
  const med = biasProxies.filter(p => p.severity === 'medium').length;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(12px)' }}>
      <div className="w-full max-w-2xl glass-card glass-card-hover rounded-2xl shadow-2xl overflow-hidden animate-scale-in" style={{ animationDelay: '0s' }}>
        <div className="warning-card-yellow px-6 py-5 flex items-start gap-4" style={{ borderRadius: '12px 12px 0 0' }}>
          <div className="w-10 h-10 rounded-xl bg-[#000000]/10 border border-[#000000]/20 flex items-center justify-center shrink-0 mt-0.5">
            <AlertTriangle className="w-5 h-5 text-[#000000]" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-[#000000] mb-1">⚠️ Fairness Review Required</h2>
            <p className="text-sm text-[#000000]/70">Aethel detected <span className="font-bold text-[#000000]">{biasProxies.length} bias proxy variable{biasProxies.length !== 1 ? 's' : ''}</span>. Review before proceeding.</p>
          </div>
        </div>
        <div className="px-6 py-4 border-b border-white/[0.06] flex gap-3 flex-wrap">
          {high > 0 && <span className="flex items-center gap-1.5 px-3 py-1 rounded-md bg-white/[0.05] border border-white/10 text-white/80 text-xs font-bold"><span className="w-2 h-2 rounded-full bg-white inline-block" />{high} High-Risk</span>}
          {med > 0 && <span className="flex items-center gap-1.5 px-3 py-1 rounded-md bg-white/[0.05] border border-white/10 text-white text-xs font-bold"><span className="w-2 h-2 rounded-full bg-white/50 inline-block" />{med} Medium-Risk</span>}
        </div>
        <div className="px-6 py-4 max-h-60 overflow-y-auto space-y-3">
          {biasProxies.map((proxy, idx) => {
            const bt = BIAS_TYPE_LABELS[proxy.bias_type] || BIAS_TYPE_LABELS.gender;
            const s = SEVERITY_STYLE[proxy.severity] || SEVERITY_STYLE.low;
            return (
              <div key={idx} className={'rounded-xl border p-4 ' + s.bg + ' ' + s.border}>
                <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                  <code className={'text-xs px-2 py-0.5 rounded-md font-mono font-semibold border ' + bt.bg + ' ' + bt.color + ' ' + bt.border}>"{proxy.text}"</code>
                  <span className={'text-xs font-semibold px-2 py-0.5 rounded-md border ' + bt.bg + ' ' + bt.color + ' ' + bt.border}>{bt.label}</span>
                  <span className={'text-xs font-bold uppercase px-2 py-0.5 rounded-md border ' + s.bg + ' ' + s.text + ' ' + s.border}>{proxy.severity}</span>
                </div>
                <p className="text-xs text-white/90 leading-relaxed"><Shield className="w-3 h-3 text-white/80 inline mr-1" />{proxy.explanation}</p>
              </div>
            );
          })}
        </div>
        <div className="px-6 py-4 border-t border-white/[0.06]">
          <label className="flex items-start gap-3 cursor-pointer group">
            <div className="relative mt-0.5 shrink-0">
              <input type="checkbox" checked={checked} onChange={e => setChecked(e.target.checked)} className="sr-only" />
              <div className={'w-5 h-5 rounded border-2 flex items-center justify-center transition-all ' + (checked ? 'bg-white border-white' : 'bg-transparent border-white/30 group-hover:border-white/60')}>
                {checked && <Check className="w-3 h-3 text-black" />}
              </div>
            </div>
            <span className="text-sm text-white leading-relaxed">
              I have reviewed all <span className="font-semibold text-white">{biasProxies.length} bias proxy warnings</span>. My decision is based solely on <span className="font-semibold text-white">technical merit</span>.
            </span>
          </label>
        </div>
        <div className="px-6 py-4 border-t border-white/[0.06] bg-black/30 flex items-center justify-between gap-3">
          <button onClick={onCancel} className="px-5 py-2.5 rounded-xl text-sm font-semibold text-white/90 border border-white/10 hover:bg-white/[0.05] hover:text-white transition-all">Cancel</button>
          <button onClick={onConfirm} disabled={!checked}
            className={'px-6 py-2.5 rounded-xl text-sm font-bold transition-all flex items-center gap-2 ' +
              (checked ? 'bg-white text-black hover:bg-white/90 active:scale-95' : 'bg-white/10 text-white/80 cursor-not-allowed')}>
            <CheckCircle className="w-4 h-4" /> Confirm & Proceed
          </button>
        </div>
      </div>
    </div>
  );
}

export function getLogColor(t) {
  if (t === 'success') return 'text-white';
  if (t === 'alert') return 'text-white';
  if (t === 'warn') return 'text-white/90';
  return 'text-white/80';
}

export function LogIcon({ type }) {
  if (type === 'success') return <Check className="w-3.5 h-3.5 text-white shrink-0" />;
  if (type === 'alert') return <AlertTriangle className="w-3.5 h-3.5 text-white/90 shrink-0" />;
  if (type === 'warn') return <AlertTriangle className="w-3.5 h-3.5 text-white/80 shrink-0" />;
  return <ChevronRight className="w-3.5 h-3.5 text-white shrink-0" />;
}

export function getFitVariant(fl) { if (fl === 'Strong Match') return 'emerald'; if (fl === 'Good Match') return 'indigo'; if (fl === 'Partial Match') return 'amber'; return 'rose'; }
export function getScoreColor(s) { if (s >= 80) return 'indigo'; if (s >= 60) return 'emerald'; return 'rose'; }
