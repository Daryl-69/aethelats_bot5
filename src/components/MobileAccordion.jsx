import React, { useState, useRef, useEffect } from 'react';
import { ChevronRight } from 'lucide-react';

/**
 * MobileSection — Premium collapsible accordion for mobile Results view.
 *
 * On mobile (< lg): renders a glass panel with a tap-to-expand header,
 * animated chevron, optional summary badge, and circuit-line connector.
 *
 * On desktop (>= lg): renders children directly, no wrapping.
 *
 * Props:
 *  - title: string — section heading
 *  - badge: string|ReactNode — compact summary shown in collapsed state
 *  - icon: ReactNode — Lucide icon for the header
 *  - defaultOpen: boolean — start expanded?
 *  - children: ReactNode — section body content
 *  - showConnector: boolean — show circuit line below (default true)
 *  - headerAction: ReactNode — optional button rendered in the header (e.g. "Run Test")
 *  - className: string — extra classes for the outer wrapper
 */
export function MobileSection({
  title,
  badge,
  icon,
  defaultOpen = false,
  children,
  showConnector = true,
  headerAction,
  className = '',
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const bodyRef = useRef(null);
  const [bodyHeight, setBodyHeight] = useState(0);

  // Measure body content height for smooth animation
  useEffect(() => {
    if (bodyRef.current) {
      setBodyHeight(bodyRef.current.scrollHeight);
    }
  }, [isOpen, children]);

  return (
    <>
      {/* Desktop: render children directly, no accordion */}
      <div className={`hidden lg:block ${className}`}>
        {children}
      </div>

      {/* Mobile: accordion panel */}
      <div className={`lg:hidden ${className}`}>
        <div className="glass-card rounded-2xl border border-white/[0.06] overflow-hidden">
          {/* Header — always visible */}
          <button
            onClick={() => setIsOpen(v => !v)}
            className="w-full flex items-center gap-3 px-5 py-4 text-left group transition-colors hover:bg-white/[0.02] active:bg-white/[0.04]"
          >
            {/* Chevron */}
            <div
              className="w-6 h-6 rounded-lg bg-white/[0.04] border border-white/[0.08] flex items-center justify-center shrink-0 transition-transform duration-500"
              style={{
                transform: isOpen ? 'rotate(90deg)' : 'rotate(0deg)',
                transitionTimingFunction: 'cubic-bezier(0.175, 0.885, 0.32, 1.275)',
              }}
            >
              <ChevronRight className="w-3.5 h-3.5 text-white/60" />
            </div>

            {/* Icon */}
            {icon && (
              <div className="w-7 h-7 rounded-lg bg-white/[0.03] border border-white/[0.06] flex items-center justify-center shrink-0 text-white/60">
                {icon}
              </div>
            )}

            {/* Title + Badge */}
            <div className="flex-1 min-w-0">
              <div className="text-[11px] font-bold uppercase tracking-[0.15em] text-white truncate">
                {title}
              </div>
            </div>

            {/* Badge */}
            {badge && (
              <span className="px-2.5 py-1 rounded-lg text-[10px] font-bold bg-white/[0.04] text-white/60 border border-white/[0.08] shrink-0 uppercase tracking-wider">
                {badge}
              </span>
            )}

            {/* Optional header action (e.g. "Run Test" button) */}
            {headerAction && (
              <div onClick={e => e.stopPropagation()} className="shrink-0">
                {headerAction}
              </div>
            )}
          </button>

          {/* Body — animated expand/collapse */}
          <div
            className="overflow-hidden transition-all duration-500 ease-out"
            style={{
              maxHeight: isOpen ? `${bodyHeight + 40}px` : '0px',
              opacity: isOpen ? 1 : 0,
              transitionTimingFunction: 'cubic-bezier(0.16, 1, 0.3, 1)',
            }}
          >
            <div ref={bodyRef} className="px-5 pb-5 pt-1">
              <div className="border-t border-white/[0.04] pt-4">
                {children}
              </div>
            </div>
          </div>
        </div>

        {/* Circuit connector line */}
        {showConnector && (
          <div className="circuit-connector" />
        )}
      </div>
    </>
  );
}

/**
 * CircuitConnector — standalone connector line between sections.
 * Use between non-accordion elements (e.g., between the score hero and the first accordion).
 */
export function CircuitConnector() {
  return (
    <div className="lg:hidden circuit-connector" />
  );
}
