/** @type {import('tailwindcss').Config} */
export default {
    darkMode: ["class"],
    content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
  	extend: {
    colors: {
        border: 'var(--border)',
        input: 'var(--border)',
        ring: 'var(--primary)',
        background: 'var(--bg)',
        foreground: 'var(--fg)',
        primary: {
          DEFAULT: 'var(--primary)',
          foreground: 'var(--fg)'
        },
        secondary: {
          DEFAULT: '#7000ff', // Hardcoded but keep for now unless asked
          foreground: '#ffffff'
        },
        muted: {
          DEFAULT: 'var(--text-muted)',
          foreground: 'var(--fg-dim)'
        },
        accent: {
          DEFAULT: 'var(--accent)',
          foreground: '#ffffff'
        },
        card: {
          DEFAULT: 'var(--bg-card)',
          foreground: 'var(--fg)'
        }
      },
  		borderRadius: {
  			lg: 'var(--radius)',
  			md: 'calc(var(--radius) - 2px)',
  			sm: 'calc(var(--radius) - 4px)'
  		},
  		fontFamily: {
  			sans: ['Geist', 'Inter', 'sans-serif'],
  			mono: ['JetBrains Mono', 'monospace']
  		},
        animation: {
            'scanline': 'scanline 8s linear infinite',
            'pulse-slow': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
            'glow': 'glow 2s ease-in-out infinite alternate',
        },
        keyframes: {
            scanline: {
              '0%': { transform: 'translateY(-100%)' },
              '100%': { transform: 'translateY(1000%)' },
            },
            glow: {
              '0%': { boxShadow: '0 0 5px rgba(0, 242, 255, 0.2)' },
              '100%': { boxShadow: '0 0 20px rgba(0, 242, 255, 0.6)' },
            }
        },
  	}
  },
  plugins: [require("tailwindcss-animate")],
}

