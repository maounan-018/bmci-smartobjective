<script setup>
// DashboardLayout.vue — Habillage commun des vues authentifiées : Navbar + contenu + footer.
// Reprend le footer de marque BMCI qui était dans App.tsx.
import Navbar from '@/components/Navbar.vue';
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
  </div>
</template>
