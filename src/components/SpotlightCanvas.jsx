import React, { useEffect, useRef } from 'react';

export default function SpotlightCanvas() {
  const containerRef = useRef(null);

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!containerRef.current) return;
      const { clientX, clientY } = e;
      containerRef.current.style.setProperty('--x', `${clientX}px`);
      containerRef.current.style.setProperty('--y', `${clientY}px`);
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  return (
    <div className="fixed inset-0 z-0 bg-[#030303] pointer-events-none overflow-hidden">
      {/* 
        The spotlight layer. 
        It is fully hidden except where the radial gradient mask reveals it around the cursor. 
      */}
      <div 
        ref={containerRef}
        className="absolute inset-0 w-full h-full transition-opacity duration-1000"
        style={{
          '--x': '50vw',
          '--y': '50vh',
          maskImage: 'radial-gradient(circle 800px at var(--x) var(--y), black 0%, transparent 100%)',
          WebkitMaskImage: 'radial-gradient(circle 800px at var(--x) var(--y), black 0%, transparent 100%)',
        }}
      >
        {/* A complex, high-end technical dot grid that is revealed by the spotlight */}
        <div 
          className="absolute inset-0 w-full h-full opacity-[0.15]"
          style={{
            backgroundImage: 'radial-gradient(circle, rgba(255,255,255,1) 1px, transparent 1px)',
            backgroundSize: '32px 32px'
          }}
        />
        
        {/* Secondary structural lines revealed by the spotlight */}
        <div 
          className="absolute inset-0 w-full h-full opacity-[0.03]"
          style={{
            backgroundImage: `
              linear-gradient(to right, rgba(255,255,255,1) 1px, transparent 1px),
              linear-gradient(to bottom, rgba(255,255,255,1) 1px, transparent 1px)
            `,
            backgroundSize: '128px 128px'
          }}
        />
      </div>
    </div>
  );
}
