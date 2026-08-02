import React from 'react';

export default function CircuitLoader({ phase }) {
  // SVG paths for the 90-degree jagged "mirror cube" circuitry lines
  const circuits = [
    "M 15 50 L 30 50 L 30 20 L 70 20 L 70 80 L 45 80 L 45 50",
    "M 80 90 L 55 90 L 55 60 L 35 60 L 35 15 L 45 15 L 45 45",
    "M 5 10 L 25 10 L 25 75 L 10 75 L 10 35 L 35 35 L 35 55",
    "M 85 10 L 85 40 L 60 40 L 60 100 L 30 100 L 30 85 L 70 85"
  ];

  // Perfectly 1:1 mapped shield trace
  // Uses an 87x100 viewBox to identically match the 1778x2047 ratio of the HorseLoader
  const shieldPath = "M 43.5 2 L 85 13.5 C 85 50 70 85 43.5 98 C 17 85 2 50 2 13.5 Z";

  return (
    <div className={`absolute inset-0 pointer-events-none transition-opacity duration-500 ${phase === 'complete' ? 'opacity-0' : 'opacity-100'}`}>
      <svg width="100%" height="100%" viewBox="0 0 87 100" preserveAspectRatio="xMidYMid meet" fill="none" className="overflow-visible">

        {/* Phase 1: Jagged Circuitry Lines */}
        <g 
          className="transition-opacity duration-500"
          style={{ opacity: phase === 'loading' ? 1 : 0 }}
        >
          {circuits.map((d, i) => (
            <path 
              key={i}
              d={d}
              stroke="rgba(255,255,255,0.5)"
              strokeWidth="0.4"
              strokeLinejoin="miter"
              className="circuit-path"
              style={{
                strokeDasharray: '25 90',
                animation: `circuit-flow 3s linear infinite`,
                animationDelay: `${i * 0.5}s`
              }}
            />
          ))}
        </g>

        {/* Phase 2: Forming the Shield */}
        <path
          d={shieldPath}
          stroke="rgba(255,255,255,0.7)"
          strokeWidth="0.6"
          strokeLinejoin="round"
          className="transition-opacity duration-1000"
          style={{
            opacity: phase === 'forming' ? 1 : 0,
            strokeDasharray: 400,
            strokeDashoffset: phase === 'forming' ? 0 : 400,
            transition: phase === 'forming' ? 'stroke-dashoffset 3000ms ease-in-out' : 'none'
          }}
        />
      </svg>

      <style>{`
        @keyframes circuit-flow {
          0% { stroke-dashoffset: 115; }
          100% { stroke-dashoffset: 0; }
        }
      `}</style>
    </div>
  );
}
