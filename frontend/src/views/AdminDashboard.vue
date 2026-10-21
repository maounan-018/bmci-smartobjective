<script setup>
// AdminDashboard.vue — Espace d'administration (rôle ADMIN uniquement).
// Gestion des comptes : lister par type, actifs/inactifs, créer, modifier le rôle,
// réinitialiser le mot de passe, mettre hors ligne (désactiver) / réactiver, supprimer.
// La SÉCURITÉ réelle est imposée par le backend (require_super_admin) ; cet écran
// ne fait qu'orchestrer les appels et rafraîchir la liste depuis la base.
import { ref, computed, onMounted } from 'vue';
import { ApiService } from '@/services/apiService';
import DashboardLayout from '@/layouts/DashboardLayout.vue';
import {
  ShieldCheck, RefreshCw, UserPlus, Pencil, KeyRound, Power, Trash2, Loader2,
} from 'lucide-vue-next';

const users = ref([]);
const loading = ref(false);
const error = ref('');
const filterRole = ref('all');
const filterActive = ref('all'); // all | active | inactive
const showCreate = ref(false);
const newUser = ref({ email: '', name: '', role: 'COLLAB', password: '', manager_id: '' });
const editingUser = ref(null);

const EMAIL_RE = /^[a-z]+\.[a-z]+[0-9]*@bmci.local$/;
const emailValid = computed(() => EMAIL_RE.test((newUser.value.email || '').trim().toLowerCase()));
const managers = computed(() => users.value.filter((u) => u.role === 'MANAGER'));

const stats = computed(() => {
  const s = { total: users.value.length, active: 0, ADMIN: 0, HR: 0, MANAGER: 0, COLLAB: 0 };
  users.value.forEach((u) => { if (u.active) s.active++; s[u.role] = (s[u.role] || 0) + 1; });
  return s;
});
const filtered = computed(() => users.value.filter((u) => {
  if (filterRole.value !== 'all' && u.role !== filterRole.value) return false;
  if (filterActive.value === 'active' && !u.active) return false;
  if (filterActive.value === 'inactive' && u.active) return false;
  return true;
}));

async function load() {
  loading.value = true;
  error.value = '';
  try { users.value = await ApiService.adminListUsers(); } finally { loading.value = false; }
}
onMounted(load);

async function createUser() {
  const payload = { ...newUser.value };
  if (!payload.manager_id) delete payload.manager_id;
  const res = await ApiService.adminCreateUser(payload);
  if (res.ok) {
    showCreate.value = false;
    newUser.value = { email: '', name: '', role: 'COLLAB', password: '', manager_id: '' };
    await load();
  } else { error.value = res.error; }
}
function startEdit(u) {
  editingUser.value = { id: u.id, email: u.email, name: u.name, role: u.role, manager_id: u.manager_id || '' };
}
async function saveEdit() {
  const u = editingUser.value;
  const res = await ApiService.adminUpdateUser(u.id, { name: u.name, role: u.role, manager_id: u.manager_id || null });
  if (res.ok) { editingUser.value = null; await load(); } else { error.value = res.error; }
}
async function toggleActive(u) {
  const res = await ApiService.adminSetUserActive(u.id, !u.active);
  if (res.ok) await load(); else error.value = res.error;
}
async function resetPwd(u) {
  const pwd = window.prompt(`Nouveau mot de passe pour ${u.name} (min. 6 caractères) :`);
  if (!pwd) return;
  if (pwd.length < 6) { error.value = 'Le mot de passe doit faire au moins 6 caractères.'; return; }
  const res = await ApiService.adminResetUserPassword(u.id, pwd);
  if (res.ok) window.alert('Mot de passe réinitialisé.'); else error.value = res.error;
}
async function removeUser(u) {
  if (!window.confirm(`Supprimer définitivement le compte « ${u.name} » (${u.email}) et toutes ses données ?`)) return;
  const res = await ApiService.adminDeleteUser(u.id);
  if (res.ok) await load(); else error.value = res.error;
}

const roleLabel = { ADMIN: 'Admin', HR: 'RH', MANAGER: 'Manager', COLLAB: 'Collaborateur' };
const roleClass = {
  ADMIN: 'bg-slate-800 text-white', HR: 'bg-emerald-100 text-emerald-700',
  MANAGER: 'bg-purple-100 text-purple-700', COLLAB: 'bg-slate-100 text-slate-600',
};
</script>

<template>
  <DashboardLayout>
    <div class="max-w-6xl mx-auto px-4 py-8 space-y-6">
      <!-- En-tête -->
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-black text-slate-800 flex items-center gap-2">
            <ShieldCheck class="text-slate-700" :size="28" /> Administration des comptes
          </h1>
          <p class="text-sm text-slate-400">Création, rôles, activation et suppression des utilisateurs.</p>
        </div>
        <button @click="load" class="p-2 border border-slate-200 rounded-lg text-slate-600 hover:bg-slate-50" title="Rafraîchir"><RefreshCw :size="18" /></button>
      </div>

      <!-- Statistiques par type -->
      <div class="grid grid-cols-3 md:grid-cols-6 gap-3">
        <div class="bg-white p-4 rounded-xl border"><div class="text-[10px] text-slate-400 uppercase font-bold">Total</div><div class="text-2xl font-black text-slate-800">{{ stats.total }}</div></div>
        <div class="bg-emerald-50 p-4 rounded-xl border border-emerald-100"><div class="text-[10px] text-emerald-600 uppercase font-bold">Actifs</div><div class="text-2xl font-black text-emerald-700">{{ stats.active }}</div></div>
        <div class="bg-white p-4 rounded-xl border"><div class="text-[10px] text-slate-400 uppercase font-bold">Admin</div><div class="text-2xl font-black text-slate-800">{{ stats.ADMIN }}</div></div>
        <div class="bg-white p-4 rounded-xl border"><div class="text-[10px] text-slate-400 uppercase font-bold">RH</div><div class="text-2xl font-black text-slate-800">{{ stats.HR }}</div></div>
        <div class="bg-white p-4 rounded-xl border"><div class="text-[10px] text-slate-400 uppercase font-bold">Managers</div><div class="text-2xl font-black text-slate-800">{{ stats.MANAGER }}</div></div>
        <div class="bg-white p-4 rounded-xl border"><div class="text-[10px] text-slate-400 uppercase font-bold">Collab.</div><div class="text-2xl font-black text-slate-800">{{ stats.COLLAB }}</div></div>
      </div>

      <div v-if="error" class="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 flex items-center justify-between">
        <span>{{ error }}</span><button @click="error = ''" class="font-bold">✕</button>
      </div>

      <!-- Filtres + action -->
      <div class="bg-white p-4 rounded-2xl border flex flex-wrap items-center gap-3">
        <select v-model="filterRole" class="px-3 py-2 border border-slate-200 rounded-lg text-sm">
          <option value="all">Tous les types</option>
          <option value="ADMIN">Admin</option>
          <option value="HR">RH</option>
          <option value="MANAGER">Manager</option>
          <option value="COLLAB">Collaborateur</option>
        </select>
        <select v-model="filterActive" class="px-3 py-2 border border-slate-200 rounded-lg text-sm">
          <option value="all">Actifs + inactifs</option>
          <option value="active">Actifs seulement</option>
          <option value="inactive">Inactifs seulement</option>
        </select>
        <span class="text-sm text-slate-400">{{ filtered.length }} compte(s)</span>
        <button @click="showCreate = !showCreate" class="ml-auto flex items-center gap-2 px-4 py-2 bg-slate-800 text-white rounded-lg font-bold text-sm hover:bg-slate-900">
          <UserPlus :size="16" /> Nouveau compte
        </button>
      </div>

      <!-- Formulaire de création -->
      <div v-if="showCreate" class="bg-white p-5 rounded-2xl border grid grid-cols-1 md:grid-cols-2 gap-3">
        <input v-model="newUser.name" placeholder="Nom complet (ex : Karim Bennani)" class="px-3 py-2 border border-slate-200 rounded-lg text-sm" />
        <div>
          <input v-model="newUser.email" placeholder="prenom.nom@bmci.local" class="w-full px-3 py-2 border rounded-lg text-sm" :class="newUser.email && !emailValid ? 'border-red-300' : 'border-slate-200'" />
          <p v-if="newUser.email && !emailValid" class="text-xs text-red-500 mt-1">Format requis : prenom.nom@bmci.local</p>
        </div>
        <select v-model="newUser.role" class="px-3 py-2 border border-slate-200 rounded-lg text-sm">
          <option value="COLLAB">Collaborateur</option>
          <option value="MANAGER">Manager</option>
          <option value="HR">RH</option>
          <option value="ADMIN">Admin</option>
        </select>
        <select v-if="newUser.role === 'COLLAB'" v-model="newUser.manager_id" class="px-3 py-2 border border-slate-200 rounded-lg text-sm">
          <option value="">— Manager (optionnel) —</option>
          <option v-for="m in managers" :key="m.id" :value="m.id">{{ m.name }}</option>
        </select>
        <input v-model="newUser.password" placeholder="Mot de passe (min. 6)" class="px-3 py-2 border border-slate-200 rounded-lg text-sm" />
        <div class="md:col-span-2 flex justify-end gap-2">
          <button @click="showCreate = false" class="px-4 py-2 text-sm font-bold text-slate-500 hover:bg-slate-100 rounded-lg">Annuler</button>
          <button @click="createUser" :disabled="!newUser.name.trim() || !emailValid || newUser.password.length < 6" class="px-4 py-2 bg-slate-800 text-white rounded-lg font-bold text-sm hover:bg-slate-900 disabled:opacity-50">Créer</button>
        </div>
      </div>

      <!-- Table des comptes -->
      <div class="bg-white rounded-2xl border overflow-hidden">
        <div v-if="loading" class="py-12 text-center"><Loader2 class="animate-spin text-slate-400 mx-auto" :size="28" /></div>
        <table v-else class="w-full text-left text-sm">
          <thead>
            <tr class="border-b bg-slate-50 text-xs text-slate-500 uppercase">
              <th class="p-3">Nom</th><th class="p-3">Email</th><th class="p-3">Type</th>
              <th class="p-3 text-center">Statut</th><th class="p-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in filtered" :key="u.id" :class="['border-b hover:bg-slate-50', u.active ? '' : 'opacity-60']">
              <td class="p-3 font-semibold text-slate-800">{{ u.name }}</td>
              <td class="p-3 text-slate-500">{{ u.email }}</td>
              <td class="p-3"><span :class="['text-xs font-bold px-2 py-0.5 rounded', roleClass[u.role] || 'bg-slate-100 text-slate-600']">{{ roleLabel[u.role] || u.role }}</span></td>
              <td class="p-3 text-center"><span :class="['text-xs font-bold px-2 py-0.5 rounded', u.active ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-200 text-slate-500']">{{ u.active ? 'Actif' : 'Hors ligne' }}</span></td>
              <td class="p-3">
                <div class="flex items-center justify-end gap-1">
                  <button @click="startEdit(u)" class="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg" title="Modifier"><Pencil :size="16" /></button>
                  <button @click="resetPwd(u)" class="p-2 text-slate-500 hover:text-amber-600 hover:bg-amber-50 rounded-lg" title="Réinitialiser le mot de passe"><KeyRound :size="16" /></button>
                  <button @click="toggleActive(u)" :class="['p-2 rounded-lg', u.active ? 'text-slate-500 hover:text-amber-600 hover:bg-amber-50' : 'text-emerald-600 hover:bg-emerald-50']" :title="u.active ? 'Mettre hors ligne' : 'Réactiver'"><Power :size="16" /></button>
                  <button @click="removeUser(u)" class="p-2 text-slate-500 hover:text-red-600 hover:bg-red-50 rounded-lg" title="Supprimer"><Trash2 :size="16" /></button>
                </div>
              </td>
            </tr>
            <tr v-if="!filtered.length"><td colspan="5" class="p-8 text-center text-slate-400">Aucun compte pour ce filtre.</td></tr>
          </tbody>
        </table>
      </div>

      <!-- Modal d'édition -->
      <div v-if="editingUser" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" @click="editingUser = null">
        <div class="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6" @click.stop>
          <h3 class="font-bold text-lg text-slate-800 mb-1">Modifier le compte</h3>
          <p class="text-xs text-slate-400 mb-4">{{ editingUser.email }}</p>
          <div class="space-y-3">
            <input v-model="editingUser.name" placeholder="Nom" class="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm" />
            <select v-model="editingUser.role" class="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm">
              <option value="COLLAB">Collaborateur</option>
              <option value="MANAGER">Manager</option>
              <option value="HR">RH</option>
              <option value="ADMIN">Admin</option>
            </select>
            <select v-if="editingUser.role === 'COLLAB'" v-model="editingUser.manager_id" class="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm">
              <option value="">— Sans manager —</option>
              <option v-for="m in managers" :key="m.id" :value="m.id">{{ m.name }}</option>
            </select>
          </div>
          <div class="flex justify-end gap-2 mt-5">
            <button @click="editingUser = null" class="px-4 py-2 text-sm font-bold text-slate-500 hover:bg-slate-100 rounded-lg">Annuler</button>
            <button @click="saveEdit" class="px-4 py-2 bg-slate-800 text-white rounded-lg font-bold text-sm hover:bg-slate-900">Enregistrer</button>
          </div>
        </div>
      </div>
    </div>
  </DashboardLayout>
</template>
