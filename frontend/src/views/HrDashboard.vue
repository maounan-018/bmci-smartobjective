<script setup>
// HrDashboard.vue — Module d'analyse RH (migration de pages/HrDashboard.tsx).
// Import des fichiers (stratégie / objectifs), analyse groupée via SSE, tableaux de bord
// analytiques (graphiques vue-chartjs en remplacement de recharts), vue détaillée et
// analyse SMART personnelle du RH. L'utilisateur provient du store d'auth.
import { ref, computed, onMounted, watch } from 'vue';
import { useAuthStore } from '@/stores/authStore';
import { ApiService } from '@/services/apiService';
import { Line, Bar, Pie } from 'vue-chartjs';
import {
  Chart as ChartJS, Title, Tooltip, Legend, BarElement, CategoryScale,
  LinearScale, PointElement, LineElement, ArcElement,
} from 'chart.js';
import DashboardLayout from '@/layouts/DashboardLayout.vue';
import {
  ShieldCheck, Upload, Download, ChevronRight, Loader2, Target, Users, BarChart3,
  CheckCircle2, AlertCircle, TrendingUp, FileSpreadsheet, Sparkles, RefreshCw, Eye,
  Filter, FileCheck2, History,
} from 'lucide-vue-next';

// Enregistrement des éléments Chart.js nécessaires.
ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale, PointElement, LineElement, ArcElement);

const COLORS = ['#059669', '#10b981', '#6ee7b7', '#a7f3d0'];
const PIE_COLORS = ['#059669', '#f59e0b', '#ef4444'];

const auth = useAuthStore();

const view = ref('dashboard'); // 'dashboard' | 'details'
const loading = ref(true);
const error = ref(null);

// Données
const analytics = ref(null);
const objectives = ref([]);
const imports = ref([]);

// Filtres
const filters = ref({ entity: '', manager: '', period: '' });

// Import & analyse
const stratFile = ref(null);
const objFile = ref(null);
const isUploading = ref(null); // 'strategy' | 'objectives' | null
const isAnalyzing = ref(false);
const lastAnalysis = ref(null);
const analysisProgress = ref({ current: 0, total: 0, title: '' });
const stratFileInput = ref(null);
const objFileInput = ref(null);

// Import Excel personnel
const isImportingPersonal = ref(false);
const personalImportResults = ref(null);
const personalFileInput = ref(null);

// Historique des analyses personnelles RH
const hrAnalysisHistory = ref([]);
const selectedHrAnalysis = ref(null);

// Formulaire d'analyse personnelle RH
const hrObjectiveTitle = ref('');
const hrObjectiveDesc = ref('');
const isAnalyzingPersonal = ref(false);
const hrAnalysisResult = ref(null);

// Vue détaillée d'un objectif
const selectedHRObjective = ref(null);

// Export
const showExportMenu = ref(false);
const isExporting = ref(false);

// Critères SMART communs aux modaux.
const criteriaDefs = [
  { key: 'S', label: 'Spécifique', desc: "L'objectif est-il clairement défini ?" },
  { key: 'M', label: 'Mesurable', desc: 'Peut-on quantifier le résultat ?' },
  { key: 'A', label: 'Atteignable', desc: "L'objectif est-il réaliste ?" },
  { key: 'R', label: 'Réaliste', desc: "Est-il pertinent pour l'organisation ?" },
  { key: 'T', label: 'Temporel', desc: 'Y a-t-il une échéance définie ?' },
];

onMounted(loadData);
watch(filters, loadData, { deep: true });

async function loadData() {
  loading.value = true;
  error.value = null;
  try {
    const [analyticsData, objectivesData, importsData, hrAnalysisData] = await Promise.all([
      ApiService.getHRAnalytics(filters.value),
      ApiService.getHRObjectivesDetails(filters.value),
      ApiService.getHRImports(),
      ApiService.getHRAnalysisResults(),
    ]);
    analytics.value = analyticsData;
    objectives.value = objectivesData.objectives;
    imports.value = importsData;
    if (hrAnalysisData) hrAnalysisHistory.value = hrAnalysisData.results || [];
  } catch (err) {
    console.error(err);
    error.value = 'Erreur lors de la récupération des données RH.';
  } finally {
    loading.value = false;
  }
}

async function handleFileUpload(type) {
  const file = type === 'strategy' ? stratFile.value : objFile.value;
  if (!file) return;
  isUploading.value = type;
  error.value = null;
  try {
    const result = type === 'strategy'
      ? await ApiService.importStrategyExcel(file)
      : await ApiService.importObjectivesExcel(file);
    if (result.success) {
      alert(`${result.imported} lignes importées depuis ${file.name}.`);
      if (type === 'strategy') stratFile.value = null;
      if (type === 'objectives') objFile.value = null;
      await loadData();
    } else {
      throw new Error(result.error || 'Erreur inconnue');
    }
  } catch (err) {
    error.value = `Erreur import (${type}): ${err.message}`;
  } finally {
    isUploading.value = null;
  }
}

async function handleAnalyze() {
  isAnalyzing.value = true;
  error.value = null;
  lastAnalysis.value = null;
  analysisProgress.value = { current: 0, total: 0, title: '' };
  try {
    const result = await ApiService.analyzeBatch([], (progress) => {
      if (progress.type === 'start') {
        analysisProgress.value = { current: 0, total: progress.total || 0, title: '' };
      } else if (progress.type === 'progress') {
        analysisProgress.value = { current: progress.current || 0, total: progress.total || 0, title: progress.title || '' };
      }
    });
    if (result.success) {
      lastAnalysis.value = result;
      await loadData();
    } else {
      throw new Error("L'analyse groupée a échoué.");
    }
  } catch (err) {
    error.value = err.message;
  } finally {
    isAnalyzing.value = false;
    analysisProgress.value = { current: 0, total: 0, title: '' };
  }
}

async function handleAnalyzeHRObjective() {
  if (!hrObjectiveTitle.value.trim()) {
    alert('Veuillez saisir un titre pour votre objectif.');
    return;
  }
  isAnalyzingPersonal.value = true;
  hrAnalysisResult.value = null;
  try {
    const result = await ApiService.analyzeHRPersonalObjective(hrObjectiveTitle.value, hrObjectiveDesc.value);
    if (result) {
      hrAnalysisResult.value = result;
      const hrAnalysisData = await ApiService.getHRAnalysisResults();
      if (hrAnalysisData) hrAnalysisHistory.value = hrAnalysisData.results || [];
      hrObjectiveTitle.value = '';
      hrObjectiveDesc.value = '';
    }
  } catch (err) {
    console.error('Erreur analyse:', err);
    error.value = "Erreur lors de l'analyse de l'objectif.";
  } finally {
    isAnalyzingPersonal.value = false;
  }
}

async function handleImportPersonalExcel(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
    alert('Format non supporté. Veuillez utiliser un fichier Excel (.xlsx ou .xls)');
    return;
  }
  isImportingPersonal.value = true;
  personalImportResults.value = null;
  error.value = null;
  try {
    const result = await ApiService.importExcelForAnalysis(file);
    if (result) {
      personalImportResults.value = result;
      await loadData();
    }
  } catch (err) {
    console.error('Erreur import:', err);
    error.value = err.message || "Erreur lors de l'import du fichier Excel.";
  } finally {
    isImportingPersonal.value = false;
    if (personalFileInput.value) personalFileInput.value.value = '';
  }
}

async function handleExport(format) {
  isExporting.value = true;
  showExportMenu.value = false;
  try {
    const blob = format === 'excel'
      ? await ApiService.exportHRExcel(filters.value)
      : await ApiService.exportHRPdf(filters.value);
    if (blob) {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const date = new Date().toISOString().split('T')[0];
      a.download = format === 'excel' ? `Rapport_RH_BMCI_${date}.xlsx` : `Rapport_RH_BMCI_${date}.pdf`;
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

function resetFilters() {
  filters.value = { entity: '', manager: '', period: '' };
}

function onStratFileChange(e) { stratFile.value = e.target.files?.[0] || null; }
function onObjFileChange(e) { objFile.value = e.target.files?.[0] || null; }

// Glisser-deposer (drag & drop) depuis l'Explorateur du systeme.
// Permet de contourner la popup "Charger depuis mobile" d'Edge :
// l'utilisateur fait glisser le fichier directement sur la zone.
const dragStrat = ref(false);
const dragObj = ref(false);

function _validateExcel(file) {
  if (!file) return null;
  const name = (file.name || '').toLowerCase();
  if (!name.endsWith('.xlsx') && !name.endsWith('.xls')) {
    alert('Format non supporté. Veuillez utiliser un fichier Excel (.xlsx ou .xls).');
    return null;
  }
  return file;
}

function onStratDrop(e) {
  dragStrat.value = false;
  const f = _validateExcel(e.dataTransfer?.files?.[0]);
  if (f) stratFile.value = f;
}
function onObjDrop(e) {
  dragObj.value = false;
  const f = _validateExcel(e.dataTransfer?.files?.[0]);
  if (f) objFile.value = f;
}

function downloadPersonalTemplate() {
  const csvContent = "Titre,Description\nAméliorer les performances RH,Objectif stratégique pour Q2\nOptimiser le recrutement,Réduire le délai de recrutement de 20%";
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'modele_objectifs_rh.csv';
  link.click();
}

function formatDateTime(value) {
  return new Date(value).toLocaleDateString('fr-FR', {
    day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
  });
}

// Parsing tolérant des analyses (objet ou chaîne JSON).
function parseJson(value) {
  if (!value) return {};
  if (typeof value === 'string') {
    try { return JSON.parse(value || '{}'); } catch { return {}; }
  }
  return value;
}

// ============ DONNÉES DES GRAPHIQUES (vue-chartjs) ============
const lineChartData = computed(() => ({
  labels: (analytics.value?.smart_evolution || []).map(d => d.month),
  datasets: [
    {
      label: 'Score SMART',
      data: (analytics.value?.smart_evolution || []).map(d => d.avg_smart),
      borderColor: '#059669', backgroundColor: '#059669', tension: 0.3,
    },
    {
      label: 'Alignement',
      data: (analytics.value?.alignment_evolution || []).map(d => d.avg_alignment),
      borderColor: '#f59e0b', backgroundColor: '#f59e0b', tension: 0.3,
    },
  ],
}));
const lineChartOptions = {
  responsive: true, maintainAspectRatio: false,
  scales: { y: { min: 0, max: 100, ticks: { callback: v => `${v}%` } } },
};

const blockingChartData = computed(() => ({
  labels: (analytics.value?.blocking_points || []).map(d => d.criteria),
  datasets: [{
    label: "Nb. d'échecs",
    data: (analytics.value?.blocking_points || []).map(d => d.failures),
    backgroundColor: '#ef4444',
  }],
}));
const blockingChartOptions = {
  indexAxis: 'y', responsive: true, maintainAspectRatio: false,
  plugins: { legend: { display: false } },
};

const alignmentPieData = computed(() => ({
  labels: (analytics.value?.alignment_distribution || []).map(d => d.level),
  datasets: [{
    data: (analytics.value?.alignment_distribution || []).map(d => d.count),
    backgroundColor: PIE_COLORS,
  }],
}));
const smartPieData = computed(() => ({
  labels: (analytics.value?.smart_distribution || []).map(d => d.level),
  datasets: [{
    data: (analytics.value?.smart_distribution || []).map(d => d.count),
    backgroundColor: COLORS,
  }],
}));
const pieOptions = { responsive: true, maintainAspectRatio: false };

const hasData = computed(() => analytics.value && analytics.value.global_stats.total > 0);

// Helpers KPI / tableaux comparatifs.
function kpiDisplay(value, format) {
  if (value === undefined || value === null) return 'N/A';
  return format === 'percent' ? `${value.toFixed(0)}%` : value.toLocaleString('fr-FR');
}

// Modaux : détail d'une analyse RH personnelle.
const hrModalSmart = computed(() => parseJson(selectedHrAnalysis.value?.smart_analysis));
const hrModalAlignment = computed(() => parseJson(selectedHrAnalysis.value?.alignment_analysis));

// Modaux : détail d'un objectif RH.
const objModalSmart = computed(() => parseJson(selectedHRObjective.value?.smart_analysis));
const objModalAlignment = computed(() => parseJson(selectedHRObjective.value?.alignment_analysis));

function smartValid(analysisObj, item, key) {
  return analysisObj?.[key] || item?.[`${key.toLowerCase()}_score`];
}
function smartExplanation(analysisObj, key) {
  return analysisObj?.[`${key}_explanation`] || analysisObj?.[`${key.toLowerCase()}_explanation`];
}
function smartIssueFor(analysisObj, key) {
  return analysisObj?.issues?.find(i => i.letter === key);
}
function noDetailedAnalysis(analysisObj) {
  return !analysisObj?.issues && !Object.keys(analysisObj || {}).some(k => ['S', 'M', 'A', 'R', 'T'].includes(k));
}
</script>

<template>
  <DashboardLayout>
    <div class="p-4 md:p-8 max-w-7xl mx-auto space-y-8">
      <!-- ===== MODAL: Détail objectif RH ===== -->
      <div v-if="selectedHRObjective" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
          <div class="sticky top-0 bg-gradient-to-r from-emerald-600 to-teal-600 p-6 rounded-t-2xl">
            <div class="flex items-center justify-between">
              <div>
                <h2 class="text-xl font-bold text-white">{{ selectedHRObjective.title }}</h2>
                <p class="text-emerald-100 text-sm mt-1">
                  {{ selectedHRObjective.user_name || 'Collaborateur' }} • {{ selectedHRObjective.entity || 'Entité N/A' }} • {{ selectedHRObjective.period || 'Période N/A' }}
                </p>
              </div>
              <button @click="selectedHRObjective = null" class="p-2 text-white/80 hover:text-white hover:bg-white/20 rounded-lg transition-colors">
                <ChevronRight :size="24" class="rotate-180" />
              </button>
            </div>
          </div>

          <div class="p-6 space-y-6">
            <div v-if="selectedHRObjective.description" class="bg-slate-50 p-4 rounded-xl">
              <h3 class="font-bold text-slate-700 mb-2">Description</h3>
              <p class="text-slate-600">{{ selectedHRObjective.description }}</p>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div class="bg-emerald-50 p-4 rounded-xl text-center">
                <div class="text-3xl font-black text-emerald-600">{{ selectedHRObjective.smart_score?.toFixed(0) || 0 }}%</div>
                <div class="text-sm text-emerald-700 font-medium">Score SMART</div>
              </div>
              <div class="bg-amber-50 p-4 rounded-xl text-center">
                <div class="text-3xl font-black text-amber-600">{{ selectedHRObjective.alignment_score?.toFixed(0) || 0 }}%</div>
                <div class="text-sm text-amber-700 font-medium">Score Alignement</div>
              </div>
            </div>

            <div class="bg-white border rounded-xl p-4">
              <h3 class="font-bold text-slate-800 mb-4 flex items-center gap-2">
                <Target :size="20" class="text-emerald-600" />
                Critères SMART - Analyse détaillée
              </h3>
              <div class="space-y-3">
                <div v-for="criterion in criteriaDefs" :key="criterion.key" :class="['p-4 rounded-xl border', smartValid(objModalSmart, selectedHRObjective, criterion.key) ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200']">
                  <div class="flex items-center gap-3">
                    <span :class="['w-10 h-10 flex items-center justify-center rounded-lg text-lg font-bold', smartValid(objModalSmart, selectedHRObjective, criterion.key) ? 'bg-emerald-500 text-white' : 'bg-red-500 text-white']">{{ criterion.key }}</span>
                    <div class="flex-1">
                      <div class="font-semibold text-slate-800">{{ criterion.label }}</div>
                      <div class="text-xs text-slate-500">{{ criterion.desc }}</div>
                    </div>
                    <CheckCircle2 v-if="smartValid(objModalSmart, selectedHRObjective, criterion.key)" :size="24" class="text-emerald-500" />
                    <AlertCircle v-else :size="24" class="text-red-500" />
                  </div>
                  <p v-if="smartExplanation(objModalSmart, criterion.key)" class="mt-2 text-sm text-slate-600 pl-13 ml-13">{{ smartExplanation(objModalSmart, criterion.key) }}</p>
                  <div v-if="!smartValid(objModalSmart, selectedHRObjective, criterion.key) && smartIssueFor(objModalSmart, criterion.key)" class="mt-2 ml-13 pl-13">
                    <p class="text-sm text-red-600">{{ smartIssueFor(objModalSmart, criterion.key).problem }}</p>
                    <p v-if="smartIssueFor(objModalSmart, criterion.key).fix" class="text-sm text-emerald-600 mt-1">💡 {{ smartIssueFor(objModalSmart, criterion.key).fix }}</p>
                  </div>
                </div>
              </div>
              <div v-if="noDetailedAnalysis(objModalSmart)" class="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-xl text-center">
                <p class="text-sm text-blue-600">ℹ️ Les scores SMART ci-dessus sont basés sur les données enregistrées. Les détails complets seront disponibles pour les prochaines analyses.</p>
              </div>
            </div>

            <div v-if="objModalAlignment && Object.keys(objModalAlignment).length" class="bg-white border rounded-xl p-4">
              <h3 class="font-bold text-slate-800 mb-4 flex items-center gap-2">
                <TrendingUp :size="20" class="text-amber-600" />
                Alignement Stratégique
              </h3>
              <div v-if="objModalAlignment.top_matches && objModalAlignment.top_matches.length > 0" class="space-y-2">
                <h4 class="font-semibold text-slate-700 text-sm">Objectifs stratégiques alignés :</h4>
                <div v-for="(match, idx) in objModalAlignment.top_matches" :key="idx" class="bg-emerald-50 border border-emerald-100 rounded-lg p-3">
                  <div class="flex items-center justify-between">
                    <span class="font-semibold text-emerald-700">{{ match.objective_id }}</span>
                    <span class="bg-emerald-500 text-white text-xs px-2 py-1 rounded-full font-bold">{{ match.score }}%</span>
                  </div>
                  <p v-if="match.reason" class="text-emerald-600 text-sm mt-1">{{ match.reason }}</p>
                </div>
              </div>
              <div v-if="objModalAlignment.gaps && objModalAlignment.gaps.length > 0" class="mt-4 space-y-2">
                <h4 class="font-semibold text-slate-700 text-sm">Points d'amélioration :</h4>
                <div v-for="(gap, idx) in objModalAlignment.gaps" :key="idx" class="bg-amber-50 border border-amber-100 rounded-lg p-3 text-amber-700 text-sm">⚠️ {{ gap }}</div>
              </div>
            </div>

            <div v-if="objModalSmart?.rewrite_fr || selectedHRObjective.rewrite_fr || objModalSmart?.rewrite_en || selectedHRObjective.rewrite_en" class="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-100 rounded-xl p-4">
              <h3 class="font-bold text-blue-800 mb-4 flex items-center gap-2"><Sparkles :size="20" />Reformulations Suggérées</h3>
              <div v-if="objModalSmart?.rewrite_fr || selectedHRObjective.rewrite_fr" class="mb-3">
                <h4 class="font-semibold text-blue-700 text-sm mb-1">🇫🇷 Français :</h4>
                <p class="bg-white p-3 rounded-lg text-slate-700 border">{{ objModalSmart?.rewrite_fr || selectedHRObjective.rewrite_fr }}</p>
              </div>
              <div v-if="objModalSmart?.rewrite_en || selectedHRObjective.rewrite_en">
                <h4 class="font-semibold text-blue-700 text-sm mb-1">🇬🇧 English :</h4>
                <p class="bg-white p-3 rounded-lg text-slate-700 border">{{ objModalSmart?.rewrite_en || selectedHRObjective.rewrite_en }}</p>
              </div>
            </div>

            <div class="bg-slate-50 rounded-xl p-4">
              <h3 class="font-bold text-slate-700 mb-3">Informations</h3>
              <div class="grid grid-cols-2 gap-4 text-sm">
                <div><span class="text-slate-500">Manager :</span><span class="ml-2 font-medium">{{ selectedHRObjective.manager_name || 'N/A' }}</span></div>
                <div><span class="text-slate-500">Entité :</span><span class="ml-2 font-medium">{{ selectedHRObjective.entity || 'N/A' }}</span></div>
                <div><span class="text-slate-500">Période :</span><span class="ml-2 font-medium">{{ selectedHRObjective.period || 'N/A' }}</span></div>
                <div><span class="text-slate-500">Analysé le :</span><span class="ml-2 font-medium">{{ selectedHRObjective.analyzed_at ? formatDateTime(selectedHRObjective.analyzed_at) : 'N/A' }}</span></div>
              </div>
            </div>
          </div>

          <div class="sticky bottom-0 bg-slate-50 p-4 rounded-b-2xl border-t flex justify-end">
            <button @click="selectedHRObjective = null" class="px-6 py-2 bg-emerald-600 text-white rounded-lg font-bold hover:bg-emerald-700 transition-colors">Fermer</button>
          </div>
        </div>
      </div>

      <!-- ===== MODAL: Détail analyse RH personnelle ===== -->
      <div v-if="selectedHrAnalysis" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" @click="selectedHrAnalysis = null">
        <div class="bg-white rounded-2xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-hidden" @click.stop>
          <div class="sticky top-0 bg-gradient-to-r from-amber-500 to-orange-600 p-6 text-white">
            <div class="flex items-center justify-between">
              <div>
                <h2 class="text-xl font-bold">{{ selectedHrAnalysis.objective_title || 'Analyse personnelle' }}</h2>
                <p class="text-amber-100 text-sm mt-1">Analysé le {{ formatDateTime(selectedHrAnalysis.analyzed_at) }}</p>
              </div>
              <button @click="selectedHrAnalysis = null" class="p-2 text-white/80 hover:text-white hover:bg-white/20 rounded-lg">
                <ChevronRight :size="24" class="rotate-180" />
              </button>
            </div>
            <div class="mt-4 flex items-center gap-6">
              <div class="text-4xl font-bold">{{ Math.round(selectedHrAnalysis.smart_score || 0) }}%</div>
              <div class="flex gap-1">
                <span v-for="letter in ['S','M','A','R','T']" :key="letter" :class="['w-8 h-8 flex items-center justify-center rounded font-bold', smartValid(hrModalSmart, selectedHrAnalysis, letter) ? 'bg-white text-amber-600' : 'bg-white/30 text-white']">{{ letter }}</span>
              </div>
            </div>
          </div>

          <div class="p-6 overflow-y-auto max-h-[60vh]">
            <div v-if="selectedHrAnalysis.description" class="mb-6 p-4 bg-slate-50 rounded-xl">
              <h3 class="font-bold text-slate-700 mb-2">Description</h3>
              <p class="text-slate-600">{{ selectedHrAnalysis.description }}</p>
            </div>

            <div class="space-y-4">
              <h3 class="font-bold text-lg text-slate-800 flex items-center gap-2"><Target :size="20" class="text-emerald-500" />Analyse SMART détaillée</h3>
              <div class="grid gap-3">
                <div v-for="criterion in criteriaDefs" :key="criterion.key" :class="['p-4 rounded-xl border', smartValid(hrModalSmart, selectedHrAnalysis, criterion.key) ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200']">
                  <div class="flex items-center gap-3">
                    <span :class="['w-8 h-8 flex items-center justify-center rounded-lg font-bold', smartValid(hrModalSmart, selectedHrAnalysis, criterion.key) ? 'bg-emerald-500 text-white' : 'bg-red-500 text-white']">{{ criterion.key }}</span>
                    <div class="flex-1">
                      <div class="font-medium text-slate-800">{{ criterion.label }}</div>
                      <div class="text-xs text-slate-500">{{ criterion.desc }}</div>
                    </div>
                    <CheckCircle2 v-if="smartValid(hrModalSmart, selectedHrAnalysis, criterion.key)" :size="24" class="text-emerald-500" />
                    <AlertCircle v-else :size="24" class="text-red-500" />
                  </div>
                  <p v-if="smartExplanation(hrModalSmart, criterion.key)" class="mt-2 text-sm text-slate-600 pl-11">{{ smartExplanation(hrModalSmart, criterion.key) }}</p>
                  <div v-if="!smartValid(hrModalSmart, selectedHrAnalysis, criterion.key) && smartIssueFor(hrModalSmart, criterion.key)" class="mt-2 pl-11">
                    <p class="text-sm text-red-600">{{ smartIssueFor(hrModalSmart, criterion.key).problem }}</p>
                    <p v-if="smartIssueFor(hrModalSmart, criterion.key).fix" class="text-sm text-emerald-600 mt-1">💡 {{ smartIssueFor(hrModalSmart, criterion.key).fix }}</p>
                  </div>
                </div>
              </div>

              <div v-if="hrModalSmart?.issues && hrModalSmart.issues.length > 0" class="mt-6">
                <h4 class="font-bold text-slate-700 mb-3 flex items-center gap-2"><AlertCircle :size="18" class="text-amber-500" />Points d'amélioration ({{ hrModalSmart.issues.length }})</h4>
                <div class="space-y-2">
                  <div v-for="(issue, idx) in hrModalSmart.issues" :key="idx" class="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                    <div class="font-medium text-amber-800"><span class="font-bold text-amber-900">[{{ issue.letter }}]</span> {{ issue.problem || issue }}</div>
                    <div v-if="issue.suggestion || issue.fix" class="text-sm text-amber-600 mt-1">💡 {{ issue.suggestion || issue.fix }}</div>
                  </div>
                </div>
              </div>

              <div v-if="hrModalSmart?.rewrite_fr || hrModalSmart?.rewrite_en || hrModalSmart?.suggestion" class="mt-6 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl">
                <h4 class="font-bold text-blue-800 mb-3 flex items-center gap-2"><Sparkles :size="18" />Reformulations suggérées</h4>
                <div class="space-y-3">
                  <div v-if="hrModalSmart?.rewrite_fr" class="p-3 bg-white rounded-lg border border-blue-100">
                    <div class="text-xs font-medium text-blue-500 mb-1">🇫🇷 Version française améliorée</div>
                    <p class="text-slate-800 font-medium">{{ hrModalSmart.rewrite_fr }}</p>
                  </div>
                  <div v-if="hrModalSmart?.rewrite_en" class="p-3 bg-white rounded-lg border border-blue-100">
                    <div class="text-xs font-medium text-blue-500 mb-1">🇬🇧 English improved version</div>
                    <p class="text-slate-800 font-medium">{{ hrModalSmart.rewrite_en }}</p>
                  </div>
                  <div v-if="hrModalSmart?.suggestion && !hrModalSmart?.rewrite_fr" class="p-3 bg-white rounded-lg border border-blue-100">
                    <div class="text-xs font-medium text-blue-500 mb-1">💡 Suggestion</div>
                    <p class="text-slate-800">{{ hrModalSmart.suggestion }}</p>
                  </div>
                </div>
              </div>
            </div>

            <div v-if="(hrModalAlignment && Object.keys(hrModalAlignment).length) || (selectedHrAnalysis.alignment_score && selectedHrAnalysis.alignment_score > 0)" class="mt-6 pt-6 border-t border-slate-200">
              <h3 class="font-bold text-lg text-slate-800 flex items-center gap-2 mb-4"><TrendingUp :size="20" class="text-purple-500" />Alignement stratégique</h3>
              <div class="flex items-center gap-4 mb-4">
                <div class="text-3xl font-bold text-purple-600">{{ hrModalAlignment?.alignment_score || selectedHrAnalysis.alignment_score || 0 }}%</div>
                <div class="text-sm text-slate-500">Score d'alignement avec les objectifs stratégiques</div>
              </div>
              <div v-if="hrModalAlignment?.top_matches && hrModalAlignment.top_matches.length > 0" class="space-y-2">
                <h4 class="text-sm font-medium text-slate-600">Objectifs stratégiques liés :</h4>
                <div v-for="(match, idx) in hrModalAlignment.top_matches" :key="idx" class="p-3 bg-purple-50 rounded-lg flex items-center justify-between">
                  <span class="text-purple-800">{{ match.title || match.objective_id || match }}</span>
                  <span v-if="match.score" class="text-sm font-bold text-purple-600">{{ match.score }}%</span>
                </div>
              </div>
            </div>

            <div v-if="noDetailedAnalysis(hrModalSmart)" class="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-xl text-center">
              <p class="text-sm text-blue-600">ℹ️ Les scores SMART ci-dessus sont basés sur les données enregistrées. Les détails complets seront disponibles pour les prochaines analyses.</p>
            </div>
          </div>

          <div class="p-4 border-t border-slate-200 bg-slate-50 flex justify-end">
            <button @click="selectedHrAnalysis = null" class="px-6 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 rounded-lg font-medium transition-colors">Fermer</button>
          </div>
        </div>
      </div>

      <!-- ===== DASHBOARD ===== -->
      <header class="flex flex-col md:flex-row md:items-start justify-between gap-6">
        <div>
          <h1 class="text-3xl font-extrabold text-emerald-900 flex items-center gap-3">
            <ShieldCheck :size="32" />
            Module d'Analyse RH
          </h1>
          <p class="text-slate-500 mt-1">Import, analyse et visualisation des objectifs.</p>
        </div>
        <div class="flex items-start gap-2">
          <div class="relative">
            <button @click="showExportMenu = !showExportMenu" :disabled="isExporting" class="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg font-bold hover:bg-emerald-700 text-sm shadow-sm disabled:opacity-50">
              <Loader2 v-if="isExporting" :size="16" class="animate-spin" />
              <Download v-else :size="16" />
              Exporter
            </button>
            <div v-if="showExportMenu" class="absolute right-0 top-full mt-2 bg-white rounded-lg shadow-lg border border-slate-200 overflow-hidden z-50 min-w-[160px]">
              <button @click="handleExport('excel')" class="w-full px-4 py-3 text-left text-sm hover:bg-emerald-50 flex items-center gap-2 text-slate-700"><FileSpreadsheet :size="16" class="text-emerald-600" />Export Excel</button>
              <button @click="handleExport('pdf')" class="w-full px-4 py-3 text-left text-sm hover:bg-red-50 flex items-center gap-2 text-slate-700 border-t border-slate-100"><FileSpreadsheet :size="16" class="text-red-600" />Export PDF</button>
            </div>
          </div>
          <button @click="loadData" class="p-3 border border-slate-200 rounded-lg text-slate-600 hover:bg-slate-50" title="Rafraîchir"><RefreshCw :size="18" /></button>
        </div>
      </header>

      <div v-if="error" class="bg-red-50 border border-red-200 p-4 rounded-xl flex items-center gap-3 text-red-700">
        <AlertCircle :size="20" />
        <p class="text-sm font-medium">{{ error }}</p>
        <button @click="error = null" class="ml-auto text-xs font-bold uppercase bg-white/50 px-2 py-1 rounded">X</button>
      </div>

      <!-- Import & analyse -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div class="lg:col-span-2 bg-white p-6 rounded-2xl shadow-sm border border-slate-100 space-y-6">
          <h2 class="font-bold text-xl text-slate-800">1. Import des Données</h2>
          <div class="grid md:grid-cols-2 gap-6">
            <div
              class="p-4 rounded-xl border-2 border-dashed transition-colors"
              :class="dragStrat ? 'bg-emerald-50 border-emerald-500' : 'bg-slate-50 border-slate-200'"
              @drop.prevent="onStratDrop"
              @dragover.prevent="dragStrat = true"
              @dragenter.prevent="dragStrat = true"
              @dragleave.prevent="dragStrat = false"
            >
              <h3 class="font-semibold text-emerald-800 flex items-center gap-2"><Target :size="18" />Objectifs Stratégiques</h3>
              <p class="text-xs text-slate-500 mt-1 mb-3">
                Importer le fichier Excel des axes directeurs.
                <span class="block mt-1 text-emerald-700">Glissez-déposez le fichier ici, ou cliquez ci-dessous.</span>
              </p>
              <input type="file" ref="stratFileInput" @change="onStratFileChange" class="hidden" accept=".xlsx, .xls" />
              <div class="flex items-center gap-2">
                <button @click="stratFileInput?.click()" class="flex-1 text-center text-xs font-bold bg-white border border-slate-300 rounded-md px-3 py-2 truncate hover:bg-slate-100">{{ stratFile ? stratFile.name : 'Choisir un fichier...' }}</button>
                <button @click="handleFileUpload('strategy')" :disabled="!stratFile || isUploading === 'strategy'" class="px-3 py-2 bg-emerald-600 text-white rounded-md font-bold hover:bg-emerald-700 disabled:opacity-50">
                  <Loader2 v-if="isUploading === 'strategy'" class="animate-spin" :size="16" />
                  <Upload v-else :size="16" />
                </button>
              </div>
            </div>
            <div
              class="p-4 rounded-xl border-2 border-dashed transition-colors"
              :class="dragObj ? 'bg-emerald-50 border-emerald-500' : 'bg-slate-50 border-slate-200'"
              @drop.prevent="onObjDrop"
              @dragover.prevent="dragObj = true"
              @dragenter.prevent="dragObj = true"
              @dragleave.prevent="dragObj = false"
            >
              <h3 class="font-semibold text-emerald-800 flex items-center gap-2"><Users :size="18" />Objectifs Collaborateurs</h3>
              <p class="text-xs text-slate-500 mt-1 mb-3">
                Importer le fichier Excel des objectifs individuels.
                <span class="block mt-1 text-emerald-700">Glissez-déposez le fichier ici, ou cliquez ci-dessous.</span>
              </p>
              <input type="file" ref="objFileInput" @change="onObjFileChange" class="hidden" accept=".xlsx, .xls" />
              <div class="flex items-center gap-2">
                <button @click="objFileInput?.click()" class="flex-1 text-center text-xs font-bold bg-white border border-slate-300 rounded-md px-3 py-2 truncate hover:bg-slate-100">{{ objFile ? objFile.name : 'Choisir un fichier...' }}</button>
                <button @click="handleFileUpload('objectives')" :disabled="!objFile || isUploading === 'objectives'" class="px-3 py-2 bg-emerald-600 text-white rounded-md font-bold hover:bg-emerald-700 disabled:opacity-50">
                  <Loader2 v-if="isUploading === 'objectives'" class="animate-spin" :size="16" />
                  <Upload v-else :size="16" />
                </button>
              </div>
            </div>
          </div>
          <div class="border-t border-slate-100 pt-6 space-y-3">
            <h2 class="font-bold text-xl text-slate-800">2. Lancement de l'Analyse</h2>
            <p class="text-sm text-slate-500">Une fois les fichiers importés, lancez l'analyse pour calculer les scores SMART et d'alignement pour tous les nouveaux objectifs.</p>
            <button @click="handleAnalyze" :disabled="isAnalyzing" class="w-full flex items-center justify-center gap-3 px-4 py-3 bg-amber-500 text-white rounded-lg font-bold hover:bg-amber-600 text-base shadow-md disabled:opacity-60">
              <template v-if="isAnalyzing"><Loader2 class="animate-spin" :size="20" />Analyse en cours...</template>
              <template v-else><Sparkles :size="20" />Lancer l'analyse groupée</template>
            </button>
            <div v-if="isAnalyzing && analysisProgress.total > 0" class="bg-amber-50 border border-amber-200 rounded-lg p-4 space-y-2">
              <div class="flex justify-between items-center text-sm font-semibold text-amber-800">
                <span>Objectif {{ analysisProgress.current }} / {{ analysisProgress.total }}</span>
                <span>{{ Math.round((analysisProgress.current / analysisProgress.total) * 100) }}%</span>
              </div>
              <div class="w-full bg-amber-200 rounded-full h-3 overflow-hidden">
                <div class="bg-amber-500 h-3 rounded-full transition-all duration-300" :style="{ width: `${(analysisProgress.current / analysisProgress.total) * 100}%` }"></div>
              </div>
              <p class="text-xs text-amber-700 truncate">En cours : {{ analysisProgress.title }}</p>
            </div>
            <div v-if="lastAnalysis" class="bg-emerald-50 text-emerald-800 p-3 rounded-lg text-sm flex items-center gap-3 border border-emerald-200">
              <FileCheck2 :size="18" />
              Dernière analyse : {{ lastAnalysis.analyzed }} objectifs traités avec {{ lastAnalysis.errors }} erreurs.
            </div>
          </div>
        </div>

        <!-- Historique des imports -->
        <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
          <h2 class="font-bold text-xl text-slate-800 mb-4 flex items-center gap-2"><History :size="20" />Historique des Imports</h2>
          <div class="space-y-3 max-h-96 overflow-y-auto pr-2">
            <template v-if="imports.length > 0">
              <div v-for="imp in imports" :key="imp.id" class="bg-slate-50 p-3 rounded-lg text-xs">
                <div class="flex justify-between items-center">
                  <span :class="['font-bold', imp.import_type === 'strategy' ? 'text-purple-700' : 'text-blue-700']">{{ imp.import_type === 'strategy' ? 'Stratégie' : 'Objectifs' }}</span>
                  <span class="text-slate-400">{{ new Date(imp.created_at).toLocaleString('fr-FR') }}</span>
                </div>
                <div class="text-slate-600 mt-1 truncate">Fichier : {{ imp.filename }}</div>
                <div class="text-slate-500 font-semibold mt-1">{{ imp.records_count }} lignes importées</div>
              </div>
            </template>
            <p v-else class="text-sm text-slate-400 text-center py-8">Aucun import récent.</p>
          </div>
        </div>
      </div>

      <!-- Tableaux de bord analytiques -->
      <div class="bg-white p-6 md:p-8 rounded-2xl shadow-sm border border-slate-100">
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
          <h2 class="font-bold text-xl text-slate-800">3. Tableaux de Bord Analytiques</h2>
          <div class="flex items-center gap-2 p-1 bg-slate-100 rounded-lg">
            <button @click="view = 'dashboard'" :class="['px-4 py-1.5 text-sm font-bold rounded-md', view === 'dashboard' ? 'bg-white shadow-sm text-emerald-700' : 'text-slate-500']">Dashboard</button>
            <button @click="view = 'details'" :class="['px-4 py-1.5 text-sm font-bold rounded-md', view === 'details' ? 'bg-white shadow-sm text-emerald-700' : 'text-slate-500']">Détails</button>
          </div>
        </div>

        <div v-if="loading" class="h-64 flex items-center justify-center"><Loader2 class="animate-spin text-emerald-500" :size="32" /></div>

        <div v-else-if="!hasData" class="text-center py-16 bg-slate-50 rounded-2xl border-2 border-dashed border-slate-200">
          <BarChart3 :size="48" class="mx-auto text-slate-300 mb-4" />
          <h3 class="text-lg font-bold text-slate-600">Aucune donnée à afficher</h3>
          <p class="text-sm text-slate-400 mt-1">Importez des fichiers pour commencer l'analyse.</p>
        </div>

        <!-- Vue dashboard analytique -->
        <div v-else-if="view === 'dashboard'" class="space-y-8">
          <div class="flex flex-wrap items-center gap-3 p-3 bg-slate-50 rounded-xl border">
            <Filter :size="16" class="text-slate-500" />
            <span class="text-sm font-bold text-slate-600 mr-2">Filtres :</span>
            <select v-model="filters.entity" class="text-sm border-slate-200 rounded-md">
              <option value="">Toutes les entités</option>
              <option v-for="e in analytics?.filters.entities" :key="e" :value="e">{{ e }}</option>
            </select>
            <select v-model="filters.manager" class="text-sm border-slate-200 rounded-md">
              <option value="">Tous les managers</option>
              <option v-for="m in analytics?.filters.managers" :key="m" :value="m">{{ m }}</option>
            </select>
            <select v-model="filters.period" class="text-sm border-slate-200 rounded-md">
              <option value="">Toutes les périodes</option>
              <option v-for="p in analytics?.filters.periods" :key="p" :value="p">{{ p }}</option>
            </select>
            <button @click="resetFilters" class="text-xs font-bold text-slate-500 hover:underline ml-auto">Réinitialiser</button>
          </div>

          <!-- KPIs -->
          <div class="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div class="bg-slate-50/50 p-4 rounded-xl border">
              <p class="text-xs font-bold text-slate-500 uppercase">Objectifs Analysés</p>
              <p class="text-3xl font-black text-emerald-800 mt-1">{{ kpiDisplay(analytics?.global_stats.analyzed || 0) }}<template v-if="analytics?.global_stats.total !== undefined"> / {{ analytics.global_stats.total.toLocaleString('fr-FR') }}</template></p>
            </div>
            <div class="bg-slate-50/50 p-4 rounded-xl border">
              <p class="text-xs font-bold text-slate-500 uppercase">Score SMART Moyen</p>
              <p class="text-3xl font-black text-emerald-800 mt-1">{{ kpiDisplay(analytics?.avg_scores.avg_smart, 'percent') }}</p>
            </div>
            <div class="bg-slate-50/50 p-4 rounded-xl border">
              <p class="text-xs font-bold text-slate-500 uppercase">Alignement Moyen</p>
              <p class="text-3xl font-black text-emerald-800 mt-1">{{ kpiDisplay(analytics?.avg_scores.avg_alignment, 'percent') }}</p>
            </div>
            <div class="bg-slate-50/50 p-4 rounded-xl border">
              <p class="text-xs font-bold text-slate-500 uppercase">Objectifs Validés</p>
              <p class="text-3xl font-black text-emerald-800 mt-1">{{ kpiDisplay(analytics?.global_stats.validated || 0) }}</p>
            </div>
          </div>

          <!-- Graphiques -->
          <div class="grid lg:grid-cols-2 gap-8">
            <div class="bg-slate-50/50 p-6 rounded-xl border h-full">
              <h3 class="font-bold text-slate-800 mb-4">Évolution des Scores Mensuels</h3>
              <div class="h-[250px]"><Line :data="lineChartData" :options="lineChartOptions" /></div>
            </div>
            <div class="bg-slate-50/50 p-6 rounded-xl border h-full">
              <h3 class="font-bold text-slate-800 mb-4">Top 5 Points Bloquants (Critères SMART)</h3>
              <div class="h-[250px]"><Bar :data="blockingChartData" :options="blockingChartOptions" /></div>
            </div>
          </div>
          <div class="grid lg:grid-cols-2 gap-8">
            <div class="bg-slate-50/50 p-6 rounded-xl border h-full">
              <h3 class="font-bold text-slate-800 mb-4">Répartition Alignement Stratégique</h3>
              <div class="h-[200px]"><Pie :data="alignmentPieData" :options="pieOptions" /></div>
            </div>
            <div class="bg-slate-50/50 p-6 rounded-xl border h-full">
              <h3 class="font-bold text-slate-800 mb-4">Répartition Score SMART</h3>
              <div class="h-[200px]"><Pie :data="smartPieData" :options="pieOptions" /></div>
            </div>
          </div>

          <!-- Tableaux comparatifs -->
          <div class="grid lg:grid-cols-2 gap-8">
            <div class="bg-slate-50/50 p-6 rounded-xl border">
              <h3 class="font-bold text-slate-800 mb-4">Comparaison par Entité</h3>
              <div class="max-h-60 overflow-y-auto">
                <table class="w-full text-sm text-left">
                  <thead><tr class="text-xs text-slate-500 border-b"><th class="pb-2">Entity</th><th class="pb-2 text-center">SMART</th><th class="pb-2 text-center">Alignement</th><th class="pb-2 text-center">Nb Obj.</th></tr></thead>
                  <tbody class="divide-y divide-slate-200">
                    <tr v-for="(item, i) in analytics?.entity_comparison" :key="i">
                      <td class="py-2 font-semibold truncate max-w-xs">{{ item.entity }}</td>
                      <td class="py-2 text-center font-bold text-emerald-700">{{ item.avg_smart?.toFixed(0) }}%</td>
                      <td class="py-2 text-center font-bold text-amber-700">{{ item.avg_alignment?.toFixed(0) }}%</td>
                      <td class="py-2 text-center text-slate-500">{{ item.count }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
            <div class="bg-slate-50/50 p-6 rounded-xl border">
              <h3 class="font-bold text-slate-800 mb-4">Comparaison par Manager</h3>
              <div class="max-h-60 overflow-y-auto">
                <table class="w-full text-sm text-left">
                  <thead><tr class="text-xs text-slate-500 border-b"><th class="pb-2">Manager</th><th class="pb-2 text-center">SMART</th><th class="pb-2 text-center">Alignement</th><th class="pb-2 text-center">Nb Obj.</th></tr></thead>
                  <tbody class="divide-y divide-slate-200">
                    <tr v-for="(item, i) in analytics?.manager_comparison" :key="i">
                      <td class="py-2 font-semibold truncate max-w-xs">{{ item.manager }}</td>
                      <td class="py-2 text-center font-bold text-emerald-700">{{ item.avg_smart?.toFixed(0) }}%</td>
                      <td class="py-2 text-center font-bold text-amber-700">{{ item.avg_alignment?.toFixed(0) }}%</td>
                      <td class="py-2 text-center text-slate-500">{{ item.count }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>

        <!-- Vue détails (tableau) -->
        <div v-else class="space-y-4">
          <div class="flex flex-wrap items-center gap-3 p-3 bg-slate-50 rounded-xl border">
            <Filter :size="16" class="text-slate-500" />
            <span class="text-sm font-bold text-slate-600 mr-2">Filtres :</span>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-left text-sm">
              <thead>
                <tr class="border-b bg-slate-50 text-xs text-slate-500 uppercase">
                  <th class="p-3">Collaborateur</th>
                  <th class="p-3">Objectif</th>
                  <th class="p-3 text-center">SMART Score</th>
                  <th class="p-3 text-center">Alignement</th>
                  <th class="p-3">Entité</th>
                  <th class="p-3">Manager</th>
                  <th class="p-3">Période</th>
                  <th class="p-3 text-center">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y">
                <tr v-for="obj in objectives" :key="obj.id" class="hover:bg-slate-50 cursor-pointer" @click="selectedHRObjective = obj">
                  <td class="p-3 font-semibold">{{ obj.user_name || 'N/A' }}</td>
                  <td class="p-3 max-w-xs">
                    <p class="font-bold truncate">{{ obj.title }}</p>
                    <p class="text-xs text-slate-500 truncate">{{ obj.description }}</p>
                  </td>
                  <td class="p-3 text-center font-bold">
                    <span :class="obj.smart_score && obj.smart_score >= 80 ? 'text-emerald-600' : obj.smart_score && obj.smart_score >= 50 ? 'text-amber-600' : 'text-red-600'">{{ obj.smart_score?.toFixed(0) || 'N/A' }}%</span>
                  </td>
                  <td class="p-3 text-center font-bold">
                    <span :class="obj.alignment_score && obj.alignment_score >= 80 ? 'text-emerald-600' : obj.alignment_score && obj.alignment_score >= 50 ? 'text-amber-600' : 'text-red-600'">{{ obj.alignment_score?.toFixed(0) || 'N/A' }}%</span>
                  </td>
                  <td class="p-3">{{ obj.entity || 'N/A' }}</td>
                  <td class="p-3">{{ obj.manager_name || 'N/A' }}</td>
                  <td class="p-3">{{ obj.period || 'N/A' }}</td>
                  <td class="p-3 text-center">
                    <button @click.stop="selectedHRObjective = obj" class="p-2 text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors" title="Voir les détails"><Eye :size="18" /></button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- ===== ANALYSE SMART PERSONNELLE DU RH ===== -->
      <div class="space-y-6">
        <div class="bg-gradient-to-r from-purple-600 to-indigo-600 rounded-2xl p-6 text-white">
          <h2 class="text-2xl font-black flex items-center gap-3"><Sparkles :size="28" />Mon Analyse SMART</h2>
          <p class="text-purple-100 mt-2">Saisissez votre objectif personnel et obtenez une analyse SMART détaillée avec des recommandations d'amélioration.</p>
        </div>

        <div class="bg-white rounded-2xl shadow-sm border p-6">
          <h3 class="font-bold text-lg text-slate-800 mb-4 flex items-center gap-2"><Sparkles :size="20" class="text-purple-500" />Analyser mon objectif</h3>
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">Titre de l'objectif *</label>
              <input v-model="hrObjectiveTitle" type="text" placeholder="Ex: Optimiser le processus de recrutement pour réduire le délai d'embauche de 30%" class="w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-purple-500" />
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">Description (optionnel)</label>
              <textarea v-model="hrObjectiveDesc" placeholder="Contexte, moyens, contraintes, indicateurs de suivi..." :rows="3" class="w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-purple-500 resize-none"></textarea>
            </div>
            <button @click="handleAnalyzeHRObjective" :disabled="isAnalyzingPersonal || !hrObjectiveTitle.trim()" :class="['w-full py-3 rounded-xl font-bold text-white flex items-center justify-center gap-2 transition-all', isAnalyzingPersonal || !hrObjectiveTitle.trim() ? 'bg-slate-300 cursor-not-allowed' : 'bg-gradient-to-r from-purple-500 to-indigo-600 hover:from-purple-600 hover:to-indigo-700']">
              <template v-if="isAnalyzingPersonal"><Loader2 :size="20" class="animate-spin" />Analyse en cours...</template>
              <template v-else><Sparkles :size="20" />Analyser mon objectif</template>
            </button>
          </div>
        </div>

        <!-- Résultat de l'analyse -->
        <div v-if="hrAnalysisResult" class="bg-white rounded-2xl shadow-lg border-2 border-emerald-200 p-6">
          <h3 class="font-bold text-lg text-emerald-700 mb-4 flex items-center gap-2"><CheckCircle2 :size="24" />Résultat de l'analyse</h3>
          <div class="flex items-center gap-6 mb-6">
            <div :class="['text-5xl font-black', hrAnalysisResult.smart_score >= 80 ? 'text-emerald-600' : hrAnalysisResult.smart_score >= 60 ? 'text-yellow-600' : 'text-red-600']">{{ Math.round(hrAnalysisResult.smart_score) }}%</div>
            <div class="flex gap-2">
              <span v-for="letter in ['S','M','A','R','T']" :key="letter" :class="['w-10 h-10 flex items-center justify-center rounded-lg font-bold', hrAnalysisResult.smart_analysis?.[letter] ? 'bg-emerald-500 text-white' : 'bg-slate-200 text-slate-500']">{{ letter }}</span>
            </div>
          </div>
          <div v-if="hrAnalysisResult.smart_analysis?.issues && hrAnalysisResult.smart_analysis.issues.length > 0" class="mb-6">
            <h4 class="font-bold text-slate-700 mb-3">Points d'amélioration :</h4>
            <div class="space-y-2">
              <div v-for="(issue, idx) in hrAnalysisResult.smart_analysis.issues" :key="idx" class="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                <div class="font-semibold text-amber-800">[{{ issue.letter }}] {{ issue.problem }}</div>
                <div v-if="issue.fix" class="text-sm text-amber-600 mt-1">💡 {{ issue.fix }}</div>
              </div>
            </div>
          </div>
          <div v-if="hrAnalysisResult.smart_analysis?.rewrite_fr || hrAnalysisResult.smart_analysis?.rewrite_en" class="p-4 bg-blue-50 border border-blue-200 rounded-xl">
            <h4 class="font-bold text-blue-800 mb-2">Reformulation suggérée :</h4>
            <p v-if="hrAnalysisResult.smart_analysis?.rewrite_fr" class="text-blue-700">🇫🇷 {{ hrAnalysisResult.smart_analysis.rewrite_fr }}</p>
            <p v-if="hrAnalysisResult.smart_analysis?.rewrite_en" class="text-blue-600 mt-2">🇬🇧 {{ hrAnalysisResult.smart_analysis.rewrite_en }}</p>
          </div>
        </div>

        <!-- Import Excel personnel -->
        <div class="bg-gradient-to-r from-amber-50 to-orange-50 p-6 rounded-2xl border border-amber-200">
          <h3 class="font-bold text-lg text-amber-800 mb-4 flex items-center gap-2"><FileSpreadsheet :size="20" />Ou importer des objectifs via Excel</h3>
          <p class="text-sm text-amber-700 mb-4">Importez un fichier Excel contenant vos propres objectifs à analyser. Le fichier doit contenir une colonne <strong>"Titre"</strong> (obligatoire) et optionnellement une colonne <strong>"Description"</strong>.</p>
          <div class="flex items-center gap-4">
            <input ref="personalFileInput" type="file" accept=".xlsx,.xls" @change="handleImportPersonalExcel" class="hidden" id="personal-excel-import" />
            <label for="personal-excel-import" :class="['flex items-center gap-2 px-6 py-3 rounded-lg font-bold cursor-pointer transition-all', isImportingPersonal ? 'bg-slate-300 text-slate-600 cursor-not-allowed' : 'bg-gradient-to-r from-amber-500 to-orange-600 text-white hover:from-amber-600 hover:to-orange-700']">
              <template v-if="isImportingPersonal"><Loader2 :size="20" class="animate-spin" />Import en cours...</template>
              <template v-else><Upload :size="20" />Choisir un fichier Excel</template>
            </label>
            <a href="#" @click.prevent="downloadPersonalTemplate" class="text-sm text-amber-600 hover:underline flex items-center gap-1"><Download :size="16" />Télécharger un modèle</a>
          </div>
        </div>

        <!-- Résultats import personnel -->
        <div v-if="personalImportResults" class="bg-white p-6 rounded-2xl shadow-sm border border-emerald-200">
          <h3 class="font-bold text-lg text-slate-800 mb-4 flex items-center gap-2"><CheckCircle2 :size="20" class="text-emerald-500" />Résultats de l'import ({{ personalImportResults.total_processed }} objectif(s) analysé(s))</h3>
          <div v-if="personalImportResults.results && personalImportResults.results.length > 0" class="space-y-4 max-h-[500px] overflow-y-auto">
            <div v-for="(result, idx) in personalImportResults.results" :key="idx" class="p-4 bg-slate-50 rounded-lg border border-slate-200">
              <div class="flex items-start justify-between mb-3">
                <div class="flex-1">
                  <h4 class="font-semibold text-slate-800">{{ result.title }}</h4>
                  <p v-if="result.description" class="text-sm text-slate-500 mt-1">{{ result.description }}</p>
                </div>
                <div :class="['text-2xl font-bold ml-4', result.smart_score >= 80 ? 'text-emerald-600' : result.smart_score >= 60 ? 'text-yellow-600' : 'text-red-600']">{{ Math.round(result.smart_score) }}%</div>
              </div>
              <div class="flex gap-2 mb-3">
                <div v-for="letter in ['S','M','A','R','T']" :key="letter" :class="['w-8 h-8 rounded flex items-center justify-center text-sm font-bold', result.smart_analysis?.[letter] ? 'bg-emerald-500 text-white' : 'bg-slate-200 text-slate-500']">{{ letter }}</div>
              </div>
              <div v-if="result.alignment_analysis" class="text-xs text-slate-600">Alignement stratégique: <span class="font-bold">{{ result.alignment_analysis.alignment_score?.toFixed(0) || 0 }}%</span></div>
              <div v-if="result.smart_analysis?.issues && result.smart_analysis.issues.length > 0" class="mt-2">
                <p class="text-xs text-red-600 font-medium">⚠️ {{ result.smart_analysis.issues.length }} amélioration(s) suggérée(s)</p>
              </div>
            </div>
          </div>
          <div v-if="personalImportResults.errors && personalImportResults.errors.length > 0" class="mt-4 p-4 bg-red-50 rounded-lg border border-red-200">
            <h4 class="font-semibold text-red-700 mb-2">Erreurs ({{ personalImportResults.errors.length }})</h4>
            <p v-for="(err, idx) in personalImportResults.errors" :key="idx" class="text-sm text-red-600">Ligne {{ err.row }}: {{ err.title }} - {{ err.error }}</p>
          </div>
          <button @click="personalImportResults = null" class="mt-4 text-sm text-slate-500 hover:text-slate-700">Fermer les résultats</button>
        </div>

        <!-- Historique des analyses personnelles -->
        <div v-if="!personalImportResults" class="bg-white rounded-2xl shadow-sm border overflow-hidden">
          <div class="p-4 bg-gradient-to-r from-slate-50 to-slate-100 border-b flex items-center justify-between">
            <h3 class="font-bold text-lg text-slate-800 flex items-center gap-2">
              <History :size="20" class="text-slate-400" />
              Historique de mes analyses
              <span v-if="hrAnalysisHistory.length > 0" class="bg-slate-200 text-slate-600 text-xs px-2 py-0.5 rounded-full ml-2">{{ hrAnalysisHistory.length }}</span>
            </h3>
          </div>
          <div v-if="hrAnalysisHistory.length === 0" class="p-8 text-center text-slate-400">
            <Sparkles :size="32" class="mx-auto mb-2 opacity-50" />
            <p>Aucune analyse effectuée pour le moment.</p>
            <p class="text-sm mt-1">Importez un fichier Excel ci-dessus pour commencer.</p>
          </div>
          <div v-else class="divide-y divide-slate-100 max-h-96 overflow-y-auto">
            <div v-for="(item, idx) in hrAnalysisHistory" :key="item.id || idx" class="p-4 hover:bg-slate-50 transition-colors cursor-pointer group" @click="selectedHrAnalysis = item">
              <div class="flex items-center justify-between">
                <div class="flex-1">
                  <div class="font-medium text-slate-800 group-hover:text-emerald-600 transition-colors">{{ item.objective_title || `Analyse #${idx + 1}` }}</div>
                  <div class="text-xs text-slate-400 mt-1 flex items-center gap-2">
                    <span>{{ formatDateTime(item.analyzed_at) }}</span>
                    <span class="text-emerald-500 opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1"><Eye :size="12" /> Voir détails</span>
                  </div>
                </div>
                <div class="flex items-center gap-3">
                  <div class="flex gap-1">
                    <span v-for="letter in ['s','m','a','r','t']" :key="letter" :class="['w-6 h-6 flex items-center justify-center rounded text-xs font-bold', (item.smart_analysis?.[letter.toUpperCase()] || item[`${letter}_score`]) ? 'bg-emerald-500 text-white' : 'bg-slate-200 text-slate-400']">{{ letter.toUpperCase() }}</span>
                  </div>
                  <div :class="['text-lg font-bold', item.smart_score >= 80 ? 'text-emerald-600' : item.smart_score >= 60 ? 'text-yellow-600' : 'text-red-600']">{{ Math.round(item.smart_score || 0) }}%</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </DashboardLayout>
</template>
