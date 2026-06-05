// utils/formatters.js — Petites fonctions de formatage réutilisables dans les vues.

// Formate une date ISO en date locale française lisible (ex. "10 mars 2026").
export function formatDate(iso) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });
  } catch {
    return iso;
  }
}

// Arrondit un score (0–100) en entier, en tolérant null/undefined.
export function formatScore(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return Math.round(value);
}

// Déclenche le téléchargement d'un Blob (export Excel/PDF côté backend).
export function downloadBlob(blob, filename) {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}
