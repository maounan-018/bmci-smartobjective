/** @type {import('tailwindcss').Config} */
// Configuration Tailwind (build local, sans CDN).
// `content` liste les fichiers scannés pour ne générer que les classes utilisées
// -> CSS final minimal, livré dans le build (offline, aucun appel Internet).
export default {
  content: ['./index.html', './src/**/*.{vue,js}'],
  theme: {
    extend: {
      // Inter auto-hébergée (cf. @fontsource/inter importé dans main.js), avec
      // repli sur des polices système si jamais elle n'était pas chargée.
      fontFamily: {
        sans: [
          'Inter',
          'ui-sans-serif',
          'system-ui',
          '-apple-system',
          'Segoe UI',
          'Roboto',
          'Helvetica Neue',
          'Arial',
          'sans-serif',
        ],
      },
    },
  },
  plugins: [],
};
