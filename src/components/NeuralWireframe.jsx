import React, { useEffect, useRef, useState } from 'react';

export default function NeuralWireframe() {
  const svgRef = useRef(null);
  const requestRef = useRef(null);
  const mouse = useRef({ x: window.innerWidth / 2, y: window.innerHeight / 2 });
  const targetBox = useRef(null); // Will hold bounding box of hovered magnetic element
  const isTouchDevice = useRef(false);

  const isMobile = window.innerWidth < 768;
  const nodeCount = isMobile ? 6 : 20;

  // Generate abstract nodes
  const nodes = useRef(Array.from({ length: nodeCount }).map((_, i) => ({
    id: i,
    baseX: Math.random() * window.innerWidth,
    baseY: Math.random() * window.innerHeight,
    x: 0,
    y: 0,
    vx: 0,
    vy: 0,
    phase: Math.random() * Math.PI * 2
  })));

  useEffect(() => {
    if (window.matchMedia("(pointer: coarse)").matches) {
      isTouchDevice.current = true;
    }

    const onMouseMove = (e) => {
      if (isTouchDevice.current) return;
      mouse.current.x = e.clientX;
      mouse.current.y = e.clientY;
    };

    const onMouseOver = (e) => {
      if (isTouchDevice.current) return;
      const target = e.target.closest('[data-wireframe="magnetic"]');
      if (target) {
        targetBox.current = target.getBoundingClientRect();
      } else {
        targetBox.current = null;
      }
    };

    const render = (ts) => {
      if (!svgRef.current) return;
      
      const width = window.innerWidth;
      const height = window.innerHeight;

      // Update nodes
      nodes.current.forEach(node => {
        // Natural drifting
        node.baseX += Math.sin(ts * 0.001 + node.phase) * 0.5;
        node.baseY += Math.cos(ts * 0.0012 + node.phase) * 0.5;

        // Wrap around
        if (node.baseX > width + 100) node.baseX = -100;
        if (node.baseX < -100) node.baseX = width + 100;
        if (node.baseY > height + 100) node.baseY = -100;
        if (node.baseY < -100) node.baseY = height + 100;

        let targetX = node.baseX;
        let targetY = node.baseY;

        // Magnetic hover effect
        if (targetBox.current) {
          // Calculate a point on the perimeter of the target box
          const box = targetBox.current;
          const perimeterRatio = node.id / nodes.current.length;
          
          // Map ratio to perimeter
          if (perimeterRatio < 0.25) { // Top edge
            targetX = box.left + (perimeterRatio / 0.25) * box.width;
            targetY = box.top;
          } else if (perimeterRatio < 0.5) { // Right edge
            targetX = box.right;
            targetY = box.top + ((perimeterRatio - 0.25) / 0.25) * box.height;
          } else if (perimeterRatio < 0.75) { // Bottom edge
            targetX = box.right - ((perimeterRatio - 0.5) / 0.25) * box.width;
            targetY = box.bottom;
          } else { // Left edge
            targetX = box.left;
            targetY = box.bottom - ((perimeterRatio - 0.75) / 0.25) * box.height;
          }
          
          // Add a slight padding/glow radius
          const centerX = box.left + box.width / 2;
          const centerY = box.top + box.height / 2;
          const dx = targetX - centerX;
          const dy = targetY - centerY;
          const dist = Math.sqrt(dx*dx + dy*dy);
          targetX += (dx/dist) * 15;
          targetY += (dy/dist) * 15;
        } else {
          // Repel from mouse slightly when not hovering a button
          const dx = mouse.current.x - node.baseX;
          const dy = mouse.current.y - node.baseY;
          const dist = Math.sqrt(dx*dx + dy*dy);
          if (dist < 200) {
            targetX -= (dx / dist) * (200 - dist) * 0.5;
            targetY -= (dy / dist) * (200 - dist) * 0.5;
          }
        }

        // Spring physics
        const spring = targetBox.current ? 0.1 : 0.02;
        const friction = 0.8;
        
        node.vx += (targetX - node.x) * spring;
        node.vy += (targetY - node.y) * spring;
        node.vx *= friction;
        node.vy *= friction;
        node.x += node.vx;
        node.y += node.vy;
      });

      // Update DOM
      const paths = svgRef.current.querySelectorAll('path');
      let pathIdx = 0;
      
      // Connect each node to the 3 nearest neighbors
      for (let i = 0; i < nodes.current.length; i++) {
        const n1 = nodes.current[i];
        
        // Find nearest
        const distances = nodes.current.map(n2 => ({
          node: n2,
          d: Math.sqrt(Math.pow(n1.x - n2.x, 2) + Math.pow(n1.y - n2.y, 2))
        })).sort((a, b) => a.d - b.d).slice(1, 4); // skip self (idx 0), take next 3

        distances.forEach(target => {
          if (paths[pathIdx]) {
            const n2 = target.node;
            // Draw a bezier curve between them
            const midX = (n1.x + n2.x) / 2;
            const midY = (n1.y + n2.y) / 2;
            // offset control point based on mouse for extra dynamism
            const cpX = midX + (mouse.current.x - midX) * 0.1;
            const cpY = midY + (mouse.current.y - midY) * 0.1;
            
            paths[pathIdx].setAttribute('d', `M ${n1.x} ${n1.y} Q ${cpX} ${cpY} ${n2.x} ${n2.y}`);
            
            // Adjust opacity based on distance and hover state
            let opacity = targetBox.current ? 0.6 : Math.max(0.05, 1 - (target.d / 400));
            paths[pathIdx].style.opacity = opacity;
          }
          pathIdx++;
        });
      }

      requestRef.current = requestAnimationFrame(render);
    };

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseover', onMouseOver);
    requestRef.current = requestAnimationFrame(render);

    return () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseover', onMouseOver);
      cancelAnimationFrame(requestRef.current);
    };
  }, []);

  // 20 nodes * 3 connections = 60 paths
  return (
    <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden mix-blend-screen">
      <svg ref={svgRef} className="w-full h-full" fill="none" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="wireframeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#ffffff" stopOpacity="0.2" />
            <stop offset="50%" stopColor="#ffffff" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#ffffff" stopOpacity="0.1" />
          </linearGradient>
        </defs>
        {Array.from({ length: nodeCount * 3 }).map((_, i) => (
          <path 
            key={i} 
            stroke="url(#wireframeGrad)" 
            strokeWidth="1" 
            className="transition-opacity duration-300 ease-out will-change-transform"
          />
        ))}
      </svg>
    </div>
  );
}
