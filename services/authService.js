/**
 * Service d'authentification pour ObjectifSMART-AI
 * Gère login, logout, session et appels API sécurisés
 */

const API_BASE = '/api';
const TOKEN_KEY = 'bmci_auth_token';
const USER_KEY = 'bmci_auth_user';

/**
 * Service d'authentification centralisé
 */
export const AuthService = {
  // ==================== TOKEN MANAGEMENT ====================

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

  // ==================== USER MANAGEMENT ====================

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

  // ==================== AUTH ENDPOINTS ====================

  /**
   * Récupère la liste des managers pour le select
   */
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

  /**
   * Inscription d'un nouveau collaborateur
   */
  async register(credentials) {
    try {
      const response = await fetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(credentials)
      });

      const data = await response.json();

      if (!response.ok) {
        return { success: false, error: data.detail || 'Erreur lors de l\'inscription' };
      }

      this.setToken(data.token);
      const user = {
        id: data.user.id,
        name: data.user.name,
        email: data.user.email,
        role: data.user.role,
        manager_id: data.user.manager_id,
        team: data.user.team
      };
      this.setStoredUser(user);

      return { success: true, user };
    } catch (error) {
      console.error('[AuthService] Erreur register:', error);
      return { success: false, error: 'Erreur de connexion au serveur' };
    }
  },

  /**
   * Connexion utilisateur
   */
  async login(credentials) {
    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(credentials)
      });

      const data = await response.json();

      if (!response.ok) {
        return { success: false, error: data.detail || 'Identifiants incorrects' };
      }

      this.setToken(data.token);
      const user = {
        id: data.user.id,
        name: data.user.name,
        email: data.user.email,
        role: data.user.role,
        manager_id: data.user.manager_id,
        team: data.user.team
      };
      this.setStoredUser(user);

      return { success: true, user };
    } catch (error) {
      console.error('[AuthService] Erreur login:', error);
      return { success: false, error: 'Erreur de connexion au serveur' };
    }
  },

  /**
   * Déconnexion
   */
  async logout() {
    try {
      const token = this.getToken();
      if (token) {
        await fetch(`${API_BASE}/auth/logout`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` }
        });
      }
    } catch (error) {
      console.error('[AuthService] Erreur logout:', error);
    } finally {
      this.clearToken();
    }
  },

  /**
   * Vérifie et rafraîchit la session
   */
  async validateSession() {
    const token = this.getToken();
    if (!token) return null;

    try {
      const response = await fetch(`${API_BASE}/auth/me`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!response.ok) {
        this.clearToken();
        return null;
      }

      const data = await response.json();
      const user = {
        id: data.user.id,
        name: data.user.name,
        email: data.user.email,
        role: data.user.role,
        manager_id: data.user.manager_id,
        team: data.user.team
      };
      this.setStoredUser(user);
      return user;
    } catch {
      this.clearToken();
      return null;
    }
  },

  // ==================== AUTHENTICATED API CALLS ====================

  /**
   * Headers avec authentification
   */
  getAuthHeaders() {
    const token = this.getToken();
    return {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    };
  },

  /**
   * Headers avec authentification sans Content-Type (pour FormData)
   */
  getAuthHeadersNoContentType() {
    const token = this.getToken();
    return {
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    };
  },

  /**
   * Fetch authentifié
   */
  async authFetch(url, options = {}) {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...this.getAuthHeaders(),
        ...(options.headers || {})
      }
    });

    // Si 401, déconnecter
    if (response.status === 401) {
      this.clearToken();
      window.location.href = '/';
    }

    return response;
  }
};

export default AuthService;
