/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        synchrony: {
          yellow:      '#F5C518',
          'yellow-hover': '#E2B310',
          gold:        '#FFD200',       // brighter site-button yellow
          'gold-hover':'#F0C400',
          cream:       '#FBF3D6',       // pale hero / section band
          'cream-deep':'#F7EBC0',
          ink:         '#1A1A1A',       // near-black headline text
          navy:        '#1E2A45',
          'navy-dark': '#0F1E36',
          'navy-light':'#2C3E60',
          slate:       '#6B7A99',
          'page-bg':   '#F3F5F9',
          'card-bg':   '#FFFFFF',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        card: '0 1px 4px 0 rgba(30,42,69,0.08), 0 4px 16px 0 rgba(30,42,69,0.06)',
        'card-hover': '0 4px 12px 0 rgba(30,42,69,0.12), 0 8px 24px 0 rgba(30,42,69,0.08)',
      },
    },
  },
  plugins: [],
}
