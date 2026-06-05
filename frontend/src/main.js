// main.js — Point d'entrée de l'application Vue.
// Équivalent de l'ancien index.tsx (React). Crée l'app, branche Pinia (stores)
// et Vue Router (navigation + gardes de rôle), puis monte sur #app.

import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import router from './router';

const app = createApp(App);
app.use(createPinia());
app.use(router);
app.mount('#app');
