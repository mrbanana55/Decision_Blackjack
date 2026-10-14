import React, { useRef } from 'react';
import gsap from 'gsap';
import { useGSAP } from '@gsap/react';
import { CardVisualState } from '../types/simulation';
import { CARD_BACK_URL } from '../lib/cardAssets';

interface CardViewProps {
  card: CardVisualState;
  delayMs?: number;
  className?: string;
}

export const CardView: React.FC<CardViewProps> = ({
  card,
  delayMs = 300,
  className = '',
}) => {
  const cardRef = useRef<HTMLDivElement>(null);

  // Dynamic duration scaling formula (T024):
  // Scales down smoothly with speed slider, transitioning to 0s at delay_ms === 0
  const duration = Math.max(0, Math.min(0.4, (delayMs / 1000) * 0.4));

  useGSAP(
    () => {
      if (!cardRef.current) return;

      if (duration === 0) {
        // Instant placement without animation
        gsap.set(cardRef.current, {
          opacity: 1,
          y: 0,
          scale: 1,
          rotate: card.is_horizontal ? 90 : 0,
        });
      } else {
        // Smooth card deal from shoe
        gsap.fromTo(
          cardRef.current,
          {
            opacity: 0,
            y: -30,
            scale: 0.85,
            rotate: card.is_horizontal ? 45 : -10,
          },
          {
            opacity: 1,
            y: 0,
            scale: 1,
            rotate: card.is_horizontal ? 90 : 0,
            duration,
            ease: 'power2.out',
          }
        );
      }
    },
    { dependencies: [card.id, card.is_horizontal, duration, card.is_hidden, card.svg_path], scope: cardRef }
  );

  const imageSrc = card.is_hidden ? CARD_BACK_URL : card.svg_path;

  return (
    <div
      ref={cardRef}
      className={`relative inline-block select-none transition-shadow ${
        card.is_horizontal ? 'origin-center my-3 mx-2' : ''
      } ${className}`}
      style={{
        width: '56px',
        height: '80px',
      }}
    >
      <img
        src={imageSrc}
        alt={card.is_hidden ? 'Card Back' : card.card_str}
        className="h-full w-full object-contain rounded-md shadow-md border border-slate-700/40 bg-white"
        loading="eager"
      />
    </div>
  );
};
