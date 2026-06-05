import React, { useState, useEffect, useMemo, useRef } from 'react';
import { ApiService } from '../services/apiService';
import { Objective, CompanyObjective, User, SmartAnalysis } from '../types';
import SmartBadge from '../components/SmartBadge';
import AlignmentChart from '../components/AlignmentChart';
import { 
  Users, Target, ChevronRight, Loader2, AlertCircle, 
  CheckCircle2, TrendingUp, RefreshCw, Eye, Plus, Download,
  Search, PieChart as PieChartIcon, Play, Sparkles, FileSpreadsheet, Upload, X
} from 'lucide-react';
import { 
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer
} from 'recharts';

type LoadingState = 'idle' | 'loading' | 'success' | 'error';

interface ManagerDashboardProps {
  user: User;
}

const ManagerDashboard: React.FC<ManagerDashboardProps> = ({ user }) => {
  // Tâche active (null = vue principale avec les 3 tâches)
  const [activeTask, setActiveTask] = useState<'smart' | 'team' | 'strategy' | null>(null);
  const [loadingState, setLoadingState] = useState<LoadingState>('loading');
  const [error, setError] = useState<string | null>(null);
  
  // Données depuis l'API
  const [teamObjectives, setTeamObjectives] = useState<Objective[]>([]);
  const [teamStats, setTeamStats] = useState<any>(null);
  const [companyObjectives, setCompanyObjectives] = useState<CompanyObjective[]>([]);
  
  // Analyse SMART du Manager (ses propres objectifs)
  const [myObjectiveTitle, setMyObjectiveTitle] = useState('');
  const [myObjectiveDesc, setMyObjectiveDesc] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [myAnalysisResult, setMyAnalysisResult] = useState<any>(null);
  const [analysisHistory, setAnalysisHistory] = useState<any[]>([]);
  
  // Import Excel
  const [isImporting, setIsImporting] = useState(false);
  const [importResults, setImportResults] = useState<any>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Vue détaillée
  const [selectedObjective, setSelectedObjective] = useState<Objective | null>(null);
  
  // Analyse historique sélectionnée pour voir les détails
  const [selectedHistoryItem, setSelectedHistoryItem] = useState<any>(null);
  
  // Objectif stratégique
  const [newGoalTitle, setNewGoalTitle] = useState('');
  const [newGoalDesc, setNewGoalDesc] = useState('');

  // Filtres
  const [filterMember, setFilterMember] = useState<string>('all');
  const [filterSmartStatus, setFilterSmartStatus] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  
  // État pour l'analyse en cours
  const [analyzingId, setAnalyzingId] = useState<string | null>(null);

  // ============ CHARGEMENT INITIAL ============
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoadingState('loading');
      
      // Charger les données
      const [objectives, stats, companyObjs, analysisData] = await Promise.all([
        ApiService.getManagerObjectives(),
        ApiService.getManagerTeamStats(),
        ApiService.getCompanyObjectives(),
        ApiService.getManagerAnalysisResults()
      ]);
      
      setTeamObjectives(objectives);
      setTeamStats(stats);
      setCompanyObjectives(companyObjs);
      
      // Charger l'historique des analyses personnelles du manager
      if (analysisData) {
        setAnalysisHistory(analysisData.results || []);
      }
      
      setLoadingState('success');
    } catch (err) {
      console.error('[ManagerDashboard] Erreur chargement:', err);
      setLoadingState('error');
      setError('Erreur lors du chargement des données.');
    }
  };

  // ============ ANALYSE SMART PERSONNELLE DU MANAGER ============
  const handleAnalyzeMyObjective = async () => {
    if (!myObjectiveTitle.trim()) {
      alert('Veuillez saisir un titre pour votre objectif.');
      return;
    }
    
    setIsAnalyzing(true);
    setMyAnalysisResult(null);
    
    try {
      // Appel API pour analyser l'objectif personnel du manager
      const result = await ApiService.analyzeManagerPersonalObjective(myObjectiveTitle, myObjectiveDesc);
      
      if (result) {
        setMyAnalysisResult(result);
        
        // Créer une nouvelle entrée pour l'historique
        const newHistoryEntry = {
          ...result,
          objective_title: myObjectiveTitle,
          analyzed_at: new Date().toISOString(),
          id: `temp-${Date.now()}`
        };

        // Mettre à jour l'historique localement pour un effet temps réel
        setAnalysisHistory(prevHistory => [newHistoryEntry, ...prevHistory]);

        // Recharger l'historique depuis le serveur pour confirmer
        const analysisData = await ApiService.getManagerAnalysisResults();
        if (analysisData) {
          setAnalysisHistory(analysisData.results || []);
        }

        // Effacer le formulaire après analyse réussie
        setMyObjectiveTitle('');
        setMyObjectiveDesc('');
      }
    } catch (err) {
      console.error('Erreur analyse:', err);
      alert('Erreur lors de l\'analyse. Vérifiez que le serveur Ollama est actif.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  // ============ IMPORT EXCEL POUR ANALYSE ============
  const handleImportExcel = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    
    // Vérifier l'extension
    if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
      alert('Format non supporté. Veuillez utiliser un fichier Excel (.xlsx ou .xls)');
      return;
    }
    
    setIsImporting(true);
    setImportResults(null);
    
    try {
      const result = await ApiService.importExcelForAnalysis(file);
      if (result) {
        setImportResults(result);
        // Recharger l'historique des analyses
        const analysisData = await ApiService.getManagerAnalysisResults();
        if (analysisData) {
          setAnalysisHistory(analysisData.results || []);
        }
      }
    } catch (err: any) {
      console.error('Erreur import:', err);
      alert(err.message || 'Erreur lors de l\'import du fichier Excel.');
    } finally {
      setIsImporting(false);
      // Réinitialiser l'input file
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  // ============ KPIs CALCULÉS ============
  const kpis = useMemo(() => {
    if (!teamStats) {
      return {
        totalMembers: 0,
        totalObjectives: 0,
        smartRate: null,
        avgAlignment: null,
        alertsCount: 0
      };
    }
    
    const alertsCount = teamObjectives.filter(o => 
      o.smartAnalysis?.overall === false || 
      (o.alignmentAnalysis?.alignment_score ?? 100) < 50
    ).length;
    
    return {
      totalMembers: teamStats.team_members || 0,
      totalObjectives: teamStats.total_objectives || 0,
      smartRate: teamStats.smart_rate,
      avgAlignment: teamStats.avg_alignment,
      alertsCount
    };
  }, [teamStats, teamObjectives]);

  // ============ STATISTIQUES SMART ============
  const smartStats = useMemo(() => {
    const total = teamObjectives.length;
    if (total === 0) return { total: 0, smart: 0, nonSmart: 0, pending: 0, smartRate: null, criteriaStats: { S: 0, M: 0, A: 0, R: 0, T: 0 }, byMember: [], analyzed: 0 };
    
    const analyzed = teamObjectives.filter(o => o.smartAnalysis);
    const smart = analyzed.filter(o => o.smartAnalysis?.overall === true).length;
    const nonSmart = analyzed.filter(o => o.smartAnalysis?.overall === false).length;
    const pending = teamObjectives.filter(o => !o.smartAnalysis).length;
    const smartRate = analyzed.length > 0 ? Math.round((smart / analyzed.length) * 100) : null;
    
    // Critères SMART
    const criteriaStats = { S: 0, M: 0, A: 0, R: 0, T: 0 };
    analyzed.forEach(o => {
      if (o.smartAnalysis?.S) criteriaStats.S++;
      if (o.smartAnalysis?.M) criteriaStats.M++;
      if (o.smartAnalysis?.A) criteriaStats.A++;
      if (o.smartAnalysis?.R) criteriaStats.R++;
      if (o.smartAnalysis?.T) criteriaStats.T++;
    });

    // Par collaborateur
    const byMember: { name: string; smart: number; nonSmart: number; total: number; avgAlignment: number }[] = [];
    const memberGroups = teamObjectives.reduce((acc, o) => {
      const name = o.user_name || 'Inconnu';
      if (!acc[name]) acc[name] = [];
      acc[name].push(o);
      return acc;
    }, {} as Record<string, Objective[]>);
    
    Object.entries(memberGroups).forEach(([name, objs]) => {
      const objList = objs as Objective[];
      const memberSmart = objList.filter(o => o.smartAnalysis?.overall === true).length;
      const memberNonSmart = objList.filter(o => o.smartAnalysis?.overall === false).length;
      const memberAlignments = objList.map(o => o.alignmentAnalysis?.alignment_score).filter((s): s is number => s !== undefined);
      const memberAvgAlign = memberAlignments.length > 0 ? Math.round(memberAlignments.reduce((a, b) => a + b, 0) / memberAlignments.length) : 0;
      byMember.push({ name, smart: memberSmart, nonSmart: memberNonSmart, total: objList.length, avgAlignment: memberAvgAlign });
    });
    
    return { total, smart, nonSmart, pending, smartRate, criteriaStats, byMember, analyzed: analyzed.length };
  }, [teamObjectives]);

  // ============ FILTRAGE ============
  const filteredObjectives = useMemo(() => {
    return teamObjectives.filter(o => {
      if (filterMember !== 'all' && o.user_name !== filterMember) return false;
      if (filterSmartStatus === 'smart' && o.smartAnalysis?.overall !== true) return false;
      if (filterSmartStatus === 'non-smart' && o.smartAnalysis?.overall !== false) return false;
      if (filterSmartStatus === 'pending' && o.smartAnalysis) return false;
      if (searchQuery && !o.title.toLowerCase().includes(searchQuery.toLowerCase())) return false;
      return true;
    });
  }, [teamObjectives, filterMember, filterSmartStatus, searchQuery]);

  // ============ EXPORT EXCEL/PDF ============
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  const handleExport = async (format: 'excel' | 'pdf') => {
    setIsExporting(true);
    setShowExportMenu(false);
    
    try {
      const blob = format === 'excel' 
        ? await ApiService.exportManagerExcel()
        : await ApiService.exportManagerPdf();
      
      if (blob) {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = format === 'excel' 
          ? `Rapport_Manager_${new Date().toISOString().split('T')[0]}.xlsx`
          : `Rapport_Manager_${new Date().toISOString().split('T')[0]}.pdf`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
      } else {
        alert('Erreur lors de l\'export. Vérifiez que les dépendances sont installées (openpyxl, reportlab).');
      }
    } catch (err) {
      console.error('Export error:', err);
      alert('Erreur lors de l\'export.');
    } finally {
      setIsExporting(false);
    }
  };

  // ============ AJOUT OBJECTIF STRATÉGIQUE ============
  const handleAddCompanyGoal = async () => {
    if (!newGoalTitle.trim()) return;
    
    const success = await ApiService.createCompanyObjective({
      id: `STRAT-${Date.now()}`,
      title: newGoalTitle,
      description: newGoalDesc
    });
    
    if (success) {
      await loadData();
      setNewGoalTitle('');
      setNewGoalDesc('');
    }
  };

  // ============ ANALYSE D'UN OBJECTIF (MANAGER) ============
  const handleAnalyzeObjective = async (objectiveId: string) => {
    setAnalyzingId(objectiveId);
    setError(null);
    
    try {
      const result = await ApiService.analyzeManagerObjective(objectiveId);
      
      if (result.success) {
        // Mettre à jour l'objectif dans la liste locale
        setTeamObjectives(prev => prev.map(obj => {
          if (obj.id === objectiveId) {
            return {
              ...obj,
              smartAnalysis: result.smart_analysis,
              alignmentAnalysis: result.alignment_analysis,
              status: 'analyzed'
            };
          }
          return obj;
        }));
        
        // Rafraîchir les stats
        const newStats = await ApiService.getManagerTeamStats();
        setTeamStats(newStats);
        
        // Si l'objectif est sélectionné, mettre à jour la vue détaillée
        if (selectedObjective?.id === objectiveId) {
          setSelectedObjective(prev => prev ? {
            ...prev,
            smartAnalysis: result.smart_analysis,
            alignmentAnalysis: result.alignment_analysis,
            status: 'analyzed'
          } : null);
        }
      } else {
        setError(result.error || "Erreur lors de l'analyse");
      }
    } catch (err) {
      console.error('[ManagerDashboard] Erreur analyse:', err);
      setError("Erreur lors de l'analyse de l'objectif");
    } finally {
      setAnalyzingId(null);
    }
  };

  // Données pour le graphique circulaire SMART
  const pieData = useMemo(() => {
    if (smartStats.analyzed === 0) return [];
    return [
      { name: 'SMART', value: smartStats.smart, color: '#059669' },
      { name: 'Non SMART', value: smartStats.nonSmart, color: '#f59e0b' },
      { name: 'En attente', value: smartStats.pending, color: '#94a3b8' }
    ].filter(d => d.value > 0);
  }, [smartStats]);

  // ============ ÉTATS DE CHARGEMENT ============
  if (loadingState === 'loading') {
    return (
      <div className="p-8 max-w-7xl mx-auto flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="animate-spin text-emerald-600" size={48} />
          <p className="text-slate-500 font-medium">Chargement des données d'équipe...</p>
        </div>
      </div>
    );
  }

  // ============ VUE DÉTAILLÉE ============
  if (selectedObjective) {
    return (
      <div className="p-8 max-w-7xl mx-auto space-y-8">
        <button onClick={() => setSelectedObjective(null)} className="flex items-center gap-2 text-emerald-600 font-bold hover:underline">
          <ChevronRight className="rotate-180" size={20} /> Retour
        </button>
        
        <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-100">
          <div className="flex items-center justify-between mb-6">
            <div>
              <div className="text-xs font-bold text-slate-400 uppercase mb-1">{selectedObjective.user_name || 'Collaborateur'}</div>
              <h1 className="text-2xl font-extrabold text-slate-900">{selectedObjective.title}</h1>
              <p className="text-slate-500 mt-1">{selectedObjective.description || 'Sans description'}</p>
            </div>
            <div className={`px-4 py-2 rounded-full text-sm font-bold ${
              selectedObjective.smartAnalysis?.overall ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
            }`}>
              {selectedObjective.smartAnalysis?.overall ? '✓ SMART' : '✗ NON SMART'}
            </div>
          </div>

          {/* Analyse SMART complète */}
          <div className="mt-8 space-y-6">
            <div className="bg-slate-50 p-6 rounded-xl">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-bold text-lg text-emerald-900 flex items-center gap-2">
                  Analyse S.M.A.R.T.
                  {selectedObjective.smartAnalysis?.overall ? <CheckCircle2 className="text-emerald-500" size={20} /> : <AlertCircle className="text-amber-500" size={20} />}
                </h3>
                <div className="text-sm font-medium text-slate-500">
                  Confiance: {selectedObjective.smartAnalysis?.confidence !== undefined ? `${(selectedObjective.smartAnalysis.confidence * 100).toFixed(0)}%` : 'Indisponible'}
                </div>
              </div>
              <div className="flex justify-between items-center">
                <SmartBadge letter="S" active={selectedObjective.smartAnalysis?.S || false} label="Spécifique" />
                <SmartBadge letter="M" active={selectedObjective.smartAnalysis?.M || false} label="Mesurable" />
                <SmartBadge letter="A" active={selectedObjective.smartAnalysis?.A || false} label="Atteignable" />
                <SmartBadge letter="R" active={selectedObjective.smartAnalysis?.R || false} label="Pertinent" />
                <SmartBadge letter="T" active={selectedObjective.smartAnalysis?.T || false} label="Temporel" />
              </div>
            </div>

            {/* Issues */}
            {(selectedObjective.smartAnalysis?.issues?.length || 0) > 0 && (
              <div className="bg-amber-50 p-6 rounded-xl border border-amber-100">
                <h4 className="font-bold text-amber-900 mb-3 flex items-center gap-2"><AlertCircle size={18} />Ce qui manque / À améliorer</h4>
                <div className="space-y-3">
                  {selectedObjective.smartAnalysis?.issues?.map((issue, idx) => (
                    <div key={idx} className="bg-white p-4 rounded-lg shadow-sm border border-amber-100">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="w-6 h-6 rounded-full bg-amber-500 text-white text-xs flex items-center justify-center font-bold">{issue.letter}</span>
                        <span className="font-bold text-slate-700">{issue.problem}</span>
                      </div>
                      <p className="text-sm text-slate-600 pl-8">💡 <strong>Recommandation:</strong> {issue.fix}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Alignement */}
            <div className="bg-white p-6 rounded-xl border border-slate-100 flex items-center gap-6">
              <AlignmentChart score={selectedObjective.alignmentAnalysis?.alignment_score ?? null} />
              <div className="flex-1">
                <h4 className="font-bold text-slate-800 mb-1">Alignement Stratégique</h4>
                <div className="flex gap-2 flex-wrap mt-2">
                  {selectedObjective.alignmentAnalysis?.top_matches?.map(m => (
                    <div key={m.objective_id} className="text-xs bg-emerald-50 text-emerald-700 px-3 py-2 rounded-lg border border-emerald-100">
                      <div className="font-bold">{m.objective_id}: {m.score}%</div>
                      <div className="text-emerald-600 mt-1">{m.reason}</div>
                    </div>
                  ))}
                  {(!selectedObjective.alignmentAnalysis?.top_matches?.length) && <span className="text-xs text-slate-400">Aucune correspondance</span>}
                </div>
              </div>
            </div>

            {/* Réécritures */}
            <div className="bg-white p-6 rounded-xl border border-slate-100 space-y-4">
              <h4 className="font-bold text-emerald-900">Reformulations Suggérées</h4>
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <div className="text-xs font-bold text-slate-400 uppercase mb-1">Français</div>
                  <div className="bg-slate-50 p-4 rounded-xl text-sm italic text-slate-700 border border-slate-100">
                    "{selectedObjective.smartAnalysis?.rewrite_fr || 'Indisponible'}"
                  </div>
                </div>
                <div>
                  <div className="text-xs font-bold text-slate-400 uppercase mb-1">Anglais</div>
                  <div className="bg-slate-50 p-4 rounded-xl text-sm italic text-slate-700 border border-slate-100">
                    "{selectedObjective.smartAnalysis?.rewrite_en || 'Unavailable'}"
                  </div>
                </div>
              </div>
            </div>

            {/* Synthèse managériale */}
            <div className="bg-emerald-50 p-6 rounded-xl border border-emerald-100">
              <h4 className="font-bold text-emerald-900 mb-4 flex items-center gap-2"><TrendingUp size={18} />Synthèse Managériale</h4>
              <div className="grid md:grid-cols-3 gap-4">
                <div className="bg-white p-4 rounded-xl">
                  <div className="text-xs text-slate-400 uppercase font-bold">Statut SMART</div>
                  <div className={`text-lg font-black mt-1 ${selectedObjective.smartAnalysis?.overall ? 'text-emerald-600' : 'text-amber-600'}`}>
                    {selectedObjective.smartAnalysis?.overall ? 'Conforme' : 'À améliorer'}
                  </div>
                </div>
                <div className="bg-white p-4 rounded-xl">
                  <div className="text-xs text-slate-400 uppercase font-bold">Alignement</div>
                  <div className={`text-lg font-black mt-1 ${(selectedObjective.alignmentAnalysis?.alignment_score || 0) >= 70 ? 'text-emerald-600' : 'text-amber-600'}`}>
                    {selectedObjective.alignmentAnalysis?.alignment_score !== undefined ? `${selectedObjective.alignmentAnalysis.alignment_score}%` : 'N/A'}
                  </div>
                </div>
                <div className="bg-white p-4 rounded-xl">
                  <div className="text-xs text-slate-400 uppercase font-bold">Recommandation</div>
                  <div className="text-sm font-medium mt-1 text-slate-700">
                    {selectedObjective.smartAnalysis?.overall && (selectedObjective.alignmentAnalysis?.alignment_score || 0) >= 70
                      ? '✅ Valider'
                      : '🔄 Demander révision'}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ============ VUE PRINCIPALE ============
  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <header className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-extrabold text-emerald-900 flex items-center gap-3">
            <Users size={32} />
            Tableau de Bord Manager
          </h1>
          <p className="text-slate-500">Équipe: {user.team || 'Mon équipe'}</p>
        </div>
        <button onClick={loadData} className="p-2 border border-slate-200 rounded-lg text-slate-600 hover:bg-slate-50" title="Rafraîchir">
          <RefreshCw size={18} />
        </button>
      </header>

      {error && (
        <div className="bg-red-50 border border-red-200 p-4 rounded-xl flex items-center gap-3 text-red-700">
          <AlertCircle size={20} />
          <p className="text-sm font-medium">{error}</p>
          <button onClick={() => setError(null)} className="ml-auto text-xs font-bold">Masquer</button>
        </div>
      )}

      {/* KPIs Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
          <div className="text-[10px] font-bold text-slate-400 uppercase">Collaborateurs</div>
          <div className="text-3xl font-black text-emerald-800 mt-1">{kpis.totalMembers}</div>
        </div>
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
          <div className="text-[10px] font-bold text-slate-400 uppercase">Total Objectifs</div>
          <div className="text-3xl font-black text-emerald-800 mt-1">{kpis.totalObjectives}</div>
        </div>
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
          <div className="text-[10px] font-bold text-slate-400 uppercase">Taux SMART</div>
          <div className="text-3xl font-black text-emerald-800 mt-1">
            {kpis.smartRate !== null ? `${kpis.smartRate}%` : <span className="text-slate-300 text-lg">—</span>}
          </div>
        </div>
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
          <div className="text-[10px] font-bold text-slate-400 uppercase">Alignement Moyen</div>
          <div className="text-3xl font-black text-emerald-800 mt-1">
            {kpis.avgAlignment !== null ? `${kpis.avgAlignment}%` : <span className="text-slate-300 text-lg">—</span>}
          </div>
        </div>
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
          <div className="text-[10px] font-bold text-slate-400 uppercase">Alertes</div>
          <div className={`text-3xl font-black mt-1 ${kpis.alertsCount > 0 ? 'text-amber-600' : 'text-emerald-600'}`}>
            {kpis.alertsCount}
          </div>
        </div>
      </div>

      {/* ============ SECTION TÂCHES - Vue principale ============ */}
      {activeTask === null && (
        <div className="space-y-6">
          <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
            <Play size={24} className="text-emerald-600" />
            Mes Tâches
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Tâche 1: Analyser mon objectif */}
            <div className="bg-gradient-to-br from-amber-50 to-yellow-50 border-2 border-amber-200 p-6 rounded-2xl shadow-sm hover:shadow-lg transition-all group">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 bg-amber-500 rounded-xl flex items-center justify-center shadow-md">
                  <Sparkles size={24} className="text-white" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-amber-900">Analyser mon objectif</h3>
                  <p className="text-xs text-amber-600">Analyse SMART personnelle</p>
                </div>
              </div>
              <p className="text-sm text-amber-700 mb-4">
                Saisissez votre objectif personnel et obtenez une analyse SMART détaillée avec des recommandations.
              </p>
              <div className="flex items-center justify-between">
                <span className="text-xs text-amber-500 font-medium">
                  {analysisHistory.length} analyse(s) effectuée(s)
                </span>
                <button 
                  onClick={() => setActiveTask('smart')}
                  className="px-4 py-2 bg-amber-500 text-white rounded-lg font-bold text-sm hover:bg-amber-600 transition-colors flex items-center gap-2 group-hover:scale-105"
                >
                  <Play size={16} />
                  Démarrer
                </button>
              </div>
            </div>

            {/* Tâche 2: Mon équipe */}
            <div className="bg-gradient-to-br from-emerald-50 to-teal-50 border-2 border-emerald-200 p-6 rounded-2xl shadow-sm hover:shadow-lg transition-all group">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 bg-emerald-500 rounded-xl flex items-center justify-center shadow-md">
                  <Users size={24} className="text-white" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-emerald-900">Mon équipe</h3>
                  <p className="text-xs text-emerald-600">Suivi des objectifs d'équipe</p>
                </div>
              </div>
              <p className="text-sm text-emerald-700 mb-4">
                Consultez et analysez les objectifs de votre équipe, exportez les rapports et identifiez les alertes.
              </p>
              <div className="flex items-center justify-between">
                <span className="text-xs text-emerald-500 font-medium">
                  {kpis.totalObjectives} objectif(s) · {kpis.alertsCount} alerte(s)
                </span>
                <button 
                  onClick={() => setActiveTask('team')}
                  className="px-4 py-2 bg-emerald-500 text-white rounded-lg font-bold text-sm hover:bg-emerald-600 transition-colors flex items-center gap-2 group-hover:scale-105"
                >
                  <Play size={16} />
                  Démarrer
                </button>
              </div>
            </div>

            {/* Tâche 3: Objectifs stratégiques */}
            <div className="bg-gradient-to-br from-purple-50 to-indigo-50 border-2 border-purple-200 p-6 rounded-2xl shadow-sm hover:shadow-lg transition-all group">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 bg-purple-500 rounded-xl flex items-center justify-center shadow-md">
                  <Target size={24} className="text-white" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-purple-900">Objectifs stratégiques</h3>
                  <p className="text-xs text-purple-600">Catalogue entreprise</p>
                </div>
              </div>
              <p className="text-sm text-purple-700 mb-4">
                Gérez le catalogue des objectifs stratégiques de l'entreprise pour l'alignement.
              </p>
              <div className="flex items-center justify-between">
                <span className="text-xs text-purple-500 font-medium">
                  {companyObjectives.length} objectif(s) stratégique(s)
                </span>
                <button 
                  onClick={() => setActiveTask('strategy')}
                  className="px-4 py-2 bg-purple-500 text-white rounded-lg font-bold text-sm hover:bg-purple-600 transition-colors flex items-center gap-2 group-hover:scale-105"
                >
                  <Play size={16} />
                  Démarrer
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ============ TÂCHE: Analyse SMART personnelle ============ */}
      {activeTask === 'smart' && (
        <div className="space-y-6">
          {/* Header avec bouton retour */}
          <div className="flex items-center justify-between">
            <button 
              onClick={() => setActiveTask(null)}
              className="flex items-center gap-2 text-amber-600 font-bold hover:underline"
            >
              <ChevronRight className="rotate-180" size={20} /> Retour aux tâches
            </button>
            <div className="flex items-center gap-2 bg-amber-100 text-amber-700 px-4 py-2 rounded-lg">
              <Sparkles size={18} />
              <span className="font-bold">Tâche: Analyser mon objectif</span>
            </div>
          </div>
          {/* Formulaire d'analyse */}
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
            <h3 className="font-bold text-lg text-slate-800 mb-4 flex items-center gap-2">
              <Sparkles size={20} className="text-amber-500" />
              Analyser mon objectif
            </h3>
            <p className="text-sm text-slate-500 mb-4">
              Saisissez votre objectif et obtenez une analyse SMART détaillée avec des recommandations d'amélioration.
            </p>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Titre de l'objectif *</label>
                <input
                  type="text"
                  value={myObjectiveTitle}
                  onChange={e => setMyObjectiveTitle(e.target.value)}
                  placeholder="Ex: Augmenter le chiffre d'affaires de 15% d'ici fin Q2"
                  className="w-full px-4 py-3 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Description (optionnel)</label>
                <textarea
                  value={myObjectiveDesc}
                  onChange={e => setMyObjectiveDesc(e.target.value)}
                  placeholder="Contexte, moyens, contraintes..."
                  rows={3}
                  className="w-full px-4 py-3 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
                />
              </div>
              <button
                onClick={handleAnalyzeMyObjective}
                disabled={isAnalyzing || !myObjectiveTitle.trim()}
                className="w-full bg-gradient-to-r from-emerald-600 to-teal-600 text-white px-6 py-3 rounded-lg font-bold flex items-center justify-center gap-2 hover:from-emerald-700 hover:to-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                {isAnalyzing ? (
                  <>
                    <Loader2 size={20} className="animate-spin" />
                    Analyse en cours...
                  </>
                ) : (
                  <>
                    <Sparkles size={20} />
                    Analyser mon objectif
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Section Import Excel */}
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
            <h3 className="font-bold text-lg text-slate-800 mb-4 flex items-center gap-2">
              <FileSpreadsheet size={20} className="text-emerald-500" />
              Importer des objectifs depuis Excel
            </h3>
            <p className="text-sm text-slate-500 mb-4">
              Importez un fichier Excel contenant plusieurs objectifs à analyser en lot. 
              Le fichier doit contenir une colonne <strong>"Titre"</strong> (obligatoire) et optionnellement une colonne <strong>"Description"</strong>.
            </p>
            
            <div className="flex items-center gap-4">
              <input
                ref={fileInputRef}
                type="file"
                accept=".xlsx,.xls"
                onChange={handleImportExcel}
                className="hidden"
                id="excel-import"
              />
              <label
                htmlFor="excel-import"
                className={`flex items-center gap-2 px-6 py-3 rounded-lg font-bold cursor-pointer transition-all ${
                  isImporting 
                    ? 'bg-slate-300 text-slate-600 cursor-not-allowed' 
                    : 'bg-gradient-to-r from-blue-500 to-indigo-600 text-white hover:from-blue-600 hover:to-indigo-700'
                }`}
              >
                {isImporting ? (
                  <>
                    <Loader2 size={20} className="animate-spin" />
                    Import en cours...
                  </>
                ) : (
                  <>
                    <Upload size={20} />
                    Choisir un fichier Excel
                  </>
                )}
              </label>
              
              <a
                href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,"
                download="modele_objectifs.xlsx"
                onClick={(e) => {
                  e.preventDefault();
                  // Créer un modèle simple CSV téléchargeable
                  const csvContent = "Titre,Description\nAugmenter les ventes de 20%,Objectif de développement commercial pour Q2\nRéduire les coûts opérationnels,Optimisation des processus internes";
                  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
                  const url = URL.createObjectURL(blob);
                  const link = document.createElement('a');
                  link.href = url;
                  link.download = 'modele_objectifs.csv';
                  link.click();
                }}
                className="text-sm text-blue-600 hover:underline flex items-center gap-1"
              >
                <Download size={16} />
                Télécharger un modèle
              </a>
            </div>
          </div>

          {/* Résultats de l'import Excel */}
          {importResults && (
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-blue-200">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-bold text-lg text-slate-800 flex items-center gap-2">
                  <CheckCircle2 size={20} className="text-blue-500" />
                  Résultats de l'import
                </h3>
                <button
                  onClick={() => setImportResults(null)}
                  className="text-slate-400 hover:text-slate-600"
                >
                  <X size={20} />
                </button>
              </div>
              
              {/* Informations de scan */}
              {importResults.scan_info && (
                <div className="mb-4 p-3 bg-blue-50 rounded-lg text-sm">
                  <div className="font-medium text-blue-800 mb-1">📊 Structure détectée automatiquement</div>
                  <div className="text-blue-600 space-y-1">
                    <p>• Feuille sélectionnée: <span className="font-medium">{importResults.scan_info.selected_sheet}</span></p>
                    <p>• Colonne objectifs: <span className="font-medium">{importResults.scan_info.detected_objective_column?.name}</span> (confiance: {Math.round((importResults.scan_info.detected_objective_column?.score || 0) * 100)}%)</p>
                    {importResults.scan_info.detected_description_column && (
                      <p>• Colonne descriptions: <span className="font-medium">{importResults.scan_info.detected_description_column.name}</span></p>
                    )}
                  </div>
                </div>
              )}
              
              {/* Statistiques d'extraction */}
              {importResults.extraction_info && (
                <div className="mb-4 grid grid-cols-3 gap-3">
                  <div className="p-3 bg-emerald-50 rounded-lg text-center">
                    <div className="text-2xl font-bold text-emerald-600">{importResults.extraction_info.total_extracted}</div>
                    <div className="text-xs text-emerald-700">Extraits</div>
                  </div>
                  <div className="p-3 bg-blue-50 rounded-lg text-center">
                    <div className="text-2xl font-bold text-blue-600">{importResults.extraction_info.total_analyzed}</div>
                    <div className="text-xs text-blue-700">Analysés</div>
                  </div>
                  <div className="p-3 bg-red-50 rounded-lg text-center">
                    <div className="text-2xl font-bold text-red-600">{importResults.extraction_info.total_errors}</div>
                    <div className="text-xs text-red-700">Erreurs</div>
                  </div>
                </div>
              )}
              
              {importResults.results && importResults.results.length > 0 && (
                <div className="space-y-4 max-h-[500px] overflow-y-auto">
                  {importResults.results.map((result: any, idx: number) => (
                    <div key={idx} className={`p-4 rounded-lg border ${result.success ? 'bg-slate-50 border-slate-200' : 'bg-red-50 border-red-200'}`}>
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className="text-xs bg-slate-200 text-slate-600 px-2 py-0.5 rounded">#{result.objective_id}</span>
                            <h4 className="font-semibold text-slate-800">{result.title}</h4>
                          </div>
                          {result.description && (
                            <p className="text-sm text-slate-500 mt-1">{result.description}</p>
                          )}
                        </div>
                        {result.success && (
                          <div className={`text-2xl font-bold ${
                            result.smart_score >= 80 ? 'text-emerald-600' : 
                            result.smart_score >= 60 ? 'text-yellow-600' : 'text-red-600'
                          }`}>
                            {Math.round(result.smart_score)}%
                          </div>
                        )}
                      </div>
                      
                      {result.success ? (
                        <>
                          {/* Critères SMART */}
                          <div className="flex gap-2 mb-3">
                            {['S', 'M', 'A', 'R', 'T'].map(letter => (
                              <div
                                key={letter}
                                className={`w-8 h-8 rounded flex items-center justify-center text-sm font-bold ${
                                  result[`${letter.toLowerCase()}_score`] 
                                    ? 'bg-emerald-500 text-white' 
                                    : 'bg-slate-200 text-slate-500'
                                }`}
                              >
                                {letter}
                              </div>
                            ))}
                            
                            {/* Score alignement */}
                            {result.alignment_score !== null && (
                              <div className="ml-auto flex items-center gap-2">
                                <span className={`text-sm font-medium px-2 py-1 rounded ${
                                  result.alignment_text === 'Fort' ? 'bg-purple-100 text-purple-700' :
                                  result.alignment_text === 'Moyen' ? 'bg-yellow-100 text-yellow-700' :
                                  'bg-red-100 text-red-700'
                                }`}>
                                  Alignement: {result.alignment_text} ({result.alignment_score}%)
                                </span>
                              </div>
                            )}
                          </div>
                          
                          {/* Recommandations */}
                          {result.recommendations && result.recommendations.length > 0 && (
                            <div className="mt-2 p-2 bg-amber-50 rounded text-sm">
                              <p className="font-medium text-amber-700 mb-1">💡 Recommandations:</p>
                              <ul className="list-disc list-inside text-amber-600 space-y-0.5">
                                {result.recommendations.slice(0, 2).map((rec: string, i: number) => (
                                  <li key={i}>{rec}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                          
                          {/* Reformulations */}
                          {(result.rewrite_fr || result.rewrite_en) && (
                            <div className="mt-2 p-2 bg-blue-50 rounded text-sm">
                              <p className="font-medium text-blue-700 mb-1">✨ Reformulation suggérée:</p>
                              {result.rewrite_fr && (
                                <p className="text-blue-600">🇫🇷 {result.rewrite_fr}</p>
                              )}
                            </div>
                          )}
                        </>
                      ) : (
                        <div className="text-red-600 text-sm">
                          ❌ Erreur: {result.error}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
              
              {importResults.errors && importResults.errors.length > 0 && (
                <div className="mt-4 p-4 bg-red-50 rounded-lg border border-red-200">
                  <h4 className="font-semibold text-red-700 mb-2">Erreurs ({importResults.errors.length})</h4>
                  {importResults.errors.map((err: any, idx: number) => (
                    <p key={idx} className="text-sm text-red-600">
                      Ligne {err.row}: {err.title} - {err.error}
                    </p>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Résultat de l'analyse en cours */}
          {myAnalysisResult && (
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-emerald-200">
              <h3 className="font-bold text-lg text-slate-800 mb-4 flex items-center gap-2">
                <CheckCircle2 size={20} className="text-emerald-500" />
                Résultat de l'analyse
              </h3>
              
              {/* Score SMART */}
              <div className="flex items-center gap-4 mb-6">
                <div className={`text-4xl font-bold ${myAnalysisResult.smart_score >= 80 ? 'text-emerald-600' : myAnalysisResult.smart_score >= 60 ? 'text-yellow-600' : 'text-red-600'}`}>
                  {Math.round(myAnalysisResult.smart_score)}%
                </div>
                <div>
                  <div className="text-sm font-semibold text-slate-700">Score SMART</div>
                  <div className="text-xs text-slate-500">
                    {myAnalysisResult.smart_analysis?.overall ? 'Objectif SMART validé ✓' : 'Améliorations nécessaires'}
                  </div>
                </div>
              </div>
              
              {/* Critères SMART */}
              <div className="flex gap-2 mb-6">
                {['S', 'M', 'A', 'R', 'T'].map(letter => (
                  <div
                    key={letter}
                    className={`w-12 h-12 rounded-lg flex flex-col items-center justify-center ${
                      myAnalysisResult.smart_analysis?.[letter] 
                        ? 'bg-emerald-500 text-white' 
                        : 'bg-slate-200 text-slate-500'
                    }`}
                  >
                    <span className="text-lg font-bold">{letter}</span>
                  </div>
                ))}
              </div>
              
              {/* Issues / Points d'amélioration */}
              {myAnalysisResult.smart_analysis?.issues && myAnalysisResult.smart_analysis.issues.length > 0 && (
                <div className="mb-6">
                  <h4 className="font-semibold text-slate-700 mb-2 flex items-center gap-2">
                    <AlertCircle size={16} className="text-orange-500" />
                    Points à améliorer
                  </h4>
                  <div className="space-y-2">
                    {myAnalysisResult.smart_analysis.issues.map((issue: any, idx: number) => (
                      <div key={idx} className="bg-orange-50 border border-orange-200 rounded-lg p-3">
                        <div className="flex items-start gap-2">
                          <span className="bg-orange-500 text-white text-xs font-bold px-2 py-0.5 rounded">{issue.letter}</span>
                          <div>
                            <p className="text-sm text-slate-700">{issue.problem}</p>
                            {issue.fix && (
                              <p className="text-xs text-emerald-600 mt-1">💡 {issue.fix}</p>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Reformulation suggérée */}
              {myAnalysisResult.smart_analysis?.rewrite_fr && (
                <div className="mb-6">
                  <h4 className="font-semibold text-slate-700 mb-2 flex items-center gap-2">
                    <RefreshCw size={16} className="text-blue-500" />
                    Reformulation suggérée
                  </h4>
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <p className="text-sm text-blue-800 italic">"{myAnalysisResult.smart_analysis.rewrite_fr}"</p>
                  </div>
                </div>
              )}
              
              {/* Score d'alignement */}
              {myAnalysisResult.alignment_analysis && (
                <div>
                  <h4 className="font-semibold text-slate-700 mb-2 flex items-center gap-2">
                    <Target size={16} className="text-purple-500" />
                    Alignement stratégique: {myAnalysisResult.alignment_analysis.alignment_score}%
                  </h4>
                  {myAnalysisResult.alignment_analysis.top_matches?.length > 0 && (
                    <div className="text-xs text-slate-500">
                      Aligné avec: {myAnalysisResult.alignment_analysis.top_matches.map((m: any) => m.objective_id).join(', ')}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Historique des analyses */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
            <div className="p-4 border-b border-slate-100">
              <h3 className="font-bold text-lg text-slate-800 flex items-center gap-2">
                <PieChartIcon size={20} className="text-slate-400" />
                Historique de mes analyses
                {analysisHistory.length > 0 && (
                  <span className="bg-slate-200 text-slate-600 text-xs px-2 py-0.5 rounded-full ml-2">
                    {analysisHistory.length}
                  </span>
                )}
              </h3>
            </div>
            
            {analysisHistory.length === 0 ? (
              <div className="p-8 text-center text-slate-400">
                <Sparkles size={32} className="mx-auto mb-2 opacity-50" />
                <p>Aucune analyse effectuée pour le moment.</p>
              </div>
            ) : (
              <div className="divide-y divide-slate-100 max-h-96 overflow-y-auto">
                {analysisHistory.map((item, idx) => (
                  <div 
                    key={item.id || idx} 
                    className="p-4 hover:bg-slate-50 transition-colors cursor-pointer group"
                    onClick={() => setSelectedHistoryItem(item)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="font-medium text-slate-800 group-hover:text-emerald-600 transition-colors">
                          {item.objective_title || `Analyse #${idx + 1}`}
                        </div>
                        <div className="text-xs text-slate-400 mt-1 flex items-center gap-2">
                          <span>{new Date(item.analyzed_at).toLocaleDateString('fr-FR', {
                            day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'
                          })}</span>
                          <span className="text-emerald-500 opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1">
                            <Eye size={12} /> Voir détails
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="flex gap-1">
                          {['s', 'm', 'a', 'r', 't'].map(letter => (
                            <span
                              key={letter}
                              className={`w-6 h-6 flex items-center justify-center rounded text-xs font-bold ${
                                item[`${letter}_score`] ? 'bg-emerald-500 text-white' : 'bg-slate-200 text-slate-400'
                              }`}
                            >
                              {letter.toUpperCase()}
                            </span>
                          ))}
                        </div>
                        <div className={`text-lg font-bold ${item.smart_score >= 80 ? 'text-emerald-600' : item.smart_score >= 60 ? 'text-yellow-600' : 'text-red-600'}`}>
                          {Math.round(item.smart_score)}%
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ============ TÂCHE: Mon Équipe ============ */}
      {activeTask === 'team' && (
        <div className="space-y-6">
          {/* Header avec bouton retour */}
          <div className="flex items-center justify-between">
            <button 
              onClick={() => setActiveTask(null)}
              className="flex items-center gap-2 text-emerald-600 font-bold hover:underline"
            >
              <ChevronRight className="rotate-180" size={20} /> Retour aux tâches
            </button>
            <div className="flex items-center gap-2 bg-emerald-100 text-emerald-700 px-4 py-2 rounded-lg">
              <Users size={18} />
              <span className="font-bold">Tâche: Mon équipe</span>
            </div>
          </div>
          
          {/* Actions et filtres */}
          <div className="flex flex-wrap gap-4 items-center justify-between">
            <div className="flex gap-3 items-center">
              <div className="relative">
                <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  placeholder="Rechercher..."
                  className="pl-9 pr-4 py-2 border border-slate-200 rounded-lg text-sm w-48"
                />
              </div>
              <select 
                value={filterMember} 
                onChange={e => setFilterMember(e.target.value)}
                className="px-3 py-2 border border-slate-200 rounded-lg text-sm"
              >
                <option value="all">Tous les collaborateurs</option>
                {smartStats.byMember.map(m => (
                  <option key={m.name} value={m.name}>{m.name}</option>
                ))}
              </select>
              <select 
                value={filterSmartStatus} 
                onChange={e => setFilterSmartStatus(e.target.value)}
                className="px-3 py-2 border border-slate-200 rounded-lg text-sm"
              >
                <option value="all">Tous statuts</option>
                <option value="smart">✓ SMART</option>
                <option value="non-smart">✗ Non SMART</option>
                <option value="pending">⏳ En attente</option>
              </select>
            </div>
            {/* Menu d'export avec choix Excel/PDF */}
            <div className="relative">
              <button 
                onClick={() => setShowExportMenu(!showExportMenu)}
                disabled={isExporting}
                className="px-4 py-2 bg-emerald-600 text-white rounded-lg font-bold text-sm hover:bg-emerald-700 flex items-center gap-2 disabled:opacity-50"
              >
                {isExporting ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
                Exporter
              </button>
              {showExportMenu && (
                <div className="absolute right-0 top-full mt-2 bg-white rounded-lg shadow-lg border border-slate-200 overflow-hidden z-50 min-w-[160px]">
                  <button 
                    onClick={() => handleExport('excel')}
                    className="w-full px-4 py-3 text-left text-sm hover:bg-emerald-50 flex items-center gap-2 text-slate-700"
                  >
                    <FileSpreadsheet size={16} className="text-emerald-600" />
                    Export Excel
                  </button>
                  <button 
                    onClick={() => handleExport('pdf')}
                    className="w-full px-4 py-3 text-left text-sm hover:bg-red-50 flex items-center gap-2 text-slate-700 border-t border-slate-100"
                  >
                    <FileSpreadsheet size={16} className="text-red-600" />
                    Export PDF
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* KPIs SMART */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-100 text-center">
              <div className="text-2xl font-black text-slate-800">{smartStats.total}</div>
              <div className="text-[10px] text-slate-400 uppercase font-bold">Total analysés</div>
            </div>
            <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-100 text-center">
              <div className="text-2xl font-black text-emerald-600">{smartStats.smart}</div>
              <div className="text-[10px] text-slate-400 uppercase font-bold">SMART</div>
            </div>
            <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-100 text-center">
              <div className="text-2xl font-black text-amber-600">{smartStats.nonSmart}</div>
              <div className="text-[10px] text-slate-400 uppercase font-bold">Non SMART</div>
            </div>
            <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-100 text-center">
              <div className="text-2xl font-black text-emerald-600">{smartStats.smartRate !== null ? `${smartStats.smartRate}%` : '—'}</div>
              <div className="text-[10px] text-slate-400 uppercase font-bold">Taux conformité</div>
            </div>
            <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-100 text-center">
              <div className="text-2xl font-black text-blue-600">{kpis.avgAlignment !== null ? `${kpis.avgAlignment}%` : '—'}</div>
              <div className="text-[10px] text-slate-400 uppercase font-bold">Alignement moy.</div>
            </div>
          </div>

          <div className="grid lg:grid-cols-3 gap-6">
            {/* Liste des résultats */}
            <div className="lg:col-span-2 bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
              <h3 className="font-bold text-lg text-slate-800 mb-4">
                Objectifs de l'équipe ({filteredObjectives.length})
              </h3>
              
              {filteredObjectives.length === 0 ? (
                <div className="text-center py-12 text-slate-400">
                  <AlertCircle size={48} className="mx-auto mb-4 text-slate-300" />
                  <p>Aucun objectif trouvé.</p>
                </div>
              ) : (
                <div className="space-y-3 max-h-[500px] overflow-y-auto">
                  {filteredObjectives.map(obj => (
                    <div key={obj.id} className="p-4 bg-slate-50 rounded-xl hover:bg-slate-100 transition-all">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="text-xs text-slate-400 font-bold uppercase">{obj.user_name || 'Collaborateur'}</div>
                          <div className="font-bold text-slate-800">{obj.title}</div>
                        </div>
                        <div className="flex items-center gap-3">
                          <div className={`px-2 py-1 rounded text-xs font-bold ${obj.smartAnalysis?.overall ? 'bg-emerald-100 text-emerald-700' : obj.smartAnalysis ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-500'}`}>
                            {obj.smartAnalysis?.overall ? 'SMART' : obj.smartAnalysis ? 'Non SMART' : 'En attente'}
                          </div>
                          {obj.smartAnalysis && (
                            <div className="flex gap-0.5">
                              {['S', 'M', 'A', 'R', 'T'].map(l => (
                                <span key={l} className={`w-4 h-4 rounded text-[8px] flex items-center justify-center font-bold ${obj.smartAnalysis?.[l as keyof SmartAnalysis] ? 'bg-emerald-500 text-white' : 'bg-slate-200 text-slate-400'}`}>
                                  {l}
                                </span>
                              ))}
                            </div>
                          )}
                          {/* Bouton Analyser - visible si pas encore analysé */}
                          {!obj.smartAnalysis && (
                            <button 
                              onClick={() => handleAnalyzeObjective(obj.id)} 
                              disabled={analyzingId === obj.id}
                              className="px-2 py-1 bg-amber-500 text-white rounded text-xs font-bold hover:bg-amber-600 disabled:opacity-50 flex items-center gap-1"
                              title="Lancer l'analyse SMART"
                            >
                              {analyzingId === obj.id ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />}
                              Analyser
                            </button>
                          )}
                          {/* Bouton Ré-analyser - visible si déjà analysé */}
                          {obj.smartAnalysis && (
                            <button 
                              onClick={() => handleAnalyzeObjective(obj.id)} 
                              disabled={analyzingId === obj.id}
                              className="p-1 text-slate-400 hover:text-amber-600 disabled:opacity-50"
                              title="Relancer l'analyse"
                            >
                              {analyzingId === obj.id ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                            </button>
                          )}
                          <button onClick={() => setSelectedObjective(obj)} className="text-emerald-600 hover:text-emerald-800">
                            <Eye size={16} />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Graphiques et stats */}
            <div className="space-y-6">
              {/* Camembert SMART */}
              <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
                <h3 className="font-bold text-sm text-slate-800 mb-4 flex items-center gap-2">
                  <PieChartIcon size={16} />Répartition SMART
                </h3>
                {pieData.length > 0 ? (
                  <div className="h-48">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={60} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`} labelLine={false}>
                          {pieData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Pie>
                        <Tooltip />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <div className="h-48 flex items-center justify-center text-slate-400 text-sm">
                    Aucune donnée
                  </div>
                )}
              </div>

              {/* Critères SMART */}
              <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
                <h3 className="font-bold text-sm text-slate-800 mb-4">Critères SMART</h3>
                <div className="space-y-2">
                  {Object.entries(smartStats.criteriaStats).map(([letter, count]) => {
                    const countNum = count as number;
                    const pct = smartStats.analyzed > 0 ? Math.round((countNum / smartStats.analyzed) * 100) : 0;
                    return (
                      <div key={letter} className="flex items-center gap-2">
                        <span className="w-6 h-6 rounded bg-emerald-100 text-emerald-700 text-xs font-bold flex items-center justify-center">{letter}</span>
                        <div className="flex-1 bg-slate-100 rounded-full h-3">
                          <div className="bg-emerald-500 h-3 rounded-full transition-all" style={{ width: `${pct}%` }}></div>
                        </div>
                        <span className="text-xs text-slate-500 w-10 text-right">{pct}%</span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Par collaborateur */}
              {smartStats.byMember.length > 0 && (
                <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
                  <h3 className="font-bold text-sm text-slate-800 mb-4">Par collaborateur</h3>
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {smartStats.byMember.map(m => (
                      <div key={m.name} className="flex items-center justify-between text-sm p-2 bg-slate-50 rounded-lg">
                        <span className="font-medium text-slate-700">{m.name}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-emerald-600 font-bold">{m.smart}</span>
                          <span className="text-slate-400">/</span>
                          <span className="text-slate-500">{m.total}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ============ TÂCHE: Objectifs Stratégiques ============ */}
      {activeTask === 'strategy' && (
        <div className="space-y-6">
          {/* Header avec bouton retour */}
          <div className="flex items-center justify-between">
            <button 
              onClick={() => setActiveTask(null)}
              className="flex items-center gap-2 text-purple-600 font-bold hover:underline"
            >
              <ChevronRight className="rotate-180" size={20} /> Retour aux tâches
            </button>
            <div className="flex items-center gap-2 bg-purple-100 text-purple-700 px-4 py-2 rounded-lg">
              <Target size={18} />
              <span className="font-bold">Tâche: Objectifs stratégiques</span>
            </div>
          </div>
          
          {/* Ajout objectif stratégique */}
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
            <h3 className="font-bold text-lg text-slate-800 mb-4 flex items-center gap-2"><Plus size={20} />Nouvel Objectif Stratégique</h3>
            <div className="flex gap-4">
              <input
                value={newGoalTitle}
                onChange={e => setNewGoalTitle(e.target.value)}
                className="flex-1 px-4 py-2 border border-slate-200 rounded-lg text-sm"
                placeholder="Titre de l'objectif stratégique..."
              />
              <input
                value={newGoalDesc}
                onChange={e => setNewGoalDesc(e.target.value)}
                className="flex-1 px-4 py-2 border border-slate-200 rounded-lg text-sm"
                placeholder="Description..."
              />
              <button
                onClick={handleAddCompanyGoal}
                disabled={!newGoalTitle.trim()}
                className="px-6 py-2 bg-purple-600 text-white rounded-lg font-bold hover:bg-purple-700 disabled:opacity-50"
              >
                Ajouter
              </button>
            </div>
          </div>

          {/* Liste catalogue */}
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
            <h3 className="font-bold text-lg text-slate-800 mb-4">Catalogue Stratégique ({companyObjectives.length})</h3>
            
            {companyObjectives.length === 0 ? (
              <div className="text-center py-12 text-slate-400">
                <Target size={48} className="mx-auto mb-4 text-slate-300" />
                <p>Aucun objectif stratégique défini.</p>
                <p className="text-sm">Ajoutez des objectifs ci-dessus.</p>
              </div>
            ) : (
              <div className="space-y-2">
                {companyObjectives.map(goal => (
                  <div key={goal.id} className="p-4 bg-slate-50 rounded-xl flex items-center gap-4">
                    <div className="text-xs font-mono text-slate-400 bg-slate-100 px-2 py-1 rounded">{goal.id}</div>
                    <div className="flex-1">
                      <div className="font-bold text-purple-900">{goal.title}</div>
                      <div className="text-xs text-slate-500">{goal.description || 'Pas de description'}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ============ MODAL: Détails de l'analyse historique ============ */}
      {selectedHistoryItem && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setSelectedHistoryItem(null)}>
          <div 
            className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-hidden"
            onClick={e => e.stopPropagation()}
          >
            {/* Header du modal */}
            <div className="bg-gradient-to-r from-emerald-600 to-emerald-700 text-white p-6">
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-xl font-bold">{selectedHistoryItem.objective_title || 'Analyse SMART'}</h2>
                  <p className="text-emerald-100 text-sm mt-1">
                    Analysé le {new Date(selectedHistoryItem.analyzed_at).toLocaleDateString('fr-FR', {
                      day: '2-digit', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit'
                    })}
                  </p>
                </div>
                <button 
                  onClick={() => setSelectedHistoryItem(null)}
                  className="p-2 hover:bg-white/20 rounded-lg transition-colors"
                >
                  <X size={24} />
                </button>
              </div>
              
              {/* Score et badges SMART */}
              <div className="flex items-center gap-6 mt-4">
                <div className="text-4xl font-bold">{Math.round(selectedHistoryItem.smart_score)}%</div>
                <div className="flex gap-2">
                  {['S', 'M', 'A', 'R', 'T'].map(letter => (
                    <span
                      key={letter}
                      className={`w-10 h-10 flex items-center justify-center rounded-lg text-lg font-bold ${
                        selectedHistoryItem[`${letter.toLowerCase()}_score`] 
                          ? 'bg-white text-emerald-600' 
                          : 'bg-emerald-500/30 text-emerald-200'
                      }`}
                    >
                      {letter}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* Contenu du modal */}
            <div className="p-6 overflow-y-auto max-h-[60vh]">
              {/* Analyse SMART détaillée */}
              <div className="space-y-4">
                <h3 className="font-bold text-lg text-slate-800 flex items-center gap-2">
                  <Target size={20} className="text-emerald-500" />
                  Analyse SMART détaillée
                </h3>
                
                <div className="grid gap-3">
                  {[
                    { key: 'S', label: 'Spécifique', desc: 'L\'objectif est-il clairement défini ?' },
                    { key: 'M', label: 'Mesurable', desc: 'Peut-on quantifier le résultat ?' },
                    { key: 'A', label: 'Atteignable', desc: 'L\'objectif est-il réaliste ?' },
                    { key: 'R', label: 'Réaliste', desc: 'Est-il pertinent pour l\'organisation ?' },
                    { key: 'T', label: 'Temporel', desc: 'Y a-t-il une échéance définie ?' }
                  ].map(criterion => {
                    // Utiliser smart_analysis OU les scores individuels de la BDD
                    const isValid = selectedHistoryItem.smart_analysis?.[criterion.key] || 
                                   selectedHistoryItem[`${criterion.key.toLowerCase()}_score`];
                    const explanation = selectedHistoryItem.smart_analysis?.[`${criterion.key}_explanation`] || 
                                       selectedHistoryItem.smart_analysis?.[`${criterion.key.toLowerCase()}_explanation`];
                    // Trouver le problème correspondant au critère
                    const issueForCriterion = selectedHistoryItem.smart_analysis?.issues?.find(
                      (i: any) => i.letter === criterion.key
                    );
                    return (
                      <div 
                        key={criterion.key}
                        className={`p-4 rounded-xl border ${
                          isValid 
                            ? 'bg-emerald-50 border-emerald-200' 
                            : 'bg-red-50 border-red-200'
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <span className={`w-8 h-8 flex items-center justify-center rounded-lg font-bold ${
                            isValid ? 'bg-emerald-500 text-white' : 'bg-red-500 text-white'
                          }`}>
                            {criterion.key}
                          </span>
                          <div className="flex-1">
                            <div className="font-medium text-slate-800">{criterion.label}</div>
                            <div className="text-xs text-slate-500">{criterion.desc}</div>
                          </div>
                          {isValid ? (
                            <CheckCircle2 size={24} className="text-emerald-500" />
                          ) : (
                            <AlertCircle size={24} className="text-red-500" />
                          )}
                        </div>
                        {explanation && (
                          <p className="mt-2 text-sm text-slate-600 pl-11">{explanation}</p>
                        )}
                        {!isValid && issueForCriterion && (
                          <div className="mt-2 pl-11">
                            <p className="text-sm text-red-600">{issueForCriterion.problem}</p>
                            {issueForCriterion.fix && (
                              <p className="text-sm text-emerald-600 mt-1">💡 {issueForCriterion.fix}</p>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* Problèmes détectés */}
                {selectedHistoryItem.smart_analysis?.issues && selectedHistoryItem.smart_analysis.issues.length > 0 && (
                  <div className="mt-6">
                    <h4 className="font-bold text-slate-700 mb-3 flex items-center gap-2">
                      <AlertCircle size={18} className="text-amber-500" />
                      Points d'amélioration ({selectedHistoryItem.smart_analysis.issues.length})
                    </h4>
                    <div className="space-y-2">
                      {selectedHistoryItem.smart_analysis.issues.map((issue: any, idx: number) => (
                        <div key={idx} className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                          <div className="font-medium text-amber-800">
                            <span className="font-bold text-amber-900">[{issue.letter}]</span> {issue.problem || issue}
                          </div>
                          {(issue.suggestion || issue.fix) && (
                            <div className="text-sm text-amber-600 mt-1">
                              💡 {issue.suggestion || issue.fix}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Reformulations suggérées */}
                {(selectedHistoryItem.smart_analysis?.rewrite_fr || selectedHistoryItem.smart_analysis?.rewrite_en || selectedHistoryItem.smart_analysis?.suggestion) && (
                  <div className="mt-6 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl">
                    <h4 className="font-bold text-blue-800 mb-3 flex items-center gap-2">
                      <Sparkles size={18} />
                      Reformulations suggérées
                    </h4>
                    <div className="space-y-3">
                      {selectedHistoryItem.smart_analysis?.rewrite_fr && (
                        <div className="p-3 bg-white rounded-lg border border-blue-100">
                          <div className="text-xs font-medium text-blue-500 mb-1">🇫🇷 Version française améliorée</div>
                          <p className="text-slate-800 font-medium">{selectedHistoryItem.smart_analysis.rewrite_fr}</p>
                        </div>
                      )}
                      {selectedHistoryItem.smart_analysis?.rewrite_en && (
                        <div className="p-3 bg-white rounded-lg border border-blue-100">
                          <div className="text-xs font-medium text-blue-500 mb-1">🇬🇧 English improved version</div>
                          <p className="text-slate-800 font-medium">{selectedHistoryItem.smart_analysis.rewrite_en}</p>
                        </div>
                      )}
                      {selectedHistoryItem.smart_analysis?.suggestion && !selectedHistoryItem.smart_analysis?.rewrite_fr && (
                        <div className="p-3 bg-white rounded-lg border border-blue-100">
                          <div className="text-xs font-medium text-blue-500 mb-1">💡 Suggestion</div>
                          <p className="text-slate-800">{selectedHistoryItem.smart_analysis.suggestion}</p>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Analyse d'alignement */}
              {(selectedHistoryItem.alignment_analysis || selectedHistoryItem.alignment_score > 0) && (
                <div className="mt-6 pt-6 border-t border-slate-200">
                  <h3 className="font-bold text-lg text-slate-800 flex items-center gap-2 mb-4">
                    <TrendingUp size={20} className="text-purple-500" />
                    Alignement stratégique
                  </h3>
                  
                  <div className="flex items-center gap-4 mb-4">
                    <div className="text-3xl font-bold text-purple-600">
                      {selectedHistoryItem.alignment_analysis?.alignment_score || selectedHistoryItem.alignment_score || 0}%
                    </div>
                    <div className="text-sm text-slate-500">Score d'alignement avec les objectifs stratégiques</div>
                  </div>

                  {selectedHistoryItem.alignment_analysis?.top_matches && selectedHistoryItem.alignment_analysis.top_matches.length > 0 && (
                    <div className="space-y-2">
                      <h4 className="text-sm font-medium text-slate-600">Objectifs stratégiques liés :</h4>
                      {selectedHistoryItem.alignment_analysis.top_matches.map((match: any, idx: number) => (
                        <div key={idx} className="p-3 bg-purple-50 rounded-lg flex items-center justify-between">
                          <span className="text-purple-800">{match.title || match}</span>
                          {match.score && (
                            <span className="text-sm font-bold text-purple-600">{match.score}%</span>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {selectedHistoryItem.alignment_analysis.gaps && selectedHistoryItem.alignment_analysis.gaps.length > 0 && (
                    <div className="mt-4">
                      <h4 className="text-sm font-medium text-slate-600 mb-2">Écarts identifiés :</h4>
                      <ul className="list-disc list-inside text-sm text-slate-500 space-y-1">
                        {selectedHistoryItem.alignment_analysis.gaps.map((gap: string, idx: number) => (
                          <li key={idx}>{gap}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* Message informatif si pas d'analyse JSON complète */}
              {!selectedHistoryItem.smart_analysis && (
                <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-xl text-center">
                  <p className="text-sm text-blue-600">
                    ℹ️ Les scores SMART ci-dessus sont basés sur les données enregistrées. 
                    Les détails complets (reformulations, suggestions) seront disponibles pour les prochaines analyses.
                  </p>
                </div>
              )}
            </div>

            {/* Footer du modal */}
            <div className="p-4 border-t border-slate-200 bg-slate-50 flex justify-end">
              <button
                onClick={() => setSelectedHistoryItem(null)}
                className="px-6 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 rounded-lg font-medium transition-colors"
              >
                Fermer
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ManagerDashboard;
