/**
 * Design Tokens — Sarvam-Level Animation System
 * Centralized configuration for colors, motion, typography, spacing
 */

export const colors = {
  // Core brand colors
  brand: {
    indigo: {
      50: '#eef2ff',
      100: '#e0e7ff',
      200: '#c7d2fe',
      300: '#a5b4fc',
      400: '#818cf8',
      500: '#6366f1',
      600: '#4f46e5',
      700: '#4338ca',
      800: '#3730a3',
      900: '#312e81',
      950: '#1e1b4b',
    },
    saffron: {
      50: '#fff7ed',
      100: '#ffedd5',
      200: '#fed7aa',
      300: '#fdba74',
      400: '#fb923c',
      500: '#f97316',
      600: '#ea580c',
      700: '#c2410c',
      800: '#9a3412',
      900: '#7c2d12',
      950: '#431407',
    },
    mint: {
      50: '#f0fdfa',
      100: '#ccfbf1',
      200: '#99f6e4',
      300: '#5eead4',
      400: '#2dd4bf',
      500: '#14b8a6',
      600: '#0d9488',
      700: '#0f766e',
      800: '#115e59',
      900: '#134e4a',
      950: '#042f2e',
    },
  },

  // Semantic colors
  semantic: {
    bg: {
      primary: '#0a0a0f',
      secondary: '#111118',
      tertiary: '#1a1a24',
      card: '#14141c',
      cardHover: '#1e1e2a',
    },
    text: {
      primary: '#fafafa',
      secondary: '#a1a1aa',
      muted: '#71717a',
      inverse: '#0a0a0f',
      accent: '#ff9f1c',
    },
    border: {
      primary: '#27272a',
      secondary: '#3f3f46',
      accent: '#ff9f1c40',
    },
    status: {
      success: '#00d4aa',
      warning: '#ff9f1c',
      error: '#ff4d4f',
      info: '#6366f1',
    },
  },

  // Gradient definitions
  gradients: {
    brand: 'linear-gradient(135deg, #6366f1 0%, #f97316 50%, #14b8a6 100%)',
    brandRadial: 'radial-gradient(ellipse at center, #6366f1 0%, #1a1a24 70%)',
    saffron: 'linear-gradient(135deg, #f97316 0%, #fb923c 100%)',
    mint: 'linear-gradient(135deg, #14b8a6 0%, #2dd4bf 100%)',
    mesh: 'linear-gradient(135deg, #6366f1 0%, #f97316 50%, #14b8a6 100%)',
    text: 'linear-gradient(135deg, #fafafa 0%, #a1a1aa 50%, #71717a 100%)',
    card: 'linear-gradient(145deg, #1e1e2a 0%, #14141c 100%)',
  },
} as const;

export const typography = {
  fonts: {
    display: '"Space Grotesk", "Noto Sans Devanagari", system-ui, sans-serif',
    body: '"Inter", "Noto Sans Devanagari", system-ui, sans-serif',
    mono: '"JetBrains Mono", "Fira Code", monospace',
  },
  sizes: {
    xs: '0.75rem',    // 12px
    sm: '0.875rem',   // 14px
    base: '1rem',     // 16px
    lg: '1.125rem',   // 18px
    xl: '1.25rem',    // 20px
    '2xl': '1.5rem',  // 24px
    '3xl': '1.875rem', // 30px
    '4xl': '2.25rem', // 36px
    '5xl': '3rem',    // 48px
    '6xl': '3.75rem', // 60px
    '7xl': '4.5rem',  // 72px
    '8xl': '6rem',    // 96px
    '9xl': '8rem',    // 128px
  },
  weights: {
    light: 300,
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
    extrabold: 800,
  },
  lineHeights: {
    tight: 1.1,
    snug: 1.375,
    normal: 1.5,
    relaxed: 1.625,
    loose: 2,
  },
  letterSpacings: {
    tighter: '-0.05em',
    tight: '-0.025em',
    normal: '0',
    wide: '0.025em',
    wider: '0.05em',
    widest: '0.1em',
  },
} as const;

export const spacing = {
  0: '0',
  1: '0.25rem',   // 4px
  2: '0.5rem',    // 8px
  3: '0.75rem',   // 12px
  4: '1rem',      // 16px
  5: '1.25rem',   // 20px
  6: '1.5rem',    // 24px
  8: '2rem',      // 32px
  10: '2.5rem',   // 40px
  12: '3rem',     // 48px
  16: '4rem',     // 64px
  20: '5rem',     // 80px
  24: '6rem',     // 96px
  32: '8rem',     // 128px
  40: '10rem',    // 160px
  48: '12rem',    // 192px
  56: '14rem',    // 224px
  64: '16rem',    // 256px
} as const;

export const borderRadius = {
  none: '0',
  sm: '0.25rem',   // 4px
  DEFAULT: '0.5rem', // 8px
  md: '0.75rem',   // 12px
  lg: '1rem',      // 16px
  xl: '1.5rem',    // 24px
  '2xl': '2rem',   // 32px
  full: '9999px',
} as const;

export const shadows = {
  sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
  DEFAULT: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
  md: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
  lg: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
  xl: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
  '2xl': '0 25px 50px -12px rgb(0 0 0 / 0.25)',
  inner: 'inset 0 2px 4px 0 rgb(0 0 0 / 0.05)',
  glow: '0 0 20px -5px rgb(99 102 241 / 0.5)',
  glowSaffron: '0 0 20px -5px rgb(249 115 22 / 0.5)',
  glowMint: '0 0 20px -5px rgb(20 184 166 / 0.5)',
  card: '0 4px 24px -4px rgb(0 0 0 / 0.4), 0 0 0 1px rgb(39 39 42 / 0.5)',
  cardHover: '0 8px 32px -4px rgb(0 0 0 / 0.5), 0 0 0 1px rgb(255 159 28 / 0.2)',
} as const;

export const transitions = {
  fast: '150ms cubic-bezier(0.4, 0, 0.2, 1)',
  normal: '250ms cubic-bezier(0.4, 0, 0.2, 1)',
  slow: '350ms cubic-bezier(0.4, 0, 0.2, 1)',
  slower: '500ms cubic-bezier(0.4, 0, 0.2, 1)',
  spring: '500ms cubic-bezier(0.34, 1.56, 0.64, 1)',
  bounce: '600ms cubic-bezier(0.68, -0.55, 0.265, 1.55)',
} as const;

// GSAP-specific configurations
export const gsapConfigs = {
  // Easing presets
  easings: {
    power1: 'power1.out',
    power2: 'power2.out',
    power3: 'power3.out',
    power4: 'power4.out',
    back: 'back.out(1.7)',
    elastic: 'elastic.out(1, 0.5)',
    bounce: 'bounce.out',
    expo: 'expo.out',
    circ: 'circ.out',
    sine: 'sine.out',
    custom: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
  },

  // Default durations
  durations: {
    instant: 0.1,
    fast: 0.3,
    normal: 0.5,
    slow: 0.8,
    slower: 1.2,
    slowest: 2,
  },

  // Stagger configurations
  stagger: {
    fast: 0.04,
    normal: 0.08,
    slow: 0.12,
    slower: 0.16,
    grid: { amount: 0.5, from: 'center' },
  },

  // ScrollTrigger defaults
  scrollTrigger: {
    toggleActions: 'play none none reverse',
    scrub: 1,
    markers: false,
    once: false,
  },

  // Magnetic button settings
  magnetic: {
    strength: 0.3,
    radius: 80,
    duration: 0.4,
    ease: 'power3.out',
  },

  // 3D card tilt
  tilt: {
    maxRotation: 8,
    perspective: 1000,
    duration: 0.3,
    ease: 'power2.out',
  },

  // Text reveal
  textReveal: {
    duration: 0.8,
    ease: 'power3.out',
    stagger: 0.04,
  },

  // Counter animation
  counter: {
    duration: 2,
    ease: 'power2.out',
  },
} as const;

export const breakpoints = {
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
} as const;

export const zIndices = {
  hide: -1,
  base: 0,
  dropdown: 1000,
  sticky: 1100,
  modal: 1300,
  popover: 1400,
  tooltip: 1500,
  toast: 1700,
  cursor: 9999,
} as const;

// Animation variants for Framer Motion
export const motionVariants = {
  fadeIn: {
    initial: { opacity: 0 },
    animate: { opacity: 1 },
    exit: { opacity: 0 },
    transition: { duration: 0.3, ease: 'easeOut' },
  },
  fadeInUp: {
    initial: { opacity: 0, y: 30 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: -20 },
    transition: { duration: 0.5, ease: [0.34, 1.56, 0.64, 1] },
  },
  fadeInDown: {
    initial: { opacity: 0, y: -30 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: 20 },
    transition: { duration: 0.5, ease: [0.34, 1.56, 0.64, 1] },
  },
  scaleIn: {
    initial: { opacity: 0, scale: 0.9 },
    animate: { opacity: 1, scale: 1 },
    exit: { opacity: 0, scale: 0.95 },
    transition: { duration: 0.4, ease: [0.34, 1.56, 0.64, 1] },
  },
  slideInLeft: {
    initial: { opacity: 0, x: -50 },
    animate: { opacity: 1, x: 0 },
    exit: { opacity: 0, x: 50 },
    transition: { duration: 0.5, ease: 'easeOut' },
  },
  slideInRight: {
    initial: { opacity: 0, x: 50 },
    animate: { opacity: 1, x: 0 },
    exit: { opacity: 0, x: -50 },
    transition: { duration: 0.5, ease: 'easeOut' },
  },
  staggerContainer: {
    initial: {},
    animate: {
      transition: {
        staggerChildren: 0.08,
        delayChildren: 0.1,
      },
    },
  },
  staggerItem: {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.5, ease: [0.34, 1.56, 0.64, 1] },
  },
} as const;

// Export all tokens as a single object
export const designTokens = {
  colors,
  typography,
  spacing,
  borderRadius,
  shadows,
  transitions,
  gsapConfigs,
  breakpoints,
  zIndices,
  motionVariants,
} as const;

export type DesignTokens = typeof designTokens;
export type Colors = typeof colors;
export type Typography = typeof typography;
export type Spacing = typeof spacing;
export type GSAPConfigs = typeof gsapConfigs;