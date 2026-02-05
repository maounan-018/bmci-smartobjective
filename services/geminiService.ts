// Service IA utilisant le backend local Ollama (smart-qwen8)
import { SmartAnalysis, AlignmentAnalysis, CompanyObjective, Objective, UserRole } from "../types";

// URL du backend local (Python FastAPI)
const API_BASE_URL = '/api';

// --- PERSISTENCE LAYER (MOCK DB) ---
const STORAGE_KEYS = {
  COMPANY_OBJECTIVES: 'bmci_company_objectives',
  PERSONAL_OBJECTIVES: 'bmci_personal_objectives',
};

class StorageDB {
  static getCompanyObjectives(): CompanyObjective[] {
    const data = localStorage.getItem(STORAGE_KEYS.COMPANY_OBJECTIVES);
    return data ? JSON.parse(data) : [
      { id: 'BMCI-01', title: 'Transformation Digitale 2025', description: 'Accélération des services mobiles' },
      { id: 'BMCI-02', title: 'Excellence Service Client', description: 'NPS cible de 45' },
      { id: 'BMCI-03', title: 'Culture Inclusion & Diversité', description: 'Index égalité 95/100' },
    ];
  }

  static saveCompanyObjectives(objectives: CompanyObjective[]) {
    localStorage.setItem(STORAGE_KEYS.COMPANY_OBJECTIVES, JSON.stringify(objectives));
  }

  static getPersonalObjectives(): Objective[] {
    const data = localStorage.getItem(STORAGE_KEYS.PERSONAL_OBJECTIVES);
    return data ? JSON.parse(data) : [];
  }

  static savePersonalObjectives(objectives: Objective[]) {
    localStorage.setItem(STORAGE_KEYS.PERSONAL_OBJECTIVES, JSON.stringify(objectives));
  }

  static addObjective(obj: Objective) {
    const all = this.getPersonalObjectives();
    const updated = [obj, ...all];
    this.savePersonalObjectives(updated);
    return updated;
  }
}

// --- AI SERVICE (LOCAL OLLAMA) ---

/**
 * Analyse un objectif via le backend local (Ollama smart-qwen8)
 */
export const analyzeSmartObjective = async (title: string, description: string): Promise<SmartAnalysis> => {
  try {
    const response = await fetch(`${API_BASE_URL}/analyze-smart`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ title, description: description || '' }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Erreur HTTP ${response.status}`);
    }

    const result = await response.json();
    return result as SmartAnalysis;
  } catch (err: any) {
    console.error("AI Error:", err);
    throw new Error(err.message || "Impossible de contacter l'IA BMCI. Vérifiez que le serveur backend et Ollama sont démarrés.");
  }
};

/**
 * Calcule l'alignement avec le catalogue stratégique via le backend local
 */
export const analyzeAlignment = async (objectiveTitle: string, companyObjectives: CompanyObjective[]): Promise<AlignmentAnalysis> => {
  try {
    const response = await fetch(`${API_BASE_URL}/analyze-alignment`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        objectiveTitle, 
        companyObjectives 
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      console.error("Alignment API Error:", errorData);
      return { alignment_score: 0, top_matches: [], gaps: ["Erreur de connexion IA"] };
    }

    const result = await response.json();
    return result as AlignmentAnalysis;
  } catch (err) {
    console.error("AI Alignment Error:", err);
    return { alignment_score: 0, top_matches: [], gaps: ["Erreur de connexion IA"] };
  }
};

// --- BATCH & FILE PROCESSING (SIMULATED API ENDPOINTS) ---

/**
 * Import du catalogue (RH)
 */
export const uploadCompanyObjectivesFile = async (file: File): Promise<{ success: boolean; count: number }> => {
  // Simulation de lecture de fichier
  return new Promise((resolve) => {
    setTimeout(() => {
      const mockNewCatalogue = [
        { id: 'STRAT-01', title: 'Excellence Opérationnelle 2025', description: 'Optimisation des processus crédits' },
        { id: 'STRAT-02', title: 'Digital First', description: 'Migration massive vers BMCI Connect' },
        { id: 'STRAT-03', title: 'Engagement Social', description: 'Projets RSE impactants' }
      ];
      StorageDB.saveCompanyObjectives(mockNewCatalogue);
      resolve({ success: true, count: mockNewCatalogue.length });
    }, 1500);
  });
};

/**
 * Import massif d'objectifs (RH ou Manager)
 */
export const uploadAllEmployeeObjectives = async (file: File): Promise<{ objectives: Objective[] }> => {
  // Simule l'analyse de chaque ligne du fichier par l'IA
  return new Promise(async (resolve) => {
    const rawData = [
      { title: "Augmenter les ventes", desc: "De 20% d'ici Noel", user: "Sara K." },
      { title: "Réduire les bugs", desc: "Sur l'app mobile", user: "Amine R." },
      { title: "Formation Agile", desc: "Passer la certif Scrum", user: "Mehdi L." }
    ];

    const processed: Objective[] = [];
    const catalogue = StorageDB.getCompanyObjectives();

    for (const row of rawData) {
      const smart = await analyzeSmartObjective(row.title, row.desc);
      const align = await analyzeAlignment(row.title, catalogue);
      
      processed.push({
        id: Math.random().toString(36).substr(2, 9),
        user_id: `U-${Math.floor(Math.random()*1000)}`,
        user_name: row.user,
        title: row.title,
        description: row.desc,
        status: 'analyzed',
        progress: 'not_started',
        createdAt: new Date().toISOString(),
        smartAnalysis: smart,
        alignmentAnalysis: align
      });
    }

    const current = StorageDB.getPersonalObjectives();
    const updated = [...processed, ...current];
    StorageDB.savePersonalObjectives(updated);
    
    resolve({ objectives: processed });
  });
};

/**
 * Récupération de l'historique (Mock)
 */
export const getUserHistory = async (userId: string): Promise<Objective[]> => {
  return StorageDB.getPersonalObjectives().filter(o => o.user_id === userId);
};

/**
 * Récupération de tous les objectifs (RH)
 */
export const getAllObjectives = async (): Promise<Objective[]> => {
  return StorageDB.getPersonalObjectives();
};

/**
 * Récupération du catalogue stratégique
 */
export const getCompanyObjectives = async (): Promise<CompanyObjective[]> => {
  return StorageDB.getCompanyObjectives();
};
