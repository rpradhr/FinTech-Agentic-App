/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Roboto', '-apple-system', 'sans-serif'],
        display: ['Google Sans', 'Roboto', 'sans-serif'],
        mono: ['Roboto Mono', 'monospace'],
      },
      colors: {
        md: {
          primary:         '#1a73e8',
          'primary-light': '#e8f0fe',
          'primary-dark':  '#1557b0',
          secondary:       '#34a853',
          error:           '#ea4335',
          warning:         '#fbbc04',
          surface:         '#ffffff',
          'surface-var':   '#f8f9fa',
          'on-surface':    '#202124',
          'on-surface-2':  '#5f6368',
          outline:         '#dadce0',
          'outline-var':   '#e8eaed',
        },
        google: {
          blue:   '#1a73e8',
          red:    '#ea4335',
          yellow: '#fbbc04',
          green:  '#34a853',
        },
      },
      borderRadius: {
        '2xl': '16px',
        '3xl': '24px',
        '4xl': '32px',
      },
      animation: {
        'fade-in':    'fadeIn 200ms ease-out',
        'slide-up':   'slideUp 300ms cubic-bezier(0.2,0,0,1)',
        'pulse-dot':  'pulseDot 1.4s infinite ease-in-out',
        'typing':     'typing 1s steps(3) infinite',
      },
      keyframes: {
        fadeIn:   { from: { opacity: '0' }, to: { opacity: '1' } },
        slideUp:  { from: { opacity: '0', transform: 'translateY(12px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
        pulseDot: {
          '0%, 80%, 100%': { transform: 'scale(0)', opacity: '0.5' },
          '40%':           { transform: 'scale(1)', opacity: '1' },
        },
        typing: {
          '0%':   { content: '"."' },
          '33%':  { content: '".."' },
          '66%':  { content: '"..."' },
          '100%': { content: '"."' },
        },
      },
      boxShadow: {
        'md-1': '0 1px 2px rgba(60,64,67,.3), 0 1px 3px 1px rgba(60,64,67,.15)',
        'md-2': '0 1px 2px rgba(60,64,67,.3), 0 2px 6px 2px rgba(60,64,67,.15)',
        'md-3': '0 4px 8px 3px rgba(60,64,67,.15), 0 1px 3px rgba(60,64,67,.3)',
        'md-4': '0 6px 10px 4px rgba(60,64,67,.15), 0 2px 3px rgba(60,64,67,.3)',
      },
    },
  },
  plugins: [],
};
