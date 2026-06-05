<script setup>
// AlignmentChart.vue — Donut d'alignement (score %). Migration d'AlignmentChart.tsx.
// La version React utilisait recharts ; ici un simple SVG natif suffit (zéro dépendance,
// même rendu : anneau émeraude rempli proportionnellement au score).
import { computed } from 'vue';

const props = defineProps({
  score: { type: Number, default: 0 },
});

const RADIUS = 37.5; // rayon moyen de l'anneau (inner 30 / outer 45 -> trait de 15)
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

const dashOffset = computed(() => {
  const clamped = Math.max(0, Math.min(100, props.score));
  return CIRCUMFERENCE * (1 - clamped / 100);
});
</script>

<template>
  <div class="w-32 h-32 relative">
    <svg viewBox="0 0 100 100" class="w-full h-full -rotate-90">
      <circle cx="50" cy="50" :r="RADIUS" fill="none" stroke="#f1f5f9" stroke-width="15" />
      <circle
        cx="50"
        cy="50"
        :r="RADIUS"
        fill="none"
        stroke="#059669"
        stroke-width="15"
        :stroke-dasharray="CIRCUMFERENCE"
        :stroke-dashoffset="dashOffset"
        stroke-linecap="butt"
      />
    </svg>
    <div class="absolute inset-0 flex items-center justify-center flex-col">
      <span class="text-xl font-bold text-emerald-800">{{ score }}%</span>
      <span class="text-[10px] text-emerald-500 font-bold uppercase">Aligné</span>
    </div>
  </div>
</template>
