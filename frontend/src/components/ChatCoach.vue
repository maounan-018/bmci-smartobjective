<script setup>
// components/ChatCoach.vue — Coach IA SMART (bouton flottant + panneau latéral).
//
// Conversation pas-à-pas avec l'assistant pour formuler un objectif SMART.
// AUTH : adapté au pattern mvc — cookie HttpOnly + CSRF via AuthService.authFetch
// (et NON un token Bearer localStorage). Le backend s'appuie sur le RAG (base de
// connaissances) pour le contexte BMCI ; il est réservé MANAGER/COLLAB (403 sinon).
import { ref, nextTick, watch } from 'vue';
import { AuthService } from '@/services/authService';

const emit = defineEmits(['use-objective']);

const isOpen = ref(false);
const messages = ref([]);
const inputText = ref('');
const isLoading = ref(false);
const finalObjective = ref(null);
const currentStep = ref('S');
const messagesContainer = ref(null);
const textareaRef = ref(null);

function openCoach() {
  isOpen.value = true;
  nextTick(() => {
    textareaRef.value?.focus();
    scrollToBottom();
  });
}

function closeCoach() {
  isOpen.value = false;
}

function resetChat() {
  if (!confirm('Recommencer la conversation ?')) return;
  messages.value = [];
  finalObjective.value = null;
  currentStep.value = 'S';
  inputText.value = '';
}

async function sendMessage() {
  const text = inputText.value.trim();
  if (!text || isLoading.value || finalObjective.value) return;

  messages.value.push({ role: 'user', content: text });
  inputText.value = '';
  isLoading.value = true;
  await nextTick();
  scrollToBottom();

  try {
    // authFetch : envoie le cookie de session + le jeton CSRF (méthode mutante).
    const response = await AuthService.authFetch('/api/chat-coach', {
      method: 'POST',
      body: JSON.stringify({ messages: messages.value }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Erreur HTTP ${response.status}`);
    }

    const data = await response.json();
    messages.value.push({ role: 'assistant', content: data.reply });

    if (data.current_step) currentStep.value = data.current_step;
    if (data.ready && data.final_objective) {
      finalObjective.value = data.final_objective;
      currentStep.value = 'SYNTHESE';
    }
  } catch (err) {
    messages.value.push({ role: 'assistant', content: 'Erreur : ' + err.message });
  } finally {
    isLoading.value = false;
    await nextTick();
    scrollToBottom();
  }
}

function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
}

watch(messages, () => nextTick(scrollToBottom), { deep: true });
</script>

<template>
  <button v-show="!isOpen" class="coach-fab" @click="openCoach">
    🤖 Coach IA
  </button>

  <div v-if="isOpen" class="coach-drawer">
    <header class="coach-header">
      <h2 class="coach-title">Coach IA SMART</h2>
      <div class="coach-header-actions">
        <button class="coach-icon-btn" title="Recommencer" @click="resetChat">↺</button>
        <button class="coach-icon-btn" title="Fermer" @click="closeCoach">✕</button>
      </div>
    </header>

    <div ref="messagesContainer" class="coach-messages">
      <div v-if="messages.length === 0" class="coach-welcome">
        Bonjour ! Je suis votre Coach IA SMART.<br>
        Décrivez votre objectif et je vous guide pas à pas.
      </div>

      <div
        v-for="(msg, index) in messages"
        :key="index"
        :class="['coach-msg', msg.role === 'user' ? 'coach-user' : 'coach-bot']"
      >
        <div class="bubble">{{ msg.content }}</div>
      </div>

      <div v-if="isLoading" class="coach-msg coach-bot">
        <div class="bubble bubble-loading">...</div>
      </div>

      <div v-if="finalObjective" class="final-card">
        <strong>Objectif SMART validé :</strong>
        <p>{{ finalObjective }}</p>
        <button class="use-btn" @click="emit('use-objective', finalObjective); closeCoach()">
          Utiliser cet objectif
        </button>
      </div>
    </div>

    <div class="coach-input">
      <textarea
        ref="textareaRef"
        v-model="inputText"
        placeholder="Votre message… (Entrée pour envoyer)"
        rows="2"
        :disabled="isLoading || !!finalObjective"
        @keydown="handleKeydown"
      ></textarea>
      <button
        class="send-btn"
        :disabled="isLoading || !inputText.trim() || !!finalObjective"
        @click="sendMessage"
      >➤</button>
    </div>
  </div>
</template>

<style scoped>
.coach-fab {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 9999;
  padding: 12px 20px;
  background: #1a6b4a;
  color: white;
  border-radius: 30px;
  cursor: pointer;
  border: none;
  font-weight: bold;
  font-size: 0.95rem;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
  transition: transform 0.15s, box-shadow 0.15s;
}
.coach-fab:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.3);
}

.coach-drawer {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  width: 400px;
  max-width: 100vw;
  background: white;
  z-index: 10000;
  box-shadow: -5px 0 25px rgba(0, 0, 0, 0.2);
  display: flex;
  flex-direction: column;
}

.coach-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  background: #f8fffe;
  border-bottom: 2px solid #1a6b4a;
}
.coach-title {
  margin: 0;
  font-size: 1rem;
  color: #1a6b4a;
}
.coach-header-actions {
  display: flex;
  gap: 8px;
}
.coach-icon-btn {
  background: none;
  border: 1px solid #ccc;
  border-radius: 4px;
  cursor: pointer;
  padding: 2px 8px;
  font-size: 1rem;
}
.coach-icon-btn:hover {
  background: #f1f5f9;
}

.coach-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.coach-welcome {
  color: #64748b;
  font-size: 0.9rem;
  text-align: center;
  padding: 20px 0;
  line-height: 1.6;
}

.coach-msg {
  display: flex;
}
.coach-user {
  justify-content: flex-end;
}
.bubble {
  padding: 10px 14px;
  border-radius: 12px;
  max-width: 85%;
  white-space: pre-wrap;
  line-height: 1.5;
  font-size: 0.9rem;
}
.coach-user .bubble {
  background: #1a6b4a;
  color: white;
  border-bottom-right-radius: 2px;
}
.coach-bot .bubble {
  background: #f1f5f9;
  color: #1e293b;
  border-bottom-left-radius: 2px;
}
.bubble-loading {
  color: #94a3b8;
  font-style: italic;
}

.final-card {
  background: #e8f5f0;
  padding: 14px;
  border-radius: 8px;
  border-left: 4px solid #1a6b4a;
  margin-top: 4px;
}
.final-card p {
  margin: 8px 0 12px;
  font-style: italic;
  color: #1e293b;
}
.use-btn {
  background: #1a6b4a;
  color: white;
  border: none;
  border-radius: 6px;
  padding: 8px 16px;
  cursor: pointer;
  font-weight: bold;
}
.use-btn:hover {
  background: #155c3d;
}

.coach-input {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 12px;
  border-top: 1px solid #e2e8f0;
}
.coach-input textarea {
  flex: 1;
  resize: none;
  border-radius: 8px;
  border: 1px solid #cbd5e1;
  padding: 8px 10px;
  font-family: inherit;
  font-size: 0.9rem;
  outline: none;
}
.coach-input textarea:focus {
  border-color: #1a6b4a;
}
.send-btn {
  background: #1a6b4a;
  color: white;
  border: none;
  border-radius: 8px;
  padding: 8px 14px;
  cursor: pointer;
  font-size: 1.1rem;
  height: 42px;
}
.send-btn:disabled {
  background: #94a3b8;
  cursor: not-allowed;
}
.send-btn:not(:disabled):hover {
  background: #155c3d;
}
</style>
