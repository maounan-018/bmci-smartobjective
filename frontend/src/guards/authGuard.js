// guards/authGuard.js — Garde de navigation globale (authentification + rôles).
//
// Remplace le routage conditionnel par rôle qui était codé en dur dans App.tsx.
// SÉCURITÉ : cette garde n'est qu'un confort d'affichage/navigation. Le backend
// FastAPI reste seul juge des accès aux données (permission_service.py).

import { useAuthStore } from '@/stores/authStore';
import { getDefaultPath } from '@/utils/permissions';

export async function authGuard(to) {
  const auth = useAuthStore();

  // Au tout premier chargement, on confirme la session auprès du backend.
  if (!auth.sessionChecked) {
    await auth.validateSession();
  }

  const isPublic = to.meta.public === true;

  // Route protégée sans utilisateur -> retour au login.
  if (!isPublic && !auth.isAuthenticated) {
    return { name: 'login' };
  }

  // Utilisateur connecté qui revient sur le login -> son dashboard par défaut.
  if (to.name === 'login' && auth.isAuthenticated) {
    return getDefaultPath(auth.role);
  }

  // Contrôle de rôle (meta.roles) -> redirection vers le dashboard autorisé.
  if (to.meta.roles && !to.meta.roles.includes(auth.role)) {
    return getDefaultPath(auth.role);
  }

  return true;
}
