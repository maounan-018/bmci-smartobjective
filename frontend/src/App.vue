<script setup>
// App.vue — Racine de l'application. La logique d'auth/routage par rôle qui vivait
// ici (App.tsx) est désormais portée par le store Pinia + le router et ses gardes.
// App.vue ne fait plus que rendre la vue active via <router-view>.
</script>

<template>
  <router-view />
</template>
