import React from 'react';

export default function TextReveal({ text, delay = 0, className = "", innerClassName = "" }) {
  const words = text.split(" ");
  
  return (
    <span className={`inline-block ${className}`}>
      {words.map((word, i) => (
        <span key={i} className="inline-block mr-[0.25em] align-bottom relative">
          <span 
            className={`inline-block translate-y-[100%] opacity-0 animate-mask-reveal ${innerClassName}`}
            style={{ 
              animationDelay: `${delay + (i * 0.08)}s`,
              animationFillMode: 'forwards'
            }}
          >
            {word}
          </span>
        </span>
      ))}
    </span>
  );
}
