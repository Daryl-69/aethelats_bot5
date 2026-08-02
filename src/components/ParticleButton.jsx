import React, { useState, useRef, useEffect } from 'react';
import { Zap } from 'lucide-react';

export default function ParticleButton({ onClick, children, className = "", ...props }) {
  const [isAnimating, setIsAnimating] = useState(false);
  const [particles, setParticles] = useState([]);
  const buttonRef = useRef(null);

  const handleClick = (e) => {
    if (isAnimating) return;
    setIsAnimating(true);
    
    // Generate particles
    const rect = buttonRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    const newParticles = Array.from({ length: 12 }).map((_, i) => ({
      id: Date.now() + i,
      x, y,
      angle: (i / 12) * Math.PI * 2,
      velocity: 40 + Math.random() * 40,
      size: 2 + Math.random() * 3,
    }));
    
    setParticles(newParticles);

    setTimeout(() => {
      setIsAnimating(false);
      setParticles([]);
      if (onClick) onClick(e);
    }, 800);
  };

  return (
    <button
      ref={buttonRef}
      onClick={handleClick}
      className={`relative overflow-hidden group ${className}`}
      {...props}
    >
      {/* Intricate SVG Border Trace on Click */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none rounded-xl" xmlns="http://www.w3.org/2000/svg">
        <rect 
          x="1" y="1" 
          width="100%" height="100%" 
          rx="11" ry="11"
          fill="none" 
          stroke={isAnimating ? "#00f0ff" : "transparent"} 
          strokeWidth="2"
          strokeDasharray="400"
          strokeDashoffset={isAnimating ? "0" : "400"}
          className="transition-all duration-700 ease-[cubic-bezier(0.16,1,0.3,1)]"
        />
      </svg>

      {/* Particles */}
      {particles.map(p => (
        <div
          key={p.id}
          className="absolute rounded-full bg-[#00f0ff] pointer-events-none"
          style={{
            left: p.x,
            top: p.y,
            width: p.size,
            height: p.size,
            transform: `translate(-50%, -50%)`,
            animation: `particle-burst 0.8s cubic-bezier(0.16,1,0.3,1) forwards`,
            '--tx': `${Math.cos(p.angle) * p.velocity}px`,
            '--ty': `${Math.sin(p.angle) * p.velocity}px`,
          }}
        />
      ))}

      {/* Button Content */}
      <div className={`relative z-10 flex items-center justify-center gap-3 transition-transform duration-200 ${isAnimating ? 'scale-95' : 'scale-100'}`}>
        {children}
      </div>
      
      {/* CSS for particles is injected globally or added in index.css, but we can do inline style trick or just add it to index.css */}
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes particle-burst {
          0% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
          100% { transform: translate(calc(-50% + var(--tx)), calc(-50% + var(--ty))) scale(0); opacity: 0; }
        }
      `}} />
    </button>
  );
}
