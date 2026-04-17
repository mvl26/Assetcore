/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Times New Roman"', 'Times', 'Georgia', 'serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        xs:   ['0.8125rem',  { lineHeight: '1.25rem' }],
        sm:   ['0.9375rem',  { lineHeight: '1.5rem' }],
        base: ['1.0625rem',  { lineHeight: '1.625rem' }],
        lg:   ['1.1875rem',  { lineHeight: '1.75rem' }],
        xl:   ['1.3125rem',  { lineHeight: '1.875rem' }],
        '2xl':['1.5rem',     { lineHeight: '2rem' }],
        '3xl':['1.875rem',   { lineHeight: '2.25rem' }],
      },
      colors: {
        brand: {
          50:  '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
          950: '#172554',
        },
        ink: {
          900: '#0d1117',
          800: '#161b22',
          700: '#21262d',
          600: '#30363d',
          500: '#484f58',
          400: '#6e7681',
          300: '#8b949e',
          200: '#b1bac4',
          100: '#c9d1d9',
          50:  '#f0f6fc',
        },
      },
      animation: {
        'fade-in':      'fadeIn 0.25s ease-out both',
        'slide-up':     'slideUp 0.3s ease-out both',
        'slide-in':     'slideIn 0.25s ease-out both',
        'scale-in':     'scaleIn 0.2s ease-out both',
        'shimmer':      'shimmer 1.6s linear infinite',
        'pulse-subtle': 'pulseSubtle 2.5s ease-in-out infinite',
        'bar-fill':     'barFill 0.7s cubic-bezier(.4,0,.2,1) both',
        'spin-slow':    'spin 2s linear infinite',
      },
      keyframes: {
        fadeIn:  { from: { opacity: '0' }, to: { opacity: '1' } },
        slideUp: {
          from: { opacity: '0', transform: 'translateY(10px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
        slideIn: {
          from: { opacity: '0', transform: 'translateX(-8px)' },
          to:   { opacity: '1', transform: 'translateX(0)' },
        },
        scaleIn: {
          from: { opacity: '0', transform: 'scale(0.96)' },
          to:   { opacity: '1', transform: 'scale(1)' },
        },
        shimmer: {
          '0%':   { backgroundPosition: '-400px 0' },
          '100%': { backgroundPosition: '400px 0' },
        },
        pulseSubtle: {
          '0%, 100%': { opacity: '1' },
          '50%':      { opacity: '0.6' },
        },
        barFill: {
          from: { transform: 'scaleX(0)', transformOrigin: 'left' },
          to:   { transform: 'scaleX(1)', transformOrigin: 'left' },
        },
      },
      boxShadow: {
        'card':       '0 1px 3px 0 rgba(0,0,0,.06), 0 0 0 1px rgba(0,0,0,.04)',
        'card-hover': '0 6px 16px 0 rgba(0,0,0,.10), 0 0 0 1px rgba(0,0,0,.04)',
        'sidebar':    '1px 0 0 0 rgba(255,255,255,.05)',
        'topbar':     '0 1px 0 0 #e2e8f0',
        'focus':      '0 0 0 3px rgba(37,99,235,.20)',
        'dropdown':   '0 8px 24px -4px rgba(0,0,0,.14), 0 0 0 1px rgba(0,0,0,.06)',
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
}
