<script setup>
// DashboardLayout.vue — Habillage commun des vues authentifiées : Navbar + contenu + footer.
// Reprend le footer de marque BMCI qui était dans App.tsx.
// Injecte aussi le Coach IA (assistant) en flottant — réservé MANAGER/COLLAB.
import Navbar from '@/components/Navbar.vue';
import ChatCoach from '@/components/ChatCoach.vue';
import { useAuthStore } from '@/stores/authStore';

const auth = useAuthStore();
</script>

<template>
  <div class="min-h-screen flex flex-col bg-slate-50">
    <Navbar />
    <main class="flex-1">
      <slot />
    </main>
    <footer class="text-center text-slate-400 text-xs py-6 space-y-1 border-t border-slate-100">
      <div>Propulsé par Qwen AI • BMCI © 2026 • Groupe BNP Paribas</div>
      <div class="font-semibold uppercase tracking-wider text-[10px]">
        Développé par des étudiants de l'École Centrale Casablanca
      </div>
    </footer>

    <!-- Assistant Coach IA (flottant) — Manager, Collaborateur et RH. -->
    <ChatCoach v-if="auth.isAuthenticated && ['MANAGER', 'COLLAB', 'HR'].includes(auth.role)" />
  </div>
</template>
