// Eagerly import all SVG playing cards using Vite glob import
const cardModules = import.meta.glob<string>('../../Assets/cards/*.svg', {
  eager: true,
  import: 'default',
});

// Map of normalized key (e.g. "ace_of_spades", "card_back") -> resolved URL string
const cardMap: Record<string, string> = {};

for (const [path, url] of Object.entries(cardModules)) {
  const filename = path.split('/').pop()?.replace('.svg', '') || '';
  cardMap[filename.toLowerCase()] = url;
}

export const CARD_BACK_URL = cardMap['card_back'] || '/Assets/cards/card_back.svg';

export interface ParsedCard {
  rank: string;
  suit: 'spades' | 'hearts' | 'diamonds' | 'clubs';
  svgUrl: string;
}

/**
 * Parses card representation (e.g., "10♠", "A♥", "Kd", "10s", "J") into rank, suit, and SVG URL.
 */
export function resolveCardAsset(cardStr: string): ParsedCard {
  if (!cardStr) {
    return {
      rank: '?',
      suit: 'spades',
      svgUrl: CARD_BACK_URL,
    };
  }

  let clean = cardStr.trim();
  if (clean.startsWith('Card(') && clean.endsWith(')')) {
    clean = clean.slice(5, -1).trim();
  }
  let rankPart = '';
  let suitPart = '';

  // Check last character for suit
  const lastChar = clean.slice(-1);
  if (['♠', '♥', '♦', '♣', 's', 'h', 'd', 'c', 'S', 'H', 'D', 'C'].includes(lastChar)) {
    suitPart = lastChar;
    rankPart = clean.slice(0, -1);
  } else {
    rankPart = clean;
  }

  // Resolve suit
  let suit: 'spades' | 'hearts' | 'diamonds' | 'clubs' = 'spades';
  switch (suitPart.toLowerCase()) {
    case '♥':
    case 'h':
      suit = 'hearts';
      break;
    case '♦':
    case 'd':
      suit = 'diamonds';
      break;
    case '♣':
    case 'c':
      suit = 'clubs';
      break;
    case '♠':
    case 's':
    default:
      suit = 'spades';
      break;
  }

  // Resolve rank name for SVG file matching
  let rankKey = rankPart.toLowerCase();
  let displayRank = rankPart.toUpperCase();

  switch (rankKey) {
    case 'a':
    case '1':
      rankKey = 'ace';
      displayRank = 'A';
      break;
    case 'k':
      rankKey = 'king';
      displayRank = 'K';
      break;
    case 'q':
      rankKey = 'queen';
      displayRank = 'Q';
      break;
    case 'j':
      rankKey = 'jack';
      displayRank = 'J';
      break;
    default:
      displayRank = rankKey;
      break;
  }

  const expectedKey = `${rankKey}_of_${suit}`;
  const svgUrl = cardMap[expectedKey] || cardMap[`${rankKey}_of_${suit}2`] || CARD_BACK_URL;

  return {
    rank: displayRank,
    suit,
    svgUrl,
  };
}

export function calculateCardsTotal(cardStrs: string[]): {
  total: number;
  is_soft: boolean;
  is_busted: boolean;
} {
  let total = 0;
  let aces = 0;

  for (const cs of cardStrs) {
    if (!cs || cs === '?') continue;
    const parsed = resolveCardAsset(cs);
    if (parsed.rank === 'A') {
      aces += 1;
      total += 11;
    } else if (['K', 'Q', 'J', '10'].includes(parsed.rank)) {
      total += 10;
    } else {
      const num = parseInt(parsed.rank, 10);
      total += isNaN(num) ? 0 : num;
    }
  }

  while (total > 21 && aces > 0) {
    total -= 10;
    aces -= 1;
  }

  return {
    total,
    is_soft: aces > 0,
    is_busted: total > 21,
  };
}
