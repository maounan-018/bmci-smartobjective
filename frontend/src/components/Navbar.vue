<script setup>
// Navbar.vue — Barre de navigation (migration de Navbar.tsx).
// Les liens sont filtrés par rôle ; la déconnexion délègue au store d'auth.
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/authStore';
import { UserRole } from '@/utils/permissions';
import {
  LayoutDashboard,
  Briefcase,
  Users,
  LogOut,
  ClipboardCheck,
  ShieldCheck,
} from 'lucide-vue-next';

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const user = computed(() => auth.user);
const isAdmin = computed(() => user.value?.role === UserRole.ADMIN);

// L'admin n'a qu'une seule vue (/admin) : cliquer le logo ne doit pas le laisser
// « rebondir » sur /admin. On s'en sert de sortie propre vers l'écran de connexion
// (déconnexion). Pour les autres rôles, le logo reste le retour à l'accueil.
async function onLogoClick() {
  if (isAdmin.value) {
    await auth.logout();
  }
  router.push('/');
}

const links = computed(() =>
  [
    { to: '/dashboard', label: 'Mon Espace', icon: LayoutDashboard, roles: [UserRole.COLLAB] },
    { to: '/manager', label: 'Mon Dashboard', icon: Users, roles: [UserRole.MANAGER] },
    { to: '/hr', label: 'Dashboard RH', icon: Briefcase, roles: [UserRole.HR] },
    { to: '/smart-analysis', label: 'Mon Analyse', icon: ClipboardCheck, roles: [UserRole.HR] },
    { to: '/admin', label: 'Administration', icon: ShieldCheck, roles: [UserRole.ADMIN] },
  ].filter((link) => user.value && link.roles.includes(user.value.role)),
);

async function handleLogout() {
  await auth.logout();
  router.push('/');
}
</script>

<template>
  <nav
    v-if="user"
    class="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between sticky top-0 z-50 shadow-sm"
  >
    <div class="flex items-center gap-8">
      <button
        type="button"
        @click="onLogoClick"
        :title="isAdmin ? 'Retour à la connexion' : 'Accueil'"
        class="flex items-center gap-2"
      >
        <div class="bg-emerald-700 p-1.5 rounded-lg flex items-center justify-center">
          <div class="grid grid-cols-2 gap-0.5">
            <div class="w-1.5 h-1.5 bg-white rounded-full"></div>
            <div class="w-1.5 h-1.5 bg-white rounded-full opacity-60"></div>
            <div class="w-1.5 h-1.5 bg-white rounded-full opacity-80"></div>
            <div class="w-1.5 h-1.5 bg-white rounded-full"></div>
          </div>
        </div>
        <div class="flex flex-col leading-tight">
          <span class="font-black text-xl tracking-tight text-emerald-800">BMCI</span>
          <span class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
            Objectif SMART
          </span>
        </div>
      </button>

      <div class="hidden md:flex items-center gap-1">
        <router-link
          v-for="link in links"
          :key="link.to"
          :to="link.to"
          :class="[
            'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
            route.path === link.to
              ? 'bg-emerald-50 text-emerald-700'
              : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900',
          ]"
        >
          <component :is="link.icon" :size="20" />
          {{ link.label }}
        </router-link>
      </div>
    </div>

    <div class="flex items-center gap-4">
      <div class="flex-col items-end mr-2 hidden sm:flex">
        <span class="text-sm font-semibold text-slate-800">{{ user.name }}</span>
        <span
          class="text-[10px] px-1.5 py-0.5 bg-emerald-100 text-emerald-700 rounded uppercase font-bold"
        >
          {{ user.role }}
        </span>
      </div>
      <button
        class="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all"
        title="Déconnexion"
        @click="handleLogout"
      >
        <LogOut :size="20" />
      </button>
    </div>
  </nav>
</template>
