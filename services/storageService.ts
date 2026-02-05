/**
 * Service de persistance centralisé pour ObjectifSMART-AI
 * Gère le stockage localStorage avec typage fort et gestion d'erreurs
 */

import { Objective, CompanyObjective } from '../types';

const STORAGE_KEYS = {
  OBJECTIVES: 'bmci_objectives',
  COMPANY_OBJECTIVES: 'bmci_company_objectives',
  LAST_SYNC: 'bmci_last_sync',
} as const;

// Données initiales vides (pas de mock)
const EMPTY_OBJECTIVES: Objective[] = [];
const EMPTY_COMPANY_OBJECTIVES: CompanyObjective[] = [];

/**
 * Service de stockage persistant avec gestion d'erreurs
 */
export const StorageService = {
  // ==================== OBJECTIFS PERSONNELS ====================
  
  /**
   * Récupère tous les objectifs depuis le stockage
   */
  getObjectives(): Objective[] {
    try {
      const data = localStorage.getItem(STORAGE_KEYS.OBJECTIVES);
      if (!data) return EMPTY_OBJECTIVES;
      const parsed = JSON.parse(data);
      return Array.isArray(parsed) ? parsed : EMPTY_OBJECTIVES;
    } catch (error) {
      console.error('[StorageService] Erreur lecture objectifs:', error);
      return EMPTY_OBJECTIVES;
    }
  },

  /**
   * Sauvegarde tous les objectifs
   */
  saveObjectives(objectives: Objective[]): boolean {
    try {
      localStorage.setItem(STORAGE_KEYS.OBJECTIVES, JSON.stringify(objectives));
      localStorage.setItem(STORAGE_KEYS.LAST_SYNC, new Date().toISOString());
      return true;
    } catch (error) {
      console.error('[StorageService] Erreur sauvegarde objectifs:', error);
      return false;
    }
  },

  /**
   * Ajoute un objectif et persiste
   */
  addObjective(objective: Objective): Objective[] {
    const current = this.getObjectives();
    const updated = [objective, ...current];
    this.saveObjectives(updated);
    return updated;
  },

  /**
   * Met à jour un objectif existant
   */
  updateObjective(id: string, updates: Partial<Objective>): Objective[] {
    const current = this.getObjectives();
    const updated = current.map(obj => 
      obj.id === id ? { ...obj, ...updates } : obj
    );
    this.saveObjectives(updated);
    return updated;
  },

  /**
   * Supprime un objectif
   */
  deleteObjective(id: string): Objective[] {
    const current = this.getObjectives();
    const updated = current.filter(obj => obj.id !== id);
    this.saveObjectives(updated);
    return updated;
  },

  /**
   * Récupère les objectifs d'un utilisateur spécifique
   */
  getObjectivesByUser(userId: string): Objective[] {
    return this.getObjectives().filter(obj => obj.user_id === userId);
  },

  // ==================== OBJECTIFS STRATÉGIQUES ====================
  
  /**
   * Récupère le catalogue stratégique
   */
  getCompanyObjectives(): CompanyObjective[] {
    try {
      const data = localStorage.getItem(STORAGE_KEYS.COMPANY_OBJECTIVES);
      if (!data) return EMPTY_COMPANY_OBJECTIVES;
      const parsed = JSON.parse(data);
      return Array.isArray(parsed) ? parsed : EMPTY_COMPANY_OBJECTIVES;
    } catch (error) {
      console.error('[StorageService] Erreur lecture catalogue:', error);
      return EMPTY_COMPANY_OBJECTIVES;
    }
  },

  /**
   * Sauvegarde le catalogue stratégique
   */
  saveCompanyObjectives(objectives: CompanyObjective[]): boolean {
    try {
      localStorage.setItem(STORAGE_KEYS.COMPANY_OBJECTIVES, JSON.stringify(objectives));
      localStorage.setItem(STORAGE_KEYS.LAST_SYNC, new Date().toISOString());
      return true;
    } catch (error) {
      console.error('[StorageService] Erreur sauvegarde catalogue:', error);
      return false;
    }
  },

  /**
   * Ajoute un objectif stratégique
   */
  addCompanyObjective(objective: CompanyObjective): CompanyObjective[] {
    const current = this.getCompanyObjectives();
    const updated = [...current, objective];
    this.saveCompanyObjectives(updated);
    return updated;
  },

  // ==================== UTILITAIRES ====================
  
  /**
   * Retourne la date de dernière synchronisation
   */
  getLastSync(): string | null {
    return localStorage.getItem(STORAGE_KEYS.LAST_SYNC);
  },

  /**
   * Efface toutes les données (reset)
   */
  clearAll(): void {
    localStorage.removeItem(STORAGE_KEYS.OBJECTIVES);
    localStorage.removeItem(STORAGE_KEYS.COMPANY_OBJECTIVES);
    localStorage.removeItem(STORAGE_KEYS.LAST_SYNC);
  },

  /**
   * Vérifie si le stockage est disponible
   */
  isAvailable(): boolean {
    try {
      const test = '__storage_test__';
      localStorage.setItem(test, test);
      localStorage.removeItem(test);
      return true;
    } catch (e) {
      return false;
    }
  },

  /**
   * Exporte toutes les données (backup)
   */
  exportAll(): { objectives: Objective[]; companyObjectives: CompanyObjective[]; exportedAt: string } {
    return {
      objectives: this.getObjectives(),
      companyObjectives: this.getCompanyObjectives(),
      exportedAt: new Date().toISOString()
    };
  },

  /**
   * Importe des données (restore)
   */
  importAll(data: { objectives?: Objective[]; companyObjectives?: CompanyObjective[] }): boolean {
    try {
      if (data.objectives) this.saveObjectives(data.objectives);
      if (data.companyObjectives) this.saveCompanyObjectives(data.companyObjectives);
      return true;
    } catch (error) {
      console.error('[StorageService] Erreur import:', error);
      return false;
    }
  }
};

export default StorageService;
