<script setup>
// LoginView.vue — Sélection de rôle, connexion et inscription (migration de Login.tsx).
// Délègue l'auth au store Pinia (et donc au backend FastAPI). Aucune logique de
// sécurité côté client : juste de la validation de formulaire et de l'UX.
import { ref, watch, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/authStore';
import { UserRole, getDefaultPath } from '@/utils/permissions';
import { AuthService } from '@/services/authService';
import {
  UserCircle,
  Users,
  ShieldCheck,
  Loader2,
  AlertCircle,
  ChevronDown,
  Eye,
  EyeOff,
  LogIn,
  UserPlus,
} from 'lucide-vue-next';

const router = useRouter();
const auth = useAuthStore();

const mode = ref('select'); // 'select' | 'login' | 'register'
const selectedRole = ref(null);
const managers = ref([]);
const loadingManagers = ref(false);

const email = ref('');
const password = ref('');
const name = ref('');
const selectedManagerId = ref('');
const showPassword = ref(false);

const isLoading = ref(false);
const error = ref(null);
const checkingSession = ref(true);

const roles = [
  {
    role: UserRole.COLLAB,
    label: 'Collaborateur',
    desc: 'Définissez et analysez vos objectifs personnels.',
    icon: UserCircle,
    iconClass: 'text-emerald-500',
    bgColor: 'hover:border-emerald-500 hover:bg-emerald-50',
  },
  {
    role: UserRole.MANAGER,
    label: 'Manager',
    desc: "Gérez les objectifs de votre équipe et l'alignement.",
    icon: Users,
    iconClass: 'text-teal-500',
    bgColor: 'hover:border-teal-500 hover:bg-teal-50',
  },
  {
    role: UserRole.HR,
    label: 'RH',
    desc: "Pilotez la stratégie et le catalogue entreprise.",
    icon: ShieldCheck,
    iconClass: 'text-green-500',
    bgColor: 'hover:border-green-500 hover:bg-green-50',
  },
];

const currentRoleMeta = computed(() => roles.find((r) => r.role === selectedRole.value));

// Vérifie une session existante au chargement (réhydratation via le backend).
onMounted(async () => {
  const user = await auth.validateSession();
  if (user) {
    router.replace(getDefaultPath(user.role));
    return;
  }
  checkingSession.value = false;
});

// Charge les managers dès qu'un COLLAB entre dans le formulaire.
watch([selectedRole, mode], () => {
  if (selectedRole.value === UserRole.COLLAB && mode.value !== 'select') {
    loadManagers();
  }
});

async function loadManagers() {
  loadingManagers.value = true;
  managers.value = await AuthService.getManagers();
  loadingManagers.value = false;
}

function handleSelectRole(role) {
  selectedRole.value = role;
  mode.value = 'login';
  error.value = null;
  // Pré-remplissage des comptes de démonstration.
  if (role === UserRole.MANAGER) {
    email.value = 'manager.digital@bmci.co.ma';
    password.value = 'REDACTED_DEMO_PWD';
  } else if (role === UserRole.HR) {
    email.value = 'rh@bmci.co.ma';
    password.value = 'REDACTED_DEMO_PWD';
  } else {
    email.value = '';
    password.value = '';
  }
}

function redirectAfterAuth(user) {
  router.replace(getDefaultPath(user.role));
}

async function handleLogin() {
  error.value = null;
  if (!email.value || !password.value) {
    error.value = 'Veuillez remplir tous les champs.';
    return;
  }
  if (selectedRole.value === UserRole.COLLAB && !selectedManagerId.value) {
    error.value = 'Veuillez sélectionner votre manager.';
    return;
  }
  isLoading.value = true;
  const result = await auth.login({
    email: email.value,
    password: password.value,
    manager_id: selectedRole.value === UserRole.COLLAB ? selectedManagerId.value : undefined,
  });
  isLoading.value = false;
  if (result.success && result.user) redirectAfterAuth(result.user);
  else error.value = result.error || 'Erreur de connexion.';
}

async function handleRegister() {
  error.value = null;
  if (!email.value || !password.value || !name.value) {
    error.value = 'Veuillez remplir tous les champs.';
    return;
  }
  if (selectedRole.value === UserRole.COLLAB && !selectedManagerId.value) {
    error.value = 'Veuillez sélectionner votre manager.';
    return;
  }
  if (password.value.length < 6) {
    error.value = 'Le mot de passe doit contenir au moins 6 caractères.';
    return;
  }
  isLoading.value = true;
  const result = await auth.register({
    email: email.value,
    password: password.value,
    name: name.value,
    role: selectedRole.value || 'COLLAB',
    manager_id: selectedRole.value === UserRole.COLLAB ? selectedManagerId.value : undefined,
  });
  isLoading.value = false;
  if (result.success && result.user) redirectAfterAuth(result.user);
  else error.value = result.error || "Erreur lors de l'inscription.";
}

function handleBack() {
  mode.value = 'select';
  selectedRole.value = null;
  email.value = '';
  password.value = '';
  name.value = '';
  selectedManagerId.value = '';
  error.value = null;
}
</script>

<template>
  <!-- Vérification de session initiale -->
  <div v-if="checkingSession" class="min-h-screen flex items-center justify-center bg-slate-50">
    <div class="flex flex-col items-center gap-4">
      <Loader2 class="animate-spin text-emerald-600" :size="48" />
      <p class="text-slate-500">Vérification de la session...</p>
    </div>
  </div>

  <div v-else class="min-h-screen flex items-center justify-center bg-slate-50 p-6">
    <div class="max-w-4xl w-full">
      <!-- En-tête -->
      <div class="text-center mb-12">
        <div
          class="inline-flex bg-emerald-700 p-4 rounded-3xl mb-6 shadow-xl shadow-emerald-100 items-center justify-center"
        >
          <div class="grid grid-cols-2 gap-1">
            <div class="w-3 h-3 bg-white rounded-full"></div>
            <div class="w-3 h-3 bg-white rounded-full opacity-60"></div>
            <div class="w-3 h-3 bg-white rounded-full opacity-80"></div>
            <div class="w-3 h-3 bg-white rounded-full"></div>
          </div>
        </div>
        <h1 class="text-4xl font-black text-emerald-900 tracking-tight mb-2">BMCI</h1>
        <p class="text-slate-500 text-lg">Plateforme d'Analyse d'Objectifs SMART</p>
      </div>

      <!-- Sélection du rôle -->
      <div v-if="mode === 'select'" class="grid md:grid-cols-3 gap-6">
        <button
          v-for="item in roles"
          :key="item.role"
          :class="[
            'bg-white border-2 border-slate-200 p-8 rounded-2xl text-left transition-all duration-300 group transform hover:-translate-y-1 shadow-sm hover:shadow-md',
            item.bgColor,
          ]"
          @click="handleSelectRole(item.role)"
        >
          <div class="mb-4 bg-slate-50 inline-block p-3 rounded-xl transition-colors group-hover:bg-white">
            <component :is="item.icon" :class="item.iconClass" :size="32" />
          </div>
          <h3 class="text-xl font-bold text-slate-800 mb-2">{{ item.label }}</h3>
          <p class="text-slate-500 text-sm leading-relaxed">{{ item.desc }}</p>
        </button>
      </div>

      <!-- Formulaire connexion / inscription -->
      <div v-else-if="selectedRole" class="max-w-md mx-auto">
        <div class="bg-white p-8 rounded-2xl shadow-lg border border-slate-100">
          <button
            class="text-sm text-slate-500 hover:text-slate-700 mb-6 flex items-center gap-1"
            @click="handleBack"
          >
            ← Retour à la sélection
          </button>

          <div class="flex items-center gap-3 mb-6 pb-6 border-b border-slate-100">
            <component :is="currentRoleMeta?.icon" :class="currentRoleMeta?.iconClass" :size="32" />
            <div>
              <div class="font-bold text-slate-800">{{ currentRoleMeta?.label }}</div>
              <div class="text-xs text-slate-500">
                {{ mode === 'login' ? 'Connexion' : 'Inscription' }}
              </div>
            </div>
          </div>

          <div
            v-if="error"
            class="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 flex items-center gap-3 text-red-700"
          >
            <AlertCircle :size="20" />
            <p class="text-sm">{{ error }}</p>
          </div>

          <form class="space-y-4" @submit.prevent="mode === 'login' ? handleLogin() : handleRegister()">
            <div v-if="mode === 'register'">
              <label class="block text-xs font-bold text-slate-500 uppercase mb-2">Nom complet</label>
              <input
                v-model="name"
                type="text"
                class="w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 transition-all"
                placeholder="Jean Dupont"
              />
            </div>

            <div>
              <label class="block text-xs font-bold text-slate-500 uppercase mb-2">Email</label>
              <input
                v-model="email"
                type="email"
                class="w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 transition-all"
                placeholder="email@bmci.co.ma"
              />
            </div>

            <div>
              <label class="block text-xs font-bold text-slate-500 uppercase mb-2">Mot de passe</label>
              <div class="relative">
                <input
                  v-model="password"
                  :type="showPassword ? 'text' : 'password'"
                  class="w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 transition-all pr-12"
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  class="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  @click="showPassword = !showPassword"
                >
                  <EyeOff v-if="showPassword" :size="18" />
                  <Eye v-else :size="18" />
                </button>
              </div>
            </div>

            <div v-if="selectedRole === UserRole.COLLAB">
              <label class="block text-xs font-bold text-slate-500 uppercase mb-2">
                Choisir votre Manager <span class="text-red-500">*</span>
              </label>
              <div v-if="loadingManagers" class="flex items-center gap-2 text-slate-400 py-3">
                <Loader2 class="animate-spin" :size="16" />
                <span class="text-sm">Chargement des managers...</span>
              </div>
              <div v-else class="relative">
                <select
                  v-model="selectedManagerId"
                  class="w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 transition-all appearance-none bg-white"
                >
                  <option value="">-- Sélectionnez votre manager --</option>
                  <option v-for="mgr in managers" :key="mgr.id" :value="mgr.id">
                    {{ mgr.name }} - {{ mgr.team || mgr.email }}
                  </option>
                </select>
                <ChevronDown
                  class="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"
                  :size="18"
                />
              </div>
              <p class="text-xs text-slate-400 mt-2">
                Cette sélection est obligatoire pour garantir le suivi par votre manager.
              </p>
            </div>

            <button
              type="submit"
              :disabled="isLoading"
              class="w-full bg-emerald-600 text-white py-3 rounded-xl font-bold hover:bg-emerald-700 transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed mt-6"
            >
              <template v-if="isLoading">
                <Loader2 class="animate-spin" :size="18" />
                {{ mode === 'login' ? 'Connexion...' : 'Inscription...' }}
              </template>
              <template v-else>
                <LogIn v-if="mode === 'login'" :size="18" />
                <UserPlus v-else :size="18" />
                {{ mode === 'login' ? 'Se connecter' : "S'inscrire" }}
              </template>
            </button>
          </form>

          <div class="mt-6 text-center">
            <!-- Inscription publique autorisee pour COLLAB, MANAGER et HR. -->
            <p v-if="mode === 'login'" class="text-sm text-slate-500">
              Pas encore de compte ?
              <button
                class="text-emerald-600 font-bold hover:underline"
                @click="mode = 'register'; error = null"
              >
                S'inscrire
              </button>
            </p>
            <p v-else class="text-sm text-slate-500">
              Déjà inscrit ?
              <button
                class="text-emerald-600 font-bold hover:underline"
                @click="mode = 'login'; error = null"
              >
                Se connecter
              </button>
            </p>
          </div>

          <div
            v-if="(selectedRole === UserRole.MANAGER || selectedRole === UserRole.HR) && mode === 'login'"
            class="mt-6 p-4 bg-slate-50 rounded-xl"
          >
            <p class="text-xs text-slate-500 font-bold uppercase mb-2">Compte de test</p>
            <p class="text-xs text-slate-600">
              {{
                selectedRole === UserRole.MANAGER
                  ? 'Email: manager.digital@bmci.co.ma / MDP: REDACTED_DEMO_PWD'
                  : 'Email: rh@bmci.co.ma / MDP: REDACTED_DEMO_PWD'
              }}
            </p>
          </div>
        </div>
      </div>

      <!-- Pied de page -->
      <div class="mt-16 text-center text-slate-400 text-xs space-y-1">
        <div>Propulsé par Qwen AI • BMCI © 2026 • Groupe BNP Paribas</div>
        <div class="font-semibold uppercase tracking-wider text-[10px]">
          Développé par des étudiants de l'École Centrale Casablanca
        </div>
      </div>
    </div>
  </div>
</template>
