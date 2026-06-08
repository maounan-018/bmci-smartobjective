/**
 * Service API centralisé avec authentification
 * Remplace les appels directs au localStorage par des appels API
 */

import { AuthService } from './authService';

const API_BASE = '/api';

export const ApiService = {
  // ==================== OBJECTIVES ====================

  async getObjectives() {
    try {
      const response = await AuthService.authFetch(`${API_BASE}/objectives`);
      if (!response.ok) throw new Error('Erreur serveur');
      const data = await response.json();

      return (data.objectives || []).map((o) => ({
        id: o.id,
        user_id: o.user_id,
        user_name: o.user_name,
        title: o.title,
        description: o.description || '',
        context: o.context,
        status: o.status,
        progress: o.progress,
        smartAnalysis: o.smart_analysis,
        alignmentAnalysis: o.alignment_analysis,
        createdAt: o.created_at
      }));
    } catch (error) {
      console.error('[ApiService] getObjectives error:', error);
      return [];
    }
  },

  async createObjective(title, description) {
    try {
      const response = await AuthService.authFetch(`${API_BASE}/objectives`, {
        method: 'POST',
        body: JSON.stringify({ title, description })
      });

      if (!response.ok) throw new Error('Erreur création');
      const data = await response.json();

      return {
        id: data.objective.id,
        user_id: data.objective.user_id,
        title: data.objective.title,
        description: data.objective.description || '',
        status: data.objective.status,
        progress: data.objective.progress,
        createdAt: new Date().toISOString()
      };
    } catch (error) {
      console.error('[ApiService] createObjective error:', error);
      return null;
    }
  },

  async updateObjective(id, updates) {
    try {
      const response = await AuthService.authFetch(`${API_BASE}/objectives/${id}`, {
        method: 'PUT',
        body: JSON.stringify(updates)
      });
      return response.ok;
    } catch (error) {
      console.error('[ApiService] updateObjective error:', error);
      return false;
    }
  },

  async deleteObjective(id) {
    try {
      const response = await AuthService.authFetch(`${API_BASE}/objectives/${id}`, {
        method: 'DELETE'
      });
      return response.ok;
    } catch (error) {
      console.error('[ApiService] deleteObjective error:', error);
      return false;
    }
  },

  // ==================== COMPANY OBJECTIVES ====================

  async getCompanyObjectives() {
    try {
      const response = await fetch(`${API_BASE}/company-objectives`);
      if (!response.ok) throw new Error('Erreur serveur');
      const data = await response.json();
      return data.company_objectives || [];
    } catch (error) {
      console.error('[ApiService] getCompanyObjectives error:', error);
      return [];
    }
  },

  async createCompanyObjective(objective) {
    try {
      const response = await AuthService.authFetch(`${API_BASE}/company-objectives`, {
        method: 'POST',
        body: JSON.stringify(objective)
      });
      return response.ok;
    } catch (error) {
      console.error('[ApiService] createCompanyObjective error:', error);
      return false;
    }
  },

  async batchCreateCompanyObjectives(objectives) {
    try {
      const response = await AuthService.authFetch(`${API_BASE}/company-objectives/batch`, {
        method: 'POST',
        body: JSON.stringify(objectives)
      });
      if (!response.ok) return 0;
      const data = await response.json();
      return data.created || 0;
    } catch (error) {
      console.error('[ApiService] batchCreateCompanyObjectives error:', error);
      return 0;
    }
  },

  // ==================== TEAM (MANAGER/HR) ====================

  async getTeamMembers() {
    try {
      const response = await AuthService.authFetch(`${API_BASE}/team/members`);
      if (!response.ok) return [];
      const data = await response.json();
      return data.members || [];
    } catch (error) {
      console.error('[ApiService] getTeamMembers error:', error);
      return [];
    }
  },

  async getTeamStats() {
    try {
      const response = await AuthService.authFetch(`${API_BASE}/team/stats`);
      if (!response.ok) return null;
      return await response.json();
    } catch (error) {
      console.error('[ApiService] getTeamStats error:', error);
      return null;
    }
  },

  // ==================== MANAGER MODULE - STRICTLY SEPARATED ====================
  // Ces endpoints sont EXCLUSIFS aux managers et ne doivent JAMAIS être utilisés par le RH

  async getManagerObjectives() {
    try {
      const response = await AuthService.authFetch(`${API_BASE}/manager/objectives`);
      if (!response.ok) throw new Error('Erreur serveur');
      const data = await response.json();

      return (data.objectives || []).map((o) => ({
        id: o.id,
        user_id: o.user_id,
        user_name: o.user_name,
        title: o.title,
        description: o.description || '',
        context: o.context,
        status: o.status,
        progress: o.progress,
        smartAnalysis: o.smart_analysis,
        alignmentAnalysis: o.alignment_analysis,
        createdAt: o.created_at,
        entity: o.entity,
        manager_name: o.manager_name,
        period: o.period
      }));
    } catch (error) {
      console.error('[ApiService] getManagerObjectives error:', error);
      return [];
    }
  },

  async getManagerTeamStats() {
    try {
      const response = await AuthService.authFetch(`${API_BASE}/manager/team-stats`);
      if (!response.ok) return null;
      return await response.json();
    } catch (error) {
      console.error('[ApiService] getManagerTeamStats error:', error);
      return null;
    }
  },

  async getManagerTeam() {
    try {
      const response = await AuthService.authFetch(`${API_BASE}/manager/team`);
      if (!response.ok) return [];
      const data = await response.json();
      return data.members || [];
    } catch (error) {
      console.error('[ApiService] getManagerTeam error:', error);
      return [];
    }
  },

  async analyzeManagerObjective(objectiveId) {
    try {
      const response = await AuthService.authFetch(`${API_BASE}/manager/analyze-objective/${objectiveId}`, {
        method: 'POST'
      });
      if (!response.ok) {
        const err = await response.json();
        return { success: false, error: err.detail || 'Erreur analyse' };
      }
      return await response.json();
    } catch (error) {
      console.error('[ApiService] analyzeManagerObjective error:', error);
      return { success: false, error: error.message };
    }
  },

  // ==================== MANAGER: Analyse SMART personnelle ====================
  async analyzeManagerPersonalObjective(title, description) {
    try {
      const response = await AuthService.authFetch(`${API_BASE}/manager/analyze-personal`, {
        method: 'POST',
        body: JSON.stringify({ title, description })
      });
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Erreur analyse');
      }
      return await response.json();
    } catch (error) {
      console.error('[ApiService] analyzeManagerPersonalObjective error:', error);
      throw error;
    }
  },

  // ==================== MANAGER: Résultats d'analyse privés ====================
  async getManagerAnalysisResults() {
    try {
      const response = await AuthService.authFetch(`${API_BASE}/manager/analysis-results`);
      if (!response.ok) return null;
      return await response.json();
    } catch (error) {
      console.error('[ApiService] getManagerAnalysisResults error:', error);
      return null;
    }
  },

  // ==================== HR: Analyse SMART personnelle ====================
  async analyzeHRPersonalObjective(title, description) {
    try {
      const response = await AuthService.authFetch(`${API_BASE}/hr/analyze-personal`, {
        method: 'POST',
        body: JSON.stringify({ title, description })
      });
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Erreur analyse');
      }
      return await response.json();
    } catch (error) {
      console.error('[ApiService] analyzeHRPersonalObjective error:', error);
      throw error;
    }
  },

  // ==================== HR: Résultats d'analyse privés ====================
  async getHRAnalysisResults() {
    try {
      const response = await AuthService.authFetch(`${API_BASE}/hr/analysis-results`);
      if (!response.ok) return null;
      return await response.json();
    } catch (error) {
      console.error('[ApiService] getHRAnalysisResults error:', error);
      return null;
    }
  },

  // ==================== COLLABORATEUR: Résultats d'analyse privés ====================
  async getCollabAnalysisResults() {
    try {
      const response = await AuthService.authFetch(`${API_BASE}/collab/analysis-results`);
      if (!response.ok) return null;
      return await response.json();
    } catch (error) {
      console.error('[ApiService] getCollabAnalysisResults error:', error);
      return null;
    }
  },

  // ==================== AI ANALYSIS ====================

  async analyzeSmartObjective(title, description) {
    try {
      const response = await AuthService.authFetch(`${API_BASE}/analyze-smart`, {
        method: 'POST',
        body: JSON.stringify({ title, description })
      });

      if (!response.ok) throw new Error('Erreur analyse');
      return await response.json();
    } catch (error) {
      console.error('[ApiService] analyzeSmartObjective error:', error);
      return null;
    }
  },

  async analyzeAlignment(objectiveTitle, companyObjectives) {
    try {
      const response = await AuthService.authFetch(`${API_BASE}/analyze-alignment`, {
        method: 'POST',
        body: JSON.stringify({ objectiveTitle, companyObjectives })
      });

      if (!response.ok) throw new Error('Erreur alignement');
      return await response.json();
    } catch (error) {
      console.error('[ApiService] analyzeAlignment error:', error);
      return null;
    }
  },

  // ==================== HR MODULE ====================

  async importStrategyExcel(file) {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const token = localStorage.getItem('bmci_auth_token');
      const response = await fetch(`${API_BASE}/hr/import-strategy`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });

      if (!response.ok) {
        const err = await response.json();
        return { success: false, error: err.detail || 'Erreur import' };
      }
      return await response.json();
    } catch (error) {
      console.error('[ApiService] importStrategyExcel error:', error);
      return { success: false, error: error.message };
    }
  },

  async importObjectivesExcel(file) {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const token = localStorage.getItem('bmci_auth_token');
      const response = await fetch(`${API_BASE}/hr/import-objectives`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });

      if (!response.ok) {
        const err = await response.json();
        return { success: false, error: err.detail || 'Erreur import' };
      }
      return await response.json();
    } catch (error) {
      console.error('[ApiService] importObjectivesExcel error:', error);
      return { success: false, error: error.message };
    }
  },

  async analyzeBatch(objectiveIds = [], onProgress) {
    try {
      const response = await AuthService.authFetch(`${API_BASE}/hr/analyze-batch`, {
        method: 'POST',
        body: JSON.stringify(objectiveIds)
      });

      if (!response.ok) throw new Error('Erreur analyse batch');

      const reader = response.body?.getReader();
      if (!reader) return await response.json();

      const decoder = new TextDecoder();
      let finalResult = { success: false };
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.type === 'done') {
                finalResult = data;
              } else if (onProgress) {
                onProgress(data);
              }
            } catch {}
          }
        }
      }

      return finalResult;
    } catch (error) {
      console.error('[ApiService] analyzeBatch error:', error);
      return { success: false };
    }
  },

  async getHRAnalytics(filters) {
    try {
      const params = new URLSearchParams();
      if (filters?.entity) params.append('entity_filter', filters.entity);
      if (filters?.manager) params.append('manager_filter', filters.manager);
      if (filters?.period) params.append('period_filter', filters.period);

      const url = `${API_BASE}/hr/analytics${params.toString() ? '?' + params.toString() : ''}`;
      const response = await AuthService.authFetch(url);

      if (!response.ok) throw new Error('Erreur analytics');
      return await response.json();
    } catch (error) {
      console.error('[ApiService] getHRAnalytics error:', error);
      return null;
    }
  },

  async getHRObjectivesDetails(filters) {
    try {
      const params = new URLSearchParams();
      if (filters?.entity) params.append('entity_filter', filters.entity);
      if (filters?.manager) params.append('manager_filter', filters.manager);
      if (filters?.period) params.append('period_filter', filters.period);
      if (filters?.smart) params.append('smart_filter', filters.smart);
      if (filters?.alignment) params.append('alignment_filter', filters.alignment);

      const url = `${API_BASE}/hr/objectives-details${params.toString() ? '?' + params.toString() : ''}`;
      const response = await AuthService.authFetch(url);

      if (!response.ok) throw new Error('Erreur détails');
      return await response.json();
    } catch (error) {
      console.error('[ApiService] getHRObjectivesDetails error:', error);
      return { objectives: [], total: 0 };
    }
  },

  async exportHRExcel(filters) {
    try {
      const params = new URLSearchParams();
      if (filters?.entity) params.append('entity_filter', filters.entity);
      if (filters?.manager) params.append('manager_filter', filters.manager);
      if (filters?.period) params.append('period_filter', filters.period);

      const url = `${API_BASE}/hr/export-excel${params.toString() ? '?' + params.toString() : ''}`;
      const response = await AuthService.authFetch(url);

      if (!response.ok) throw new Error('Erreur export');
      return await response.blob();
    } catch (error) {
      console.error('[ApiService] exportHRExcel error:', error);
      return null;
    }
  },

  async exportHRPdf(filters) {
    try {
      const params = new URLSearchParams();
      if (filters?.entity) params.append('entity_filter', filters.entity);
      if (filters?.manager) params.append('manager_filter', filters.manager);
      if (filters?.period) params.append('period_filter', filters.period);

      const url = `${API_BASE}/hr/export-pdf${params.toString() ? '?' + params.toString() : ''}`;
      const response = await AuthService.authFetch(url);

      if (!response.ok) throw new Error('Erreur export PDF');
      return await response.blob();
    } catch (error) {
      console.error('[ApiService] exportHRPdf error:', error);
      return null;
    }
  },

  async exportManagerExcel() {
    try {
      const url = `${API_BASE}/manager/export?format=excel`;
      const response = await AuthService.authFetch(url);

      if (!response.ok) throw new Error('Erreur export Excel');
      return await response.blob();
    } catch (error) {
      console.error('[ApiService] exportManagerExcel error:', error);
      return null;
    }
  },

  async exportManagerPdf() {
    try {
      const url = `${API_BASE}/manager/export?format=pdf`;
      const response = await AuthService.authFetch(url);

      if (!response.ok) throw new Error('Erreur export PDF');
      return await response.blob();
    } catch (error) {
      console.error('[ApiService] exportManagerPdf error:', error);
      return null;
    }
  },

  /**
   * Import d'un fichier Excel contenant des objectifs à analyser en lot
   * @param {File} file Fichier Excel (.xlsx, .xls)
   * @returns Résultats d'analyse SMART pour chaque objectif
   */
  async importExcelForAnalysis(file) {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API_BASE}/import-excel-analyze`, {
        method: 'POST',
        body: formData,
        headers: AuthService.getAuthHeadersNoContentType()
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Erreur import');
      }

      return await response.json();
    } catch (error) {
      console.error('[ApiService] importExcelForAnalysis error:', error);
      throw error;
    }
  },

  /**
   * Scanne un fichier Excel et retourne sa structure détectée
   */
  async scanExcelFile(file) {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API_BASE}/scan-excel`, {
        method: 'POST',
        body: formData,
        headers: AuthService.getAuthHeadersNoContentType()
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Erreur scan');
      }

      return await response.json();
    } catch (error) {
      console.error('[ApiService] scanExcelFile error:', error);
      throw error;
    }
  },

  /**
   * Importe et exporte un fichier Excel avec les analyses ajoutées
   */
  async importExcelAndExport(file) {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API_BASE}/import-excel-export`, {
        method: 'POST',
        body: formData,
        headers: AuthService.getAuthHeadersNoContentType()
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Erreur export');
      }

      return await response.blob();
    } catch (error) {
      console.error('[ApiService] importExcelAndExport error:', error);
      throw error;
    }
  },

  async getHRImports() {
    try {
      const response = await AuthService.authFetch(`${API_BASE}/hr/imports`);
      if (!response.ok) throw new Error('Erreur imports');
      const data = await response.json();
      return data.imports || [];
    } catch (error) {
      console.error('[ApiService] getHRImports error:', error);
      return [];
    }
  }
};

export default ApiService;
