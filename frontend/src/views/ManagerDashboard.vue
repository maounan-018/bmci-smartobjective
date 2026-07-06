<script setup>
// ManagerDashboard.vue — Tableau de bord Manager (migration de pages/ManagerDashboard.tsx).
// Trois tâches : analyse SMART personnelle, suivi de l'équipe, objectifs stratégiques.
// L'utilisateur provient du store d'auth ; toute la logique métier passe par ApiService (backend FastAPI).
import { ref, computed, onMounted } from 'vue';
import { useAuthStore } from '@/stores/authStore';
import { ApiService } from '@/services/apiService';
import SmartBadge from '@/components/SmartBadge.vue';
import AlignmentChart from '@/components/AlignmentChart.vue';
import DashboardLayout from '@/layouts/DashboardLayout.vue';
import KnowledgeBaseManager from '@/components/KnowledgeBaseManager.vue';
import {
  Users, Target, ChevronRight, Loader2, AlertCircle,
  CheckCircle2, TrendingUp, RefreshCw, Eye, Plus, Download,
  Search, PieChart as PieChartIcon, Play, Sparkles, FileSpreadsheet, Upload, X,
  BookOpen,
} from 'lucide-vue-next';

const auth = useAuthStore();
const user = computed(() => auth.user || {});

// Tâche active (null = vue principale avec les 3 tâches)
const activeTask = ref(null); // 'smart' | 'team' | 'strategy' | 'knowledge' | null
const loadingState = ref('loading'); // 'idle' | 'loading' | 'success' | 'error'
const error = ref(null);

// Données depuis l'API
const teamObjectives = ref([]);
const teamStats = ref(null);
const companyObjectives = ref([]);

// Analyse SMART du Manager (ses propres objectifs)
const myObjectiveTitle = ref('');
const myObjectiveDesc = ref('');
const isAnalyzing = ref(false);
const myAnalysisResult = ref(null);
const analysisHistory = ref([]);

// Import Excel
const isImporting = ref(false);
const importResults = ref(null);
const fileInput = ref(null);

// Vue détaillée
const selectedObjective = ref(null);

// Analyse historique sélectionnée pour voir les détails
const selectedHistoryItem = ref(null);

// Objectif stratégique
const newGoalTitle = ref('');
const newGoalDesc = ref('');

// Filtres
const filterMember = ref('all');
const filterSmartStatus = ref('all');
const searchQuery = ref('');

// Un clic sur un KPI du dashboard ouvre la vue « Mon équipe » filtrée en conséquence.
function goToTeam(smartStatus = 'all') {
  filterSmartStatus.value = smartStatus;
  filterMember.value = 'all';
  searchQuery.value = '';
  activeTask.value = 'team';
}

// État pour l'analyse en cours
const analyzingId = ref(null);

// Export
const showExportMenu = ref(false);
const isExporting = ref(false);

// ============ CHARGEMENT INITIAL ============
onMounted(loadData);

async function loadData() {
  try {
    loadingState.value = 'loading';
    const [objectives, stats, companyObjs, analysisData] = await Promise.all([
      ApiService.getManagerObjectives(),
      ApiService.getManagerTeamStats(),
      ApiService.getCompanyObjectives(),
      ApiService.getManagerAnalysisResults(),
    ]);
    teamObjectives.value = objectives;
    teamStats.value = stats;
    companyObjectives.value = companyObjs;
    if (analysisData) analysisHistory.value = analysisData.results || [];
    loadingState.value = 'success';
  } catch (err) {
    console.error('[ManagerDashboard] Erreur chargement:', err);
    loadingState.value = 'error';
    error.value = 'Erreur lors du chargement des données.';
  }
}

// ============ ANALYSE SMART PERSONNELLE DU MANAGER ============
async function handleAnalyzeMyObjective() {
  if (!myObjectiveTitle.value.trim()) {
    alert('Veuillez saisir un titre pour votre objectif.');
    return;
  }
  isAnalyzing.value = true;
  myAnalysisResult.value = null;
  try {
    const result = await ApiService.analyzeManagerPersonalObjective(myObjectiveTitle.value, myObjectiveDesc.value);
    if (result) {
      myAnalysisResult.value = result;
      const newHistoryEntry = {
        ...result,
        objective_title: myObjectiveTitle.value,
        analyzed_at: new Date().toISOString(),
        id: `temp-${Date.now()}`,
      };
      analysisHistory.value = [newHistoryEntry, ...analysisHistory.value];
      const analysisData = await ApiService.getManagerAnalysisResults();
      if (analysisData) analysisHistory.value = analysisData.results || [];
      myObjectiveTitle.value = '';
      myObjectiveDesc.value = '';
    }
  } catch (err) {
    console.error('Erreur analyse:', err);
    alert("Erreur lors de l'analyse. Vérifiez que le serveur Ollama est actif.");
  } finally {
    isAnalyzing.value = false;
  }
}

// ============ IMPORT EXCEL POUR ANALYSE ============
// Drag & drop : permet de glisser un fichier depuis l'Explorateur,
// sans passer par la popup "mobile" d'Edge.
const dragExcel = ref(false);
function onExcelDrop(e) {
  dragExcel.value = false;
  const file = e.dataTransfer?.files?.[0];
  if (!file) return;
  // Reutilise le handler existant via un event synthetique.
  handleImportExcel({ target: { files: [file] } });
}

async function handleImportExcel(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
    alert('Format non supporté. Veuillez utiliser un fichier Excel (.xlsx ou .xls)');
    return;
  }
  isImporting.value = true;
  importResults.value = null;
  try {
    const result = await ApiService.importExcelForAnalysis(file);
    if (result) {
      importResults.value = result;
      const analysisData = await ApiService.getManagerAnalysisResults();
      if (analysisData) analysisHistory.value = analysisData.results || [];
    }
  } catch (err) {
    console.error('Erreur import:', err);
    alert(err.message || "Erreur lors de l'import du fichier Excel.");
  } finally {
    isImporting.value = false;
    if (fileInput.value) fileInput.value.value = '';
  }
}

// ============ KPIs CALCULÉS ============
const kpis = computed(() => {
  if (!teamStats.value) {
    return { totalMembers: 0, totalObjectives: 0, smartRate: null, avgAlignment: null, alertsCount: 0 };
  }
  const alertsCount = teamObjectives.value.filter(o =>
    o.smartAnalysis?.overall === false ||
    (o.alignmentAnalysis?.alignment_score ?? 100) < 50
  ).length;
  return {
    totalMembers: teamStats.value.team_members || 0,
    totalObjectives: teamStats.value.total_objectives || 0,
    smartRate: teamStats.value.smart_rate,
    avgAlignment: teamStats.value.avg_alignment,
    alertsCount,
  };
});

// ============ STATISTIQUES SMART ============
const smartStats = computed(() => {
  const total = teamObjectives.value.length;
  if (total === 0) {
    return { total: 0, smart: 0, nonSmart: 0, pending: 0, smartRate: null, criteriaStats: { S: 0, M: 0, A: 0, R: 0, T: 0 }, byMember: [], analyzed: 0 };
  }
  const analyzed = teamObjectives.value.filter(o => o.smartAnalysis);
  const smart = analyzed.filter(o => o.smartAnalysis?.overall === true).length;
  const nonSmart = analyzed.filter(o => o.smartAnalysis?.overall === false).length;
  const pending = teamObjectives.value.filter(o => !o.smartAnalysis).length;
  const smartRate = analyzed.length > 0 ? Math.round((smart / analyzed.length) * 100) : null;

  const criteriaStats = { S: 0, M: 0, A: 0, R: 0, T: 0 };
  analyzed.forEach(o => {
    if (o.smartAnalysis?.S) criteriaStats.S++;
    if (o.smartAnalysis?.M) criteriaStats.M++;
    if (o.smartAnalysis?.A) criteriaStats.A++;
    if (o.smartAnalysis?.R) criteriaStats.R++;
    if (o.smartAnalysis?.T) criteriaStats.T++;
  });

  const byMember = [];
  const memberGroups = teamObjectives.value.reduce((acc, o) => {
    const name = o.user_name || 'Inconnu';
    if (!acc[name]) acc[name] = [];
    acc[name].push(o);
    return acc;
  }, {});
  Object.entries(memberGroups).forEach(([name, objList]) => {
    const memberSmart = objList.filter(o => o.smartAnalysis?.overall === true).length;
    const memberNonSmart = objList.filter(o => o.smartAnalysis?.overall === false).length;
    const memberAlignments = objList.map(o => o.alignmentAnalysis?.alignment_score).filter(s => s !== undefined);
    const memberAvgAlign = memberAlignments.length > 0 ? Math.round(memberAlignments.reduce((a, b) => a + b, 0) / memberAlignments.length) : 0;
    byMember.push({ name, smart: memberSmart, nonSmart: memberNonSmart, total: objList.length, avgAlignment: memberAvgAlign });
  });

  return { total, smart, nonSmart, pending, smartRate, criteriaStats, byMember, analyzed: analyzed.length };
});

// ============ FILTRAGE ============
const filteredObjectives = computed(() => {
  return teamObjectives.value.filter(o => {
    if (filterMember.value !== 'all' && o.user_name !== filterMember.value) return false;
    if (filterSmartStatus.value === 'smart' && o.smartAnalysis?.overall !== true) return false;
    if (filterSmartStatus.value === 'non-smart' && o.smartAnalysis?.overall !== false) return false;
    if (filterSmartStatus.value === 'pending' && o.smartAnalysis) return false;
    if (searchQuery.value && !o.title.toLowerCase().includes(searchQuery.value.toLowerCase())) return false;
    return true;
  });
});

// ============ EXPORT EXCEL/PDF ============
async function handleExport(format) {
  isExporting.value = true;
  showExportMenu.value = false;
  try {
    const blob = format === 'excel'
      ? await ApiService.exportManagerExcel()
      : await ApiService.exportManagerPdf();
    if (blob) {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const date = new Date().toISOString().split('T')[0];
      a.download = format === 'excel' ? `Rapport_Manager_${date}.xlsx` : `Rapport_Manager_${date}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } else {
      alert("Erreur lors de l'export. Vérifiez que les dépendances sont installées (openpyxl, reportlab).");
    }
  } catch (err) {
    console.error('Export error:', err);
    alert("Erreur lors de l'export.");
  } finally {
    isExporting.value = false;
  }
}

// ============ AJOUT OBJECTIF STRATÉGIQUE ============
async function handleAddCompanyGoal() {
  if (!newGoalTitle.value.trim()) return;
  const success = await ApiService.createCompanyObjective({
    id: `STRAT-${Date.now()}`,
    title: newGoalTitle.value,
    description: newGoalDesc.value,
  });
  if (success) {
    await loadData();
    newGoalTitle.value = '';
    newGoalDesc.value = '';
  }
}

// ============ ANALYSE D'UN OBJECTIF (MANAGER) ============
async function handleAnalyzeObjective(objectiveId) {
  analyzingId.value = objectiveId;
  error.value = null;
  try {
    const result = await ApiService.analyzeManagerObjective(objectiveId);
    if (result.success) {
      teamObjectives.value = teamObjectives.value.map(obj => {
        if (obj.id === objectiveId) {
          return { ...obj, smartAnalysis: result.smart_analysis, alignmentAnalysis: result.alignment_analysis, status: 'analyzed' };
        }
        return obj;
      });
      teamStats.value = await ApiService.getManagerTeamStats();
      if (selectedObjective.value?.id === objectiveId) {
        selectedObjective.value = {
          ...selectedObjective.value,
          smartAnalysis: result.smart_analysis,
          alignmentAnalysis: result.alignment_analysis,
          status: 'analyzed',
        };
      }
    } else {
      error.value = result.error || "Erreur lors de l'analyse";
    }
  } catch (err) {
    console.error('[ManagerDashboard] Erreur analyse:', err);
    error.value = "Erreur lors de l'analyse de l'objectif";
  } finally {
    analyzingId.value = null;
  }
}

// ============ DONNÉES DU DONUT SMART ============
// Remplace recharts par un donut SVG natif (sans dépendance).
const pieData = computed(() => {
  if (smartStats.value.analyzed === 0) return [];
  return [
    { name: 'SMART', value: smartStats.value.smart, color: '#059669' },
    { name: 'Non SMART', value: smartStats.value.nonSmart, color: '#f59e0b' },
    { name: 'En attente', value: smartStats.value.pending, color: '#94a3b8' },
  ].filter(d => d.value > 0);
});

// Segments du donut SVG (cercle de circonférence 2πr, r=42).
const donutSegments = computed(() => {
  const data = pieData.value;
  const totalValue = data.reduce((a, d) => a + d.value, 0);
  if (totalValue === 0) return [];
  const circumference = 2 * Math.PI * 42;
  let offset = 0;
  return data.map(d => {
    const fraction = d.value / totalValue;
    const seg = {
      color: d.color,
      name: d.name,
      pct: Math.round(fraction * 100),
      dash: `${fraction * circumference} ${circumference}`,
      rotation: (offset / totalValue) * 360,
    };
    offset += d.value;
    return seg;
  });
});

// Critères SMART sous forme de liste pour le template.
const criteriaList = computed(() => {
  const cs = smartStats.value.criteriaStats;
  const analyzed = smartStats.value.analyzed;
  return Object.entries(cs).map(([letter, count]) => ({
    letter,
    pct: analyzed > 0 ? Math.round((count / analyzed) * 100) : 0,
  }));
});

// Helpers de formatage pour le modal historique.
function formatHistoryDate(value) {
  return new Date(value).toLocaleDateString('fr-FR', {
    day: '2-digit', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit',
  });
}

// Modèle CSV téléchargeable.
function downloadTemplate() {
  const csvContent = "Titre,Description\nAugmenter les ventes de 20%,Objectif de développement commercial pour Q2\nRéduire les coûts opérationnels,Optimisation des processus internes";
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'modele_objectifs.csv';
  link.click();
}

// Critères pour le modal détaillé de l'historique.
const historyCriteria = [
  { key: 'S', label: 'Spécifique', desc: "L'objectif est-il clairement défini ?" },
  { key: 'M', label: 'Mesurable', desc: 'Peut-on quantifier le résultat ?' },
  { key: 'A', label: 'Atteignable', desc: "L'objectif est-il réaliste ?" },
  { key: 'R', label: 'Réaliste', desc: "Est-il pertinent pour l'organisation ?" },
  { key: 'T', label: 'Temporel', desc: 'Y a-t-il une échéance définie ?' },
];

function historyIsValid(item, key) {
  return item.smart_analysis?.[key] || item[`${key.toLowerCase()}_score`];
}
function historyExplanation(item, key) {
  return item.smart_analysis?.[`${key}_explanation`] || item.smart_analysis?.[`${key.toLowerCase()}_explanation`];
}
function historyIssueFor(item, key) {
  return item.smart_analysis?.issues?.find(i => i.letter === key);
}
</script>

<template>
  <DashboardLayout>
    <!-- ÉTAT DE CHARGEMENT -->
    <div v-if="loadingState === 'loading'" class="p-8 max-w-7xl mx-auto flex items-center justify-center min-h-[60vh]">
      <div class="flex flex-col items-center gap-4">
        <Loader2 class="animate-spin text-emerald-600" :size="48" />
        <p class="text-slate-500 font-medium">Chargement des données d'équipe...</p>
      </div>
    </div>

    <!-- VUE DÉTAILLÉE -->
    <div v-else-if="selectedObjective" class="p-8 max-w-7xl mx-auto space-y-8">
      <button @click="selectedObjective = null" class="flex items-center gap-2 text-emerald-600 font-bold hover:underline">
        <ChevronRight class="rotate-180" :size="20" /> Retour
      </button>

      <div class="bg-white p-8 rounded-2xl shadow-sm border border-slate-100">
        <div class="flex items-center justify-between mb-6">
          <div>
            <div class="text-xs font-bold text-slate-400 uppercase mb-1">{{ selectedObjective.user_name || 'Collaborateur' }}</div>
            <h1 class="text-2xl font-extrabold text-slate-900">{{ selectedObjective.title }}</h1>
            <p class="text-slate-500 mt-1">{{ selectedObjective.description || 'Sans description' }}</p>
          </div>
          <div :class="['px-4 py-2 rounded-full text-sm font-bold', selectedObjective.smartAnalysis?.overall ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700']">
            {{ selectedObjective.smartAnalysis?.overall ? '✓ SMART' : '✗ NON SMART' }}
          </div>
        </div>

        <div class="mt-8 space-y-6">
          <div class="bg-slate-50 p-6 rounded-xl">
            <div class="flex items-center justify-between mb-4">
              <h3 class="font-bold text-lg text-emerald-900 flex items-center gap-2">
                Analyse S.M.A.R.T.
                <CheckCircle2 v-if="selectedObjective.smartAnalysis?.overall" class="text-emerald-500" :size="20" />
                <AlertCircle v-else class="text-amber-500" :size="20" />
              </h3>
              <div class="text-sm font-medium text-slate-500">
                Confiance: {{ selectedObjective.smartAnalysis?.confidence !== undefined ? `${(selectedObjective.smartAnalysis.confidence * 100).toFixed(0)}%` : 'Indisponible' }}
              </div>
            </div>
            <div class="flex justify-between items-center">
              <SmartBadge letter="S" :active="selectedObjective.smartAnalysis?.S || false" label="Spécifique" />
              <SmartBadge letter="M" :active="selectedObjective.smartAnalysis?.M || false" label="Mesurable" />
              <SmartBadge letter="A" :active="selectedObjective.smartAnalysis?.A || false" label="Atteignable" />
              <SmartBadge letter="R" :active="selectedObjective.smartAnalysis?.R || false" label="Pertinent" />
              <SmartBadge letter="T" :active="selectedObjective.smartAnalysis?.T || false" label="Temporel" />
            </div>
          </div>

          <!-- Issues -->
          <div v-if="(selectedObjective.smartAnalysis?.issues?.length || 0) > 0" class="bg-amber-50 p-6 rounded-xl border border-amber-100">
            <h4 class="font-bold text-amber-900 mb-3 flex items-center gap-2"><AlertCircle :size="18" />Ce qui manque / À améliorer</h4>
            <div class="space-y-3">
              <div v-for="(issue, idx) in selectedObjective.smartAnalysis.issues" :key="idx" class="bg-white p-4 rounded-lg shadow-sm border border-amber-100">
                <div class="flex items-center gap-2 mb-2">
                  <span class="w-6 h-6 rounded-full bg-amber-500 text-white text-xs flex items-center justify-center font-bold">{{ issue.letter }}</span>
                  <span class="font-bold text-slate-700">{{ issue.problem }}</span>
                </div>
                <p class="text-sm text-slate-600 pl-8">💡 <strong>Recommandation:</strong> {{ issue.fix }}</p>
              </div>
            </div>
          </div>

          <!-- Alignement -->
          <div class="bg-white p-6 rounded-xl border border-slate-100 flex items-center gap-6">
            <AlignmentChart :score="selectedObjective.alignmentAnalysis?.alignment_score ?? null" />
            <div class="flex-1">
              <h4 class="font-bold text-slate-800 mb-1">Alignement Stratégique</h4>
              <div class="flex gap-2 flex-wrap mt-2">
                <div v-for="m in selectedObjective.alignmentAnalysis?.top_matches" :key="m.objective_id" class="text-xs bg-emerald-50 text-emerald-700 px-3 py-2 rounded-lg border border-emerald-100">
                  <div class="font-bold">{{ m.title || m.objective_id }}: {{ m.score }}%</div>
                  <div class="text-emerald-600 mt-1">{{ m.reason }}</div>
                </div>
                <span v-if="!selectedObjective.alignmentAnalysis?.top_matches?.length" class="text-xs text-slate-400">Aucune correspondance</span>
              </div>
            </div>
          </div>

          <!-- Réécritures -->
          <div class="bg-white p-6 rounded-xl border border-slate-100 space-y-4">
            <h4 class="font-bold text-emerald-900">Reformulations Suggérées</h4>
            <div class="grid md:grid-cols-2 gap-4">
              <div>
                <div class="text-xs font-bold text-slate-400 uppercase mb-1">Français</div>
                <div class="bg-slate-50 p-4 rounded-xl text-sm italic text-slate-700 border border-slate-100">
                  "{{ selectedObjective.smartAnalysis?.rewrite_fr || 'Indisponible' }}"
                </div>
              </div>
              <div>
                <div class="text-xs font-bold text-slate-400 uppercase mb-1">Anglais</div>
                <div class="bg-slate-50 p-4 rounded-xl text-sm italic text-slate-700 border border-slate-100">
                  "{{ selectedObjective.smartAnalysis?.rewrite_en || 'Unavailable' }}"
                </div>
              </div>
            </div>
          </div>

          <!-- Synthèse managériale -->
          <div class="bg-emerald-50 p-6 rounded-xl border border-emerald-100">
            <h4 class="font-bold text-emerald-900 mb-4 flex items-center gap-2"><TrendingUp :size="18" />Synthèse Managériale</h4>
            <div class="grid md:grid-cols-3 gap-4">
              <div class="bg-white p-4 rounded-xl">
                <div class="text-xs text-slate-400 uppercase font-bold">Statut SMART</div>
                <div :class="['text-lg font-black mt-1', selectedObjective.smartAnalysis?.overall ? 'text-emerald-600' : 'text-amber-600']">
                  {{ selectedObjective.smartAnalysis?.overall ? 'Conforme' : 'À améliorer' }}
                </div>
              </div>
              <div class="bg-white p-4 rounded-xl">
                <div class="text-xs text-slate-400 uppercase font-bold">Alignement</div>
                <div :class="['text-lg font-black mt-1', (selectedObjective.alignmentAnalysis?.alignment_score || 0) >= 70 ? 'text-emerald-600' : 'text-amber-600']">
                  {{ selectedObjective.alignmentAnalysis?.alignment_score !== undefined ? `${selectedObjective.alignmentAnalysis.alignment_score}%` : 'N/A' }}
                </div>
              </div>
              <div class="bg-white p-4 rounded-xl">
                <div class="text-xs text-slate-400 uppercase font-bold">Recommandation</div>
                <div class="text-sm font-medium mt-1 text-slate-700">
                  {{ selectedObjective.smartAnalysis?.overall && (selectedObjective.alignmentAnalysis?.alignment_score || 0) >= 70 ? '✅ Valider' : '🔄 Demander révision' }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- VUE PRINCIPALE -->
    <div v-else class="p-8 max-w-7xl mx-auto space-y-8">
      <header class="flex justify-between items-center">
        <div>
          <h1 class="text-3xl font-extrabold text-emerald-900 flex items-center gap-3">
            <Users :size="32" />
            Tableau de Bord Manager
          </h1>
          <p class="text-slate-500">Équipe: {{ user.team || 'Mon équipe' }}</p>
        </div>
        <button @click="loadData" class="p-2 border border-slate-200 rounded-lg text-slate-600 hover:bg-slate-50" title="Rafraîchir">
          <RefreshCw :size="18" />
        </button>
      </header>

      <div v-if="error" class="bg-red-50 border border-red-200 p-4 rounded-xl flex items-center gap-3 text-red-700">
        <AlertCircle :size="20" />
        <p class="text-sm font-medium">{{ error }}</p>
        <button @click="error = null" class="ml-auto text-xs font-bold">Masquer</button>
      </div>

      <!-- KPIs Cards (cliquables : renvoient à la liste d'équipe filtrée) -->
      <div class="grid grid-cols-1 md:grid-cols-5 gap-4">
        <div @click="goToTeam('all')" class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 cursor-pointer hover:shadow-md hover:border-emerald-200 transition-shadow">
          <div class="text-[10px] font-bold text-slate-400 uppercase">Collaborateurs</div>
          <div class="text-3xl font-black text-emerald-800 mt-1">{{ kpis.totalMembers }}</div>
        </div>
        <div @click="goToTeam('all')" class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 cursor-pointer hover:shadow-md hover:border-emerald-200 transition-shadow">
          <div class="text-[10px] font-bold text-slate-400 uppercase">Total Objectifs</div>
          <div class="text-3xl font-black text-emerald-800 mt-1">{{ kpis.totalObjectives }}</div>
        </div>
        <div @click="goToTeam('smart')" class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 cursor-pointer hover:shadow-md hover:border-emerald-200 transition-shadow">
          <div class="text-[10px] font-bold text-slate-400 uppercase">Taux SMART</div>
          <div class="text-3xl font-black text-emerald-800 mt-1">
            <template v-if="kpis.smartRate !== null">{{ kpis.smartRate }}%</template>
            <span v-else class="text-slate-300 text-lg">—</span>
          </div>
        </div>
        <div @click="goToTeam('all')" class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 cursor-pointer hover:shadow-md hover:border-emerald-200 transition-shadow">
          <div class="text-[10px] font-bold text-slate-400 uppercase">Alignement Moyen</div>
          <div class="text-3xl font-black text-emerald-800 mt-1">
            <template v-if="kpis.avgAlignment !== null">{{ kpis.avgAlignment }}%</template>
            <span v-else class="text-slate-300 text-lg">—</span>
          </div>
        </div>
        <div @click="goToTeam('non-smart')" class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 cursor-pointer hover:shadow-md hover:border-amber-200 transition-shadow">
          <div class="text-[10px] font-bold text-slate-400 uppercase">Alertes</div>
          <div :class="['text-3xl font-black mt-1', kpis.alertsCount > 0 ? 'text-amber-600' : 'text-emerald-600']">
            {{ kpis.alertsCount }}
          </div>
        </div>
      </div>

      <!-- SECTION TÂCHES - Vue principale -->
      <div v-if="activeTask === null" class="space-y-6">
        <h2 class="text-xl font-bold text-slate-800 flex items-center gap-2">
          <Play :size="24" class="text-emerald-600" />
          Mes Tâches
        </h2>

        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
          <!-- Tâche 1 -->
          <div class="bg-gradient-to-br from-amber-50 to-yellow-50 border-2 border-amber-200 p-6 rounded-2xl shadow-sm hover:shadow-lg transition-all group">
            <div class="flex items-center gap-3 mb-4">
              <div class="w-12 h-12 bg-amber-500 rounded-xl flex items-center justify-center shadow-md">
                <Sparkles :size="24" class="text-white" />
              </div>
              <div>
                <h3 class="text-lg font-bold text-amber-900">Analyser mon objectif</h3>
                <p class="text-xs text-amber-600">Analyse SMART personnelle</p>
              </div>
            </div>
            <p class="text-sm text-amber-700 mb-4">
              Saisissez votre objectif personnel et obtenez une analyse SMART détaillée avec des recommandations.
            </p>
            <div class="flex items-center justify-between">
              <span class="text-xs text-amber-500 font-medium">{{ analysisHistory.length }} analyse(s) effectuée(s)</span>
              <button @click="activeTask = 'smart'" class="px-4 py-2 bg-amber-500 text-white rounded-lg font-bold text-sm hover:bg-amber-600 transition-colors flex items-center gap-2 group-hover:scale-105">
                <Play :size="16" />
                Démarrer
              </button>
            </div>
          </div>

          <!-- Tâche 2 -->
          <div class="bg-gradient-to-br from-emerald-50 to-teal-50 border-2 border-emerald-200 p-6 rounded-2xl shadow-sm hover:shadow-lg transition-all group">
            <div class="flex items-center gap-3 mb-4">
              <div class="w-12 h-12 bg-emerald-500 rounded-xl flex items-center justify-center shadow-md">
                <Users :size="24" class="text-white" />
              </div>
              <div>
                <h3 class="text-lg font-bold text-emerald-900">Mon équipe</h3>
                <p class="text-xs text-emerald-600">Suivi des objectifs d'équipe</p>
              </div>
            </div>
            <p class="text-sm text-emerald-700 mb-4">
              Consultez et analysez les objectifs de votre équipe, exportez les rapports et identifiez les alertes.
            </p>
            <div class="flex items-center justify-between">
              <span class="text-xs text-emerald-500 font-medium">{{ kpis.totalObjectives }} objectif(s) · {{ kpis.alertsCount }} alerte(s)</span>
              <button @click="activeTask = 'team'" class="px-4 py-2 bg-emerald-500 text-white rounded-lg font-bold text-sm hover:bg-emerald-600 transition-colors flex items-center gap-2 group-hover:scale-105">
                <Play :size="16" />
                Démarrer
              </button>
            </div>
          </div>

          <!-- Tâche 3 -->
          <div class="bg-gradient-to-br from-purple-50 to-indigo-50 border-2 border-purple-200 p-6 rounded-2xl shadow-sm hover:shadow-lg transition-all group">
            <div class="flex items-center gap-3 mb-4">
              <div class="w-12 h-12 bg-purple-500 rounded-xl flex items-center justify-center shadow-md">
                <Target :size="24" class="text-white" />
              </div>
              <div>
                <h3 class="text-lg font-bold text-purple-900">Objectifs stratégiques</h3>
                <p class="text-xs text-purple-600">Catalogue entreprise</p>
              </div>
            </div>
            <p class="text-sm text-purple-700 mb-4">
              Gérez le catalogue des objectifs stratégiques de l'entreprise pour l'alignement.
            </p>
            <div class="flex items-center justify-between">
              <span class="text-xs text-purple-500 font-medium">{{ companyObjectives.length }} objectif(s) stratégique(s)</span>
              <button @click="activeTask = 'strategy'" class="px-4 py-2 bg-purple-500 text-white rounded-lg font-bold text-sm hover:bg-purple-600 transition-colors flex items-center gap-2 group-hover:scale-105">
                <Play :size="16" />
                Démarrer
              </button>
            </div>
          </div>

          <!-- Tâche 4 : Base de connaissances de l'assistant -->
          <div class="bg-gradient-to-br from-indigo-50 to-blue-50 border-2 border-indigo-200 p-6 rounded-2xl shadow-sm hover:shadow-lg transition-all group">
            <div class="flex items-center gap-3 mb-4">
              <div class="w-12 h-12 bg-indigo-500 rounded-xl flex items-center justify-center shadow-md">
                <BookOpen :size="24" class="text-white" />
              </div>
              <div>
                <h3 class="text-lg font-bold text-indigo-900">Base de connaissances</h3>
                <p class="text-xs text-indigo-600">Documents de l'assistant</p>
              </div>
            </div>
            <p class="text-sm text-indigo-700 mb-4">
              Ajoutez les documents (stratégie, politiques…) sur lesquels l'assistant s'appuie pour répondre.
            </p>
            <div class="flex items-center justify-between">
              <span class="text-xs text-indigo-500 font-medium">Alimente la recherche sémantique</span>
              <button @click="activeTask = 'knowledge'" class="px-4 py-2 bg-indigo-500 text-white rounded-lg font-bold text-sm hover:bg-indigo-600 transition-colors flex items-center gap-2 group-hover:scale-105">
                <Play :size="16" />
                Démarrer
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- TÂCHE: Base de connaissances de l'assistant -->
      <div v-if="activeTask === 'knowledge'" class="space-y-6">
        <div class="flex items-center justify-between">
          <button @click="activeTask = null" class="flex items-center gap-2 text-indigo-600 font-bold hover:underline">
            <ChevronRight class="rotate-180" :size="20" /> Retour aux tâches
          </button>
          <div class="flex items-center gap-2 bg-indigo-100 text-indigo-700 px-4 py-2 rounded-lg">
            <BookOpen :size="18" />
            <span class="font-bold">Tâche: Base de connaissances</span>
          </div>
        </div>
        <KnowledgeBaseManager />
      </div>

      <!-- TÂCHE: Analyse SMART personnelle -->
      <div v-if="activeTask === 'smart'" class="space-y-6">
        <div class="flex items-center justify-between">
          <button @click="activeTask = null" class="flex items-center gap-2 text-amber-600 font-bold hover:underline">
            <ChevronRight class="rotate-180" :size="20" /> Retour aux tâches
          </button>
          <div class="flex items-center gap-2 bg-amber-100 text-amber-700 px-4 py-2 rounded-lg">
            <Sparkles :size="18" />
            <span class="font-bold">Tâche: Analyser mon objectif</span>
          </div>
        </div>

        <!-- Formulaire d'analyse -->
        <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
          <h3 class="font-bold text-lg text-slate-800 mb-4 flex items-center gap-2">
            <Sparkles :size="20" class="text-amber-500" />
            Analyser mon objectif
          </h3>
          <p class="text-sm text-slate-500 mb-4">
            Saisissez votre objectif et obtenez une analyse SMART détaillée avec des recommandations d'amélioration.
          </p>
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">Titre de l'objectif *</label>
              <input v-model="myObjectiveTitle" type="text" placeholder="Ex: Augmenter le chiffre d'affaires de 15% d'ici fin Q2" class="w-full px-4 py-3 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500" />
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">Description (optionnel)</label>
              <textarea v-model="myObjectiveDesc" placeholder="Contexte, moyens, contraintes..." :rows="3" class="w-full px-4 py-3 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"></textarea>
            </div>
            <button @click="handleAnalyzeMyObjective" :disabled="isAnalyzing || !myObjectiveTitle.trim()" class="w-full bg-gradient-to-r from-emerald-600 to-teal-600 text-white px-6 py-3 rounded-lg font-bold flex items-center justify-center gap-2 hover:from-emerald-700 hover:to-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all">
              <template v-if="isAnalyzing"><Loader2 :size="20" class="animate-spin" />Analyse en cours...</template>
              <template v-else><Sparkles :size="20" />Analyser mon objectif</template>
            </button>
          </div>
        </div>

        <!-- Section Import Excel -->
        <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
          <h3 class="font-bold text-lg text-slate-800 mb-4 flex items-center gap-2">
            <FileSpreadsheet :size="20" class="text-emerald-500" />
            Importer des objectifs depuis Excel
          </h3>
          <p class="text-sm text-slate-500 mb-4">
            Importez un fichier Excel contenant plusieurs objectifs à analyser en lot.
            Le fichier doit contenir une colonne <strong>"Titre"</strong> (obligatoire) et optionnellement une colonne <strong>"Description"</strong>.
          </p>
          <div
            class="flex flex-col items-stretch gap-3 p-4 rounded-xl border-2 border-dashed transition-colors"
            :class="dragExcel ? 'bg-blue-50 border-blue-500' : 'bg-slate-50 border-slate-200'"
            @drop.prevent="onExcelDrop"
            @dragover.prevent="dragExcel = true"
            @dragenter.prevent="dragExcel = true"
            @dragleave.prevent="dragExcel = false"
          >
            <p class="text-xs text-blue-700 text-center">Glissez-déposez un fichier Excel ici, ou cliquez ci-dessous.</p>
            <div class="flex items-center gap-4 flex-wrap">
              <input ref="fileInput" type="file" accept=".xlsx,.xls" @change="handleImportExcel" class="hidden" id="excel-import" />
              <label for="excel-import" :class="['flex items-center gap-2 px-6 py-3 rounded-lg font-bold cursor-pointer transition-all', isImporting ? 'bg-slate-300 text-slate-600 cursor-not-allowed' : 'bg-gradient-to-r from-blue-500 to-indigo-600 text-white hover:from-blue-600 hover:to-indigo-700']">
                <template v-if="isImporting"><Loader2 :size="20" class="animate-spin" />Import en cours...</template>
                <template v-else><Upload :size="20" />Choisir un fichier Excel</template>
              </label>
              <a href="#" @click.prevent="downloadTemplate" class="text-sm text-blue-600 hover:underline flex items-center gap-1">
                <Download :size="16" />
                Télécharger un modèle
              </a>
            </div>
          </div>
        </div>

        <!-- Résultats de l'import Excel -->
        <div v-if="importResults" class="bg-white p-6 rounded-2xl shadow-sm border border-blue-200">
          <div class="flex items-center justify-between mb-4">
            <h3 class="font-bold text-lg text-slate-800 flex items-center gap-2">
              <CheckCircle2 :size="20" class="text-blue-500" />
              Résultats de l'import
            </h3>
            <button @click="importResults = null" class="text-slate-400 hover:text-slate-600"><X :size="20" /></button>
          </div>

          <div v-if="importResults.scan_info" class="mb-4 p-3 bg-blue-50 rounded-lg text-sm">
            <div class="font-medium text-blue-800 mb-1">📊 Structure détectée automatiquement</div>
            <div class="text-blue-600 space-y-1">
              <p>• Feuille sélectionnée: <span class="font-medium">{{ importResults.scan_info.selected_sheet }}</span></p>
              <p>• Colonne objectifs: <span class="font-medium">{{ importResults.scan_info.detected_objective_column?.name }}</span> (confiance: {{ Math.round((importResults.scan_info.detected_objective_column?.score || 0) * 100) }}%)</p>
              <p v-if="importResults.scan_info.detected_description_column">• Colonne descriptions: <span class="font-medium">{{ importResults.scan_info.detected_description_column.name }}</span></p>
            </div>
          </div>

          <div v-if="importResults.extraction_info" class="mb-4 grid grid-cols-3 gap-3">
            <div class="p-3 bg-emerald-50 rounded-lg text-center">
              <div class="text-2xl font-bold text-emerald-600">{{ importResults.extraction_info.total_extracted }}</div>
              <div class="text-xs text-emerald-700">Extraits</div>
            </div>
            <div class="p-3 bg-blue-50 rounded-lg text-center">
              <div class="text-2xl font-bold text-blue-600">{{ importResults.extraction_info.total_analyzed }}</div>
              <div class="text-xs text-blue-700">Analysés</div>
            </div>
            <div class="p-3 bg-red-50 rounded-lg text-center">
              <div class="text-2xl font-bold text-red-600">{{ importResults.extraction_info.total_errors }}</div>
              <div class="text-xs text-red-700">Erreurs</div>
            </div>
          </div>

          <div v-if="importResults.results && importResults.results.length > 0" class="space-y-4 max-h-[500px] overflow-y-auto">
            <div v-for="(result, idx) in importResults.results" :key="idx" :class="['p-4 rounded-lg border', result.success ? 'bg-slate-50 border-slate-200' : 'bg-red-50 border-red-200']">
              <div class="flex items-start justify-between mb-3">
                <div class="flex-1">
                  <div class="flex items-center gap-2">
                    <span class="text-xs bg-slate-200 text-slate-600 px-2 py-0.5 rounded">#{{ result.objective_id }}</span>
                    <h4 class="font-semibold text-slate-800">{{ result.title }}</h4>
                  </div>
                  <p v-if="result.description" class="text-sm text-slate-500 mt-1">{{ result.description }}</p>
                </div>
                <div v-if="result.success" :class="['text-2xl font-bold', result.smart_score >= 80 ? 'text-emerald-600' : result.smart_score >= 60 ? 'text-yellow-600' : 'text-red-600']">
                  {{ Math.round(result.smart_score) }}%
                </div>
              </div>

              <template v-if="result.success">
                <div class="flex gap-2 mb-3">
                  <div v-for="letter in ['S','M','A','R','T']" :key="letter" :class="['w-8 h-8 rounded flex items-center justify-center text-sm font-bold', result[`${letter.toLowerCase()}_score`] ? 'bg-emerald-500 text-white' : 'bg-slate-200 text-slate-500']">
                    {{ letter }}
                  </div>
                  <div v-if="result.alignment_score !== null" class="ml-auto flex items-center gap-2">
                    <span :class="['text-sm font-medium px-2 py-1 rounded', result.alignment_text === 'Fort' ? 'bg-purple-100 text-purple-700' : result.alignment_text === 'Moyen' ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700']">
                      Alignement: {{ result.alignment_text }} ({{ result.alignment_score }}%)
                    </span>
                  </div>
                </div>

                <div v-if="result.recommendations && result.recommendations.length > 0" class="mt-2 p-2 bg-amber-50 rounded text-sm">
                  <p class="font-medium text-amber-700 mb-1">💡 Recommandations:</p>
                  <ul class="list-disc list-inside text-amber-600 space-y-0.5">
                    <li v-for="(rec, i) in result.recommendations.slice(0, 2)" :key="i">{{ rec }}</li>
                  </ul>
                </div>

                <div v-if="result.rewrite_fr || result.rewrite_en" class="mt-2 p-2 bg-blue-50 rounded text-sm">
                  <p class="font-medium text-blue-700 mb-1">✨ Reformulation suggérée:</p>
                  <p v-if="result.rewrite_fr" class="text-blue-600">🇫🇷 {{ result.rewrite_fr }}</p>
                </div>
              </template>
              <div v-else class="text-red-600 text-sm">❌ Erreur: {{ result.error }}</div>
            </div>
          </div>

          <div v-if="importResults.errors && importResults.errors.length > 0" class="mt-4 p-4 bg-red-50 rounded-lg border border-red-200">
            <h4 class="font-semibold text-red-700 mb-2">Erreurs ({{ importResults.errors.length }})</h4>
            <p v-for="(err, idx) in importResults.errors" :key="idx" class="text-sm text-red-600">
              Ligne {{ err.row }}: {{ err.title }} - {{ err.error }}
            </p>
          </div>
        </div>

        <!-- Résultat de l'analyse en cours -->
        <div v-if="myAnalysisResult" class="bg-white p-6 rounded-2xl shadow-sm border border-emerald-200">
          <h3 class="font-bold text-lg text-slate-800 mb-4 flex items-center gap-2">
            <CheckCircle2 :size="20" class="text-emerald-500" />
            Résultat de l'analyse
          </h3>
          <div class="flex items-center gap-4 mb-6">
            <div :class="['text-4xl font-bold', myAnalysisResult.smart_score >= 80 ? 'text-emerald-600' : myAnalysisResult.smart_score >= 60 ? 'text-yellow-600' : 'text-red-600']">
              {{ Math.round(myAnalysisResult.smart_score) }}%
            </div>
            <div>
              <div class="text-sm font-semibold text-slate-700">Score SMART</div>
              <div class="text-xs text-slate-500">{{ myAnalysisResult.smart_analysis?.overall ? 'Objectif SMART validé ✓' : 'Améliorations nécessaires' }}</div>
            </div>
          </div>

          <div class="flex gap-2 mb-6">
            <div v-for="letter in ['S','M','A','R','T']" :key="letter" :class="['w-12 h-12 rounded-lg flex flex-col items-center justify-center', myAnalysisResult.smart_analysis?.[letter] ? 'bg-emerald-500 text-white' : 'bg-slate-200 text-slate-500']">
              <span class="text-lg font-bold">{{ letter }}</span>
            </div>
          </div>

          <div v-if="myAnalysisResult.smart_analysis?.issues && myAnalysisResult.smart_analysis.issues.length > 0" class="mb-6">
            <h4 class="font-semibold text-slate-700 mb-2 flex items-center gap-2">
              <AlertCircle :size="16" class="text-orange-500" />
              Points à améliorer
            </h4>
            <div class="space-y-2">
              <div v-for="(issue, idx) in myAnalysisResult.smart_analysis.issues" :key="idx" class="bg-orange-50 border border-orange-200 rounded-lg p-3">
                <div class="flex items-start gap-2">
                  <span class="bg-orange-500 text-white text-xs font-bold px-2 py-0.5 rounded">{{ issue.letter }}</span>
                  <div>
                    <p class="text-sm text-slate-700">{{ issue.problem }}</p>
                    <p v-if="issue.fix" class="text-xs text-emerald-600 mt-1">💡 {{ issue.fix }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-if="myAnalysisResult.smart_analysis?.rewrite_fr" class="mb-6">
            <h4 class="font-semibold text-slate-700 mb-2 flex items-center gap-2">
              <RefreshCw :size="16" class="text-blue-500" />
              Reformulation suggérée
            </h4>
            <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p class="text-sm text-blue-800 italic">"{{ myAnalysisResult.smart_analysis.rewrite_fr }}"</p>
            </div>
          </div>

          <div v-if="myAnalysisResult.alignment_analysis">
            <h4 class="font-semibold text-slate-700 mb-2 flex items-center gap-2">
              <Target :size="16" class="text-purple-500" />
              Alignement stratégique: {{ myAnalysisResult.alignment_analysis.alignment_score }}%
            </h4>
            <div v-if="myAnalysisResult.alignment_analysis.top_matches?.length > 0" class="text-xs text-slate-500">
              Aligné avec: {{ myAnalysisResult.alignment_analysis.top_matches.map(m => m.title || m.objective_id).join(', ') }}
            </div>
          </div>
        </div>

        <!-- Historique des analyses -->
        <div class="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
          <div class="p-4 border-b border-slate-100">
            <h3 class="font-bold text-lg text-slate-800 flex items-center gap-2">
              <PieChartIcon :size="20" class="text-slate-400" />
              Historique de mes analyses
              <span v-if="analysisHistory.length > 0" class="bg-slate-200 text-slate-600 text-xs px-2 py-0.5 rounded-full ml-2">{{ analysisHistory.length }}</span>
            </h3>
          </div>

          <div v-if="analysisHistory.length === 0" class="p-8 text-center text-slate-400">
            <Sparkles :size="32" class="mx-auto mb-2 opacity-50" />
            <p>Aucune analyse effectuée pour le moment.</p>
          </div>
          <div v-else class="divide-y divide-slate-100 max-h-96 overflow-y-auto">
            <div v-for="(item, idx) in analysisHistory" :key="item.id || idx" class="p-4 hover:bg-slate-50 transition-colors cursor-pointer group" @click="selectedHistoryItem = item">
              <div class="flex items-center justify-between">
                <div class="flex-1">
                  <div class="font-medium text-slate-800 group-hover:text-emerald-600 transition-colors">{{ item.objective_title || `Analyse #${idx + 1}` }}</div>
                  <div class="text-xs text-slate-400 mt-1 flex items-center gap-2">
                    <span>{{ new Date(item.analyzed_at).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) }}</span>
                    <span class="text-emerald-500 opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1"><Eye :size="12" /> Voir détails</span>
                  </div>
                </div>
                <div class="flex items-center gap-3">
                  <div class="flex gap-1">
                    <span v-for="letter in ['s','m','a','r','t']" :key="letter" :class="['w-6 h-6 flex items-center justify-center rounded text-xs font-bold', item[`${letter}_score`] ? 'bg-emerald-500 text-white' : 'bg-slate-200 text-slate-400']">
                      {{ letter.toUpperCase() }}
                    </span>
                  </div>
                  <div :class="['text-lg font-bold', item.smart_score >= 80 ? 'text-emerald-600' : item.smart_score >= 60 ? 'text-yellow-600' : 'text-red-600']">
                    {{ Math.round(item.smart_score) }}%
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- TÂCHE: Mon Équipe -->
      <div v-if="activeTask === 'team'" class="space-y-6">
        <div class="flex items-center justify-between">
          <button @click="activeTask = null" class="flex items-center gap-2 text-emerald-600 font-bold hover:underline">
            <ChevronRight class="rotate-180" :size="20" /> Retour aux tâches
          </button>
          <div class="flex items-center gap-2 bg-emerald-100 text-emerald-700 px-4 py-2 rounded-lg">
            <Users :size="18" />
            <span class="font-bold">Tâche: Mon équipe</span>
          </div>
        </div>

        <!-- Actions et filtres -->
        <div class="flex flex-wrap gap-4 items-center justify-between">
          <div class="flex gap-3 items-center">
            <div class="relative">
              <Search :size="16" class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input v-model="searchQuery" type="text" placeholder="Rechercher..." class="pl-9 pr-4 py-2 border border-slate-200 rounded-lg text-sm w-48" />
            </div>
            <select v-model="filterMember" class="px-3 py-2 border border-slate-200 rounded-lg text-sm">
              <option value="all">Tous les collaborateurs</option>
              <option v-for="m in smartStats.byMember" :key="m.name" :value="m.name">{{ m.name }}</option>
            </select>
            <select v-model="filterSmartStatus" class="px-3 py-2 border border-slate-200 rounded-lg text-sm">
              <option value="all">Tous statuts</option>
              <option value="smart">✓ SMART</option>
              <option value="non-smart">✗ Non SMART</option>
              <option value="pending">⏳ En attente</option>
            </select>
          </div>
          <div class="relative">
            <button @click="showExportMenu = !showExportMenu" :disabled="isExporting" class="px-4 py-2 bg-emerald-600 text-white rounded-lg font-bold text-sm hover:bg-emerald-700 flex items-center gap-2 disabled:opacity-50">
              <Loader2 v-if="isExporting" :size="16" class="animate-spin" />
              <Download v-else :size="16" />
              Exporter
            </button>
            <div v-if="showExportMenu" class="absolute right-0 top-full mt-2 bg-white rounded-lg shadow-lg border border-slate-200 overflow-hidden z-50 min-w-[160px]">
              <button @click="handleExport('excel')" class="w-full px-4 py-3 text-left text-sm hover:bg-emerald-50 flex items-center gap-2 text-slate-700">
                <FileSpreadsheet :size="16" class="text-emerald-600" />
                Export Excel
              </button>
              <button @click="handleExport('pdf')" class="w-full px-4 py-3 text-left text-sm hover:bg-red-50 flex items-center gap-2 text-slate-700 border-t border-slate-100">
                <FileSpreadsheet :size="16" class="text-red-600" />
                Export PDF
              </button>
            </div>
          </div>
        </div>

        <!-- KPIs SMART -->
        <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div class="bg-white p-4 rounded-xl shadow-sm border border-slate-100 text-center">
            <div class="text-2xl font-black text-slate-800">{{ smartStats.total }}</div>
            <div class="text-[10px] text-slate-400 uppercase font-bold">Total analysés</div>
          </div>
          <div class="bg-white p-4 rounded-xl shadow-sm border border-slate-100 text-center">
            <div class="text-2xl font-black text-emerald-600">{{ smartStats.smart }}</div>
            <div class="text-[10px] text-slate-400 uppercase font-bold">SMART</div>
          </div>
          <div class="bg-white p-4 rounded-xl shadow-sm border border-slate-100 text-center">
            <div class="text-2xl font-black text-amber-600">{{ smartStats.nonSmart }}</div>
            <div class="text-[10px] text-slate-400 uppercase font-bold">Non SMART</div>
          </div>
          <div class="bg-white p-4 rounded-xl shadow-sm border border-slate-100 text-center">
            <div class="text-2xl font-black text-emerald-600">{{ smartStats.smartRate !== null ? `${smartStats.smartRate}%` : '—' }}</div>
            <div class="text-[10px] text-slate-400 uppercase font-bold">Taux conformité</div>
          </div>
          <div class="bg-white p-4 rounded-xl shadow-sm border border-slate-100 text-center">
            <div class="text-2xl font-black text-blue-600">{{ kpis.avgAlignment !== null ? `${kpis.avgAlignment}%` : '—' }}</div>
            <div class="text-[10px] text-slate-400 uppercase font-bold">Alignement moy.</div>
          </div>
        </div>

        <div class="grid lg:grid-cols-3 gap-6">
          <!-- Liste des résultats -->
          <div class="lg:col-span-2 bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
            <h3 class="font-bold text-lg text-slate-800 mb-4">Objectifs de l'équipe ({{ filteredObjectives.length }})</h3>

            <div v-if="filteredObjectives.length === 0" class="text-center py-12 text-slate-400">
              <AlertCircle :size="48" class="mx-auto mb-4 text-slate-300" />
              <p>Aucun objectif trouvé.</p>
            </div>
            <div v-else class="space-y-3 max-h-[500px] overflow-y-auto">
              <div v-for="obj in filteredObjectives" :key="obj.id" class="p-4 bg-slate-50 rounded-xl hover:bg-slate-100 transition-all">
                <div class="flex items-center justify-between">
                  <div class="flex-1">
                    <div class="text-xs text-slate-400 font-bold uppercase">{{ obj.user_name || 'Collaborateur' }}</div>
                    <div class="font-bold text-slate-800">{{ obj.title }}</div>
                  </div>
                  <div class="flex items-center gap-3">
                    <div :class="['px-2 py-1 rounded text-xs font-bold', obj.smartAnalysis?.overall ? 'bg-emerald-100 text-emerald-700' : obj.smartAnalysis ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-500']">
                      {{ obj.smartAnalysis?.overall ? 'SMART' : obj.smartAnalysis ? 'Non SMART' : 'En attente' }}
                    </div>
                    <div v-if="obj.smartAnalysis" class="flex gap-0.5">
                      <span v-for="l in ['S','M','A','R','T']" :key="l" :class="['w-4 h-4 rounded text-[8px] flex items-center justify-center font-bold', obj.smartAnalysis?.[l] ? 'bg-emerald-500 text-white' : 'bg-slate-200 text-slate-400']">
                        {{ l }}
                      </span>
                    </div>
                    <button v-if="!obj.smartAnalysis" @click="handleAnalyzeObjective(obj.id)" :disabled="analyzingId === obj.id" class="px-2 py-1 bg-amber-500 text-white rounded text-xs font-bold hover:bg-amber-600 disabled:opacity-50 flex items-center gap-1" title="Lancer l'analyse SMART">
                      <Loader2 v-if="analyzingId === obj.id" :size="12" class="animate-spin" />
                      <Sparkles v-else :size="12" />
                      Analyser
                    </button>
                    <button v-if="obj.smartAnalysis" @click="handleAnalyzeObjective(obj.id)" :disabled="analyzingId === obj.id" class="p-1 text-slate-400 hover:text-amber-600 disabled:opacity-50" title="Relancer l'analyse">
                      <Loader2 v-if="analyzingId === obj.id" :size="14" class="animate-spin" />
                      <RefreshCw v-else :size="14" />
                    </button>
                    <button @click="selectedObjective = obj" class="text-emerald-600 hover:text-emerald-800"><Eye :size="16" /></button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Graphiques et stats -->
          <div class="space-y-6">
            <!-- Donut SMART (SVG) -->
            <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
              <h3 class="font-bold text-sm text-slate-800 mb-4 flex items-center gap-2"><PieChartIcon :size="16" />Répartition SMART</h3>
              <div v-if="donutSegments.length > 0" class="h-48 flex items-center justify-center gap-4">
                <svg width="120" height="120" viewBox="0 0 100 100" class="-rotate-90">
                  <circle cx="50" cy="50" r="42" fill="none" stroke="#f1f5f9" stroke-width="16" />
                  <circle v-for="(seg, i) in donutSegments" :key="i" cx="50" cy="50" r="42" fill="none" :stroke="seg.color" stroke-width="16" :stroke-dasharray="seg.dash" :transform="`rotate(${seg.rotation} 50 50)`" />
                </svg>
                <div class="space-y-1">
                  <div v-for="(seg, i) in donutSegments" :key="i" class="flex items-center gap-2 text-xs">
                    <span class="w-3 h-3 rounded-full" :style="{ backgroundColor: seg.color }"></span>
                    <span class="text-slate-600">{{ seg.name }} {{ seg.pct }}%</span>
                  </div>
                </div>
              </div>
              <div v-else class="h-48 flex items-center justify-center text-slate-400 text-sm">Aucune donnée</div>
            </div>

            <!-- Critères SMART -->
            <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
              <h3 class="font-bold text-sm text-slate-800 mb-4">Critères SMART</h3>
              <div class="space-y-2">
                <div v-for="c in criteriaList" :key="c.letter" class="flex items-center gap-2">
                  <span class="w-6 h-6 rounded bg-emerald-100 text-emerald-700 text-xs font-bold flex items-center justify-center">{{ c.letter }}</span>
                  <div class="flex-1 bg-slate-100 rounded-full h-3">
                    <div class="bg-emerald-500 h-3 rounded-full transition-all" :style="{ width: `${c.pct}%` }"></div>
                  </div>
                  <span class="text-xs text-slate-500 w-10 text-right">{{ c.pct }}%</span>
                </div>
              </div>
            </div>

            <!-- Par collaborateur -->
            <div v-if="smartStats.byMember.length > 0" class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
              <h3 class="font-bold text-sm text-slate-800 mb-4">Par collaborateur</h3>
              <div class="space-y-2 max-h-48 overflow-y-auto">
                <div v-for="m in smartStats.byMember" :key="m.name" class="flex items-center justify-between text-sm p-2 bg-slate-50 rounded-lg">
                  <span class="font-medium text-slate-700">{{ m.name }}</span>
                  <div class="flex items-center gap-2">
                    <span class="text-emerald-600 font-bold">{{ m.smart }}</span>
                    <span class="text-slate-400">/</span>
                    <span class="text-slate-500">{{ m.total }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- TÂCHE: Objectifs Stratégiques -->
      <div v-if="activeTask === 'strategy'" class="space-y-6">
        <div class="flex items-center justify-between">
          <button @click="activeTask = null" class="flex items-center gap-2 text-purple-600 font-bold hover:underline">
            <ChevronRight class="rotate-180" :size="20" /> Retour aux tâches
          </button>
          <div class="flex items-center gap-2 bg-purple-100 text-purple-700 px-4 py-2 rounded-lg">
            <Target :size="18" />
            <span class="font-bold">Tâche: Objectifs stratégiques</span>
          </div>
        </div>

        <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
          <h3 class="font-bold text-lg text-slate-800 mb-4 flex items-center gap-2"><Plus :size="20" />Nouvel Objectif Stratégique</h3>
          <div class="flex gap-4">
            <input v-model="newGoalTitle" class="flex-1 px-4 py-2 border border-slate-200 rounded-lg text-sm" placeholder="Titre de l'objectif stratégique..." />
            <input v-model="newGoalDesc" class="flex-1 px-4 py-2 border border-slate-200 rounded-lg text-sm" placeholder="Description..." />
            <button @click="handleAddCompanyGoal" :disabled="!newGoalTitle.trim()" class="px-6 py-2 bg-purple-600 text-white rounded-lg font-bold hover:bg-purple-700 disabled:opacity-50">Ajouter</button>
          </div>
        </div>

        <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
          <h3 class="font-bold text-lg text-slate-800 mb-4">Catalogue Stratégique ({{ companyObjectives.length }})</h3>
          <div v-if="companyObjectives.length === 0" class="text-center py-12 text-slate-400">
            <Target :size="48" class="mx-auto mb-4 text-slate-300" />
            <p>Aucun objectif stratégique défini.</p>
            <p class="text-sm">Ajoutez des objectifs ci-dessus.</p>
          </div>
          <div v-else class="space-y-2">
            <div v-for="goal in companyObjectives" :key="goal.id" class="p-4 bg-slate-50 rounded-xl flex items-center gap-4">
              <div class="text-xs font-mono text-slate-400 bg-slate-100 px-2 py-1 rounded">{{ goal.id }}</div>
              <div class="flex-1">
                <div class="font-bold text-purple-900">{{ goal.title }}</div>
                <div class="text-xs text-slate-500">{{ goal.description || 'Pas de description' }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- MODAL: Détails de l'analyse historique -->
      <div v-if="selectedHistoryItem" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" @click="selectedHistoryItem = null">
        <div class="bg-white rounded-2xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-hidden" @click.stop>
          <!-- Header -->
          <div class="bg-gradient-to-r from-emerald-600 to-emerald-700 text-white p-6">
            <div class="flex items-start justify-between">
              <div>
                <h2 class="text-xl font-bold">{{ selectedHistoryItem.objective_title || 'Analyse SMART' }}</h2>
                <p class="text-emerald-100 text-sm mt-1">Analysé le {{ formatHistoryDate(selectedHistoryItem.analyzed_at) }}</p>
              </div>
              <button @click="selectedHistoryItem = null" class="p-2 hover:bg-white/20 rounded-lg transition-colors"><X :size="24" /></button>
            </div>
            <div class="flex items-center gap-6 mt-4">
              <div class="text-4xl font-bold">{{ Math.round(selectedHistoryItem.smart_score) }}%</div>
              <div class="flex gap-2">
                <span v-for="letter in ['S','M','A','R','T']" :key="letter" :class="['w-10 h-10 flex items-center justify-center rounded-lg text-lg font-bold', selectedHistoryItem[`${letter.toLowerCase()}_score`] ? 'bg-white text-emerald-600' : 'bg-emerald-500/30 text-emerald-200']">
                  {{ letter }}
                </span>
              </div>
            </div>
          </div>

          <!-- Contenu -->
          <div class="p-6 overflow-y-auto max-h-[60vh]">
            <div class="space-y-4">
              <h3 class="font-bold text-lg text-slate-800 flex items-center gap-2">
                <Target :size="20" class="text-emerald-500" />
                Analyse SMART détaillée
              </h3>
              <div class="grid gap-3">
                <div v-for="criterion in historyCriteria" :key="criterion.key" :class="['p-4 rounded-xl border', historyIsValid(selectedHistoryItem, criterion.key) ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200']">
                  <div class="flex items-center gap-3">
                    <span :class="['w-8 h-8 flex items-center justify-center rounded-lg font-bold', historyIsValid(selectedHistoryItem, criterion.key) ? 'bg-emerald-500 text-white' : 'bg-red-500 text-white']">
                      {{ criterion.key }}
                    </span>
                    <div class="flex-1">
                      <div class="font-medium text-slate-800">{{ criterion.label }}</div>
                      <div class="text-xs text-slate-500">{{ criterion.desc }}</div>
                    </div>
                    <CheckCircle2 v-if="historyIsValid(selectedHistoryItem, criterion.key)" :size="24" class="text-emerald-500" />
                    <AlertCircle v-else :size="24" class="text-red-500" />
                  </div>
                  <p v-if="historyExplanation(selectedHistoryItem, criterion.key)" class="mt-2 text-sm text-slate-600 pl-11">{{ historyExplanation(selectedHistoryItem, criterion.key) }}</p>
                  <div v-if="!historyIsValid(selectedHistoryItem, criterion.key) && historyIssueFor(selectedHistoryItem, criterion.key)" class="mt-2 pl-11">
                    <p class="text-sm text-red-600">{{ historyIssueFor(selectedHistoryItem, criterion.key).problem }}</p>
                    <p v-if="historyIssueFor(selectedHistoryItem, criterion.key).fix" class="text-sm text-emerald-600 mt-1">💡 {{ historyIssueFor(selectedHistoryItem, criterion.key).fix }}</p>
                  </div>
                </div>
              </div>

              <!-- Problèmes détectés -->
              <div v-if="selectedHistoryItem.smart_analysis?.issues && selectedHistoryItem.smart_analysis.issues.length > 0" class="mt-6">
                <h4 class="font-bold text-slate-700 mb-3 flex items-center gap-2">
                  <AlertCircle :size="18" class="text-amber-500" />
                  Points d'amélioration ({{ selectedHistoryItem.smart_analysis.issues.length }})
                </h4>
                <div class="space-y-2">
                  <div v-for="(issue, idx) in selectedHistoryItem.smart_analysis.issues" :key="idx" class="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                    <div class="font-medium text-amber-800">
                      <span class="font-bold text-amber-900">[{{ issue.letter }}]</span> {{ issue.problem || issue }}
                    </div>
                    <div v-if="issue.suggestion || issue.fix" class="text-sm text-amber-600 mt-1">💡 {{ issue.suggestion || issue.fix }}</div>
                  </div>
                </div>
              </div>

              <!-- Reformulations suggérées -->
              <div v-if="selectedHistoryItem.smart_analysis?.rewrite_fr || selectedHistoryItem.smart_analysis?.rewrite_en || selectedHistoryItem.smart_analysis?.suggestion" class="mt-6 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl">
                <h4 class="font-bold text-blue-800 mb-3 flex items-center gap-2"><Sparkles :size="18" />Reformulations suggérées</h4>
                <div class="space-y-3">
                  <div v-if="selectedHistoryItem.smart_analysis?.rewrite_fr" class="p-3 bg-white rounded-lg border border-blue-100">
                    <div class="text-xs font-medium text-blue-500 mb-1">🇫🇷 Version française améliorée</div>
                    <p class="text-slate-800 font-medium">{{ selectedHistoryItem.smart_analysis.rewrite_fr }}</p>
                  </div>
                  <div v-if="selectedHistoryItem.smart_analysis?.rewrite_en" class="p-3 bg-white rounded-lg border border-blue-100">
                    <div class="text-xs font-medium text-blue-500 mb-1">🇬🇧 English improved version</div>
                    <p class="text-slate-800 font-medium">{{ selectedHistoryItem.smart_analysis.rewrite_en }}</p>
                  </div>
                  <div v-if="selectedHistoryItem.smart_analysis?.suggestion && !selectedHistoryItem.smart_analysis?.rewrite_fr" class="p-3 bg-white rounded-lg border border-blue-100">
                    <div class="text-xs font-medium text-blue-500 mb-1">💡 Suggestion</div>
                    <p class="text-slate-800">{{ selectedHistoryItem.smart_analysis.suggestion }}</p>
                  </div>
                </div>
              </div>
            </div>

            <!-- Analyse d'alignement -->
            <div v-if="selectedHistoryItem.alignment_analysis || selectedHistoryItem.alignment_score > 0" class="mt-6 pt-6 border-t border-slate-200">
              <h3 class="font-bold text-lg text-slate-800 flex items-center gap-2 mb-4">
                <TrendingUp :size="20" class="text-purple-500" />
                Alignement stratégique
              </h3>
              <div class="flex items-center gap-4 mb-4">
                <div class="text-3xl font-bold text-purple-600">{{ selectedHistoryItem.alignment_analysis?.alignment_score || selectedHistoryItem.alignment_score || 0 }}%</div>
                <div class="text-sm text-slate-500">Score d'alignement avec les objectifs stratégiques</div>
              </div>
              <div v-if="selectedHistoryItem.alignment_analysis?.top_matches && selectedHistoryItem.alignment_analysis.top_matches.length > 0" class="space-y-2">
                <h4 class="text-sm font-medium text-slate-600">Objectifs stratégiques liés :</h4>
                <div v-for="(match, idx) in selectedHistoryItem.alignment_analysis.top_matches" :key="idx" class="p-3 bg-purple-50 rounded-lg flex items-center justify-between">
                  <span class="text-purple-800">{{ match.title || match }}</span>
                  <span v-if="match.score" class="text-sm font-bold text-purple-600">{{ match.score }}%</span>
                </div>
              </div>
              <div v-if="selectedHistoryItem.alignment_analysis?.gaps && selectedHistoryItem.alignment_analysis.gaps.length > 0" class="mt-4">
                <h4 class="text-sm font-medium text-slate-600 mb-2">Écarts identifiés :</h4>
                <ul class="list-disc list-inside text-sm text-slate-500 space-y-1">
                  <li v-for="(gap, idx) in selectedHistoryItem.alignment_analysis.gaps" :key="idx">{{ gap }}</li>
                </ul>
              </div>
            </div>

            <!-- Message informatif -->
            <div v-if="!selectedHistoryItem.smart_analysis" class="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-xl text-center">
              <p class="text-sm text-blue-600">
                ℹ️ Les scores SMART ci-dessus sont basés sur les données enregistrées.
                Les détails complets (reformulations, suggestions) seront disponibles pour les prochaines analyses.
              </p>
            </div>
          </div>

          <!-- Footer -->
          <div class="p-4 border-t border-slate-200 bg-slate-50 flex justify-end">
            <button @click="selectedHistoryItem = null" class="px-6 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 rounded-lg font-medium transition-colors">Fermer</button>
          </div>
        </div>
      </div>
    </div>
  </DashboardLayout>
</template>
