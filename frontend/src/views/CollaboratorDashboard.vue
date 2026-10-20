<script setup>
// CollaboratorDashboard.vue — Espace du collaborateur (migration de CollaboratorDashboard.tsx).
// Saisie manuelle, import CSV, import Excel, historique et vue détaillée d'un objectif.
// Toute la logique d'analyse est déléguée au backend via ApiService.
import { ref, onMounted } from 'vue';
import { useAuthStore } from '@/stores/authStore';
import { ApiService } from '@/services/apiService';
import SmartBadge from '@/components/SmartBadge.vue';
import AlignmentChart from '@/components/AlignmentChart.vue';
import KnowledgeBaseManager from '@/components/KnowledgeBaseManager.vue';
import DashboardLayout from '@/layouts/DashboardLayout.vue';
import {
  Plus, Copy, CheckCircle2, AlertCircle, Sparkles, ChevronRight, Target,
  Loader2, Upload, FileText, RefreshCw, Trash2, FileSpreadsheet, Download, BookOpen,
} from 'lucide-vue-next';

const auth = useAuthStore();
const user = auth.user;

const activeTab = ref('manual'); // 'manual' | 'import' | 'excel'
const title = ref('');
const desc = ref('');
const isAnalyzing = ref(false);
const isUploading = ref(false);
const error = ref(null);

const objectives = ref([]);
const companyObjectives = ref([]);
const loadingState = ref('loading'); // 'loading' | 'success' | 'error'

const analysisHistory = ref([]);
const analysisStats = ref(null);

const selectedObjective = ref(null);

const isReanalyzing = ref(false);
const isImportingExcel = ref(false);
const excelImportResults = ref(null);
const excelFileInput = ref(null);
const fileInput = ref(null);

const SMART_LABELS = [
  { key: 'S', label: 'Spécifique' },
  { key: 'M', label: 'Mesurable' },
  { key: 'A', label: 'Atteignable' },
  { key: 'R', label: 'Pertinent' },
  { key: 'T', label: 'Temporel' },
];

onMounted(loadData);

async function loadData() {
  try {
    loadingState.value = 'loading';
    const [fetchedObjectives, fetchedCompany, analysisData] = await Promise.all([
      ApiService.getObjectives(),
      ApiService.getCompanyObjectives(),
      ApiService.getCollabAnalysisResults(),
    ]);
    objectives.value = fetchedObjectives;
    companyObjectives.value = fetchedCompany;
    if (analysisData) {
      analysisHistory.value = analysisData.results || [];
      analysisStats.value = analysisData.stats || null;
    }
    loadingState.value = 'success';
  } catch (err) {
    console.error('[CollaboratorDashboard] Erreur chargement:', err);
    loadingState.value = 'error';
    error.value = 'Erreur lors du chargement des données.';
  }
}

async function handleAnalyze() {
  if (!title.value) return;
  isAnalyzing.value = true;
  error.value = null;
  try {
    const newObj = await ApiService.createObjective(title.value, desc.value);
    if (!newObj) throw new Error('Erreur lors de la création.');
    const smartResult = await ApiService.analyzeSmartObjective(title.value, desc.value);
    const alignmentResult =
      companyObjectives.value.length > 0
        ? await ApiService.analyzeAlignment(title.value, companyObjectives.value)
        : { alignment_score: 0, top_matches: [], gaps: ['Aucun catalogue stratégique défini'] };
    await ApiService.updateObjective(newObj.id, {
      status: 'active',
      smart_analysis: smartResult || undefined,
      alignment_analysis: alignmentResult || undefined,
    });
    await loadData();
    title.value = '';
    desc.value = '';
  } catch (err) {
    console.error(err);
    error.value = err.message || "Erreur lors de l'analyse.";
  } finally {
    isAnalyzing.value = false;
  }
}

async function handleReanalyze() {
  if (!selectedObjective.value) return;
  isReanalyzing.value = true;
  error.value = null;
  try {
    const obj = selectedObjective.value;
    const smartResult = await ApiService.analyzeSmartObjective(obj.title, obj.description || '');
    const alignmentResult =
      companyObjectives.value.length > 0
        ? await ApiService.analyzeAlignment(obj.title, companyObjectives.value)
        : { alignment_score: 0, top_matches: [], gaps: ['Aucun catalogue stratégique défini'] };
    await ApiService.updateObjective(obj.id, {
      status: 'active',
      smart_analysis: smartResult || undefined,
      alignment_analysis: alignmentResult || undefined,
    });
    await loadData();
    selectedObjective.value = objectives.value.find((o) => o.id === obj.id) || null;
  } catch (err) {
    console.error(err);
    error.value = err.message || "Erreur lors de l'analyse.";
  } finally {
    isReanalyzing.value = false;
  }
}

async function handleDelete(id) {
  if (!confirm('Supprimer cet objectif ?')) return;
  const success = await ApiService.deleteObjective(id);
  if (success) {
    objectives.value = objectives.value.filter((o) => o.id !== id);
    if (selectedObjective.value?.id === id) selectedObjective.value = null;
  }
}

async function handleProgressChange(id, progress) {
  const success = await ApiService.updateObjective(id, { progress });
  if (success) {
    objectives.value = objectives.value.map((o) => (o.id === id ? { ...o, progress } : o));
    if (selectedObjective.value?.id === id) selectedObjective.value.progress = progress;
  }
}

async function handleFileUpload(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  isUploading.value = true;
  error.value = null;
  try {
    const text = await file.text();
    const lines = text.split('\n').filter((l) => l.trim());
    const headers = lines[0].split(',').map((h) => h.trim().toLowerCase());
    const titleIdx = headers.indexOf('title') !== -1 ? headers.indexOf('title') : 0;
    const descIdx = headers.indexOf('description') !== -1 ? headers.indexOf('description') : 1;
    for (let i = 1; i < lines.length; i++) {
      const cols = lines[i].split(',');
      const objTitle = cols[titleIdx]?.trim();
      const objDesc = cols[descIdx]?.trim() || '';
      if (!objTitle) continue;
      const newObj = await ApiService.createObjective(objTitle, objDesc);
      if (newObj) {
        const smartResult = await ApiService.analyzeSmartObjective(objTitle, objDesc);
        const alignmentResult =
          companyObjectives.value.length > 0
            ? await ApiService.analyzeAlignment(objTitle, companyObjectives.value)
            : null;
        await ApiService.updateObjective(newObj.id, {
          status: 'active',
          smart_analysis: smartResult || undefined,
          alignment_analysis: alignmentResult || undefined,
        });
      }
    }
    await loadData();
    alert('Import terminé.');
  } catch (err) {
    console.error(err);
    error.value = "Erreur lors de l'import.";
  } finally {
    isUploading.value = false;
    if (fileInput.value) fileInput.value.value = '';
  }
}

// Drag & drop : permet de glisser un fichier depuis l'Explorateur
// (contourne la popup "mobile" d'Edge).
const dragExcel = ref(false);
function onExcelDrop(e) {
  dragExcel.value = false;
  const file = e.dataTransfer?.files?.[0];
  if (!file) return;
  handleExcelImport({ target: { files: [file] } });
}

async function handleExcelImport(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
    alert('Format non supporté. Veuillez utiliser un fichier Excel (.xlsx ou .xls)');
    return;
  }
  isImportingExcel.value = true;
  excelImportResults.value = null;
  error.value = null;
  try {
    const result = await ApiService.importExcelForAnalysis(file);
    if (result) {
      excelImportResults.value = result;
      await loadData();
    }
  } catch (err) {
    console.error('Erreur import Excel:', err);
    error.value = err.message || "Erreur lors de l'import du fichier Excel.";
  } finally {
    isImportingExcel.value = false;
    if (excelFileInput.value) excelFileInput.value.value = '';
  }
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text);
}

function downloadModel() {
  const csvContent =
    'Titre,Description\nAugmenter mes ventes de 10%,Objectif personnel pour Q2\nAméliorer ma productivité,Réduire les temps de traitement';
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'modele_objectifs.csv';
  link.click();
}

function smartScoreClass(score) {
  if (score >= 80) return 'text-emerald-600';
  if (score >= 60) return 'text-yellow-600';
  return 'text-red-600';
}
</script>

<template>
  <DashboardLayout>
    <!-- Chargement -->
    <div
      v-if="loadingState === 'loading'"
      class="p-8 max-w-6xl mx-auto flex items-center justify-center min-h-[60vh]"
    >
      <div class="flex flex-col items-center gap-4">
        <Loader2 class="animate-spin text-emerald-600" :size="48" />
        <p class="text-slate-500 font-medium">Chargement de vos objectifs...</p>
      </div>
    </div>

    <!-- Vue détaillée -->
    <div v-else-if="selectedObjective" class="p-8 max-w-6xl mx-auto space-y-8">
      <button
        class="flex items-center gap-2 text-emerald-600 font-bold hover:underline"
        @click="selectedObjective = null"
      >
        <ChevronRight class="rotate-180" :size="20" /> Retour à mes objectifs
      </button>

      <div class="bg-white p-8 rounded-2xl shadow-sm border border-slate-100">
        <div class="flex items-center justify-between mb-6">
          <div>
            <h1 class="text-2xl font-extrabold text-slate-900">{{ selectedObjective.title }}</h1>
            <p class="text-slate-500 mt-1">
              {{ selectedObjective.description || 'Sans description' }}
            </p>
          </div>
          <select
            :value="selectedObjective.progress"
            class="px-4 py-2 border border-slate-200 rounded-lg text-sm"
            @change="handleProgressChange(selectedObjective.id, $event.target.value)"
          >
            <option value="not_started">Non démarré</option>
            <option value="in_progress">En cours</option>
            <option value="completed">Atteint</option>
            <option value="on_hold">En pause</option>
          </select>
        </div>

        <div class="mt-8 space-y-6">
          <!-- Analyse SMART -->
          <div class="bg-slate-50 p-6 rounded-xl">
            <div class="flex items-center justify-between mb-4">
              <h3 class="font-bold text-lg text-emerald-900 flex items-center gap-2">
                Analyse S.M.A.R.T.
                <CheckCircle2
                  v-if="selectedObjective.smartAnalysis?.overall"
                  class="text-emerald-500"
                  :size="20"
                />
                <AlertCircle v-else class="text-amber-500" :size="20" />
              </h3>
              <div class="flex items-center gap-3">
                <div class="text-sm font-medium text-slate-500">
                  Confiance:
                  {{
                    selectedObjective.smartAnalysis?.confidence !== undefined
                      ? (selectedObjective.smartAnalysis.confidence * 100).toFixed(0) + '%'
                      : 'Indisponible'
                  }}
                </div>
                <button
                  :disabled="isReanalyzing"
                  class="flex items-center gap-1 px-3 py-1.5 bg-emerald-600 text-white text-xs font-bold rounded-lg hover:bg-emerald-700 disabled:opacity-50 transition-colors"
                  @click="handleReanalyze"
                >
                  <Loader2 v-if="isReanalyzing" class="animate-spin" :size="14" />
                  <Sparkles v-else :size="14" />
                  {{ isReanalyzing ? 'Analyse…' : 'Analyser' }}
                </button>
              </div>
            </div>
            <div class="flex justify-between items-center">
              <SmartBadge
                v-for="c in SMART_LABELS"
                :key="c.key"
                :letter="c.key"
                :active="selectedObjective.smartAnalysis?.[c.key] || false"
                :label="c.label"
              />
            </div>
          </div>

          <!-- Points d'amélioration -->
          <div
            v-if="(selectedObjective.smartAnalysis?.issues?.length || 0) > 0"
            class="bg-amber-50 p-6 rounded-xl border border-amber-100"
          >
            <h4 class="font-bold text-amber-900 mb-3 flex items-center gap-2">
              <AlertCircle :size="18" />Points d'amélioration
            </h4>
            <div class="space-y-3">
              <div
                v-for="(issue, idx) in selectedObjective.smartAnalysis.issues"
                :key="idx"
                class="bg-white p-3 rounded-lg shadow-sm border border-amber-100"
              >
                <div class="flex items-center gap-2 mb-1">
                  <span
                    class="w-5 h-5 rounded-full bg-amber-500 text-white text-[10px] flex items-center justify-center font-bold"
                  >
                    {{ issue.letter }}
                  </span>
                  <span class="text-xs font-bold text-slate-700">{{ issue.problem }}</span>
                </div>
                <p class="text-xs text-slate-500 pl-7">💡 {{ issue.fix }}</p>
              </div>
            </div>
          </div>

          <!-- Alignement -->
          <div class="bg-white p-6 rounded-xl border border-slate-100 flex items-center gap-6">
            <AlignmentChart :score="selectedObjective.alignmentAnalysis?.alignment_score ?? 0" />
            <div class="flex-1">
              <h4 class="font-bold text-slate-800 mb-1">Alignement Stratégique</h4>
              <div class="flex gap-2 flex-wrap mt-2">
                <div
                  v-for="m in selectedObjective.alignmentAnalysis?.top_matches || []"
                  :key="m.objective_id"
                  class="text-xs bg-emerald-50 text-emerald-700 px-3 py-2 rounded-lg border border-emerald-100"
                >
                  <div class="font-bold">{{ m.title || m.objective_id }}: {{ m.score }}%</div>
                  <div class="text-emerald-600 mt-1">{{ m.reason }}</div>
                </div>
                <span
                  v-if="!selectedObjective.alignmentAnalysis?.top_matches?.length"
                  class="text-xs text-slate-400"
                >
                  Aucune correspondance
                </span>
              </div>
            </div>
          </div>

          <!-- Réécritures -->
          <div class="bg-white p-6 rounded-xl border border-slate-100 space-y-4">
            <h4 class="font-bold text-emerald-900">Réécritures Suggérées</h4>
            <div class="grid md:grid-cols-2 gap-4">
              <div>
                <div class="flex justify-between items-center mb-2">
                  <span class="text-xs font-bold text-slate-400 uppercase">Français</span>
                  <button
                    class="text-slate-400 hover:text-emerald-600"
                    @click="copyToClipboard(selectedObjective.smartAnalysis?.rewrite_fr || '')"
                  >
                    <Copy :size="14" />
                  </button>
                </div>
                <div
                  class="bg-slate-50 p-4 rounded-xl text-sm italic text-slate-700 border border-slate-100"
                >
                  "{{ selectedObjective.smartAnalysis?.rewrite_fr || 'Indisponible' }}"
                </div>
              </div>
              <div>
                <div class="flex justify-between items-center mb-2">
                  <span class="text-xs font-bold text-slate-400 uppercase">Anglais</span>
                  <button
                    class="text-slate-400 hover:text-emerald-600"
                    @click="copyToClipboard(selectedObjective.smartAnalysis?.rewrite_en || '')"
                  >
                    <Copy :size="14" />
                  </button>
                </div>
                <div
                  class="bg-slate-50 p-4 rounded-xl text-sm italic text-slate-700 border border-slate-100"
                >
                  "{{ selectedObjective.smartAnalysis?.rewrite_en || 'Unavailable' }}"
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Vue principale -->
    <div v-else class="p-8 max-w-6xl mx-auto space-y-8">
      <header class="flex justify-between items-center">
        <div>
          <h1 class="text-3xl font-extrabold text-emerald-900 flex items-center gap-3">
            <Target :size="32" />
            Mes Objectifs
          </h1>
          <p class="text-slate-500">Bienvenue, {{ user?.name }}</p>
        </div>
        <button
          class="p-2 border border-slate-200 rounded-lg text-slate-600 hover:bg-slate-50"
          title="Rafraîchir"
          @click="loadData"
        >
          <RefreshCw :size="18" />
        </button>
      </header>

      <div
        v-if="error"
        class="bg-red-50 border border-red-200 p-4 rounded-xl flex items-center gap-3 text-red-700"
      >
        <AlertCircle :size="20" />
        <p class="text-sm font-medium">{{ error }}</p>
        <button class="ml-auto text-xs font-bold" @click="error = null">Masquer</button>
      </div>

      <!-- Onglets -->
      <div class="flex gap-1 bg-slate-100 p-1 rounded-xl w-fit">
        <button
          :class="[
            'px-6 py-2 rounded-lg text-sm font-bold transition-all',
            activeTab === 'manual' ? 'bg-white shadow-sm text-emerald-700' : 'text-slate-500',
          ]"
          @click="activeTab = 'manual'"
        >
          <Plus :size="16" class="inline mr-2" />Saisie Manuelle
        </button>
        <button
          :class="[
            'px-6 py-2 rounded-lg text-sm font-bold transition-all',
            activeTab === 'import' ? 'bg-white shadow-sm text-emerald-700' : 'text-slate-500',
          ]"
          @click="activeTab = 'import'"
        >
          <Upload :size="16" class="inline mr-2" />Import CSV
        </button>
        <button
          :class="[
            'px-6 py-2 rounded-lg text-sm font-bold transition-all',
            activeTab === 'excel' ? 'bg-white shadow-sm text-amber-700' : 'text-slate-500',
          ]"
          @click="activeTab = 'excel'"
        >
          <FileSpreadsheet :size="16" class="inline mr-2" />Import Excel
        </button>
      </div>

      <!-- Saisie manuelle -->
      <div v-if="activeTab === 'manual'" class="bg-white p-8 rounded-2xl shadow-sm border border-slate-100">
        <h2 class="font-bold text-lg text-slate-800 mb-6 flex items-center gap-2">
          <Sparkles class="text-emerald-500" :size="20" />
          Nouvel Objectif
        </h2>
        <div class="space-y-4">
          <div>
            <label class="block text-xs font-bold text-slate-500 uppercase mb-2">Titre de l'objectif</label>
            <input
              v-model="title"
              class="w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500"
              placeholder="Ex: Augmenter le taux de satisfaction client de 15% d'ici Q4 2026"
            />
          </div>
          <div>
            <label class="block text-xs font-bold text-slate-500 uppercase mb-2">Description (optionnel)</label>
            <textarea
              v-model="desc"
              class="w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 min-h-[100px]"
              placeholder="Contexte, KPIs, actions prévues..."
            />
          </div>
          <button
            :disabled="isAnalyzing || !title"
            class="w-full bg-emerald-600 text-white py-3 rounded-xl font-bold hover:bg-emerald-700 disabled:opacity-50 flex items-center justify-center gap-2"
            @click="handleAnalyze"
          >
            <template v-if="isAnalyzing"><Loader2 class="animate-spin" :size="18" />Analyse en cours...</template>
            <template v-else><Sparkles :size="18" />Analyser</template>
          </button>
        </div>
      </div>

      <!-- Import CSV -->
      <div v-if="activeTab === 'import'" class="bg-white p-8 rounded-2xl shadow-sm border border-slate-100">
        <h2 class="font-bold text-lg text-slate-800 mb-4 flex items-center gap-2">
          <FileText class="text-emerald-500" :size="20" />
          Importer depuis un fichier CSV
        </h2>
        <p class="text-sm text-slate-500 mb-6">
          Format attendu : title, description (une ligne par objectif)
        </p>
        <input ref="fileInput" type="file" class="hidden" accept=".csv" @change="handleFileUpload" />
        <button
          :disabled="isUploading"
          class="px-6 py-3 border-2 border-dashed border-emerald-300 rounded-xl text-emerald-700 font-bold hover:bg-emerald-50 w-full flex items-center justify-center gap-2"
          @click="fileInput?.click()"
        >
          <template v-if="isUploading"><Loader2 class="animate-spin" :size="18" />Import en cours...</template>
          <template v-else><Upload :size="18" />Sélectionner un fichier</template>
        </button>
      </div>

      <!-- Import Excel -->
      <div v-if="activeTab === 'excel'" class="space-y-6">
        <div class="bg-gradient-to-r from-amber-50 to-orange-50 p-6 rounded-2xl border border-amber-200">
          <h2 class="font-bold text-lg text-amber-800 mb-4 flex items-center gap-2">
            <FileSpreadsheet :size="20" />
            Importer des objectifs depuis Excel
          </h2>
          <p class="text-sm text-amber-700 mb-4">
            Importez un fichier Excel contenant vos objectifs à analyser en lot. Le fichier doit
            contenir une colonne <strong>"Titre"</strong> (obligatoire) et optionnellement une
            colonne <strong>"Description"</strong>.
          </p>

          <div
            class="flex flex-col gap-3 p-4 rounded-xl border-2 border-dashed transition-colors"
            :class="dragExcel ? 'bg-amber-50 border-amber-500' : 'bg-transparent border-amber-200'"
            @drop.prevent="onExcelDrop"
            @dragover.prevent="dragExcel = true"
            @dragenter.prevent="dragExcel = true"
            @dragleave.prevent="dragExcel = false"
          >
            <p class="text-xs text-amber-700 text-center">Glissez-déposez un fichier Excel ici, ou cliquez ci-dessous.</p>
            <div class="flex items-center gap-4 flex-wrap">
            <input
              ref="excelFileInput"
              type="file"
              accept=".xlsx,.xls"
              class="hidden"
              id="collab-excel-import"
              @change="handleExcelImport"
            />
            <label
              for="collab-excel-import"
              :class="[
                'flex items-center gap-2 px-6 py-3 rounded-lg font-bold cursor-pointer transition-all',
                isImportingExcel
                  ? 'bg-slate-300 text-slate-600 cursor-not-allowed'
                  : 'bg-gradient-to-r from-amber-500 to-orange-600 text-white hover:from-amber-600 hover:to-orange-700',
              ]"
            >
              <template v-if="isImportingExcel"><Loader2 :size="20" class="animate-spin" />Import en cours...</template>
              <template v-else><Upload :size="20" />Choisir un fichier Excel</template>
            </label>

            <a
              href="#"
              class="text-sm text-amber-600 hover:underline flex items-center gap-1"
              @click.prevent="downloadModel"
            >
              <Download :size="16" />
              Télécharger un modèle
            </a>
            </div>
          </div>
        </div>

        <!-- Résultats import Excel -->
        <div
          v-if="excelImportResults"
          class="bg-white p-6 rounded-2xl shadow-sm border border-emerald-200"
        >
          <h3 class="font-bold text-lg text-slate-800 mb-4 flex items-center gap-2">
            <CheckCircle2 :size="20" class="text-emerald-500" />
            Résultats de l'import ({{ excelImportResults.total_processed }} objectif(s) analysé(s))
          </h3>

          <div
            v-if="excelImportResults.results && excelImportResults.results.length > 0"
            class="space-y-4 max-h-[400px] overflow-y-auto"
          >
            <div
              v-for="(result, idx) in excelImportResults.results"
              :key="idx"
              class="p-4 bg-slate-50 rounded-lg border border-slate-200"
            >
              <div class="flex items-start justify-between mb-3">
                <div class="flex-1">
                  <h4 class="font-semibold text-slate-800">{{ result.title }}</h4>
                  <p v-if="result.description" class="text-sm text-slate-500 mt-1">
                    {{ result.description }}
                  </p>
                </div>
                <div :class="['text-2xl font-bold ml-4', smartScoreClass(result.smart_score)]">
                  {{ Math.round(result.smart_score) }}%
                </div>
              </div>

              <div class="flex gap-2">
                <div
                  v-for="letter in ['S', 'M', 'A', 'R', 'T']"
                  :key="letter"
                  :class="[
                    'w-8 h-8 rounded flex items-center justify-center text-sm font-bold',
                    result.smart_analysis?.[letter]
                      ? 'bg-emerald-500 text-white'
                      : 'bg-slate-200 text-slate-500',
                  ]"
                >
                  {{ letter }}
                </div>
              </div>

              <p
                v-if="result.smart_analysis?.issues && result.smart_analysis.issues.length > 0"
                class="text-xs text-red-600 font-medium mt-2"
              >
                ⚠️ {{ result.smart_analysis.issues.length }} amélioration(s) suggérée(s)
              </p>
            </div>
          </div>

          <div
            v-if="excelImportResults.errors && excelImportResults.errors.length > 0"
            class="mt-4 p-4 bg-red-50 rounded-lg border border-red-200"
          >
            <h4 class="font-semibold text-red-700 mb-2">Erreurs ({{ excelImportResults.errors.length }})</h4>
            <p v-for="(err, idx) in excelImportResults.errors" :key="idx" class="text-sm text-red-600">
              Ligne {{ err.row }}: {{ err.title }} - {{ err.error }}
            </p>
          </div>

          <button class="mt-4 text-sm text-slate-500 hover:text-slate-700" @click="excelImportResults = null">
            Fermer les résultats
          </button>
        </div>
      </div>

      <!-- Historique -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
        <h3 class="font-bold text-lg text-slate-800 mb-4">
          Historique ({{ analysisHistory.length + objectives.length }})
        </h3>

        <div v-if="analysisHistory.length === 0 && objectives.length === 0" class="text-center py-12 text-slate-400">
          <Target :size="48" class="mx-auto mb-4 text-slate-300" />
          <p>Aucun objectif pour le moment.</p>
          <p class="text-sm">Créez votre premier objectif ci-dessus.</p>
        </div>

        <div v-else class="space-y-3">
          <!-- Analyses issues de la base (imports Excel) -->
          <div
            v-for="(item, idx) in analysisHistory"
            :key="item.id || `analysis-${idx}`"
            class="p-4 bg-emerald-50 rounded-xl hover:bg-emerald-100 transition-all flex items-center justify-between"
          >
            <div class="flex-1">
              <div class="font-bold text-slate-800">
                {{ item.objective_title || `Analyse #${idx + 1}` }}
              </div>
              <div class="text-xs text-slate-500 mt-1">
                {{
                  item.analyzed_at
                    ? new Date(item.analyzed_at).toLocaleDateString('fr-FR', {
                        day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
                      })
                    : 'Date inconnue'
                }}
              </div>
            </div>
            <div class="flex items-center gap-4">
              <div class="flex gap-1">
                <span
                  v-for="letter in ['s', 'm', 'a', 'r', 't']"
                  :key="letter"
                  :class="[
                    'w-6 h-6 flex items-center justify-center rounded text-xs font-bold',
                    item[`${letter}_score`] ? 'bg-emerald-500 text-white' : 'bg-red-100 text-red-500',
                  ]"
                >
                  {{ letter.toUpperCase() }}
                </span>
              </div>
              <div v-if="item.smart_score !== undefined" :class="['text-lg font-bold', smartScoreClass(item.smart_score)]">
                {{ Math.round(item.smart_score) }}%
              </div>
            </div>
          </div>

          <!-- Objectifs créés manuellement -->
          <div
            v-for="obj in objectives"
            :key="obj.id"
            class="p-4 bg-slate-50 rounded-xl hover:bg-slate-100 transition-all flex items-center justify-between"
          >
            <div class="flex-1">
              <div class="font-bold text-slate-800">{{ obj.title }}</div>
              <div class="text-xs text-slate-500 mt-1">
                {{ new Date(obj.createdAt).toLocaleDateString('fr-FR') }}
              </div>
            </div>
            <div class="flex items-center gap-4">
              <div v-if="obj.smartAnalysis" class="flex gap-1">
                <span
                  v-for="l in ['S', 'M', 'A', 'R', 'T']"
                  :key="l"
                  :class="[
                    'w-6 h-6 rounded-full text-[10px] flex items-center justify-center font-bold',
                    obj.smartAnalysis?.[l] ? 'bg-emerald-500 text-white' : 'bg-red-100 text-red-500',
                  ]"
                >
                  {{ l }}
                </span>
              </div>
              <span
                :class="[
                  'px-3 py-1 rounded-full text-[10px] font-black uppercase',
                  obj.progress === 'completed'
                    ? 'bg-emerald-100 text-emerald-700'
                    : obj.progress === 'in_progress'
                    ? 'bg-blue-100 text-blue-700'
                    : 'bg-slate-100 text-slate-400',
                ]"
              >
                {{ obj.progress.replace('_', ' ') }}
              </span>
              <button class="text-emerald-600 hover:text-emerald-800" @click="selectedObjective = obj">
                <ChevronRight :size="20" />
              </button>
              <button class="text-red-400 hover:text-red-600" @click="handleDelete(obj.id)">
                <Trash2 :size="18" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Base de connaissances de l'assistant (RAG, partagée avec le Coach IA) -->
      <div class="bg-white p-6 md:p-8 rounded-2xl shadow-sm border border-slate-100">
        <div class="flex items-center gap-2 mb-6">
          <BookOpen :size="22" class="text-indigo-600" />
          <h2 class="font-bold text-xl text-slate-800">Base de connaissances de l'assistant</h2>
        </div>
        <KnowledgeBaseManager />
      </div>
    </div>
  </DashboardLayout>
</template>
