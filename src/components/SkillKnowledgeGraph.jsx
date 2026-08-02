import React, { useState, useEffect, useRef } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import ForceGraph3D from 'react-force-graph-3d';
import { Box, Layers } from 'lucide-react';

export default function SkillKnowledgeGraph({ skillData }) {
  const [mode, setMode] = useState('2D'); // '2D' or '3D'
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const containerRef = useRef();
  const [dimensions, setDimensions] = useState({ width: 0, height: 480 });

  // Handle container resize
  useEffect(() => {
    if (containerRef.current) {
      setDimensions({ width: containerRef.current.offsetWidth, height: 480 });
    }
    const handleResize = () => {
      if (containerRef.current) {
        setDimensions({ width: containerRef.current.offsetWidth, height: 480 });
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    const nodes = [];
    const links = [];
    
    // Generate skills (use demo Customer Service data if no real data is passed)
    const skills = skillData && skillData.length > 0 
      ? [...new Set(skillData.map(s => s.canonical_name))]
      : ['Customer Service', 'Communication', 'Teamwork', 'Conflict Resolution', 'CRM', 'Empathy', 'Problem Solving'];

    skills.forEach((skillName, i) => {
      const matchData = skillData ? skillData.find(s => s.canonical_name === skillName) : null;
      const isCore = matchData ? (matchData.match_type === 'exact' || matchData.match_type === 'synonym') : (i % 2 === 0);
      nodes.push({ id: skillName, name: skillName, val: isCore ? 6 : 3, core: isCore });
    });

    if (nodes.length > 1) {
      nodes.forEach((n, i) => {
        const target1 = nodes[(i + 1) % nodes.length];
        if (target1) links.push({ source: n.id, target: target1.id });
        if (nodes.length > 4) {
          const target2 = nodes[(i + Math.floor(nodes.length/2)) % nodes.length];
          if (target2 && i < nodes.length/2) links.push({ source: n.id, target: target2.id });
        }
      });
    }

    setGraphData({ nodes, links });
  }, [skillData]);

  const draw2DNode = (node, ctx, globalScale) => {
    const label = node.name;
    const fontSize = 14 / globalScale;
    ctx.font = `${node.core ? 'bold ' : ''}${fontSize}px Inter, sans-serif`;
    
    const r = node.val * 3;
    
    ctx.beginPath();
    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI, false);
    ctx.fillStyle = node.core ? 'rgba(255,255,255,0.06)' : 'rgba(255,255,255,0.02)';
    ctx.fill();
    ctx.lineWidth = 1 / globalScale;
    ctx.strokeStyle = node.core ? 'rgba(255,255,255,0.5)' : 'rgba(255,255,255,0.15)';
    ctx.stroke();

    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = node.core ? 'rgba(255, 255, 255, 0.9)' : 'rgba(255, 255, 255, 0.5)';
    ctx.fillText(label, node.x, node.y + r + fontSize);
  };

  return (
    <div className="glass-card glass-card-hover rounded-2xl p-5 relative overflow-hidden animate-fade-in-up" ref={containerRef}>
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-base font-bold text-white animate-slide-in-right stagger-1">Skill Knowledge Graph</h3>
          <p className="text-xs text-white/80 mt-0.5 animate-slide-in-right stagger-2">Interactive physics-based topology</p>
        </div>
        <div className="flex items-center gap-1 bg-white/[0.04] p-1 rounded-xl border border-white/[0.06] animate-scale-in stagger-3">
          <button 
            onClick={() => setMode('2D')} 
            className={'flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ' + (mode === '2D' ? 'bg-white text-black shadow-lg' : 'text-white/90 hover:text-white')}
          >
            <Layers className="w-3.5 h-3.5" /> 2D
          </button>
          <button 
            onClick={() => setMode('3D')} 
            className={'flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ' + (mode === '3D' ? 'bg-white text-black shadow-lg' : 'text-white/90 hover:text-white')}
          >
            <Box className="w-3.5 h-3.5" /> 3D
          </button>
        </div>
      </div>

      <div className="relative rounded-xl overflow-hidden bg-[#0a0a0a] border border-white/[0.04] animate-fade-in stagger-4" style={{ height: '480px' }}>
        {dimensions.width > 0 && mode === '2D' && (
          <ForceGraph2D
            width={dimensions.width}
            height={dimensions.height}
            graphData={graphData}
            nodeCanvasObject={draw2DNode}
            nodePointerAreaPaint={(node, color, ctx) => {
              ctx.fillStyle = color;
              ctx.beginPath(); ctx.arc(node.x, node.y, node.val * 3 + 10, 0, 2 * Math.PI, false); ctx.fill();
            }}
            linkColor={() => 'rgba(255,255,255,0.06)'}
            linkWidth={1.5}
            cooldownTicks={100}
            d3AlphaDecay={0.05}
            d3VelocityDecay={0.15}
          />
        )}
        
        {dimensions.width > 0 && mode === '3D' && (
          <ForceGraph3D
            width={dimensions.width}
            height={dimensions.height}
            graphData={graphData}
            nodeLabel="name"
            nodeRelSize={4}
            nodeVal={node => node.val}
            nodeColor={node => node.core ? 'rgba(255,255,255,0.9)' : 'rgba(255,255,255,0.3)'}
            nodeResolution={16}
            linkColor={() => 'rgba(255,255,255,0.1)'}
            linkWidth={0.5}
            backgroundColor="#0a0a0a"
            showNavInfo={false}
          />
        )}
        
        {/* Helper text overlay */}
        <div className="absolute bottom-4 right-4 pointer-events-none text-[10px] text-white uppercase tracking-widest animate-fade-in stagger-5">
          {mode === '2D' ? 'Drag nodes to interact' : 'Drag to rotate · Scroll to zoom'}
        </div>
      </div>

      <div className="flex items-center gap-6 mt-4 pt-3 border-t border-white/[0.06] text-xs text-white/80 animate-fade-in-up stagger-6">
        <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-white/20 border border-white/30" /> Core Skill</span>
        <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-white/10 border border-white/15" /> Related Tech</span>
        <span className="flex items-center gap-1.5"><span className="w-6 h-px bg-white/15" /> Relevance</span>
        <span className="ml-auto text-white">Aethel AI Engine</span>
      </div>
    </div>
  );
}
