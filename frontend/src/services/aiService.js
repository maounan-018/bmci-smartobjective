// services/aiService.js — Appels d'analyse IA (anciennement geminiService.ts).
//
// L'IA tourne CÔTÉ BACKEND (Python FastAPI + Ollama, modèle smart-qwen8). Le
// frontend ne contacte jamais Ollama directement : il passe par /api. Renommé
// "aiService" car il n'utilise plus Gemini — c'est de l'inférence locale Ollama.

const API_BASE_URL = '/api';

// Analyse SMART d'un objectif via le backend local (Ollama).
export async function analyzeSmartObjective(title, description) {
  try {
    const response = await fetch(`${API_BASE_URL}/analyze-smart`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, description: description || '' }),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Erreur HTTP ${response.status}`);
    }
    return await response.json();
  } catch (err) {
    console.error('AI Error:', err);
    throw new Error(
      err.message ||
        "Impossible de contacter l'IA BMCI. Vérifiez que le serveur backend et Ollama sont démarrés.",
    );
  }
}

// Calcule l'alignement d'un objectif avec le catalogue stratégique (backend).
export async function analyzeAlignment(objectiveTitle, companyObjectives) {
  try {
    const response = await fetch(`${API_BASE_URL}/analyze-alignment`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ objectiveTitle, companyObjectives }),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      console.error('Alignment API Error:', errorData);
      return { alignment_score: 0, top_matches: [], gaps: ['Erreur de connexion IA'] };
    }
    return await response.json();
  } catch (err) {
    console.error('AI Alignment Error:', err);
    return { alignment_score: 0, top_matches: [], gaps: ['Erreur de connexion IA'] };
  }
}
