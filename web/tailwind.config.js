/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        carbon:       '#0d0d0d',
        snow:         '#ffffff',
        fog:          '#f9f9f9',
        pewter:       '#5d5d5d',
        'arctic-mist':'#ececec',
        'link-blue':  '#007aff',
        success:      '#00a86b',
        warning:      '#f5a623',
        danger:       '#e74c3c',
      },
      fontFamily: {
        sans:  ['"Plus Jakarta Sans"', 'ui-sans-serif', 'system-ui', '-apple-system', 'sans-serif'],
        serif: ['"DM Serif Display"', 'Georgia', 'Cambria', 'serif'],
        mono:  ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      borderRadius: {
        DEFAULT: '10px',
        input:   '28px',
        pill:    '9999px',
      },
    },
  },
  plugins: [],
}
