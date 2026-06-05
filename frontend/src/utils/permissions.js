// utils/permissions.js — Constantes de rôles et helpers d'autorisation côté UI.
//
// IMPORTANT : ces helpers ne servent qu'à ADAPTER l'affichage (masquer un menu,
// rediriger). La SÉCURITÉ réelle est imposée par le backend Python FastAPI
// (services/permission_service.py). Ne jamais s'appuyer dessus pour protéger des données.

export const UserRole = {
  COLLAB: 'COLLAB',
  MANAGER: 'MANAGER',
  HR: 'HR',
  ADMIN: 'ADMIN',
};

// Chemin d'accueil par défaut selon le rôle (équivalent de getDefaultPath dans App.tsx).
export function getDefaultPath(role) {
  switch (role) {
    case UserRole.MANAGER:
      return '/manager';
    case UserRole.HR:
      return '/hr';
    case UserRole.COLLAB:
    default:
      return '/dashboard';
  }
}

// Vrai si le rôle de l'utilisateur fait partie des rôles autorisés.
export function hasRole(user, allowedRoles) {
  return !!user && allowedRoles.includes(user.role);
}
