import React, { useState, useRef, useMemo, useEffect, useCallback } from 'react';
import { 
  ShieldCheck, Upload, Download, Search, ChevronRight, Loader2, Target, Users, BarChart3, CheckCircle2, 
  AlertCircle, TrendingUp, FileSpreadsheet, Sparkles, RefreshCw, Eye, Play, Filter, FileCheck2, History, FileWarning
} from 'lucide-react';
import { 
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, 
  ResponsiveContainer, PieChart, Pie, Cell, Legend
} from 'recharts';
import { ApiService } from '../services/apiService';
import { User, HRAnalytics, HRObjectiveDetail, HRImport, BatchAnalysisResult } from '../types';
import SmartBadge from '../components/SmartBadge';

type LoadingState = 'idle' | 'loading' | 'success' | 'error';
type View = 'dashboard' | 'details' | 'personal';

const COLORS = ['#059669', '#10b981', '#6ee7b7', '#a7f3d0'];
const PIE_COLORS = ['#059669', '#f59e0b', '#ef4444'];

interface HrDashboardProps {
  user: User;
}

const HrDashboard: React.FC<HrDashboardProps> = ({ user }) => {
  const [view, setView] = useState<View>('dashboard');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  
  // Data states
  const [analytics, setAnalytics] = useState<HRAnalytics | null>(null);
  const [objectives, setObjectives] = useState<HRObjectiveDetail[]>([]);
  const [imports, setImports] = useState<HRImport[]>([]);
  
  // Filters
  const [filters, setFilters] = useState({ entity: '', manager: '', period: '' });
  
  // Import & Analysis states
  const [stratFile, setStratFile] = useState<File | null>(null);
  const [objFile, setObjFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState<'strategy' | 'objectives' | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [lastAnalysis, setLastAnalysis] = useState<any>(null);
  const [analysisProgress, setAnalysisProgress] = useState<{ current: number; total: number; title: string }>({ current: 0, total: 0, title: '' });

  // Import Excel pour analyse personnelle
  const [isImportingPersonal, setIsImportingPersonal] = useState(false);
  const [personalImportResults, setPersonalImportResults] = useState<any>(null);
  const personalFileInputRef = useRef<HTMLInputElement>(null);
  
  // Historique des analyses personnelles du RH
  const [hrAnalysisHistory, setHrAnalysisHistory] = useState<any[]>([]);
  const [selectedHrAnalysis, setSelectedHrAnalysis] = useState<any>(null);
  
  // Formulaire d'analyse personnelle du RH
  const [hrObjectiveTitle, setHrObjectiveTitle] = useState('');
  const [hrObjectiveDesc, setHrObjectiveDesc] = useState('');
  const [isAnalyzingPersonal, setIsAnalyzingPersonal] = useState(false);
  const [hrAnalysisResult, setHrAnalysisResult] = useState<any>(null);

  // Vue détaillée d'un objectif analysé
  const [selectedHRObjective, setSelectedHRObjective] = useState<HRObjectiveDetail | null>(null);

  const stratFileInputRef = useRef<HTMLInputElement>(null);
  const objFileInputRef = useRef<HTMLInputElement>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [analyticsData, objectivesData, importsData, hrAnalysisData] = await Promise.all([
        ApiService.getHRAnalytics(filters),
        ApiService.getHRObjectivesDetails(filters),
        ApiService.getHRImports(),
        ApiService.getHRAnalysisResults()
      ]);
      setAnalytics(analyticsData);
      setObjectives(objectivesData.objectives);
      setImports(importsData);
      
      // Charger l'historique des analyses personnelles du RH
      if (hrAnalysisData) {
        setHrAnalysisHistory(hrAnalysisData.results || []);
      }
    } catch (err) {
      console.error(err);
      setError("Erreur lors de la récupération des données RH.");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleFileUpload = async (type: 'strategy' | 'objectives') => {
    const file = type === 'strategy' ? stratFile : objFile;
    if (!file) return;

    setIsUploading(type);
    setError(null);
    try {
      const result = type === 'strategy'
        ? await ApiService.importStrategyExcel(file)
        : await ApiService.importObjectivesExcel(file);

      if (result.success) {
        alert(`${result.imported} lignes importées depuis ${file.name}.`);
        if (type === 'strategy') setStratFile(null);
        if (type === 'objectives') setObjFile(null);
        await loadData();
      } else {
        throw new Error(result.error || 'Erreur inconnue');
      }
    } catch (err: any) {
      setError(`Erreur import (${type}): ${err.message}`);
    } finally {
      setIsUploading(null);
    }
  };

  const handleAnalyze = async () => {
    setIsAnalyzing(true);
    setError(null);
    setLastAnalysis(null);
    setAnalysisProgress({ current: 0, total: 0, title: '' });
    try {
      const result = await ApiService.analyzeBatch([], (progress) => {
        if (progress.type === 'start') {
          setAnalysisProgress({ current: 0, total: progress.total || 0, title: '' });
        } else if (progress.type === 'progress') {
          setAnalysisProgress({ current: progress.current || 0, total: progress.total || 0, title: progress.title || '' });
        }
      });
      if (result.success) {
        setLastAnalysis(result);
        await loadData();
      } else {
        throw new Error('L\'analyse groupée a échoué.');
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsAnalyzing(false);
      setAnalysisProgress({ current: 0, total: 0, title: '' });
    }
  };

  // ============ ANALYSE PERSONNELLE DU RH (FORMULAIRE) ============
  const handleAnalyzeHRObjective = async () => {
    if (!hrObjectiveTitle.trim()) {
      alert('Veuillez saisir un titre pour votre objectif.');
      return;
    }
    
    setIsAnalyzingPersonal(true);
    setHrAnalysisResult(null);
    
    try {
      const result = await ApiService.analyzeHRPersonalObjective(hrObjectiveTitle, hrObjectiveDesc);
      
      if (result) {
        setHrAnalysisResult(result);
        
        // Recharger l'historique depuis le serveur
        const hrAnalysisData = await ApiService.getHRAnalysisResults();
        if (hrAnalysisData) {
          setHrAnalysisHistory(hrAnalysisData.results || []);
        }

        // Effacer le formulaire après analyse réussie
        setHrObjectiveTitle('');
        setHrObjectiveDesc('');
      }
    } catch (err) {
      console.error('Erreur analyse:', err);
      setError('Erreur lors de l\'analyse de l\'objectif.');
    } finally {
      setIsAnalyzingPersonal(false);
    }
  };

  // ============ IMPORT EXCEL POUR ANALYSE PERSONNELLE ============
  const handleImportPersonalExcel = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    
    if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
      alert('Format non supporté. Veuillez utiliser un fichier Excel (.xlsx ou .xls)');
      return;
    }
    
    setIsImportingPersonal(true);
    setPersonalImportResults(null);
    setError(null);
    
    try {
      const result = await ApiService.importExcelForAnalysis(file);
      if (result) {
        setPersonalImportResults(result);
        await loadData();
      }
    } catch (err: any) {
      console.error('Erreur import:', err);
      setError(err.message || 'Erreur lors de l\'import du fichier Excel.');
    } finally {
      setIsImportingPersonal(false);
      if (personalFileInputRef.current) {
        personalFileInputRef.current.value = '';
      }
    }
  };
  
  // État pour le menu d'export
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  const handleExport = async (format: 'excel' | 'pdf') => {
    setIsExporting(true);
    setShowExportMenu(false);
    
    try {
      const blob = format === 'excel' 
        ? await ApiService.exportHRExcel(filters)
        : await ApiService.exportHRPdf(filters);
      
      if (blob) {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = format === 'excel' 
          ? `Rapport_RH_BMCI_${new Date().toISOString().split('T')[0]}.xlsx`
          : `Rapport_RH_BMCI_${new Date().toISOString().split('T')[0]}.pdf`;
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

  const renderEmptyState = () => (
    <div className="text-center py-16 bg-slate-50 rounded-2xl border-2 border-dashed border-slate-200">
      <BarChart3 size={48} className="mx-auto text-slate-300 mb-4" />
      <h3 className="text-lg font-bold text-slate-600">Aucune donnée à afficher</h3>
      <p className="text-sm text-slate-400 mt-1">Importez des fichiers pour commencer l'analyse.</p>
    </div>
  );

  const renderDashboard = () => (
    <>
      {/* Header & Actions */}
      <header className="flex flex-col md:flex-row md:items-start justify-between gap-6">
        <div>
          <h1 className="text-3xl font-extrabold text-emerald-900 flex items-center gap-3">
            <ShieldCheck size={32} />
            Module d'Analyse RH
          </h1>
          <p className="text-slate-500 mt-1">Import, analyse et visualisation des objectifs.</p>
        </div>
        <div className="flex items-start gap-2">
          {/* Menu d'export avec choix Excel/PDF */}
          <div className="relative">
            <button 
              onClick={() => setShowExportMenu(!showExportMenu)}
              disabled={isExporting}
              className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg font-bold hover:bg-emerald-700 text-sm shadow-sm disabled:opacity-50"
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
          <button onClick={loadData} className="p-3 border border-slate-200 rounded-lg text-slate-600 hover:bg-slate-50" title="Rafraîchir"><RefreshCw size={18} /></button>
        </div>
      </header>

      {error && (
        <div className="bg-red-50 border border-red-200 p-4 rounded-xl flex items-center gap-3 text-red-700">
          <AlertCircle size={20} />
          <p className="text-sm font-medium">{error}</p>
          <button onClick={() => setError(null)} className="ml-auto text-xs font-bold uppercase bg-white/50 px-2 py-1 rounded">X</button>
        </div>
      )}

      {/* Import & Analysis Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 bg-white p-6 rounded-2xl shadow-sm border border-slate-100 space-y-6">
          <h2 className="font-bold text-xl text-slate-800">1. Import des Données</h2>
          <div className="grid md:grid-cols-2 gap-6">
            {/* Strategy Import */}
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
              <h3 className="font-semibold text-emerald-800 flex items-center gap-2"><Target size={18}/>Objectifs Stratégiques</h3>
              <p className="text-xs text-slate-500 mt-1 mb-3">Importer le fichier Excel des axes directeurs de l'entreprise.</p>
              <input type="file" ref={stratFileInputRef} onChange={(e) => setStratFile(e.target.files?.[0] || null)} className="hidden" accept=".xlsx, .xls" />
              <div className="flex items-center gap-2">
                <button onClick={() => stratFileInputRef.current?.click()} className="flex-1 text-center text-xs font-bold bg-white border border-slate-300 rounded-md px-3 py-2 truncate hover:bg-slate-100">
                  {stratFile ? stratFile.name : 'Choisir un fichier...'}
                </button>
                <button onClick={() => handleFileUpload('strategy')} disabled={!stratFile || isUploading === 'strategy'} className="px-3 py-2 bg-emerald-600 text-white rounded-md font-bold hover:bg-emerald-700 disabled:opacity-50">
                  {isUploading === 'strategy' ? <Loader2 className="animate-spin" size={16}/> : <Upload size={16}/>}
                </button>
              </div>
            </div>
            {/* Objectives Import */}
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
              <h3 className="font-semibold text-emerald-800 flex items-center gap-2"><Users size={18}/>Objectifs Collaborateurs</h3>
              <p className="text-xs text-slate-500 mt-1 mb-3">Importer le fichier Excel des objectifs individuels ou d'équipe.</p>
              <input type="file" ref={objFileInputRef} onChange={(e) => setObjFile(e.target.files?.[0] || null)} className="hidden" accept=".xlsx, .xls" />
              <div className="flex items-center gap-2">
                <button onClick={() => objFileInputRef.current?.click()} className="flex-1 text-center text-xs font-bold bg-white border border-slate-300 rounded-md px-3 py-2 truncate hover:bg-slate-100">
                  {objFile ? objFile.name : 'Choisir un fichier...'}
                </button>
                <button onClick={() => handleFileUpload('objectives')} disabled={!objFile || isUploading === 'objectives'} className="px-3 py-2 bg-emerald-600 text-white rounded-md font-bold hover:bg-emerald-700 disabled:opacity-50">
                  {isUploading === 'objectives' ? <Loader2 className="animate-spin" size={16}/> : <Upload size={16}/>}
                </button>
              </div>
            </div>
          </div>
          <div className="border-t border-slate-100 pt-6 space-y-3">
            <h2 className="font-bold text-xl text-slate-800">2. Lancement de l'Analyse</h2>
            <p className="text-sm text-slate-500">
              Une fois les fichiers importés, lancez l'analyse pour calculer les scores SMART et d'alignement pour tous les nouveaux objectifs.
            </p>
            <button onClick={handleAnalyze} disabled={isAnalyzing} className="w-full flex items-center justify-center gap-3 px-4 py-3 bg-amber-500 text-white rounded-lg font-bold hover:bg-amber-600 text-base shadow-md disabled:opacity-60">
              {isAnalyzing ? <><Loader2 className="animate-spin" size={20}/>Analyse en cours...</> : <><Sparkles size={20}/>Lancer l'analyse groupée</>}
            </button>
            {isAnalyzing && analysisProgress.total > 0 && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 space-y-2">
                <div className="flex justify-between items-center text-sm font-semibold text-amber-800">
                  <span>Objectif {analysisProgress.current} / {analysisProgress.total}</span>
                  <span>{Math.round((analysisProgress.current / analysisProgress.total) * 100)}%</span>
                </div>
                <div className="w-full bg-amber-200 rounded-full h-3 overflow-hidden">
                  <div
                    className="bg-amber-500 h-3 rounded-full transition-all duration-300"
                    style={{ width: `${(analysisProgress.current / analysisProgress.total) * 100}%` }}
                  />
                </div>
                <p className="text-xs text-amber-700 truncate">En cours : {analysisProgress.title}</p>
              </div>
            )}
            {lastAnalysis && (
              <div className="bg-emerald-50 text-emerald-800 p-3 rounded-lg text-sm flex items-center gap-3 border border-emerald-200">
                <FileCheck2 size={18}/>
                Dernière analyse : {lastAnalysis.analyzed} objectifs traités avec {lastAnalysis.errors} erreurs.
              </div>
            )}
          </div>
        </div>
        {/* History Panel */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
          <h2 className="font-bold text-xl text-slate-800 mb-4 flex items-center gap-2"><History size={20}/>Historique des Imports</h2>
          <div className="space-y-3 max-h-96 overflow-y-auto pr-2">
            {imports.length > 0 ? imports.map(imp => (
              <div key={imp.id} className="bg-slate-50 p-3 rounded-lg text-xs">
                <div className="flex justify-between items-center">
                  <span className={`font-bold ${imp.import_type === 'strategy' ? 'text-purple-700' : 'text-blue-700'}`}>{imp.import_type === 'strategy' ? 'Stratégie' : 'Objectifs'}</span>
                  <span className="text-slate-400">{new Date(imp.created_at).toLocaleString('fr-FR')}</span>
                </div>
                <div className="text-slate-600 mt-1 truncate">Fichier : {imp.filename}</div>
                <div className="text-slate-500 font-semibold mt-1">{imp.records_count} lignes importées</div>
              </div>
            )) : <p className="text-sm text-slate-400 text-center py-8">Aucun import récent.</p>}
          </div>
        </div>
      </div>

      {/* Analytics Section */}
      <div className="bg-white p-6 md:p-8 rounded-2xl shadow-sm border border-slate-100">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
          <h2 className="font-bold text-xl text-slate-800">3. Tableaux de Bord Analytiques</h2>
          <div className="flex items-center gap-2 p-1 bg-slate-100 rounded-lg">
            <button onClick={() => setView('dashboard')} className={`px-4 py-1.5 text-sm font-bold rounded-md ${view === 'dashboard' ? 'bg-white shadow-sm text-emerald-700' : 'text-slate-500'}`}>
              Dashboard
            </button>
            <button onClick={() => setView('details')} className={`px-4 py-1.5 text-sm font-bold rounded-md ${view === 'details' ? 'bg-white shadow-sm text-emerald-700' : 'text-slate-500'}`}>
              Détails
            </button>
          </div>
        </div>

        {loading ? <div className="h-64 flex items-center justify-center"><Loader2 className="animate-spin text-emerald-500" size={32}/></div> : 
         !analytics || analytics.global_stats.total === 0 ? renderEmptyState() :
         view === 'dashboard' ? renderAnalyticsDashboard() : 
         renderDetailsView()
        }
      </div>
    </>
  );

  const renderAnalyticsDashboard = () => (
    <div className="space-y-8">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 p-3 bg-slate-50 rounded-xl border">
        <Filter size={16} className="text-slate-500"/>
        <span className="text-sm font-bold text-slate-600 mr-2">Filtres :</span>
        <select value={filters.entity} onChange={e => setFilters(f => ({...f, entity: e.target.value}))} className="text-sm border-slate-200 rounded-md">
          <option value="">Toutes les entités</option>
          {analytics?.filters.entities.map(e => <option key={e} value={e}>{e}</option>)}
        </select>
        <select value={filters.manager} onChange={e => setFilters(f => ({...f, manager: e.target.value}))} className="text-sm border-slate-200 rounded-md">
          <option value="">Tous les managers</option>
          {analytics?.filters.managers.map(m => <option key={m} value={m}>{m}</option>)}
        </select>
        <select value={filters.period} onChange={e => setFilters(f => ({...f, period: e.target.value}))} className="text-sm border-slate-200 rounded-md">
          <option value="">Toutes les périodes</option>
          {analytics?.filters.periods.map(p => <option key={p} value={p}>{p}</option>)}
        </select>
        <button onClick={() => setFilters({entity: '', manager: '', period: ''})} className="text-xs font-bold text-slate-500 hover:underline ml-auto">Réinitialiser</button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
        <KpiCard title="Objectifs Analysés" value={analytics?.global_stats.analyzed || 0} total={analytics?.global_stats.total} />
        <KpiCard title="Score SMART Moyen" value={analytics?.avg_scores.avg_smart} format="percent" />
        <KpiCard title="Alignement Moyen" value={analytics?.avg_scores.avg_alignment} format="percent" />
        <KpiCard title="Objectifs Validés" value={analytics?.global_stats.validated || 0} />
      </div>

      {/* Charts */}
      <div className="grid lg:grid-cols-2 gap-8">
        <ChartCard title="Évolution des Scores Mensuels">
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={analytics?.smart_evolution} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" fontSize={10} />
              <YAxis unit="%" domain={[0, 100]} fontSize={10} />
              <RechartsTooltip />
              <Legend verticalAlign="top" height={36}/>
              <Line type="monotone" dataKey="avg_smart" name="Score SMART" stroke="#059669" strokeWidth={2} />
              <Line type="monotone" dataKey="avg_alignment" name="Alignement" stroke="#f59e0b" strokeWidth={2} data={analytics?.alignment_evolution} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Top 5 Points Bloquants (Critères SMART)">
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={analytics?.blocking_points} layout="vertical" margin={{ top: 5, right: 20, left: 30, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" fontSize={10} />
              <YAxis type="category" dataKey="criteria" fontSize={10} width={80} tick={{ width: 70 }}/>
              <RechartsTooltip />
              <Bar dataKey="failures" name="Nb. d'échecs" fill="#ef4444" barSize={20} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
      <div className="grid lg:grid-cols-2 gap-8">
        <ChartCard title="Répartition Alignement Stratégique">
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={analytics?.alignment_distribution} dataKey="count" nameKey="level" cx="50%" cy="50%" outerRadius={80} labelLine={false} label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}>
                {analytics?.alignment_distribution.map((entry, index) => <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />)}
              </Pie>
              <RechartsTooltip />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Répartition Score SMART">
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={analytics?.smart_distribution} dataKey="count" nameKey="level" cx="50%" cy="50%" outerRadius={80} labelLine={false} label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}>
                {analytics?.smart_distribution.map((entry, index) => <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />)}
              </Pie>
              <RechartsTooltip />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
      
      {/* Comparison Tables */}
      <div className="grid lg:grid-cols-2 gap-8">
        <ComparisonTable title="Comparaison par Entité" data={analytics?.entity_comparison} keyName="entity" />
        <ComparisonTable title="Comparaison par Manager" data={analytics?.manager_comparison} keyName="manager" />
      </div>
    </div>
  );

  const renderDetailsView = () => (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3 p-3 bg-slate-50 rounded-xl border">
        <Filter size={16} className="text-slate-500"/>
        <span className="text-sm font-bold text-slate-600 mr-2">Filtres :</span>
        {/* Add more specific filters for details view if needed */}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b bg-slate-50 text-xs text-slate-500 uppercase">
              <th className="p-3">Collaborateur</th>
              <th className="p-3">Objectif</th>
              <th className="p-3 text-center">SMART Score</th>
              <th className="p-3 text-center">Alignement</th>
              <th className="p-3">Entité</th>
              <th className="p-3">Manager</th>
              <th className="p-3">Période</th>
              <th className="p-3 text-center">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {objectives.map(obj => (
              <tr key={obj.id} className="hover:bg-slate-50 cursor-pointer" onClick={() => setSelectedHRObjective(obj)}>
                <td className="p-3 font-semibold">{obj.user_name || 'N/A'}</td>
                <td className="p-3 max-w-xs">
                  <p className="font-bold truncate">{obj.title}</p>
                  <p className="text-xs text-slate-500 truncate">{obj.description}</p>
                </td>
                <td className="p-3 text-center font-bold">
                  <span className={obj.smart_score && obj.smart_score >= 80 ? 'text-emerald-600' : obj.smart_score && obj.smart_score >= 50 ? 'text-amber-600' : 'text-red-600'}>
                    {obj.smart_score?.toFixed(0) || 'N/A'}%
                  </span>
                </td>
                <td className="p-3 text-center font-bold">
                  <span className={obj.alignment_score && obj.alignment_score >= 80 ? 'text-emerald-600' : obj.alignment_score && obj.alignment_score >= 50 ? 'text-amber-600' : 'text-red-600'}>
                    {obj.alignment_score?.toFixed(0) || 'N/A'}%
                  </span>
                </td>
                <td className="p-3">{obj.entity || 'N/A'}</td>
                <td className="p-3">{obj.manager_name || 'N/A'}</td>
                <td className="p-3">{obj.period || 'N/A'}</td>
                <td className="p-3 text-center">
                  <button
                    onClick={(e) => { e.stopPropagation(); setSelectedHRObjective(obj); }}
                    className="p-2 text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors"
                    title="Voir les détails"
                  >
                    <Eye size={18} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );

  const renderPersonalAnalysis = () => (
    <div className="space-y-6">
      {/* Header avec titre */}
      <div className="bg-gradient-to-r from-purple-600 to-indigo-600 rounded-2xl p-6 text-white">
        <h2 className="text-2xl font-black flex items-center gap-3">
          <Sparkles size={28} />
          Mon Analyse SMART
        </h2>
        <p className="text-purple-100 mt-2">
          Saisissez votre objectif personnel et obtenez une analyse SMART détaillée avec des recommandations d'amélioration.
        </p>
      </div>

      {/* Formulaire de saisie d'objectif */}
      <div className="bg-white rounded-2xl shadow-sm border p-6">
        <h3 className="font-bold text-lg text-slate-800 mb-4 flex items-center gap-2">
          <Sparkles size={20} className="text-purple-500" />
          Analyser mon objectif
        </h3>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Titre de l'objectif *
            </label>
            <input
              type="text"
              value={hrObjectiveTitle}
              onChange={(e) => setHrObjectiveTitle(e.target.value)}
              placeholder="Ex: Optimiser le processus de recrutement pour réduire le délai d'embauche de 30%"
              className="w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Description (optionnel)
            </label>
            <textarea
              value={hrObjectiveDesc}
              onChange={(e) => setHrObjectiveDesc(e.target.value)}
              placeholder="Contexte, moyens, contraintes, indicateurs de suivi..."
              rows={3}
              className="w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-purple-500 resize-none"
            />
          </div>
          
          <button
            onClick={handleAnalyzeHRObjective}
            disabled={isAnalyzingPersonal || !hrObjectiveTitle.trim()}
            className={`w-full py-3 rounded-xl font-bold text-white flex items-center justify-center gap-2 transition-all ${
              isAnalyzingPersonal || !hrObjectiveTitle.trim()
                ? 'bg-slate-300 cursor-not-allowed'
                : 'bg-gradient-to-r from-purple-500 to-indigo-600 hover:from-purple-600 hover:to-indigo-700'
            }`}
          >
            {isAnalyzingPersonal ? (
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

      {/* Résultat de l'analyse */}
      {hrAnalysisResult && (
        <div className="bg-white rounded-2xl shadow-lg border-2 border-emerald-200 p-6">
          <h3 className="font-bold text-lg text-emerald-700 mb-4 flex items-center gap-2">
            <CheckCircle2 size={24} />
            Résultat de l'analyse
          </h3>
          
          {/* Score SMART */}
          <div className="flex items-center gap-6 mb-6">
            <div className={`text-5xl font-black ${
              hrAnalysisResult.smart_score >= 80 ? 'text-emerald-600' :
              hrAnalysisResult.smart_score >= 60 ? 'text-yellow-600' : 'text-red-600'
            }`}>
              {Math.round(hrAnalysisResult.smart_score)}%
            </div>
            <div className="flex gap-2">
              {['S', 'M', 'A', 'R', 'T'].map(letter => (
                <span
                  key={letter}
                  className={`w-10 h-10 flex items-center justify-center rounded-lg font-bold ${
                    hrAnalysisResult.smart_analysis?.[letter]
                      ? 'bg-emerald-500 text-white'
                      : 'bg-slate-200 text-slate-500'
                  }`}
                >
                  {letter}
                </span>
              ))}
            </div>
          </div>

          {/* Problèmes détectés */}
          {hrAnalysisResult.smart_analysis?.issues && hrAnalysisResult.smart_analysis.issues.length > 0 && (
            <div className="mb-6">
              <h4 className="font-bold text-slate-700 mb-3">Points d'amélioration :</h4>
              <div className="space-y-2">
                {hrAnalysisResult.smart_analysis.issues.map((issue: any, idx: number) => (
                  <div key={idx} className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                    <div className="font-semibold text-amber-800">[{issue.letter}] {issue.problem}</div>
                    {issue.fix && (
                      <div className="text-sm text-amber-600 mt-1">💡 {issue.fix}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Reformulations */}
          {(hrAnalysisResult.smart_analysis?.rewrite_fr || hrAnalysisResult.smart_analysis?.rewrite_en) && (
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl">
              <h4 className="font-bold text-blue-800 mb-2">Reformulation suggérée :</h4>
              {hrAnalysisResult.smart_analysis?.rewrite_fr && (
                <p className="text-blue-700">🇫🇷 {hrAnalysisResult.smart_analysis.rewrite_fr}</p>
              )}
              {hrAnalysisResult.smart_analysis?.rewrite_en && (
                <p className="text-blue-600 mt-2">🇬🇧 {hrAnalysisResult.smart_analysis.rewrite_en}</p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Section Import Excel pour analyse personnelle */}
      <div className="bg-gradient-to-r from-amber-50 to-orange-50 p-6 rounded-2xl border border-amber-200">
        <h3 className="font-bold text-lg text-amber-800 mb-4 flex items-center gap-2">
          <FileSpreadsheet size={20} />
          Ou importer des objectifs via Excel
        </h3>
        <p className="text-sm text-amber-700 mb-4">
          Importez un fichier Excel contenant vos propres objectifs à analyser. 
          Le fichier doit contenir une colonne <strong>"Titre"</strong> (obligatoire) et optionnellement une colonne <strong>"Description"</strong>.
        </p>
        
        <div className="flex items-center gap-4">
          <input
            ref={personalFileInputRef}
            type="file"
            accept=".xlsx,.xls"
            onChange={handleImportPersonalExcel}
            className="hidden"
            id="personal-excel-import"
          />
          <label
            htmlFor="personal-excel-import"
            className={`flex items-center gap-2 px-6 py-3 rounded-lg font-bold cursor-pointer transition-all ${
              isImportingPersonal 
                ? 'bg-slate-300 text-slate-600 cursor-not-allowed' 
                : 'bg-gradient-to-r from-amber-500 to-orange-600 text-white hover:from-amber-600 hover:to-orange-700'
            }`}
          >
            {isImportingPersonal ? (
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
              const csvContent = "Titre,Description\nAméliorer les performances RH,Objectif stratégique pour Q2\nOptimiser le recrutement,Réduire le délai de recrutement de 20%";
              const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
              const url = URL.createObjectURL(blob);
              const link = document.createElement('a');
              link.href = url;
              link.download = 'modele_objectifs_rh.csv';
              link.click();
            }}
            className="text-sm text-amber-600 hover:underline flex items-center gap-1"
          >
            <Download size={16} />
            Télécharger un modèle
          </a>
        </div>
      </div>

      {/* Résultats de l'import */}
      {personalImportResults && (
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-emerald-200">
          <h3 className="font-bold text-lg text-slate-800 mb-4 flex items-center gap-2">
            <CheckCircle2 size={20} className="text-emerald-500" />
            Résultats de l'import ({personalImportResults.total_processed} objectif(s) analysé(s))
          </h3>
          
          {personalImportResults.results && personalImportResults.results.length > 0 && (
            <div className="space-y-4 max-h-[500px] overflow-y-auto">
              {personalImportResults.results.map((result: any, idx: number) => (
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
                  <div className="flex gap-2 mb-3">
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
                  
                  {/* Alignement */}
                  {result.alignment_analysis && (
                    <div className="text-xs text-slate-600">
                      Alignement stratégique: <span className="font-bold">{result.alignment_analysis.alignment_score?.toFixed(0) || 0}%</span>
                    </div>
                  )}
                  
                  {/* Problèmes identifiés */}
                  {result.smart_analysis?.issues && result.smart_analysis.issues.length > 0 && (
                    <div className="mt-2">
                      <p className="text-xs text-red-600 font-medium">
                        ⚠️ {result.smart_analysis.issues.length} amélioration(s) suggérée(s)
                      </p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
          
          {personalImportResults.errors && personalImportResults.errors.length > 0 && (
            <div className="mt-4 p-4 bg-red-50 rounded-lg border border-red-200">
              <h4 className="font-semibold text-red-700 mb-2">Erreurs ({personalImportResults.errors.length})</h4>
              {personalImportResults.errors.map((err: any, idx: number) => (
                <p key={idx} className="text-sm text-red-600">
                  Ligne {err.row}: {err.title} - {err.error}
                </p>
              ))}
            </div>
          )}
          
          <button
            onClick={() => setPersonalImportResults(null)}
            className="mt-4 text-sm text-slate-500 hover:text-slate-700"
          >
            Fermer les résultats
          </button>
        </div>
      )}
      
      {!personalImportResults && (
        <div className="bg-white rounded-2xl shadow-sm border overflow-hidden">
          <div className="p-4 bg-gradient-to-r from-slate-50 to-slate-100 border-b flex items-center justify-between">
            <h3 className="font-bold text-lg text-slate-800 flex items-center gap-2">
              <History size={20} className="text-slate-400" />
              Historique de mes analyses
              {hrAnalysisHistory.length > 0 && (
                <span className="bg-slate-200 text-slate-600 text-xs px-2 py-0.5 rounded-full ml-2">
                  {hrAnalysisHistory.length}
                </span>
              )}
            </h3>
          </div>
          
          {hrAnalysisHistory.length === 0 ? (
            <div className="p-8 text-center text-slate-400">
              <Sparkles size={32} className="mx-auto mb-2 opacity-50" />
              <p>Aucune analyse effectuée pour le moment.</p>
              <p className="text-sm mt-1">Importez un fichier Excel ci-dessus pour commencer.</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-100 max-h-96 overflow-y-auto">
              {hrAnalysisHistory.map((item, idx) => (
                <div 
                  key={item.id || idx} 
                  className="p-4 hover:bg-slate-50 transition-colors cursor-pointer group"
                  onClick={() => setSelectedHrAnalysis(item)}
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
                        {['s', 'm', 'a', 'r', 't'].map(letter => {
                          const isValid = item.smart_analysis?.[letter.toUpperCase()] || item[`${letter}_score`];
                          return (
                            <span
                              key={letter}
                              className={`w-6 h-6 flex items-center justify-center rounded text-xs font-bold ${
                                isValid ? 'bg-emerald-500 text-white' : 'bg-slate-200 text-slate-400'
                              }`}
                            >
                              {letter.toUpperCase()}
                            </span>
                          );
                        })}
                      </div>
                      <div className={`text-lg font-bold ${
                        item.smart_score >= 80 ? 'text-emerald-600' : 
                        item.smart_score >= 60 ? 'text-yellow-600' : 'text-red-600'
                      }`}>
                        {Math.round(item.smart_score || 0)}%
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );

  // Modal de détail d'une analyse personnelle du RH
  const renderHrAnalysisDetailModal = () => {
    if (!selectedHrAnalysis) return null;
    
    const item = selectedHrAnalysis;
    
    // Parser les analyses JSON
    let smartAnalysis: any = null;
    let alignmentAnalysis: any = null;
    
    try {
      smartAnalysis = typeof item.smart_analysis === 'string' 
        ? JSON.parse(item.smart_analysis || '{}') 
        : (item.smart_analysis || {});
    } catch (e) {
      smartAnalysis = {};
    }
    
    try {
      alignmentAnalysis = typeof item.alignment_analysis === 'string' 
        ? JSON.parse(item.alignment_analysis || '{}') 
        : (item.alignment_analysis || {});
    } catch (e) {
      alignmentAnalysis = {};
    }
    
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setSelectedHrAnalysis(null)}>
        <div className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-hidden" onClick={e => e.stopPropagation()}>
          {/* Header */}
          <div className="sticky top-0 bg-gradient-to-r from-amber-500 to-orange-600 p-6 text-white">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold">{item.objective_title || 'Analyse personnelle'}</h2>
                <p className="text-amber-100 text-sm mt-1">
                  Analysé le {new Date(item.analyzed_at).toLocaleDateString('fr-FR', {
                    day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'
                  })}
                </p>
              </div>
              <button
                onClick={() => setSelectedHrAnalysis(null)}
                className="p-2 text-white/80 hover:text-white hover:bg-white/20 rounded-lg"
              >
                <ChevronRight size={24} className="rotate-180" />
              </button>
            </div>
            
            {/* Score header */}
            <div className="mt-4 flex items-center gap-6">
              <div className="text-4xl font-bold">{Math.round(item.smart_score || 0)}%</div>
              <div className="flex gap-1">
                {['S', 'M', 'A', 'R', 'T'].map(letter => {
                  const isValid = smartAnalysis?.[letter] || item[`${letter.toLowerCase()}_score`];
                  return (
                    <span
                      key={letter}
                      className={`w-8 h-8 flex items-center justify-center rounded font-bold ${
                        isValid ? 'bg-white text-amber-600' : 'bg-white/30 text-white'
                      }`}
                    >
                      {letter}
                    </span>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Contenu du modal */}
          <div className="p-6 overflow-y-auto max-h-[60vh]">
            {/* Description si présente */}
            {item.description && (
              <div className="mb-6 p-4 bg-slate-50 rounded-xl">
                <h3 className="font-bold text-slate-700 mb-2">Description</h3>
                <p className="text-slate-600">{item.description}</p>
              </div>
            )}
            
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
                  const isValid = smartAnalysis?.[criterion.key] || item[`${criterion.key.toLowerCase()}_score`];
                  const explanation = smartAnalysis?.[`${criterion.key}_explanation`] || smartAnalysis?.[`${criterion.key.toLowerCase()}_explanation`];
                  const issueForCriterion = smartAnalysis?.issues?.find((i: any) => i.letter === criterion.key);
                  
                  return (
                    <div 
                      key={criterion.key}
                      className={`p-4 rounded-xl border ${
                        isValid ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200'
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

              {/* Problèmes détectés globaux */}
              {smartAnalysis?.issues && smartAnalysis.issues.length > 0 && (
                <div className="mt-6">
                  <h4 className="font-bold text-slate-700 mb-3 flex items-center gap-2">
                    <AlertCircle size={18} className="text-amber-500" />
                    Points d'amélioration ({smartAnalysis.issues.length})
                  </h4>
                  <div className="space-y-2">
                    {smartAnalysis.issues.map((issue: any, idx: number) => (
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
              {(smartAnalysis?.rewrite_fr || smartAnalysis?.rewrite_en || smartAnalysis?.suggestion) && (
                <div className="mt-6 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl">
                  <h4 className="font-bold text-blue-800 mb-3 flex items-center gap-2">
                    <Sparkles size={18} />
                    Reformulations suggérées
                  </h4>
                  <div className="space-y-3">
                    {smartAnalysis?.rewrite_fr && (
                      <div className="p-3 bg-white rounded-lg border border-blue-100">
                        <div className="text-xs font-medium text-blue-500 mb-1">🇫🇷 Version française améliorée</div>
                        <p className="text-slate-800 font-medium">{smartAnalysis.rewrite_fr}</p>
                      </div>
                    )}
                    {smartAnalysis?.rewrite_en && (
                      <div className="p-3 bg-white rounded-lg border border-blue-100">
                        <div className="text-xs font-medium text-blue-500 mb-1">🇬🇧 English improved version</div>
                        <p className="text-slate-800 font-medium">{smartAnalysis.rewrite_en}</p>
                      </div>
                    )}
                    {smartAnalysis?.suggestion && !smartAnalysis?.rewrite_fr && (
                      <div className="p-3 bg-white rounded-lg border border-blue-100">
                        <div className="text-xs font-medium text-blue-500 mb-1">💡 Suggestion</div>
                        <p className="text-slate-800">{smartAnalysis.suggestion}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Analyse d'alignement */}
            {(alignmentAnalysis || (item.alignment_score && item.alignment_score > 0)) && (
              <div className="mt-6 pt-6 border-t border-slate-200">
                <h3 className="font-bold text-lg text-slate-800 flex items-center gap-2 mb-4">
                  <TrendingUp size={20} className="text-purple-500" />
                  Alignement stratégique
                </h3>
                
                <div className="flex items-center gap-4 mb-4">
                  <div className="text-3xl font-bold text-purple-600">
                    {alignmentAnalysis?.alignment_score || item.alignment_score || 0}%
                  </div>
                  <div className="text-sm text-slate-500">Score d'alignement avec les objectifs stratégiques</div>
                </div>

                {alignmentAnalysis?.top_matches && alignmentAnalysis.top_matches.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="text-sm font-medium text-slate-600">Objectifs stratégiques liés :</h4>
                    {alignmentAnalysis.top_matches.map((match: any, idx: number) => (
                      <div key={idx} className="p-3 bg-purple-50 rounded-lg flex items-center justify-between">
                        <span className="text-purple-800">{match.title || match.objective_id || match}</span>
                        {match.score && (
                          <span className="text-sm font-bold text-purple-600">{match.score}%</span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Message informatif si pas d'analyse JSON complète */}
            {!smartAnalysis?.issues && !Object.keys(smartAnalysis || {}).some(k => ['S', 'M', 'A', 'R', 'T'].includes(k)) && (
              <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-xl text-center">
                <p className="text-sm text-blue-600">
                  ℹ️ Les scores SMART ci-dessus sont basés sur les données enregistrées. 
                  Les détails complets seront disponibles pour les prochaines analyses.
                </p>
              </div>
            )}
          </div>

          {/* Footer du modal */}
          <div className="p-4 border-t border-slate-200 bg-slate-50 flex justify-end">
            <button
              onClick={() => setSelectedHrAnalysis(null)}
              className="px-6 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 rounded-lg font-medium transition-colors"
            >
              Fermer
            </button>
          </div>
        </div>
      </div>
    );
  };

  // Modal de détail d'un objectif RH
  const renderObjectiveDetailModal = () => {
    if (!selectedHRObjective) return null;
    
    const obj = selectedHRObjective;
    
    // Parser les analyses JSON
    let smartAnalysis: any = null;
    let alignmentAnalysis: any = null;
    
    try {
      smartAnalysis = typeof obj.smart_analysis === 'string' 
        ? JSON.parse(obj.smart_analysis || '{}') 
        : (obj.smart_analysis || {});
    } catch (e) {
      console.error('Erreur parsing smart_analysis:', e);
      smartAnalysis = {};
    }
    
    try {
      alignmentAnalysis = typeof obj.alignment_analysis === 'string' 
        ? JSON.parse(obj.alignment_analysis || '{}') 
        : (obj.alignment_analysis || {});
    } catch (e) {
      console.error('Erreur parsing alignment_analysis:', e);
      alignmentAnalysis = {};
    }
    
    // Extraire les reformulations depuis smartAnalysis
    const rewriteFr = smartAnalysis?.rewrite_fr || obj.rewrite_fr;
    const rewriteEn = smartAnalysis?.rewrite_en || obj.rewrite_en;
    
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
          {/* Header */}
          <div className="sticky top-0 bg-gradient-to-r from-emerald-600 to-teal-600 p-6 rounded-t-2xl">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-white">{obj.title}</h2>
                <p className="text-emerald-100 text-sm mt-1">
                  {obj.user_name || 'Collaborateur'} • {obj.entity || 'Entité N/A'} • {obj.period || 'Période N/A'}
                </p>
              </div>
              <button
                onClick={() => setSelectedHRObjective(null)}
                className="p-2 text-white/80 hover:text-white hover:bg-white/20 rounded-lg transition-colors"
              >
                <ChevronRight size={24} className="rotate-180" />
              </button>
            </div>
          </div>
          
          <div className="p-6 space-y-6">
            {/* Description */}
            {obj.description && (
              <div className="bg-slate-50 p-4 rounded-xl">
                <h3 className="font-bold text-slate-700 mb-2">Description</h3>
                <p className="text-slate-600">{obj.description}</p>
              </div>
            )}
            
            {/* Scores */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-emerald-50 p-4 rounded-xl text-center">
                <div className="text-3xl font-black text-emerald-600">{obj.smart_score?.toFixed(0) || 0}%</div>
                <div className="text-sm text-emerald-700 font-medium">Score SMART</div>
              </div>
              <div className="bg-amber-50 p-4 rounded-xl text-center">
                <div className="text-3xl font-black text-amber-600">{obj.alignment_score?.toFixed(0) || 0}%</div>
                <div className="text-sm text-amber-700 font-medium">Score Alignement</div>
              </div>
            </div>
            
            {/* Critères SMART */}
            <div className="bg-white border rounded-xl p-4">
              <h3 className="font-bold text-slate-800 mb-4 flex items-center gap-2">
                <Target size={20} className="text-emerald-600" />
                Critères SMART - Analyse détaillée
              </h3>
              
              {/* Grille des 5 critères avec détails */}
              <div className="space-y-3">
                {[
                  { key: 'S', label: 'Spécifique', desc: 'L\'objectif est-il clairement défini ?' },
                  { key: 'M', label: 'Mesurable', desc: 'Peut-on quantifier le résultat ?' },
                  { key: 'A', label: 'Atteignable', desc: 'L\'objectif est-il réaliste ?' },
                  { key: 'R', label: 'Réaliste', desc: 'Est-il pertinent pour l\'organisation ?' },
                  { key: 'T', label: 'Temporel', desc: 'Y a-t-il une échéance définie ?' }
                ].map(criterion => {
                  const isValid = smartAnalysis?.[criterion.key] || obj[`${criterion.key.toLowerCase()}_score` as keyof typeof obj];
                  const explanation = smartAnalysis?.[`${criterion.key}_explanation`] || smartAnalysis?.[`${criterion.key.toLowerCase()}_explanation`];
                  const issueForCriterion = smartAnalysis?.issues?.find((i: any) => i.letter === criterion.key);
                  
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
                        <span className={`w-10 h-10 flex items-center justify-center rounded-lg text-lg font-bold ${
                          isValid ? 'bg-emerald-500 text-white' : 'bg-red-500 text-white'
                        }`}>
                          {criterion.key}
                        </span>
                        <div className="flex-1">
                          <div className="font-semibold text-slate-800">{criterion.label}</div>
                          <div className="text-xs text-slate-500">{criterion.desc}</div>
                        </div>
                        {isValid ? (
                          <CheckCircle2 size={24} className="text-emerald-500" />
                        ) : (
                          <AlertCircle size={24} className="text-red-500" />
                        )}
                      </div>
                      {explanation && (
                        <p className="mt-2 text-sm text-slate-600 pl-13 ml-13">{explanation}</p>
                      )}
                      {!isValid && issueForCriterion && (
                        <div className="mt-2 ml-13 pl-13">
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
              
              {/* Message si pas d'analyse détaillée */}
              {!smartAnalysis?.issues && !Object.keys(smartAnalysis || {}).some(k => ['S', 'M', 'A', 'R', 'T'].includes(k)) && (
                <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-xl text-center">
                  <p className="text-sm text-blue-600">
                    ℹ️ Les scores SMART ci-dessus sont basés sur les données enregistrées. 
                    Les détails complets seront disponibles pour les prochaines analyses.
                  </p>
                </div>
              )}
            </div>
            
            {/* Alignement stratégique */}
            {alignmentAnalysis && (
              <div className="bg-white border rounded-xl p-4">
                <h3 className="font-bold text-slate-800 mb-4 flex items-center gap-2">
                  <TrendingUp size={20} className="text-amber-600" />
                  Alignement Stratégique
                </h3>
                
                {alignmentAnalysis.top_matches && alignmentAnalysis.top_matches.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="font-semibold text-slate-700 text-sm">Objectifs stratégiques alignés :</h4>
                    {alignmentAnalysis.top_matches.map((match: any, idx: number) => (
                      <div key={idx} className="bg-emerald-50 border border-emerald-100 rounded-lg p-3">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-emerald-700">{match.objective_id}</span>
                          <span className="bg-emerald-500 text-white text-xs px-2 py-1 rounded-full font-bold">
                            {match.score}%
                          </span>
                        </div>
                        {match.reason && <p className="text-emerald-600 text-sm mt-1">{match.reason}</p>}
                      </div>
                    ))}
                  </div>
                )}
                
                {alignmentAnalysis.gaps && alignmentAnalysis.gaps.length > 0 && (
                  <div className="mt-4 space-y-2">
                    <h4 className="font-semibold text-slate-700 text-sm">Points d'amélioration :</h4>
                    {alignmentAnalysis.gaps.map((gap: string, idx: number) => (
                      <div key={idx} className="bg-amber-50 border border-amber-100 rounded-lg p-3 text-amber-700 text-sm">
                        ⚠️ {gap}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
            
            {/* Reformulations suggérées */}
            {(rewriteFr || rewriteEn) && (
              <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-100 rounded-xl p-4">
                <h3 className="font-bold text-blue-800 mb-4 flex items-center gap-2">
                  <Sparkles size={20} />
                  Reformulations Suggérées
                </h3>
                {rewriteFr && (
                  <div className="mb-3">
                    <h4 className="font-semibold text-blue-700 text-sm mb-1">🇫🇷 Français :</h4>
                    <p className="bg-white p-3 rounded-lg text-slate-700 border">{rewriteFr}</p>
                  </div>
                )}
                {rewriteEn && (
                  <div>
                    <h4 className="font-semibold text-blue-700 text-sm mb-1">🇬🇧 English :</h4>
                    <p className="bg-white p-3 rounded-lg text-slate-700 border">{rewriteEn}</p>
                  </div>
                )}
              </div>
            )}
            
            {/* Métadonnées */}
            <div className="bg-slate-50 rounded-xl p-4">
              <h3 className="font-bold text-slate-700 mb-3">Informations</h3>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-slate-500">Manager :</span>
                  <span className="ml-2 font-medium">{obj.manager_name || 'N/A'}</span>
                </div>
                <div>
                  <span className="text-slate-500">Entité :</span>
                  <span className="ml-2 font-medium">{obj.entity || 'N/A'}</span>
                </div>
                <div>
                  <span className="text-slate-500">Période :</span>
                  <span className="ml-2 font-medium">{obj.period || 'N/A'}</span>
                </div>
                <div>
                  <span className="text-slate-500">Analysé le :</span>
                  <span className="ml-2 font-medium">
                    {obj.analyzed_at ? new Date(obj.analyzed_at).toLocaleDateString('fr-FR', {
                      day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'
                    }) : 'N/A'}
                  </span>
                </div>
              </div>
            </div>
          </div>
          
          {/* Footer */}
          <div className="sticky bottom-0 bg-slate-50 p-4 rounded-b-2xl border-t flex justify-end">
            <button
              onClick={() => setSelectedHRObjective(null)}
              className="px-6 py-2 bg-emerald-600 text-white rounded-lg font-bold hover:bg-emerald-700 transition-colors"
            >
              Fermer
            </button>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-8">
      {renderObjectiveDetailModal()}
      {renderHrAnalysisDetailModal()}
      {renderDashboard()}
    </div>
  );
};

// --- Sub-components ---

const KpiCard: React.FC<{ title: string; value?: number | null; total?: number; format?: 'percent' | 'number' }> = ({ title, value, total, format = 'number' }) => {
  const displayValue = value !== undefined && value !== null ? 
    (format === 'percent' ? `${value.toFixed(0)}%` : value.toLocaleString('fr-FR')) : 
    'N/A';
  
  const totalDisplay = total !== undefined ? ` / ${total.toLocaleString('fr-FR')}` : '';

  return (
    <div className="bg-slate-50/50 p-4 rounded-xl border">
      <p className="text-xs font-bold text-slate-500 uppercase">{title}</p>
      <p className="text-3xl font-black text-emerald-800 mt-1">{displayValue}{totalDisplay}</p>
    </div>
  );
};

const ChartCard: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
  <div className="bg-slate-50/50 p-6 rounded-xl border h-full">
    <h3 className="font-bold text-slate-800 mb-4">{title}</h3>
    {children}
  </div>
);

const ComparisonTable: React.FC<{ title: string; data?: any[]; keyName: string }> = ({ title, data, keyName }) => (
  <div className="bg-slate-50/50 p-6 rounded-xl border">
    <h3 className="font-bold text-slate-800 mb-4">{title}</h3>
    <div className="max-h-60 overflow-y-auto">
      <table className="w-full text-sm text-left">
        <thead>
          <tr className="text-xs text-slate-500 border-b">
            <th className="pb-2">{keyName.charAt(0).toUpperCase() + keyName.slice(1)}</th>
            <th className="pb-2 text-center">SMART</th>
            <th className="pb-2 text-center">Alignement</th>
            <th className="pb-2 text-center">Nb Obj.</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200">
          {data?.map((item, i) => (
            <tr key={i}>
              <td className="py-2 font-semibold truncate max-w-xs">{item[keyName]}</td>
              <td className="py-2 text-center font-bold text-emerald-700">{item.avg_smart?.toFixed(0)}%</td>
              <td className="py-2 text-center font-bold text-amber-700">{item.avg_alignment?.toFixed(0)}%</td>
              <td className="py-2 text-center text-slate-500">{item.count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </div>
);

export default HrDashboard;
