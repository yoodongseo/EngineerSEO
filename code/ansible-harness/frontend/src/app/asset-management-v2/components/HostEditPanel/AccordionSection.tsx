'use client';

import { useState, type ReactNode } from 'react';

interface AccordionSectionProps {
  title: string;
  children: ReactNode;
  defaultOpen?: boolean;
}

export default function AccordionSection({ title, children, defaultOpen = false }: AccordionSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="section">
      <div 
        className="header" 
        onClick={() => setIsOpen(!isOpen)}
        role="button"
        aria-expanded={isOpen}
      >
        {title} <span className="arrow">{isOpen ? '▼' : '▶'}</span>
      </div>
      {isOpen && <div className="content">{children}</div>}
    </div>
  );
}
