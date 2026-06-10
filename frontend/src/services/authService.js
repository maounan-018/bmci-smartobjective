// services/authService.js — Authentification par cookie de session HttpOnly.
//
// Le token de session vit dans un cookie **HttpOnly** posé par le backend : il
// n'est JAMAIS accessible au JavaScript (donc involable par XSS). Le frontend ne
// stocke que le PROFIL utilisateur (non sensible) pour l'affichage.
//
// Les requêtes mutantes (POST/PUT/PATCH/DELETE) envoient le jeton CSRF
// (double-submit) : on lit le cookie non-HttpOnly `csrf_token` et on le renvoie
// dans l'en-tête `X-CSRF-Token`. Tous les appels utilisent `credentials: 'include'`
// pour que le navigateur transmette les cookies.

const API_BASE = '/api';
const USER_KEY = 'bmci_auth_user';
const CSRF_COOKIE = 'csrf_token';
const MUTATING = ['POST', 'PUT', 'PATCH', 'DELETE'];

function readCookie(name) {
  const m = document.cookie.match('(?:^|; )' + name + '=([^;]*)');
  return m ? decodeURIComponent(m[1]) : '';
}

export const AuthService = {
  // ==================== PROFIL UTILISATEUR (non sensible) ====================
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
  clearStoredUser() {
    localStorage.removeItem(USER_KEY);
  },

  // Jeton CSRF (cookie non-HttpOnly posé par le backend).
  csrfToken() {
    return readCookie(CSRF_COOKIE);
  },
  // En-têtes pour un upload multipart authentifié : CSRF uniquement
  // (pas de Content-Type, fixé automatiquement par le navigateur pour FormData).
  uploadHeaders() {
    return { 'X-CSRF-Token': this.csrfToken() };
  },

  // ==================== SSO SAML ====================
  ssoLoginUrl() {
    return `${API_BASE}/auth/saml/login`;
  },
  // Échange le code SSO à usage unique (reçu en query) : le backend pose alors
  // le cookie de session. Le token ne transite jamais par le JS ni l'URL.
  async exchangeSsoCode(code) {
    try {
      const response = await fetch(`${API_BASE}/auth/saml/exchange`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code }),
      });
      return response.ok;
    } catch {
      return false;
    }
  },
  // État du SSO côté backend : { enabled, simulation }.
  async getSsoStatus() {
    try {
      const response = await fetch(`${API_BASE}/auth/saml/status`);
      if (!response.ok) return { enabled: false, simulation: false };
      const data = await response.json();
      return { enabled: !!data.enabled, simulation: !!data.simulation };
    } catch {
      return { enabled: false, simulation: false };
    }
  },

  // ==================== AUTH ====================
  async login(credentials) {
    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(credentials),
      });
      const data = await response.json();
      if (!response.ok) {
        return { success: false, error: data.detail || 'Identifiants incorrects' };
      }
      const user = this._normalizeUser(data.user);
      this.setStoredUser(user);
      return { success: true, user };
    } catch (error) {
      console.error('[AuthService] Erreur login:', error);
      return { success: false, error: 'Erreur de connexion au serveur' };
    }
  },

  async logout() {
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'X-CSRF-Token': this.csrfToken() },
      });
    } catch (error) {
      console.error('[AuthService] Erreur logout:', error);
    } finally {
      this.clearStoredUser();
    }
  },

  // Réhydrate la session au démarrage via le cookie (aucun token côté JS).
  async validateSession() {
    try {
      const response = await fetch(`${API_BASE}/auth/me`, { credentials: 'include' });
      if (!response.ok) {
        this.clearStoredUser();
        return null;
      }
      const data = await response.json();
      const user = this._normalizeUser(data.user);
      this.setStoredUser(user);
      return user;
    } catch {
      this.clearStoredUser();
      return null;
    }
  },

  // ==================== APPELS API AUTHENTIFIÉS ====================
  // Fetch authentifié : envoie le cookie + le jeton CSRF sur les méthodes mutantes,
  // et déconnecte automatiquement sur 401.
  async authFetch(url, options = {}) {
    const method = (options.method || 'GET').toUpperCase();
    const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
    if (MUTATING.includes(method)) {
      headers['X-CSRF-Token'] = this.csrfToken();
    }
    const response = await fetch(url, { ...options, credentials: 'include', headers });
    if (response.status === 401) {
      this.clearStoredUser();
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
