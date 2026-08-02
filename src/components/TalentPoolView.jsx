import React, { useState, useEffect } from 'react';
import { Users, FileText, Clock, Search, ChevronRight, AlertTriangle, LayoutGrid, List } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { API_URL } from './constants';
import KanbanBoardView from './KanbanBoardView';

function ScorePill({ score }) {
  const color = score >= 75 ? 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20'
              : score >= 50 ? 'text-yellow-400 bg-yellow-400/10 border-yellow-400/20'
              : 'text-red-400 bg-red-400/10 border-red-400/20';
  return (
    <span className={`px-2 py-0.5 rounded-full text-[10px] font-black border ${color}`}>
      {score}
    </span>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="w-16 h-16 rounded-2xl bg-white/[0.03] border border-white/[0.06] flex items-center justify-center mb-5">
        <Users className="w-8 h-8 text-white/20" />
      </div>
      <h3 className="text-lg font-bold text-white mb-2">No candidates yet</h3>
      <p className="text-sm text-white/40 max-w-xs">
        Upload and analyze resumes in Batch Mode to populate your talent pipeline.
      </p>
    </div>
  );
}

function fmtDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  const diffD = Math.floor((Date.now() - d) / 86400000);
  if (diffD < 1)  return 'today';
  if (diffD < 7)  return `${diffD}d ago`;
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
}

export default function TalentPoolView() {
  const { authHeaders } = useAuth();
  const [scans, setScans]       = useState([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState(null);
  const [search, setSearch]     = useState('');
  const [view, setView]         = useState('board'); // 'board' | 'list'

  useEffect(() => {
    setLoading(true);
    fetch(`${API_URL}/user/scans`, { headers: authHeaders() })
      .then(r => r.ok ? r.json() : r.json().then(e => { throw new Error(e.detail); }))
      .then(data => { setScans(data.scans || []); setLoading(false); })
      .catch(e  => { setError(e.message); setLoading(false); });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filtered = scans.filter(s =>
    !search || s.role_target?.toLowerCase().includes(search.toLowerCase()) ||
    s.file_name?.toLowerCase().includes(search.toLowerCase()) ||
    s.candidate_id?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="p-4 sm:p-8 animate-fade-in">
      {/* Header */}
      <div className="mb-6 flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="text-[11px] font-bold uppercase tracking-[0.2em] text-white/50 mb-1">Talent Pool</div>
          <h1 className="text-3xl font-bold text-white">Pipeline Board</h1>
          <p className="text-white/40 text-sm mt-1">Track every candidate across your hiring funnel</p>
        </div>
        <div className="flex items-center gap-3 mt-2">
          <span className="px-2 py-1 rounded-lg bg-white/[0.04] border border-white/[0.06] text-xs text-white/30">
            {scans.length} total
          </span>
          {/* Board / List toggle */}
          <div className="flex items-center rounded-xl bg-white/[0.04] border border-white/[0.06] p-0.5">
            <button
              onClick={() => setView('board')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                view === 'board' ? 'bg-white text-black' : 'text-white/40 hover:text-white'
              }`}
            >
              <LayoutGrid className="w-3.5 h-3.5" /> Board
            </button>
            <button
              onClick={() => setView('list')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                view === 'list' ? 'bg-white text-black' : 'text-white/40 hover:text-white'
              }`}
            >
              <List className="w-3.5 h-3.5" /> List
            </button>
          </div>
        </div>
      </div>

      {/* Search bar */}
      <div className="relative mb-6 max-w-md">
        <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
        <input
          type="text"
          placeholder="Search by role, file or ID…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl px-4 py-2.5 pl-10 text-sm text-white placeholder-white/20 focus:outline-none focus:border-white/20 focus:bg-white/[0.05] transition-all"
        />
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center gap-2 text-white/40 text-sm py-10">
          <span className="w-4 h-4 border-2 border-white/20 border-t-white/60 rounded-full animate-spin" />
          Loading candidates…
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="flex items-start gap-3 p-4 rounded-xl bg-red-500/[0.06] border border-red-500/15 text-sm">
          <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
          <p className="text-red-300">{error}</p>
        </div>
      )}

      {/* Empty */}
      {!loading && !error && scans.length === 0 && <EmptyState />}

      {/* Board View */}
      {!loading && !error && scans.length > 0 && view === 'board' && (
        <KanbanBoardView scans={filtered} />
      )}

      {/* List View */}
      {!loading && !error && scans.length > 0 && view === 'list' && (
        <>
          {filtered.length === 0 && search && (
            <div className="text-center py-16 text-white/30 text-sm">No results for "{search}"</div>
          )}
          {filtered.length > 0 && (
            <div className="glass-card rounded-2xl overflow-hidden">
              {/* Header row */}
              <div className="hidden md:grid grid-cols-12 gap-3 px-5 py-3 border-b border-white/[0.05] bg-white/[0.02]">
                {['Candidate ID', 'File', 'Role', 'Score', 'Stage', 'Date', ''].map((h, i) => (
                  <div key={i} className={`text-[10px] font-bold uppercase tracking-widest text-white/30 ${
                    i === 0 ? 'col-span-2' : i === 1 ? 'col-span-3' : i === 2 ? 'col-span-2' : i === 3 ? 'col-span-1 text-center' : i === 4 ? 'col-span-2' : i === 5 ? 'col-span-1' : 'col-span-1'
                  }`}>{h}</div>
                ))}
              </div>
              <div className="divide-y divide-white/[0.04]">
                {filtered.map((scan, idx) => (
                  <div
                    key={scan.id}
                    className="flex flex-col md:grid md:grid-cols-12 gap-2 md:gap-3 px-4 md:px-5 py-4 hover:bg-white/[0.02] transition-colors group animate-fade-in-up"
                    style={{ animationDelay: `${idx * 0.04}s` }}
                  >
                    <div className="md:col-span-2 flex items-center gap-2">
                      <div className="w-7 h-7 rounded-lg bg-white/[0.04] border border-white/[0.06] flex items-center justify-center shrink-0">
                        <FileText className="w-3.5 h-3.5 text-white/40" />
                      </div>
                      <span className="text-xs font-mono text-white/60">{scan.candidate_id || `#${scan.id}`}</span>
                    </div>
                    <div className="md:col-span-3 flex items-center">
                      <span className="text-sm text-white truncate" title={scan.file_name}>{scan.file_name || 'Resume'}</span>
                    </div>
                    <div className="md:col-span-2 flex items-center">
                      <span className="text-xs text-white/50">{scan.role_target}</span>
                    </div>
                    <div className="md:col-span-1 flex items-center md:justify-center">
                      <ScorePill score={scan.fit_score} />
                    </div>
                    <div className="md:col-span-2 flex items-center">
                      <span className="text-xs text-white/40 px-2 py-0.5 rounded-full bg-white/[0.04] border border-white/[0.06]">
                        {scan.kanban_stage || 'Sourced'}
                      </span>
                    </div>
                    <div className="md:col-span-1 flex items-center gap-1 text-xs text-white/30">
                      <Clock className="w-3 h-3 shrink-0" />
                      {fmtDate(scan.timestamp)}
                    </div>
                    <div className="md:col-span-1 hidden md:flex items-center justify-end">
                      <ChevronRight className="w-4 h-4 text-white/20 group-hover:text-white/50 transition-colors" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
