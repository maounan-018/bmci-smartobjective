<script setup>
// components/KnowledgeBaseManager.vue — Base de connaissances de l'assistant (RAG).
//
// Téléverse des documents (PDF / Word / Excel / texte) qui alimentent la
// recherche sémantique de l'assistant, puis les liste et permet de les
// supprimer. Réservé MANAGER/ADMIN : le backend applique aussi la garde de rôle.
import { ref, onMounted } from 'vue';
import { ApiService } from '@/services/apiService';
import {
  UploadCloud, FileText, Trash2, Loader2, X, CheckCircle2, AlertCircle,
} from 'lucide-vue-next';

const ACCEPTED = '.pdf,.docx,.xlsx,.txt,.md';

const documents = ref([]);
const loading = ref(false);
const uploading = ref(false);
const message = ref(null); // { type: 'success' | 'error', text }
const fileInput = ref(null);
const selectedFile = ref(null);
const title = ref('');
const dragOver = ref(false);

onMounted(loadDocuments);

async function loadDocuments() {
  loading.value = true;
  documents.value = await ApiService.getRagDocuments();
  loading.value = false;
}

function pickFile(e) {
  const f = e.target.files?.[0];
  if (f) selectedFile.value = f;
}

function onDrop(e) {
  dragOver.value = false;
  const f = e.dataTransfer?.files?.[0];
  if (f) selectedFile.value = f;
}

function clearSelection() {
  selectedFile.value = null;
  title.value = '';
  if (fileInput.value) fileInput.value.value = '';
}

async function upload() {
  if (!selectedFile.value) return;
  uploading.value = true;
  message.value = null;
  const res = await ApiService.uploadRagDocument(selectedFile.value, { title: title.value });
  uploading.value = false;
  if (res.success) {
    message.value = {
      type: 'success',
      text: `« ${res.document.title} » indexé (${res.document.chunk_count} passage(s)).`,
    };
    clearSelection();
    await loadDocuments();
  } else {
    message.value = { type: 'error', text: res.error || 'Échec du téléversement.' };
  }
}

async function remove(doc) {
  if (!confirm(`Supprimer « ${doc.title} » de la base de connaissances ?`)) return;
  const ok = await ApiService.deleteRagDocument(doc.id);
  if (ok) {
    documents.value = documents.value.filter((d) => d.id !== doc.id);
  } else {
    message.value = { type: 'error', text: 'Échec de la suppression.' };
  }
}

function formatDate(iso) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' });
  } catch {
    return iso;
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Zone de téléversement -->
    <div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
      <h3 class="text-lg font-bold text-slate-800 mb-1 flex items-center gap-2">
        <UploadCloud :size="20" class="text-indigo-600" /> Ajouter un document
      </h3>
      <p class="text-sm text-slate-500 mb-4">
        PDF, Word, Excel ou texte. Le document est découpé et indexé pour la recherche sémantique de l'assistant.
      </p>

      <div
        class="border-2 border-dashed rounded-xl p-6 text-center transition-colors cursor-pointer"
        :class="dragOver ? 'border-indigo-400 bg-indigo-50' : 'border-slate-300 hover:border-indigo-300'"
        @click="fileInput.click()"
        @dragover.prevent="dragOver = true"
        @dragleave.prevent="dragOver = false"
        @drop.prevent="onDrop"
      >
        <input ref="fileInput" type="file" :accept="ACCEPTED" class="hidden" @change="pickFile" />
        <UploadCloud :size="32" class="mx-auto mb-2 text-slate-400" />
        <p v-if="!selectedFile" class="text-sm text-slate-600">
          Glissez un fichier ici ou <span class="text-indigo-600 font-bold">cliquez pour choisir</span>
        </p>
        <p v-else class="text-sm font-bold text-slate-700 flex items-center justify-center gap-2">
          <FileText :size="16" /> {{ selectedFile.name }}
        </p>
      </div>

      <div v-if="selectedFile" class="mt-4 space-y-3">
        <input
          v-model="title" type="text"
          placeholder="Titre (optionnel — sinon le nom du fichier)"
          class="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
        />
        <div class="flex items-center gap-2">
          <button
            @click="upload" :disabled="uploading"
            class="px-4 py-2 bg-indigo-600 text-white rounded-lg font-bold text-sm hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-2"
          >
            <Loader2 v-if="uploading" :size="16" class="animate-spin" />
            <UploadCloud v-else :size="16" />
            {{ uploading ? 'Indexation…' : 'Téléverser et indexer' }}
          </button>
          <button @click="clearSelection" :disabled="uploading" class="px-3 py-2 text-slate-500 hover:text-slate-700 text-sm">
            Annuler
          </button>
        </div>
      </div>

      <div
        v-if="message" class="mt-4 p-3 rounded-lg text-sm flex items-center gap-2"
        :class="message.type === 'success' ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'"
      >
        <CheckCircle2 v-if="message.type === 'success'" :size="16" />
        <AlertCircle v-else :size="16" />
        <span class="flex-1">{{ message.text }}</span>
        <button @click="message = null"><X :size="14" /></button>
      </div>
    </div>

    <!-- Liste des documents indexés -->
    <div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-lg font-bold text-slate-800">Documents indexés</h3>
        <span class="text-xs text-slate-500">{{ documents.length }} document(s)</span>
      </div>

      <div v-if="loading" class="text-center py-8 text-slate-400">
        <Loader2 :size="24" class="mx-auto animate-spin" />
      </div>
      <div v-else-if="documents.length === 0" class="text-center py-8 text-slate-400">
        <FileText :size="32" class="mx-auto mb-2 opacity-50" />
        <p class="text-sm">Aucun document. Ajoutez-en un ci-dessus pour enrichir l'assistant.</p>
      </div>
      <ul v-else class="divide-y divide-slate-100">
        <li v-for="doc in documents" :key="doc.id" class="py-3 flex items-center gap-3">
          <div class="w-9 h-9 rounded-lg bg-indigo-50 flex items-center justify-center shrink-0">
            <FileText :size="18" class="text-indigo-600" />
          </div>
          <div class="min-w-0 flex-1">
            <p class="font-bold text-sm text-slate-800 truncate">{{ doc.title }}</p>
            <p class="text-xs text-slate-500">
              {{ doc.chunk_count }} passage(s) · {{ (doc.source_type || '').toUpperCase() }} · {{ formatDate(doc.created_at) }}
              <span v-if="doc.scope && doc.scope !== 'GLOBAL'" class="ml-1 px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">{{ doc.scope }}</span>
            </p>
          </div>
          <button @click="remove(doc)" class="p-2 text-slate-400 hover:text-red-600" title="Supprimer">
            <Trash2 :size="16" />
          </button>
        </li>
      </ul>
    </div>
  </div>
</template>
