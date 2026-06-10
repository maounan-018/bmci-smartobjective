<script setup>
// LoginView.vue — Page d'accueil : SSO d'entreprise OU connexion locale (dev).
//
// SSO actif (réel ou simulation) => page épurée avec UNIQUEMENT le bouton SSO.
//   Plus d'inscription : les comptes sont créés par l'annuaire (JIT provisioning).
// SSO inactif (dev local) => connexion email/mot de passe sur les comptes seedés.
//
// Aucune logique de sécurité côté client : juste de la validation de formulaire et de l'UX.
import { ref, onMounted, computed } from 'vue';
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
  Eye,
  EyeOff,
  LogIn,
} from 'lucide-vue-next';

const router = useRouter();
const auth = useAuthStore();

const mode = ref('select'); // 'select' | 'login'
const selectedRole = ref(null);

const email = ref('');
const password = ref('');
const showPassword = ref(false);

const isLoading = ref(false);
const error = ref(null);
const checkingSession = ref(true);
const ssoEnabled = ref(false);     // SSO actif (réel OU simulation) => page SSO uniquement
const ssoSimulation = ref(false);  // true en mode simulation (dev)

// Démarre le SSO : le backend redirige le navigateur vers l'IdP de la banque.
function startSso() {
  window.location.href = AuthService.ssoLoginUrl();
}

const roles = [
  {
    role: UserRole.COLLAB,
    label: 'Collaborateur',
    desc: 'Définissez et analysez vos objectifs personnels.',
    icon: UserCircle,
    iconClass: 'text-emerald-500',
    bgColor: 'hover:border-emerald-500 hover:bg-emerald-50',
    demo: { email: 'collab@bmci.ma', password: 'REDACTED_DEMO_PWD' },
  },
  {
    role: UserRole.MANAGER,
    label: 'Manager',
    desc: "Gérez les objectifs de votre équipe et l'alignement.",
    icon: Users,
    iconClass: 'text-teal-500',
    bgColor: 'hover:border-teal-500 hover:bg-teal-50',
    demo: { email: 'manager@bmci.ma', password: 'REDACTED_DEMO_PWD' },
  },
  {
    role: UserRole.HR,
    label: 'RH',
    desc: 'Pilotez la stratégie et le catalogue entreprise.',
    icon: ShieldCheck,
    iconClass: 'text-green-500',
    bgColor: 'hover:border-green-500 hover:bg-green-50',
    demo: { email: 'hr@bmci.ma', password: 'REDACTED_DEMO_PWD' },
  },
];

const currentRoleMeta = computed(() => roles.find((r) => r.role === selectedRole.value));

// Vérifie une session existante au chargement (réhydratation via le backend).
onMounted(async () => {
  // Retour d'un login SSO : token (succès) ou flag d'erreur passés en query.
  const params = new URLSearchParams(window.location.search);
  const ssoToken = params.get('sso_token');
  const ssoErr = params.get('sso_error');
  if (ssoToken) {
    AuthService.setToken(ssoToken);
  } else if (ssoErr) {
    error.value = "Échec de la connexion SSO. Réessayez ou contactez l'administrateur.";
  }
  if (ssoToken || ssoErr) {
    // Nettoie l'URL (retire le query) en conservant le hash de route.
    window.history.replaceState({}, document.title, window.location.pathname + window.location.hash);
  }

  const user = await auth.validateSession();
  if (user) {
    router.replace(getDefaultPath(user.role));
    return;
  }
  checkingSession.value = false;
  const sso = await AuthService.getSsoStatus();
  ssoEnabled.value = sso.enabled;
  ssoSimulation.value = sso.simulation;
});

function handleSelectRole(role) {
  selectedRole.value = role;
  mode.value = 'login';
  error.value = null;
  // Pré-remplissage du compte de démonstration seedé.
  const meta = roles.find((r) => r.role === role);
  email.value = meta?.demo?.email || '';
  password.value = meta?.demo?.password || '';
}

async function handleLogin() {
  error.value = null;
  if (!email.value || !password.value) {
    error.value = 'Veuillez remplir tous les champs.';
    return;
  }
  isLoading.value = true;
  const result = await auth.login({ email: email.value, password: password.value });
  isLoading.value = false;
  if (result.success && result.user) router.replace(getDefaultPath(result.user.role));
  else error.value = result.error || 'Erreur de connexion.';
}

function handleBack() {
  mode.value = 'select';
  selectedRole.value = null;
  email.value = '';
  password.value = '';
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

      <!-- SSO actif (réel ou simulation) : page épurée, AUCUNE inscription locale -->
      <div v-if="ssoEnabled" class="max-w-md mx-auto">
        <div
          v-if="error"
          class="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 flex items-center gap-3 text-red-700"
        >
          <AlertCircle :size="20" />
          <p class="text-sm">{{ error }}</p>
        </div>

        <div class="bg-white p-8 rounded-2xl shadow-lg border border-slate-100 text-center">
          <div class="inline-flex bg-emerald-50 p-4 rounded-2xl mb-5">
            <ShieldCheck class="text-emerald-600" :size="36" />
          </div>
          <h2 class="text-xl font-bold text-slate-800 mb-2">Connexion sécurisée</h2>
          <p class="text-slate-500 text-sm mb-6">
            Connectez-vous avec votre compte d'entreprise BMCI.
            Votre rôle est attribué automatiquement par l'annuaire.
          </p>

          <button
            class="w-full bg-emerald-600 text-white py-3 rounded-xl font-bold hover:bg-emerald-700 transition-all flex items-center justify-center gap-2"
            @click="startSso"
          >
            <LogIn :size="18" />
            Se connecter avec le SSO BMCI
          </button>

          <div
            v-if="ssoSimulation"
            class="mt-5 p-3 bg-amber-50 border border-amber-200 rounded-xl text-amber-800 text-xs"
          >
            ⚠️ Mode simulation (développement) — l'IdP réel n'est pas encore branché.
          </div>
        </div>
      </div>

      <!-- Mode local (dev, SSO inactif) : sélection du rôle -->
      <div v-else-if="mode === 'select'" class="grid md:grid-cols-3 gap-6">
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

      <!-- Formulaire de connexion (mode local uniquement) -->
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
              <div class="text-xs text-slate-500">Connexion</div>
            </div>
          </div>

          <div
            v-if="error"
            class="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 flex items-center gap-3 text-red-700"
          >
            <AlertCircle :size="20" />
            <p class="text-sm">{{ error }}</p>
          </div>

          <form class="space-y-4" @submit.prevent="handleLogin">
            <div>
              <label class="block text-xs font-bold text-slate-500 uppercase mb-2">Email</label>
              <input
                v-model="email"
                type="email"
                class="w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 transition-all"
                placeholder="email@bmci.ma"
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

            <button
              type="submit"
              :disabled="isLoading"
              class="w-full bg-emerald-600 text-white py-3 rounded-xl font-bold hover:bg-emerald-700 transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed mt-6"
            >
              <template v-if="isLoading">
                <Loader2 class="animate-spin" :size="18" />
                Connexion...
              </template>
              <template v-else>
                <LogIn :size="18" />
                Se connecter
              </template>
            </button>
          </form>

          <div class="mt-6 p-4 bg-slate-50 rounded-xl">
            <p class="text-xs text-slate-500 font-bold uppercase mb-2">Compte de démonstration</p>
            <p class="text-xs text-slate-600">
              {{ currentRoleMeta?.demo?.email }} / {{ currentRoleMeta?.demo?.password }}
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
