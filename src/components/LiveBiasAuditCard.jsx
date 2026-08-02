import React, { useEffect, useState } from 'react';
import { BarChart2, AlertTriangle, Cpu, ShieldCheck } from 'lucide-react';
import { API_URL } from './constants';

function AnimatedNumber({ value, isFloat = false, duration = 1500 }) {
  const [val, setVal] = useState(0);
  useEffect(() => {
    let start = null;
    const numericValue = typeof value === 'string' ? parseFloat(value.replace('+', '')) : value;
    if (isNaN(numericValue)) {
      setVal(0);
      return;
    }
    const step = (ts) => {
      if (!start) start = ts;
      const p = Math.min((ts - start) / duration, 1);
      const easeOut = 1 - Math.pow(1 - p, 3);
      setVal(easeOut * numericValue);
      if (p < 1) requestAnimationFrame(step);
    };
    const id = requestAnimationFrame(step);
    return () => cancelAnimationFrame(id);
  }, [value, duration]);

  if (isFloat) {
    const formatted = val.toFixed(1);
    const hasPlus = typeof value === 'string' && value.includes('+');
    return <>{(val > 0 || hasPlus) ? `+${formatted}` : formatted}</>;
  }
  return <>{Math.round(val).toLocaleString('en-IN')}</>;
}

export default function LiveBiasAuditCard() {
  const [mounted, setMounted] = useState(false);
  const [liveData, setLiveData] = useState(null);
  const [statsData, setStatsData] = useState(null);

  useEffect(() => {
    setMounted(true);
    fetch(`${API_URL}/bias-comparison`).then(r => r.json()).then(setLiveData).catch(() => {});
    fetch(`${API_URL}/stats`).then(r => r.json()).then(setStatsData).catch(() => {});
  }, []);

  const displayModels = [];
  if (liveData && liveData.models && Object.keys(liveData.models).length > 0) {
    const keys = Object.keys(liveData.models).sort((a, b) => a === 'aethel' ? -1 : b === 'aethel' ? 1 : 0);
    keys.slice(0, 4).forEach(key => {
      const m = liveData.models[key];
      const isAethel = key === 'aethel';
      displayModels.push({
        name: isAethel ? 'FairAI (Aethel)' : key,
        scans: m.sample_count,
        iit: m.delta_institution > 0 ? `+${m.delta_institution.toFixed(1)}` : m.delta_institution.toFixed(1),
        gap: m.delta_gap > 0 ? `+${m.delta_gap.toFixed(1)}` : m.delta_gap.toFixed(1),
        icon: isAethel ? <ShieldCheck className="w-4 h-4 text-white" /> : <Cpu className="w-4 h-4 text-white/50" />,
        isAethel
      });
    });
  } else {
    // fallback
    displayModels.push(
      { name: 'Aethel (FairAI)', scans: 27, iit: '+1.0', gap: '+2.0', icon: <ShieldCheck className="w-4 h-4 text-white" />, isAethel: true },
      { name: 'Llama 3 70B', scans: 14, iit: '+9.0', gap: '+6.0', icon: <Cpu className="w-4 h-4 text-white/50" />, isAethel: false },
      { name: 'Gemma 7B', scans: 12, iit: '+12.0', gap: '+8.0', icon: <Cpu className="w-4 h-4 text-white/50" />, isAethel: false },
      { name: 'Mixtral 8x7B', scans: 11, iit: '+7.0', gap: '+5.0', icon: <Cpu className="w-4 h-4 text-white/50" />, isAethel: false }
    );
  }

  const avgScore = statsData ? Math.round(statsData.avg_score) : 62;
  const poolSize = statsData ? statsData.pool_size : 114;
  
  let biasReduction = 73;
  if (liveData && liveData.models) {
    const aethel = liveData.models['aethel'];
    let maxBias = 0;
    Object.keys(liveData.models).forEach(k => {
      if (k !== 'aethel' && liveData.models[k].total_bias > maxBias) {
        maxBias = liveData.models[k].total_bias;
      }
    });
    if (aethel && maxBias > 0) {
      biasReduction = Math.max(0, Math.round(((maxBias - aethel.total_bias) / maxBias) * 100));
    }
  }

  return (
    <div className="w-full flex flex-col gap-4 font-sans text-left">
      
      {/* Main Table Card */}
      <div className="w-full bg-[#050505] rounded-2xl border border-white/[0.05] overflow-hidden flex flex-col shadow-2xl relative">
        
        {/* Dynamic Glare Overlay */}
        <div className="absolute inset-0 bg-gradient-to-br from-white/[0.03] to-transparent pointer-events-none" />

        {/* Header */}
        <div className="p-4 border-b border-white/[0.05] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <BarChart2 className="w-4 h-4 text-white/70" />
            <h3 className="text-white text-[11px] font-bold tracking-[0.15em] uppercase">Live Bias Audit</h3>
          </div>
          {liveData ? (
            <div className="px-3 py-1 rounded-full bg-emerald-400/10 border border-emerald-400/20 text-emerald-400 text-[9px] font-bold tracking-widest uppercase flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" /> Live Data
            </div>
          ) : (
            <div className="px-3 py-1 rounded-full bg-white/[0.05] border border-white/[0.1] text-white/60 text-[9px] font-bold tracking-widest uppercase">
              Demo
            </div>
          )}
        </div>

        {/* Table Content */}
        <div className="p-4">
          {/* Headers */}
          <div className="grid grid-cols-5 gap-3 mb-3 text-[10px] font-bold tracking-widest text-white/40 uppercase">
            <div className="col-span-2">Model</div>
            <div className="text-center">Scans</div>
            <div className="text-center">Institution Δ</div>
            <div className="text-center">Gap Δ</div>
          </div>

          {/* Rows */}
          <div className="flex flex-col gap-3">
            {displayModels.map((m, i) => (
              <div 
                key={m.name + i}
                className={`grid grid-cols-5 gap-3 items-center p-2.5 rounded-xl border transition-all duration-700 ease-out transform
                  ${mounted ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-4'}
                  ${m.isAethel ? 'bg-white/[0.03] border-white/10' : 'bg-transparent border-white/[0.02]'}
                `}
                style={{ transitionDelay: `${i * 150}ms` }}
              >
                <div className="col-span-2 flex items-center gap-3 overflow-hidden">
                  <div className={`w-6 h-6 rounded-md flex items-center justify-center bg-black/50 ${m.isAethel ? 'border border-white/20' : 'border border-white/5'}`}>
                    {m.icon}
                  </div>
                  <span className={`text-xs sm:text-sm font-semibold truncate capitalize ${m.isAethel ? 'text-white' : 'text-white/60'}`}>
                    {m.name}
                  </span>
                </div>
                <div className="text-center">
                  <span className="text-lg font-black tabular-nums text-white">
                    <AnimatedNumber value={m.scans} />
                  </span>
                </div>
                <div className="text-center">
                  <span className={`text-sm font-bold tabular-nums ${m.isAethel ? 'text-emerald-400' : 'text-white/80'}`}>
                    <AnimatedNumber value={m.iit} isFloat />
                  </span>
                </div>
                <div className="text-center">
                  <span className={`text-sm font-bold tabular-nums ${m.isAethel ? 'text-emerald-400' : 'text-white/80'}`}>
                    <AnimatedNumber value={m.gap} isFloat />
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Alert Box */}
          <div 
            className={`mt-4 p-3 rounded-xl border border-white/[0.05] bg-white/[0.02] flex gap-3 items-start transition-all duration-700 delay-700 ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}
          >
            <AlertTriangle className="w-4 h-4 text-white/50 shrink-0 mt-0.5" />
            <p className="text-white/50 text-xs leading-relaxed">
              All mainstream LLMs raised their score when college changed from NIT Trichy <span className="font-mono text-[10px]">→</span> IIT Bombay. Aethel's delta: <strong className="text-white">+{displayModels.find(m => m.isAethel)?.iit.replace('+', '')} pt</strong>.
            </p>
          </div>
        </div>
      </div>

      {/* Bottom Metric Cards */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { value: `${avgScore} pts`, label: 'AVG SCORE', delay: 800 },
          { value: poolSize, label: 'SCANS IN POOL', delay: 900 },
          { value: `${biasReduction}%`, label: 'BIAS REDUCTION', delay: 1000 },
        ].map((stat, i) => (
          <div 
            key={i}
            className={`bg-[#050505] p-4 rounded-xl border border-white/[0.05] flex flex-col items-center justify-center shadow-lg transition-all duration-700 ${mounted ? 'opacity-100 scale-100' : 'opacity-0 scale-95'}`}
            style={{ transitionDelay: `${stat.delay}ms` }}
          >
            <span className="text-2xl font-black text-white tracking-tight tabular-nums mb-1">{stat.value}</span>
            <span className="text-[9px] font-bold text-white/40 tracking-widest uppercase text-center">{stat.label}</span>
          </div>
        ))}
      </div>

    </div>
  );
}
