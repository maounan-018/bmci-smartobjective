// stores/authStore.js — État d'authentification global (Pinia).
//
// Remplace le useState(user) qui vivait dans App.tsx. Centralise l'utilisateur
// courant et les actions login/logout/validateSession, consommées par le router
// (gardes de rôle), la Navbar et les vues.

import { defineStore } from 'pinia';
import { AuthService } from '@/services/authService';

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: AuthService.getStoredUser(), // réhydratation optimiste depuis le local
    sessionChecked: false, // vrai une fois validateSession() exécuté au démarrage
  }),

  getters: {
    isAuthenticated: (state) => !!state.user,
    role: (state) => state.user?.role || null,
  },

  actions: {
    // Vérifie la session auprès du backend (token toujours valide ?).
    async validateSession() {
      const user = await AuthService.validateSession();
      this.user = user;
      this.sessionChecked = true;
      return user;
    },

    async login(credentials) {
      const result = await AuthService.login(credentials);
      if (result.success) this.user = result.user;
      return result;
    },

    async logout() {
      await AuthService.logout();
      this.user = null;
    },
  },
});
