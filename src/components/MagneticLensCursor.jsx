import React, { useEffect, useRef, useState } from 'react';

export default function MagneticLensCursor() {
  const cursorRef = useRef(null);
  const requestRef = useRef(null);
  const mouse = useRef({ x: window.innerWidth / 2, y: window.innerHeight / 2 });
  const pos = useRef({ x: window.innerWidth / 2, y: window.innerHeight / 2 });
  const hoveredRectRef = useRef(null);
  const [hoveredRect, setHoveredRect] = useState(null);  // kept for the style effect only
  const [isTouchDevice, setIsTouchDevice] = useState(false);

  useEffect(() => {
    if (window.matchMedia("(pointer: coarse)").matches) {
      setIsTouchDevice(true);
      return;
    }

    const onMouseMove = (e) => {
      mouse.current.x = e.clientX;
      mouse.current.y = e.clientY;
    };

    const onMouseOver = (e) => {
      const target = e.target.closest('button, a, [data-cursor="magnetic"]');
      if (target) {
        const rect = target.getBoundingClientRect();
        hoveredRectRef.current = rect;
        setHoveredRect(rect);
      } else {
        hoveredRectRef.current = null;
        setHoveredRect(null);
      }
    };

    const render = () => {
      if (!cursorRef.current) return;

      // Lerp physics for smooth trailing
      pos.current.x += (mouse.current.x - pos.current.x) * 0.15;
      pos.current.y += (mouse.current.y - pos.current.y) * 0.15;

      if (hoveredRectRef.current) {
        // Snap to button bounds
        cursorRef.current.style.transform = `translate3d(${hoveredRectRef.current.left}px, ${hoveredRectRef.current.top}px, 0)`;
      } else {
        // Default dot
        cursorRef.current.style.transform = `translate3d(calc(${pos.current.x}px - 50%), calc(${pos.current.y}px - 50%), 0)`;
      }

      requestRef.current = requestAnimationFrame(render);
    };

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseover', onMouseOver);
    requestRef.current = requestAnimationFrame(render);

    // Hide system cursor
    document.body.style.cursor = 'none';

    return () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseover', onMouseOver);
      cancelAnimationFrame(requestRef.current);
      document.body.style.cursor = 'auto';
    };
  }, []); // stable — never re-registers listeners

  // Update heavy visual styles ONLY when hoveredRect changes, not 60fps!
  useEffect(() => {
    if (!cursorRef.current) return;
    
    if (hoveredRect) {
      cursorRef.current.style.width = `${hoveredRect.width}px`;
      cursorRef.current.style.height = `${hoveredRect.height}px`;
      cursorRef.current.style.borderRadius = '12px';
      cursorRef.current.style.opacity = '1';
      cursorRef.current.style.backdropFilter = 'invert(1) grayscale(1)';
      cursorRef.current.style.backgroundColor = 'transparent';
      cursorRef.current.style.border = '1px solid rgba(255,255,255,0.5)';
    } else {
      cursorRef.current.style.width = '12px';
      cursorRef.current.style.height = '12px';
      cursorRef.current.style.borderRadius = '50%';
      cursorRef.current.style.opacity = '0.5';
      cursorRef.current.style.backdropFilter = 'none';
      cursorRef.current.style.backgroundColor = 'white';
      cursorRef.current.style.border = 'none';
    }
  }, [hoveredRect]);



  if (isTouchDevice) return null;

  return (
    <div
      ref={cursorRef}
      className="fixed top-0 left-0 z-[9999] pointer-events-none transition-[width,height,border-radius,opacity,backdrop-filter] duration-300 ease-out will-change-transform mix-blend-difference"
    />
  );
}
