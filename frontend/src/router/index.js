// router/index.js — Définition des routes et branchement de la garde globale.
//
// Migration de la logique de routage d'App.tsx (HashRouter + routes par rôle) vers
// Vue Router. On garde le mode "hash" pour rester iso-comportement avec l'app React
// (URLs en #/...) et éviter toute config serveur de fallback SPA.

import { createRouter, createWebHashHistory } from 'vue-router';
import { authGuard } from '@/guards/authGuard';
import { UserRole } from '@/utils/permissions';

import LoginView from '@/views/LoginView.vue';
import CollaboratorDashboard from '@/views/CollaboratorDashboard.vue';
import ManagerDashboard from '@/views/ManagerDashboard.vue';
import HrDashboard from '@/views/HrDashboard.vue';
import SmartAnalysisView from '@/views/SmartAnalysisView.vue';

const routes = [
  { path: '/', name: 'login', component: LoginView, meta: { public: true } },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: CollaboratorDashboard,
    meta: { roles: [UserRole.COLLAB] },
  },
  {
    path: '/manager',
    name: 'manager',
    component: ManagerDashboard,
    meta: { roles: [UserRole.MANAGER] },
  },
  {
    path: '/hr',
    name: 'hr',
    component: HrDashboard,
    meta: { roles: [UserRole.HR] },
  },
  {
    path: '/smart-analysis',
    name: 'smart-analysis',
    component: SmartAnalysisView,
    meta: { roles: [UserRole.HR] },
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
];

const router = createRouter({
  history: createWebHashHistory(),
  routes,
});

router.beforeEach(authGuard);

export default router;
