// main.js — Point d'entrée de l'application Vue.
// Équivalent de l'ancien index.tsx (React). Crée l'app, branche Pinia (stores)
// et Vue Router (navigation + gardes de rôle), puis monte sur #app.

// Police Inter auto-hébergée (offline) — les graisses utilisées par l'UI.
import '@fontsource/inter/300.css';
import '@fontsource/inter/400.css';
import '@fontsource/inter/500.css';
import '@fontsource/inter/600.css';
import '@fontsource/inter/700.css';
// Tailwind compilé localement (remplace le CDN cdn.tailwindcss.com).
import './style.css';

import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import router from './router';

const app = createApp(App);
app.use(createPinia());
app.use(router);
app.mount('#app');
