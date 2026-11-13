import type { Config } from 'tailwindcss'
import defaultTheme from 'tailwindcss/defaultTheme'
import typography from '@tailwindcss/typography'

export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Exact brand palette. Never add other hues.
        night: '#243341',
        alabaster: '#F0F2F5',
        ocean: '#205D96',
        steel: '#294B6C',
        glacial: '#B5DBFF',
        ice: '#E0F0FF',
        cream: '#FFEDCF',
        champagne: '#FFEBC9',
        sage: '#519A76',
        // Semantic tokens: values switch with the `dark` class (see index.css)
        app: 'var(--c-bg)',
        side: 'var(--c-side)',
        surface: 'var(--c-surface)',
        card: 'var(--c-card)',
        ink: 'var(--c-ink)',
        'ink-muted': 'var(--c-ink-muted)',
        line: 'var(--c-line)',
        accent: 'var(--c-accent)',
        'accent-soft': 'var(--c-accent-soft)',
        action: 'var(--c-action)',
        'action-hover': 'var(--c-action-hover)',
        'action-ink': 'var(--c-action-ink)',
        badge: 'var(--c-badge)',
        'badge-ink': 'var(--c-badge-ink)',
        mark: 'var(--c-mark)',
        bubble: 'var(--c-bubble)',
      },
      fontFamily: {
        sans: ['"Inter Variable"', ...defaultTheme.fontFamily.sans],
        display: ['"Fraunces Variable"', ...defaultTheme.fontFamily.serif],
      },
      boxShadow: {
        float:
          '0 1px 2px rgb(36 51 65 / 0.06), 0 12px 28px -12px rgb(36 51 65 / 0.22)',
        glass: '0 24px 60px -20px rgb(0 0 0 / 0.45)',
      },
      keyframes: {
        'fade-up': {
          '0%': { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'none' },
        },
        'mark-pulse': {
          '0%': { boxShadow: '0 0 0 0 rgb(32 93 150 / 0.45)' },
          '100%': { boxShadow: '0 0 0 14px rgb(32 93 150 / 0)' },
        },
        'dot-pulse': {
          '0%,100%': { opacity: '1' },
          '50%': { opacity: '0.35' },
        },
        'sheet-in-left': {
          from: { transform: 'translateX(-100%)' },
          to: { transform: 'none' },
        },
        'sheet-in-right': {
          from: { transform: 'translateX(100%)' },
          to: { transform: 'none' },
        },
      },
      animation: {
        'fade-up': 'fade-up .35s ease-out both',
        'mark-pulse': 'mark-pulse 1.4s ease-out 1',
        'dot-pulse': 'dot-pulse 1.6s ease-in-out infinite',
        'sheet-in-left': 'sheet-in-left .28s cubic-bezier(.22,1,.36,1) both',
        'sheet-in-right': 'sheet-in-right .28s cubic-bezier(.22,1,.36,1) both',
      },
    },
  },
  plugins: [typography],
} satisfies Config
