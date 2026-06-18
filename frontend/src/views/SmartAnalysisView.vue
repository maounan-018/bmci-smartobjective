<script setup>
// SmartAnalysisView.vue — Analyse SMART personnelle du RH (migration de SmartAnalysisPage.tsx).
// Saisie d'un objectif, analyse via le backend, historique et modal de détails.
import { ref, onMounted } from 'vue';
import { ApiService } from '@/services/apiService';
import DashboardLayout from '@/layouts/DashboardLayout.vue';
import {
  Sparkles, Loader2, AlertCircle, CheckCircle2, Target, RefreshCw,
  PieChart as PieChartIcon, X, Eye,
} from 'lucide-vue-next';

const myObjectiveTitle = ref('');
const myObjectiveDesc = ref('');
const isAnalyzing = ref(false);
const myAnalysisResult = ref(null);
const analysisHistory = ref([]);
const loadingHistory = ref(true);
const selectedHistoryItem = ref(null);

onMounted(loadHistory);

async function loadHistory() {
  try {
    loadingHistory.value = true;
    const data = await ApiService.getHRAnalysisResults();
    if (data) analysisHistory.value = data.results || [];
  } catch (err) {
    console.error('Erreur chargement historique:', err);
  } finally {
    loadingHistory.value = false;
  }
}

async function handleAnalyzeMyObjective() {
  if (!myObjectiveTitle.value.trim()) {
    alert('Veuillez saisir un titre pour votre objectif.');
    return;
  }
  isAnalyzing.value = true;
  myAnalysisResult.value = null;
  try {
    const result = await ApiService.analyzeHRPersonalObjective(
      myObjectiveTitle.value,
      myObjectiveDesc.value,
    );
    if (result) {
      myAnalysisResult.value = result;
      await loadHistory();
    }
  } catch (err) {
    console.error('Erreur analyse:', err);
    alert("Erreur lors de l'analyse. Vérifiez que le serveur Ollama est actif.");
  } finally {
    isAnalyzing.value = false;
  }
}

function scoreClass(score) {
  if (score >= 80) return 'text-emerald-600';
  if (score >= 60) return 'text-yellow-600';
  return 'text-red-600';
}
</script>

<template>
  <DashboardLayout>
    <div class="p-6 max-w-5xl mx-auto space-y-6">
      <!-- En-tête -->
      <div class="bg-gradient-to-r from-purple-600 to-indigo-600 rounded-2xl p-6 text-white">
        <div class="flex items-center gap-3 mb-2">
          <Sparkles :size="28" />
          <h1 class="text-2xl font-bold">Mon Analyse SMART</h1>
        </div>
        <p class="text-purple-100">
          Saisissez votre objectif personnel et obtenez une analyse SMART détaillée avec des
          recommandations d'amélioration.
        </p>
      </div>

      <!-- Formulaire -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
        <h3 class="font-bold text-lg text-slate-800 mb-4 flex items-center gap-2">
          <Sparkles :size="20" class="text-amber-500" />
          Analyser mon objectif
        </h3>
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1">Titre de l'objectif *</label>
            <input
              v-model="myObjectiveTitle"
              type="text"
              placeholder="Ex: Optimiser le processus de recrutement pour réduire le délai d'embauche de 30%"
              class="w-full px-4 py-3 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1">Description (optionnel)</label>
            <textarea
              v-model="myObjectiveDesc"
              placeholder="Contexte, moyens, contraintes, indicateurs de suivi..."
              :rows="3"
              class="w-full px-4 py-3 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
            />
          </div>
          <button
            :disabled="isAnalyzing || !myObjectiveTitle.trim()"
            class="w-full bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-6 py-3 rounded-lg font-bold flex items-center justify-center gap-2 hover:from-purple-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            @click="handleAnalyzeMyObjective"
          >
            <template v-if="isAnalyzing"><Loader2 :size="20" class="animate-spin" />Analyse en cours...</template>
            <template v-else><Sparkles :size="20" />Analyser mon objectif</template>
          </button>
        </div>
      </div>

      <!-- Résultat en cours -->
      <div v-if="myAnalysisResult" class="bg-white p-6 rounded-2xl shadow-sm border border-purple-200">
        <h3 class="font-bold text-lg text-slate-800 mb-4 flex items-center gap-2">
          <CheckCircle2 :size="20" class="text-purple-500" />
          Résultat de l'analyse
        </h3>

        <div class="flex items-center gap-4 mb-6">
          <div :class="['text-4xl font-bold', scoreClass(myAnalysisResult.smart_score)]">
            {{ Math.round(myAnalysisResult.smart_score) }}%
          </div>
          <div>
            <div class="text-sm font-semibold text-slate-700">Score SMART</div>
            <div class="text-xs text-slate-500">
              {{ myAnalysisResult.smart_analysis?.overall ? 'Objectif SMART validé ✓' : 'Améliorations nécessaires' }}
            </div>
          </div>
        </div>

        <div class="flex gap-2 mb-6">
          <div
            v-for="letter in ['S', 'M', 'A', 'R', 'T']"
            :key="letter"
            :class="[
              'w-12 h-12 rounded-lg flex flex-col items-center justify-center',
              myAnalysisResult.smart_analysis?.[letter] ? 'bg-purple-500 text-white' : 'bg-slate-200 text-slate-500',
            ]"
          >
            <span class="text-lg font-bold">{{ letter }}</span>
          </div>
        </div>

        <div
          v-if="myAnalysisResult.smart_analysis?.issues && myAnalysisResult.smart_analysis.issues.length > 0"
          class="mb-6"
        >
          <h4 class="font-semibold text-slate-700 mb-2 flex items-center gap-2">
            <AlertCircle :size="16" class="text-orange-500" />
            Points à améliorer
          </h4>
          <div class="space-y-2">
            <div
              v-for="(issue, idx) in myAnalysisResult.smart_analysis.issues"
              :key="idx"
              class="bg-orange-50 border border-orange-200 rounded-lg p-3"
            >
              <div class="flex items-start gap-2">
                <span class="bg-orange-500 text-white text-xs font-bold px-2 py-0.5 rounded">{{ issue.letter }}</span>
                <div>
                  <p class="text-sm text-slate-700">{{ issue.problem }}</p>
                  <p v-if="issue.fix" class="text-xs text-purple-600 mt-1">💡 {{ issue.fix }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div
          v-if="myAnalysisResult.smart_analysis?.rewrite_fr || myAnalysisResult.smart_analysis?.rewrite_en"
          class="mb-6"
        >
          <h4 class="font-semibold text-slate-700 mb-2 flex items-center gap-2">
            <RefreshCw :size="16" class="text-blue-500" />
            Reformulations suggérées
          </h4>
          <div class="space-y-3">
            <div v-if="myAnalysisResult.smart_analysis.rewrite_fr" class="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div class="flex items-center gap-2 mb-2">
                <span class="text-lg">🇫🇷</span>
                <span class="text-xs font-bold text-blue-700 uppercase">Français</span>
              </div>
              <p class="text-sm text-blue-800 italic">"{{ myAnalysisResult.smart_analysis.rewrite_fr }}"</p>
            </div>
            <div v-if="myAnalysisResult.smart_analysis.rewrite_en" class="bg-indigo-50 border border-indigo-200 rounded-lg p-4">
              <div class="flex items-center gap-2 mb-2">
                <span class="text-lg">🇬🇧</span>
                <span class="text-xs font-bold text-indigo-700 uppercase">English</span>
              </div>
              <p class="text-sm text-indigo-800 italic">"{{ myAnalysisResult.smart_analysis.rewrite_en }}"</p>
            </div>
          </div>
        </div>

        <div v-if="myAnalysisResult.alignment_analysis">
          <h4 class="font-semibold text-slate-700 mb-2 flex items-center gap-2">
            <Target :size="16" class="text-purple-500" />
            Alignement stratégique: {{ myAnalysisResult.alignment_analysis.alignment_score }}%
          </h4>
          <div v-if="myAnalysisResult.alignment_analysis.top_matches?.length > 0" class="text-xs text-slate-500">
            Aligné avec:
            {{ myAnalysisResult.alignment_analysis.top_matches.map((m) => m.title || m.objective_id).join(', ') }}
          </div>
        </div>
      </div>

      <!-- Historique -->
      <div class="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
        <div class="p-4 border-b border-slate-100">
          <h3 class="font-bold text-lg text-slate-800 flex items-center gap-2">
            <PieChartIcon :size="20" class="text-slate-400" />
            Historique de mes analyses
            <span
              v-if="analysisHistory.length > 0"
              class="bg-purple-100 text-purple-600 text-xs px-2 py-0.5 rounded-full ml-2"
            >
              {{ analysisHistory.length }}
            </span>
          </h3>
        </div>

        <div v-if="loadingHistory" class="p-8 text-center text-slate-400">
          <Loader2 :size="32" class="mx-auto mb-2 animate-spin" />
          <p>Chargement...</p>
        </div>
        <div v-else-if="analysisHistory.length === 0" class="p-8 text-center text-slate-400">
          <Sparkles :size="32" class="mx-auto mb-2 opacity-50" />
          <p>Aucune analyse effectuée pour le moment.</p>
        </div>
        <div v-else class="divide-y divide-slate-100 max-h-96 overflow-y-auto">
          <div
            v-for="(item, idx) in analysisHistory"
            :key="item.id || idx"
            class="p-4 hover:bg-slate-50 transition-colors cursor-pointer"
            @click="selectedHistoryItem = item"
          >
            <div class="flex items-center justify-between">
              <div class="flex-1">
                <div class="font-medium text-slate-800">
                  {{ item.objective_title || `Analyse #${idx + 1}` }}
                </div>
                <div class="text-xs text-slate-400 mt-1">
                  {{
                    new Date(item.analyzed_at).toLocaleDateString('fr-FR', {
                      day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
                    })
                  }}
                </div>
              </div>
              <div class="flex items-center gap-3">
                <div class="flex gap-1">
                  <span
                    v-for="letter in ['s', 'm', 'a', 'r', 't']"
                    :key="letter"
                    :class="[
                      'w-6 h-6 flex items-center justify-center rounded text-xs font-bold',
                      item[`${letter}_score`] ? 'bg-purple-500 text-white' : 'bg-slate-200 text-slate-400',
                    ]"
                  >
                    {{ letter.toUpperCase() }}
                  </span>
                </div>
                <div :class="['text-lg font-bold', scoreClass(item.smart_score)]">
                  {{ Math.round(item.smart_score) }}%
                </div>
                <Eye :size="18" class="text-slate-400" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Modal détails -->
      <div
        v-if="selectedHistoryItem"
        class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      >
        <div class="bg-white rounded-2xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
          <div class="p-6 border-b border-slate-100 flex items-center justify-between sticky top-0 bg-white">
            <h3 class="font-bold text-lg text-slate-800">Détails de l'analyse</h3>
            <button class="p-2 hover:bg-slate-100 rounded-lg" @click="selectedHistoryItem = null">
              <X :size="20" />
            </button>
          </div>

          <div class="p-6 space-y-6">
            <div>
              <h4 class="text-sm font-semibold text-slate-500 mb-1">Objectif analysé</h4>
              <p class="text-slate-800 font-medium">{{ selectedHistoryItem.objective_title || 'Sans titre' }}</p>
            </div>

            <div class="flex items-center gap-4">
              <div :class="['text-4xl font-bold', scoreClass(selectedHistoryItem.smart_score)]">
                {{ Math.round(selectedHistoryItem.smart_score) }}%
              </div>
              <div>
                <div class="text-sm font-semibold text-slate-700">Score SMART</div>
                <div class="text-xs text-slate-500">
                  {{ selectedHistoryItem.smart_score >= 80 ? 'Objectif SMART validé ✓' : 'Améliorations nécessaires' }}
                </div>
              </div>
            </div>

            <div>
              <h4 class="text-sm font-semibold text-slate-500 mb-2">Critères SMART</h4>
              <div class="flex gap-2">
                <div
                  v-for="letter in ['S', 'M', 'A', 'R', 'T']"
                  :key="letter"
                  :class="[
                    'w-12 h-12 rounded-lg flex flex-col items-center justify-center',
                    selectedHistoryItem[`${letter.toLowerCase()}_score`]
                      ? 'bg-purple-500 text-white'
                      : 'bg-slate-200 text-slate-500',
                  ]"
                >
                  <span class="text-lg font-bold">{{ letter }}</span>
                </div>
              </div>
            </div>

            <div
              v-if="selectedHistoryItem.smart_analysis?.issues && selectedHistoryItem.smart_analysis.issues.length > 0"
            >
              <h4 class="font-semibold text-slate-700 mb-2 flex items-center gap-2">
                <AlertCircle :size="16" class="text-orange-500" />
                Points à améliorer
              </h4>
              <div class="space-y-2">
                <div
                  v-for="(issue, idx) in selectedHistoryItem.smart_analysis.issues"
                  :key="idx"
                  class="bg-orange-50 border border-orange-200 rounded-lg p-3"
                >
                  <div class="flex items-start gap-2">
                    <span class="bg-orange-500 text-white text-xs font-bold px-2 py-0.5 rounded">{{ issue.letter }}</span>
                    <div>
                      <p class="text-sm text-slate-700">{{ issue.problem }}</p>
                      <p v-if="issue.fix" class="text-xs text-purple-600 mt-1">💡 {{ issue.fix }}</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div
              v-if="(selectedHistoryItem.smart_score || 0) < 100 && (selectedHistoryItem.smart_analysis?.rewrite_fr || selectedHistoryItem.smart_analysis?.rewrite_en)"
            >
              <h4 class="font-semibold text-slate-700 mb-2 flex items-center gap-2">
                <RefreshCw :size="16" class="text-blue-500" />
                Reformulations suggérées
              </h4>
              <div class="space-y-3">
                <div
                  v-if="selectedHistoryItem.smart_analysis.rewrite_fr"
                  class="bg-blue-50 border border-blue-200 rounded-lg p-4"
                >
                  <div class="flex items-center gap-2 mb-2">
                    <span class="text-lg">🇫🇷</span>
                    <span class="text-xs font-bold text-blue-700 uppercase">Français</span>
                  </div>
                  <p class="text-sm text-blue-800 italic">"{{ selectedHistoryItem.smart_analysis.rewrite_fr }}"</p>
                </div>
                <div
                  v-if="selectedHistoryItem.smart_analysis.rewrite_en"
                  class="bg-indigo-50 border border-indigo-200 rounded-lg p-4"
                >
                  <div class="flex items-center gap-2 mb-2">
                    <span class="text-lg">🇬🇧</span>
                    <span class="text-xs font-bold text-indigo-700 uppercase">English</span>
                  </div>
                  <p class="text-sm text-indigo-800 italic">"{{ selectedHistoryItem.smart_analysis.rewrite_en }}"</p>
                </div>
              </div>
            </div>

            <div v-if="selectedHistoryItem.alignment_analysis">
              <h4 class="font-semibold text-slate-700 mb-2 flex items-center gap-2">
                <Target :size="16" class="text-purple-500" />
                Alignement stratégique: {{ selectedHistoryItem.alignment_analysis.alignment_score }}%
              </h4>
              <div v-if="selectedHistoryItem.alignment_analysis.top_matches?.length > 0" class="text-xs text-slate-500">
                Aligné avec:
                {{ selectedHistoryItem.alignment_analysis.top_matches.map((m) => m.title || m.objective_id).join(', ') }}
              </div>
            </div>

            <div class="text-xs text-slate-400 pt-4 border-t border-slate-100">
              Analysé le
              {{
                new Date(selectedHistoryItem.analyzed_at).toLocaleDateString('fr-FR', {
                  day: '2-digit', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit',
                })
              }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </DashboardLayout>
</template>
