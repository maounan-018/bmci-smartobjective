// services/authService.js — Authentification et appels API authentifiés.
//
// Migration fidèle de l'ancien authService.ts (React). Conserve le mécanisme
// par token Bearer attendu par le backend FastAPI actuel (Authorization: Bearer ...).
// Le token reste la SOURCE de session ; le backend reste la source de vérité sécurité.
//
// NOTE migration future SSO/cookies : quand le backend exposera des cookies
// HttpOnly, il suffira de retirer la gestion localStorage ici sans toucher aux vues.

const API_BASE = '/api';
const TOKEN_KEY = 'bmci_auth_token';
const USER_KEY = 'bmci_auth_user';

export const AuthService = {
  // ==================== GESTION DU TOKEN ====================
  getToken() {
    return localStorage.getItem(TOKEN_KEY);
  },
  setToken(token) {
    localStorage.setItem(TOKEN_KEY, token);
  },
  clearToken() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },

  // ==================== GESTION DE L'UTILISATEUR ====================
  getStoredUser() {
    try {
      const data = localStorage.getItem(USER_KEY);
      return data ? JSON.parse(data) : null;
    } catch {
      return null;
    }
  },
  setStoredUser(user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  },
  isAuthenticated() {
    return !!this.getToken() && !!this.getStoredUser();
  },

  // ==================== SSO SAML ====================
  // URL backend qui démarre le SSO (redirige vers l'IdP de la banque).
  ssoLoginUrl() {
    return `${API_BASE}/auth/saml/login`;
  },
  // Le SSO est-il configuré côté backend ? (pour afficher/masquer le bouton SSO)
  async isSsoEnabled() {
    try {
      const response = await fetch(`${API_BASE}/auth/saml/status`);
      if (!response.ok) return false;
      const data = await response.json();
      return !!data.enabled;
    } catch {
      return false;
    }
  },

  // ==================== ENDPOINTS D'AUTH ====================

  // Liste des managers (pour le select à l'inscription d'un COLLAB).
  async getManagers() {
    try {
      const response = await fetch(`${API_BASE}/managers`);
      if (!response.ok) throw new Error('Erreur serveur');
      const data = await response.json();
      return data.managers || [];
    } catch (error) {
      console.error('[AuthService] Erreur getManagers:', error);
      return [];
    }
  },

  // Inscription d'un nouveau collaborateur.
  async register(credentials) {
    try {
      const response = await fetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(credentials),
      });
      const data = await response.json();
      if (!response.ok) {
        return { success: false, error: data.detail || "Erreur lors de l'inscription" };
      }
      this.setToken(data.token);
      const user = this._normalizeUser(data.user);
      this.setStoredUser(user);
      return { success: true, user };
    } catch (error) {
      console.error('[AuthService] Erreur register:', error);
      return { success: false, error: 'Erreur de connexion au serveur' };
    }
  },

  // Connexion utilisateur.
  async login(credentials) {
    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(credentials),
      });
      const data = await response.json();
      if (!response.ok) {
        return { success: false, error: data.detail || 'Identifiants incorrects' };
      }
      this.setToken(data.token);
      const user = this._normalizeUser(data.user);
      this.setStoredUser(user);
      return { success: true, user };
    } catch (error) {
      console.error('[AuthService] Erreur login:', error);
      return { success: false, error: 'Erreur de connexion au serveur' };
    }
  },

  // Déconnexion volontaire (invalide la session côté backend + nettoie le local).
  async logout() {
    try {
      const token = this.getToken();
      if (token) {
        await fetch(`${API_BASE}/auth/logout`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
        });
      }
    } catch (error) {
      console.error('[AuthService] Erreur logout:', error);
    } finally {
      this.clearToken();
    }
  },

  // Réhydrate la session au démarrage : vérifie le token auprès de /auth/me.
  async validateSession() {
    const token = this.getToken();
    if (!token) return null;
    try {
      const response = await fetch(`${API_BASE}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        this.clearToken();
        return null;
      }
      const data = await response.json();
      const user = this._normalizeUser(data.user);
      this.setStoredUser(user);
      return user;
    } catch {
      this.clearToken();
      return null;
    }
  },

  // ==================== APPELS API AUTHENTIFIÉS ====================
  getAuthHeaders() {
    const token = this.getToken();
    return {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
  },
  getAuthHeadersNoContentType() {
    const token = this.getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  },

  // Fetch authentifié : ajoute le token et déconnecte automatiquement sur 401.
  async authFetch(url, options = {}) {
    const response = await fetch(url, {
      ...options,
      headers: { ...this.getAuthHeaders(), ...(options.headers || {}) },
    });
    if (response.status === 401) {
      this.clearToken();
      window.location.href = '/';
    }
    return response;
  },

  // Normalise le profil utilisateur renvoyé par le backend.
  _normalizeUser(u) {
    return {
      id: u.id,
      name: u.name,
      email: u.email,
      role: u.role,
      manager_id: u.manager_id,
      team: u.team,
    };
  },
};

export default AuthService;
