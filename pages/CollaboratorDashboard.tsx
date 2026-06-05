import React, { useState, useRef, useEffect } from 'react';
import { ApiService } from '../services/apiService';
import { Objective, SmartAnalysis, AlignmentAnalysis, CompanyObjective, User } from '../types';
import SmartBadge from '../components/SmartBadge';
import AlignmentChart from '../components/AlignmentChart';
import { Plus, Copy, CheckCircle2, AlertCircle, Sparkles, ChevronRight, Target, Loader2, Upload, FileText, RefreshCw, Trash2, FileSpreadsheet, Download } from 'lucide-react';

type LoadingState = 'idle' | 'loading' | 'success' | 'error';

interface CollaboratorDashboardProps {
  user: User;
}

const CollaboratorDashboard: React.FC<CollaboratorDashboardProps> = ({ user }) => {
  const [activeTab, setActiveTab] = useState<'manual' | 'import' | 'excel'>('manual');
  const [title, setTitle] = useState('');
  const [desc, setDesc] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // États persistés via API
  const [objectives, setObjectives] = useState<Objective[]>([]);
  const [companyObjectives, setCompanyObjectives] = useState<CompanyObjective[]>([]);
  const [loadingState, setLoadingState] = useState<LoadingState>('loading');
  
  // Historique des analyses
  const [analysisHistory, setAnalysisHistory] = useState<any[]>([]);
  const [analysisStats, setAnalysisStats] = useState<any>(null);
  
  // Vue détaillée
  const [selectedObjective, setSelectedObjective] = useState<Objective | null>(null);
  
  // Import Excel pour analyse personnelle
  const [isImportingExcel, setIsImportingExcel] = useState(false);
  const [excelImportResults, setExcelImportResults] = useState<any>(null);
  const excelFileInputRef = useRef<HTMLInputElement>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ============ CHARGEMENT INITIAL DEPUIS L'API ============
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoadingState('loading');
      
      const [fetchedObjectives, fetchedCompanyObjectives, analysisData] = await Promise.all([
        ApiService.getObjectives(),
        ApiService.getCompanyObjectives(),
        ApiService.getCollabAnalysisResults()
      ]);
      
      setObjectives(fetchedObjectives);
      setCompanyObjectives(fetchedCompanyObjectives);
      
      // Charger l'historique des analyses du collaborateur
      if (analysisData) {
        setAnalysisHistory(analysisData.results || []);
        setAnalysisStats(analysisData.stats || null);
      }
      
      setLoadingState('success');
      
      console.log('[CollaboratorDashboard] Données chargées:', {
        objectives: fetchedObjectives.length,
        companyObjectives: fetchedCompanyObjectives.length,
        analysisHistory: analysisData?.results?.length || 0
      });
    } catch (err) {
      console.error('[CollaboratorDashboard] Erreur chargement:', err);
      setLoadingState('error');
      setError('Erreur lors du chargement des données.');
    }
  };

  // ============ ANALYSE MANUELLE ============
  const handleAnalyze = async () => {
    if (!title) return;
    setIsAnalyzing(true);
    setError(null);
    
    try {
      // 1. Créer l'objectif via API
      const newObj = await ApiService.createObjective(title, desc);
      if (!newObj) throw new Error("Erreur lors de la création.");
      
      // 2. Analyser SMART
      const smartResult = await ApiService.analyzeSmartObjective(title, desc);
      
      // 3. Analyser alignement si catalogue disponible
      const alignmentResult = companyObjectives.length > 0 
        ? await ApiService.analyzeAlignment(title, companyObjectives)
        : { alignment_score: 0, top_matches: [], gaps: ['Aucun catalogue stratégique défini'] };
      
      // 4. Mettre à jour l'objectif avec les analyses
      await ApiService.updateObjective(newObj.id, {
        status: 'analyzed',
        smart_analysis: smartResult || undefined,
        alignment_analysis: alignmentResult || undefined
      });
      
      // 5. Rafraîchir la liste
      await loadData();
      
      setTitle('');
      setDesc('');
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Erreur lors de l'analyse.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  // ============ SUPPRESSION ============
  const handleDelete = async (id: string) => {
    if (!confirm('Supprimer cet objectif ?')) return;
    
    const success = await ApiService.deleteObjective(id);
    if (success) {
      setObjectives(prev => prev.filter(o => o.id !== id));
      if (selectedObjective?.id === id) setSelectedObjective(null);
    }
  };

  // ============ MISE À JOUR PROGRESS ============
  const handleProgressChange = async (id: string, progress: string) => {
    const success = await ApiService.updateObjective(id, { progress });
    if (success) {
      setObjectives(prev => prev.map(o => o.id === id ? { ...o, progress: progress as any } : o));
    }
  };

  // ============ IMPORT FICHIER ============
  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    
    setIsUploading(true);
    setError(null);
    
    try {
      const text = await file.text();
      const lines = text.split('\n').filter(l => l.trim());
      const headers = lines[0].split(',').map(h => h.trim().toLowerCase());
      
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
          const alignmentResult = companyObjectives.length > 0
            ? await ApiService.analyzeAlignment(objTitle, companyObjectives)
            : null;
          
          await ApiService.updateObjective(newObj.id, {
            status: 'analyzed',
            smart_analysis: smartResult || undefined,
            alignment_analysis: alignmentResult || undefined
          });
        }
      }
      
      await loadData();
      alert(`Import terminé.`);
    } catch (err: any) {
      console.error(err);
      setError("Erreur lors de l'import.");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // ============ IMPORT EXCEL POUR ANALYSE PERSONNELLE ============
  const handleExcelImport = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    
    if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
      alert('Format non supporté. Veuillez utiliser un fichier Excel (.xlsx ou .xls)');
      return;
    }
    
    setIsImportingExcel(true);
    setExcelImportResults(null);
    setError(null);
    
    try {
      const result = await ApiService.importExcelForAnalysis(file);
      if (result) {
        setExcelImportResults(result);
        await loadData();
      }
    } catch (err: any) {
      console.error('Erreur import Excel:', err);
      setError(err.message || 'Erreur lors de l\'import du fichier Excel.');
    } finally {
      setIsImportingExcel(false);
      if (excelFileInputRef.current) {
        excelFileInputRef.current.value = '';
      }
    }
  };

  // ============ COPY TO CLIPBOARD ============
  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  // ============ ÉTATS DE CHARGEMENT ============
  if (loadingState === 'loading') {
    return (
      <div className="p-8 max-w-6xl mx-auto flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="animate-spin text-emerald-600" size={48} />
          <p className="text-slate-500 font-medium">Chargement de vos objectifs...</p>
        </div>
      </div>
    );
  }

  // ============ VUE DÉTAILLÉE ============
  if (selectedObjective) {
    return (
      <div className="p-8 max-w-6xl mx-auto space-y-8">
        <button onClick={() => setSelectedObjective(null)} className="flex items-center gap-2 text-emerald-600 font-bold hover:underline">
          <ChevronRight className="rotate-180" size={20} /> Retour à mes objectifs
        </button>
        
        <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-100">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-2xl font-extrabold text-slate-900">{selectedObjective.title}</h1>
              <p className="text-slate-500 mt-1">{selectedObjective.description || 'Sans description'}</p>
            </div>
            <select
              value={selectedObjective.progress}
              onChange={(e) => handleProgressChange(selectedObjective.id, e.target.value)}
              className="px-4 py-2 border border-slate-200 rounded-lg text-sm"
            >
              <option value="not_started">Non démarré</option>
              <option value="in_progress">En cours</option>
              <option value="completed">Atteint</option>
              <option value="on_hold">En pause</option>
            </select>
          </div>

          {/* Analyse SMART */}
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
                <h4 className="font-bold text-amber-900 mb-3 flex items-center gap-2"><AlertCircle size={18} />Points d'amélioration</h4>
                <div className="space-y-3">
                  {selectedObjective.smartAnalysis?.issues?.map((issue, idx) => (
                    <div key={idx} className="bg-white p-3 rounded-lg shadow-sm border border-amber-100">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="w-5 h-5 rounded-full bg-amber-500 text-white text-[10px] flex items-center justify-center font-bold">{issue.letter}</span>
                        <span className="text-xs font-bold text-slate-700">{issue.problem}</span>
                      </div>
                      <p className="text-xs text-slate-500 pl-7">💡 {issue.fix}</p>
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
              <h4 className="font-bold text-emerald-900">Réécritures Suggérées</h4>
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-xs font-bold text-slate-400 uppercase">Français</span>
                    <button onClick={() => copyToClipboard(selectedObjective.smartAnalysis?.rewrite_fr || '')} className="text-slate-400 hover:text-emerald-600"><Copy size={14} /></button>
                  </div>
                  <div className="bg-slate-50 p-4 rounded-xl text-sm italic text-slate-700 border border-slate-100">
                    "{selectedObjective.smartAnalysis?.rewrite_fr || 'Indisponible'}"
                  </div>
                </div>
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-xs font-bold text-slate-400 uppercase">Anglais</span>
                    <button onClick={() => copyToClipboard(selectedObjective.smartAnalysis?.rewrite_en || '')} className="text-slate-400 hover:text-emerald-600"><Copy size={14} /></button>
                  </div>
                  <div className="bg-slate-50 p-4 rounded-xl text-sm italic text-slate-700 border border-slate-100">
                    "{selectedObjective.smartAnalysis?.rewrite_en || 'Unavailable'}"
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
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      <header className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-extrabold text-emerald-900 flex items-center gap-3">
            <Target size={32} />
            Mes Objectifs
          </h1>
          <p className="text-slate-500">Bienvenue, {user.name}</p>
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

      {/* Tabs */}
      <div className="flex gap-1 bg-slate-100 p-1 rounded-xl w-fit">
        <button onClick={() => setActiveTab('manual')} className={`px-6 py-2 rounded-lg text-sm font-bold transition-all ${activeTab === 'manual' ? 'bg-white shadow-sm text-emerald-700' : 'text-slate-500'}`}>
          <Plus size={16} className="inline mr-2" />Saisie Manuelle
        </button>
        <button onClick={() => setActiveTab('import')} className={`px-6 py-2 rounded-lg text-sm font-bold transition-all ${activeTab === 'import' ? 'bg-white shadow-sm text-emerald-700' : 'text-slate-500'}`}>
          <Upload size={16} className="inline mr-2" />Import CSV
        </button>
        <button onClick={() => setActiveTab('excel')} className={`px-6 py-2 rounded-lg text-sm font-bold transition-all ${activeTab === 'excel' ? 'bg-white shadow-sm text-amber-700' : 'text-slate-500'}`}>
          <FileSpreadsheet size={16} className="inline mr-2" />Import Excel
        </button>
      </div>

      {/* Manual Input */}
      {activeTab === 'manual' && (
        <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-100">
          <h2 className="font-bold text-lg text-slate-800 mb-6 flex items-center gap-2">
            <Sparkles className="text-emerald-500" size={20} />
            Nouvel Objectif
          </h2>
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase mb-2">Titre de l'objectif</label>
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500"
                placeholder="Ex: Augmenter le taux de satisfaction client de 15% d'ici Q4 2026"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase mb-2">Description (optionnel)</label>
              <textarea
                value={desc}
                onChange={(e) => setDesc(e.target.value)}
                className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 min-h-[100px]"
                placeholder="Contexte, KPIs, actions prévues..."
              />
            </div>
            <button
              onClick={handleAnalyze}
              disabled={isAnalyzing || !title}
              className="w-full bg-emerald-600 text-white py-3 rounded-xl font-bold hover:bg-emerald-700 disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isAnalyzing ? <><Loader2 className="animate-spin" size={18} />Analyse en cours...</> : <><Sparkles size={18} />Analyser</>}
            </button>
          </div>
        </div>
      )}

      {/* Import CSV */}
      {activeTab === 'import' && (
        <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-100">
          <h2 className="font-bold text-lg text-slate-800 mb-4 flex items-center gap-2">
            <FileText className="text-emerald-500" size={20} />
            Importer depuis un fichier CSV
          </h2>
          <p className="text-sm text-slate-500 mb-6">Format attendu : title, description (une ligne par objectif)</p>
          <input type="file" ref={fileInputRef} onChange={handleFileUpload} className="hidden" accept=".csv" />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            className="px-6 py-3 border-2 border-dashed border-emerald-300 rounded-xl text-emerald-700 font-bold hover:bg-emerald-50 w-full flex items-center justify-center gap-2"
          >
            {isUploading ? <><Loader2 className="animate-spin" size={18} />Import en cours...</> : <><Upload size={18} />Sélectionner un fichier</>}
          </button>
        </div>
      )}

      {/* Import Excel */}
      {activeTab === 'excel' && (
        <div className="space-y-6">
          <div className="bg-gradient-to-r from-amber-50 to-orange-50 p-6 rounded-2xl border border-amber-200">
            <h2 className="font-bold text-lg text-amber-800 mb-4 flex items-center gap-2">
              <FileSpreadsheet size={20} />
              Importer des objectifs depuis Excel
            </h2>
            <p className="text-sm text-amber-700 mb-4">
              Importez un fichier Excel contenant vos objectifs à analyser en lot.
              Le fichier doit contenir une colonne <strong>"Titre"</strong> (obligatoire) et optionnellement une colonne <strong>"Description"</strong>.
            </p>
            
            <div className="flex items-center gap-4 flex-wrap">
              <input
                ref={excelFileInputRef}
                type="file"
                accept=".xlsx,.xls"
                onChange={handleExcelImport}
                className="hidden"
                id="collab-excel-import"
              />
              <label
                htmlFor="collab-excel-import"
                className={`flex items-center gap-2 px-6 py-3 rounded-lg font-bold cursor-pointer transition-all ${
                  isImportingExcel 
                    ? 'bg-slate-300 text-slate-600 cursor-not-allowed' 
                    : 'bg-gradient-to-r from-amber-500 to-orange-600 text-white hover:from-amber-600 hover:to-orange-700'
                }`}
              >
                {isImportingExcel ? (
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
                href="#"
                onClick={(e) => {
                  e.preventDefault();
                  const csvContent = "Titre,Description\nAugmenter mes ventes de 10%,Objectif personnel pour Q2\nAméliorer ma productivité,Réduire les temps de traitement";
                  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
                  const url = URL.createObjectURL(blob);
                  const link = document.createElement('a');
                  link.href = url;
                  link.download = 'modele_objectifs.csv';
                  link.click();
                }}
                className="text-sm text-amber-600 hover:underline flex items-center gap-1"
              >
                <Download size={16} />
                Télécharger un modèle
              </a>
            </div>
          </div>

          {/* Résultats de l'import Excel */}
          {excelImportResults && (
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-emerald-200">
              <h3 className="font-bold text-lg text-slate-800 mb-4 flex items-center gap-2">
                <CheckCircle2 size={20} className="text-emerald-500" />
                Résultats de l'import ({excelImportResults.total_processed} objectif(s) analysé(s))
              </h3>
              
              {excelImportResults.results && excelImportResults.results.length > 0 && (
                <div className="space-y-4 max-h-[400px] overflow-y-auto">
                  {excelImportResults.results.map((result: any, idx: number) => (
                    <div key={idx} className="p-4 bg-slate-50 rounded-lg border border-slate-200">
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex-1">
                          <h4 className="font-semibold text-slate-800">{result.title}</h4>
                          {result.description && (
                            <p className="text-sm text-slate-500 mt-1">{result.description}</p>
                          )}
                        </div>
                        <div className={`text-2xl font-bold ml-4 ${
                          result.smart_score >= 80 ? 'text-emerald-600' : 
                          result.smart_score >= 60 ? 'text-yellow-600' : 'text-red-600'
                        }`}>
                          {Math.round(result.smart_score)}%
                        </div>
                      </div>
                      
                      {/* Critères SMART */}
                      <div className="flex gap-2">
                        {['S', 'M', 'A', 'R', 'T'].map(letter => (
                          <div
                            key={letter}
                            className={`w-8 h-8 rounded flex items-center justify-center text-sm font-bold ${
                              result.smart_analysis?.[letter] 
                                ? 'bg-emerald-500 text-white' 
                                : 'bg-slate-200 text-slate-500'
                            }`}
                          >
                            {letter}
                          </div>
                        ))}
                      </div>
                      
                      {result.smart_analysis?.issues && result.smart_analysis.issues.length > 0 && (
                        <p className="text-xs text-red-600 font-medium mt-2">
                          ⚠️ {result.smart_analysis.issues.length} amélioration(s) suggérée(s)
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
              
              {excelImportResults.errors && excelImportResults.errors.length > 0 && (
                <div className="mt-4 p-4 bg-red-50 rounded-lg border border-red-200">
                  <h4 className="font-semibold text-red-700 mb-2">Erreurs ({excelImportResults.errors.length})</h4>
                  {excelImportResults.errors.map((err: any, idx: number) => (
                    <p key={idx} className="text-sm text-red-600">
                      Ligne {err.row}: {err.title} - {err.error}
                    </p>
                  ))}
                </div>
              )}
              
              <button
                onClick={() => setExcelImportResults(null)}
                className="mt-4 text-sm text-slate-500 hover:text-slate-700"
              >
                Fermer les résultats
              </button>
            </div>
          )}
        </div>
      )}

      {/* Liste des objectifs analysés */}
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
        <h3 className="font-bold text-lg text-slate-800 mb-4">
          Historique ({analysisHistory.length + objectives.length})
        </h3>
        
        {analysisHistory.length === 0 && objectives.length === 0 ? (
          <div className="text-center py-12 text-slate-400">
            <Target size={48} className="mx-auto mb-4 text-slate-300" />
            <p>Aucun objectif pour le moment.</p>
            <p className="text-sm">Créez votre premier objectif ci-dessus.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {/* Analyses depuis la base de données (Excel imports) */}
            {analysisHistory.map((item, idx) => (
              <div key={item.id || `analysis-${idx}`} className="p-4 bg-emerald-50 rounded-xl hover:bg-emerald-100 transition-all flex items-center justify-between">
                <div className="flex-1">
                  <div className="font-bold text-slate-800">{item.objective_title || `Analyse #${idx + 1}`}</div>
                  <div className="text-xs text-slate-500 mt-1">
                    {item.analyzed_at ? new Date(item.analyzed_at).toLocaleDateString('fr-FR', {
                      day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'
                    }) : 'Date inconnue'}
                  </div>
                </div>
                <div className="flex items-center gap-4">
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
                  {item.smart_score !== undefined && (
                    <div className={`text-lg font-bold ${item.smart_score >= 80 ? 'text-emerald-600' : item.smart_score >= 60 ? 'text-yellow-600' : 'text-red-600'}`}>
                      {Math.round(item.smart_score)}%
                    </div>
                  )}
                </div>
              </div>
            ))}
            
            {/* Objectifs créés manuellement */}
            {objectives.map(obj => (
              <div key={obj.id} className="p-4 bg-slate-50 rounded-xl hover:bg-slate-100 transition-all flex items-center justify-between">
                <div className="flex-1">
                  <div className="font-bold text-slate-800">{obj.title}</div>
                  <div className="text-xs text-slate-500 mt-1">{new Date(obj.createdAt).toLocaleDateString('fr-FR')}</div>
                </div>
                <div className="flex items-center gap-4">
                  {obj.smartAnalysis && (
                    <div className="flex gap-1">
                      {['S', 'M', 'A', 'R', 'T'].map(l => (
                        <span key={l} className={`w-6 h-6 rounded-full text-[10px] flex items-center justify-center font-bold ${obj.smartAnalysis?.[l as keyof SmartAnalysis] ? 'bg-emerald-500 text-white' : 'bg-slate-200 text-slate-400'}`}>
                          {l}
                        </span>
                      ))}
                    </div>
                  )}
                  <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase ${
                    obj.progress === 'completed' ? 'bg-emerald-100 text-emerald-700' :
                    obj.progress === 'in_progress' ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-400'
                  }`}>
                    {obj.progress.replace('_', ' ')}
                  </span>
                  <button onClick={() => setSelectedObjective(obj)} className="text-emerald-600 hover:text-emerald-800">
                    <ChevronRight size={20} />
                  </button>
                  <button onClick={() => handleDelete(obj.id)} className="text-red-400 hover:text-red-600">
                    <Trash2 size={18} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default CollaboratorDashboard;
