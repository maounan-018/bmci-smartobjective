import { useState, useEffect } from "react";
import { ApiService } from "../services/apiService";
import {
  Sparkles,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Target,
  RefreshCw,
  PieChart as PieChartIcon,
  X,
  Eye
} from "lucide-react";
const SmartAnalysisPage = ({ user }) => {
  const [myObjectiveTitle, setMyObjectiveTitle] = useState("");
  const [myObjectiveDesc, setMyObjectiveDesc] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [myAnalysisResult, setMyAnalysisResult] = useState(null);
  const [analysisHistory, setAnalysisHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [selectedHistoryItem, setSelectedHistoryItem] = useState(null);
  useEffect(() => {
    loadHistory();
  }, []);
  const loadHistory = async () => {
    try {
      setLoadingHistory(true);
      const data = await ApiService.getHRAnalysisResults();
      if (data) {
        setAnalysisHistory(data.results || []);
      }
    } catch (err) {
      console.error("Erreur chargement historique:", err);
    } finally {
      setLoadingHistory(false);
    }
  };
  const handleAnalyzeMyObjective = async () => {
    if (!myObjectiveTitle.trim()) {
      alert("Veuillez saisir un titre pour votre objectif.");
      return;
    }
    setIsAnalyzing(true);
    setMyAnalysisResult(null);
    try {
      const result = await ApiService.analyzeHRPersonalObjective(myObjectiveTitle, myObjectiveDesc);
      if (result) {
        setMyAnalysisResult(result);
        await loadHistory();
      }
    } catch (err) {
      console.error("Erreur analyse:", err);
      alert("Erreur lors de l'analyse. V\xE9rifiez que le serveur Ollama est actif.");
    } finally {
      setIsAnalyzing(false);
    }
  };
  return <div className="p-6 max-w-5xl mx-auto space-y-6">
      {
    /* Header */
  }
      <div className="bg-gradient-to-r from-purple-600 to-indigo-600 rounded-2xl p-6 text-white">
        <div className="flex items-center gap-3 mb-2">
          <Sparkles size={28} />
          <h1 className="text-2xl font-bold">Mon Analyse SMART</h1>
        </div>
        <p className="text-purple-100">
          Saisissez votre objectif personnel et obtenez une analyse SMART détaillée avec des recommandations d'amélioration.
        </p>
      </div>

      {
    /* Formulaire d'analyse */
  }
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
        <h3 className="font-bold text-lg text-slate-800 mb-4 flex items-center gap-2">
          <Sparkles size={20} className="text-amber-500" />
          Analyser mon objectif
        </h3>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Titre de l'objectif *</label>
            <input
    type="text"
    value={myObjectiveTitle}
    onChange={(e) => setMyObjectiveTitle(e.target.value)}
    placeholder="Ex: Optimiser le processus de recrutement pour réduire le délai d'embauche de 30%"
    className="w-full px-4 py-3 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
  />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Description (optionnel)</label>
            <textarea
    value={myObjectiveDesc}
    onChange={(e) => setMyObjectiveDesc(e.target.value)}
    placeholder="Contexte, moyens, contraintes, indicateurs de suivi..."
    rows={3}
    className="w-full px-4 py-3 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
  />
          </div>
          <button
    onClick={handleAnalyzeMyObjective}
    disabled={isAnalyzing || !myObjectiveTitle.trim()}
    className="w-full bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-6 py-3 rounded-lg font-bold flex items-center justify-center gap-2 hover:from-purple-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
  >
            {isAnalyzing ? <>
                <Loader2 size={20} className="animate-spin" />
                Analyse en cours...
              </> : <>
                <Sparkles size={20} />
                Analyser mon objectif
              </>}
          </button>
        </div>
      </div>

      {
    /* Résultat de l'analyse en cours */
  }
      {myAnalysisResult && <div className="bg-white p-6 rounded-2xl shadow-sm border border-purple-200">
          <h3 className="font-bold text-lg text-slate-800 mb-4 flex items-center gap-2">
            <CheckCircle2 size={20} className="text-purple-500" />
            Résultat de l'analyse
          </h3>
          
          {
    /* Score SMART */
  }
          <div className="flex items-center gap-4 mb-6">
            <div className={`text-4xl font-bold ${myAnalysisResult.smart_score >= 80 ? "text-emerald-600" : myAnalysisResult.smart_score >= 60 ? "text-yellow-600" : "text-red-600"}`}>
              {Math.round(myAnalysisResult.smart_score)}%
            </div>
            <div>
              <div className="text-sm font-semibold text-slate-700">Score SMART</div>
              <div className="text-xs text-slate-500">
                {myAnalysisResult.smart_analysis?.overall ? "Objectif SMART valid\xE9 \u2713" : "Am\xE9liorations n\xE9cessaires"}
              </div>
            </div>
          </div>
          
          {
    /* Critères SMART */
  }
          <div className="flex gap-2 mb-6">
            {["S", "M", "A", "R", "T"].map((letter) => <div
    key={letter}
    className={`w-12 h-12 rounded-lg flex flex-col items-center justify-center ${myAnalysisResult.smart_analysis?.[letter] ? "bg-purple-500 text-white" : "bg-slate-200 text-slate-500"}`}
  >
                <span className="text-lg font-bold">{letter}</span>
              </div>)}
          </div>
          
          {
    /* Issues / Points d'amélioration */
  }
          {myAnalysisResult.smart_analysis?.issues && myAnalysisResult.smart_analysis.issues.length > 0 && <div className="mb-6">
              <h4 className="font-semibold text-slate-700 mb-2 flex items-center gap-2">
                <AlertCircle size={16} className="text-orange-500" />
                Points à améliorer
              </h4>
              <div className="space-y-2">
                {myAnalysisResult.smart_analysis.issues.map((issue, idx) => <div key={idx} className="bg-orange-50 border border-orange-200 rounded-lg p-3">
                    <div className="flex items-start gap-2">
                      <span className="bg-orange-500 text-white text-xs font-bold px-2 py-0.5 rounded">{issue.letter}</span>
                      <div>
                        <p className="text-sm text-slate-700">{issue.problem}</p>
                        {issue.fix && <p className="text-xs text-purple-600 mt-1">💡 {issue.fix}</p>}
                      </div>
                    </div>
                  </div>)}
              </div>
            </div>}
          
          {
    /* Reformulations suggérées */
  }
          {(myAnalysisResult.smart_analysis?.rewrite_fr || myAnalysisResult.smart_analysis?.rewrite_en) && <div className="mb-6">
              <h4 className="font-semibold text-slate-700 mb-2 flex items-center gap-2">
                <RefreshCw size={16} className="text-blue-500" />
                Reformulations suggérées
              </h4>
              <div className="space-y-3">
                {myAnalysisResult.smart_analysis.rewrite_fr && <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-lg">🇫🇷</span>
                      <span className="text-xs font-bold text-blue-700 uppercase">Français</span>
                    </div>
                    <p className="text-sm text-blue-800 italic">"{myAnalysisResult.smart_analysis.rewrite_fr}"</p>
                  </div>}
                {myAnalysisResult.smart_analysis.rewrite_en && <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-lg">🇬🇧</span>
                      <span className="text-xs font-bold text-indigo-700 uppercase">English</span>
                    </div>
                    <p className="text-sm text-indigo-800 italic">"{myAnalysisResult.smart_analysis.rewrite_en}"</p>
                  </div>}
              </div>
            </div>}
          
          {
    /* Score d'alignement */
  }
          {myAnalysisResult.alignment_analysis && <div>
              <h4 className="font-semibold text-slate-700 mb-2 flex items-center gap-2">
                <Target size={16} className="text-purple-500" />
                Alignement stratégique: {myAnalysisResult.alignment_analysis.alignment_score}%
              </h4>
              {myAnalysisResult.alignment_analysis.top_matches?.length > 0 && <div className="text-xs text-slate-500">
                  Aligné avec: {myAnalysisResult.alignment_analysis.top_matches.map((m) => m.objective_id).join(", ")}
                </div>}
            </div>}
        </div>}

      {
    /* Historique des analyses */
  }
      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
        <div className="p-4 border-b border-slate-100">
          <h3 className="font-bold text-lg text-slate-800 flex items-center gap-2">
            <PieChartIcon size={20} className="text-slate-400" />
            Historique de mes analyses
            {analysisHistory.length > 0 && <span className="bg-purple-100 text-purple-600 text-xs px-2 py-0.5 rounded-full ml-2">
                {analysisHistory.length}
              </span>}
          </h3>
        </div>
        
        {loadingHistory ? <div className="p-8 text-center text-slate-400">
            <Loader2 size={32} className="mx-auto mb-2 animate-spin" />
            <p>Chargement...</p>
          </div> : analysisHistory.length === 0 ? <div className="p-8 text-center text-slate-400">
            <Sparkles size={32} className="mx-auto mb-2 opacity-50" />
            <p>Aucune analyse effectuée pour le moment.</p>
          </div> : <div className="divide-y divide-slate-100 max-h-96 overflow-y-auto">
            {analysisHistory.map((item, idx) => <div
    key={item.id || idx}
    className="p-4 hover:bg-slate-50 transition-colors cursor-pointer"
    onClick={() => setSelectedHistoryItem(item)}
  >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="font-medium text-slate-800">
                      {item.objective_title || `Analyse #${idx + 1}`}
                    </div>
                    <div className="text-xs text-slate-400 mt-1">
                      {new Date(item.analyzed_at).toLocaleDateString("fr-FR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  })}
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="flex gap-1">
                      {["s", "m", "a", "r", "t"].map((letter) => <span
    key={letter}
    className={`w-6 h-6 flex items-center justify-center rounded text-xs font-bold ${item[`${letter}_score`] ? "bg-purple-500 text-white" : "bg-slate-200 text-slate-400"}`}
  >
                          {letter.toUpperCase()}
                        </span>)}
                    </div>
                    <div className={`text-lg font-bold ${item.smart_score >= 80 ? "text-emerald-600" : item.smart_score >= 60 ? "text-yellow-600" : "text-red-600"}`}>
                      {Math.round(item.smart_score)}%
                    </div>
                    <Eye size={18} className="text-slate-400" />
                  </div>
                </div>
              </div>)}
          </div>}
      </div>

      {
    /* Modal de détails */
  }
      {selectedHistoryItem && <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-slate-100 flex items-center justify-between sticky top-0 bg-white">
              <h3 className="font-bold text-lg text-slate-800">Détails de l'analyse</h3>
              <button onClick={() => setSelectedHistoryItem(null)} className="p-2 hover:bg-slate-100 rounded-lg">
                <X size={20} />
              </button>
            </div>
            
            <div className="p-6 space-y-6">
              {
    /* Titre de l'objectif */
  }
              <div>
                <h4 className="text-sm font-semibold text-slate-500 mb-1">Objectif analysé</h4>
                <p className="text-slate-800 font-medium">{selectedHistoryItem.objective_title || "Sans titre"}</p>
              </div>
              
              {
    /* Score SMART */
  }
              <div className="flex items-center gap-4">
                <div className={`text-4xl font-bold ${selectedHistoryItem.smart_score >= 80 ? "text-emerald-600" : selectedHistoryItem.smart_score >= 60 ? "text-yellow-600" : "text-red-600"}`}>
                  {Math.round(selectedHistoryItem.smart_score)}%
                </div>
                <div>
                  <div className="text-sm font-semibold text-slate-700">Score SMART</div>
                  <div className="text-xs text-slate-500">
                    {selectedHistoryItem.smart_score >= 80 ? "Objectif SMART valid\xE9 \u2713" : "Am\xE9liorations n\xE9cessaires"}
                  </div>
                </div>
              </div>
              
              {
    /* Critères SMART */
  }
              <div>
                <h4 className="text-sm font-semibold text-slate-500 mb-2">Critères SMART</h4>
                <div className="flex gap-2">
                  {["S", "M", "A", "R", "T"].map((letter) => <div
    key={letter}
    className={`w-12 h-12 rounded-lg flex flex-col items-center justify-center ${selectedHistoryItem[`${letter.toLowerCase()}_score`] ? "bg-purple-500 text-white" : "bg-slate-200 text-slate-500"}`}
  >
                      <span className="text-lg font-bold">{letter}</span>
                    </div>)}
                </div>
              </div>
              
              {
    /* Points d'amélioration */
  }
              {selectedHistoryItem.smart_analysis?.issues && selectedHistoryItem.smart_analysis.issues.length > 0 && <div>
                  <h4 className="font-semibold text-slate-700 mb-2 flex items-center gap-2">
                    <AlertCircle size={16} className="text-orange-500" />
                    Points à améliorer
                  </h4>
                  <div className="space-y-2">
                    {selectedHistoryItem.smart_analysis.issues.map((issue, idx) => <div key={idx} className="bg-orange-50 border border-orange-200 rounded-lg p-3">
                        <div className="flex items-start gap-2">
                          <span className="bg-orange-500 text-white text-xs font-bold px-2 py-0.5 rounded">{issue.letter}</span>
                          <div>
                            <p className="text-sm text-slate-700">{issue.problem}</p>
                            {issue.fix && <p className="text-xs text-purple-600 mt-1">💡 {issue.fix}</p>}
                          </div>
                        </div>
                      </div>)}
                  </div>
                </div>}
              
              {
    /* Reformulation suggérée */
  }
              {(selectedHistoryItem.smart_analysis?.rewrite_fr || selectedHistoryItem.smart_analysis?.rewrite_en) && <div>
                  <h4 className="font-semibold text-slate-700 mb-2 flex items-center gap-2">
                    <RefreshCw size={16} className="text-blue-500" />
                    Reformulations suggérées
                  </h4>
                  <div className="space-y-3">
                    {selectedHistoryItem.smart_analysis.rewrite_fr && <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-lg">🇫🇷</span>
                          <span className="text-xs font-bold text-blue-700 uppercase">Français</span>
                        </div>
                        <p className="text-sm text-blue-800 italic">"{selectedHistoryItem.smart_analysis.rewrite_fr}"</p>
                      </div>}
                    {selectedHistoryItem.smart_analysis.rewrite_en && <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-4">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-lg">🇬🇧</span>
                          <span className="text-xs font-bold text-indigo-700 uppercase">English</span>
                        </div>
                        <p className="text-sm text-indigo-800 italic">"{selectedHistoryItem.smart_analysis.rewrite_en}"</p>
                      </div>}
                  </div>
                </div>}
              
              {
    /* Score d'alignement */
  }
              {selectedHistoryItem.alignment_analysis && <div>
                  <h4 className="font-semibold text-slate-700 mb-2 flex items-center gap-2">
                    <Target size={16} className="text-purple-500" />
                    Alignement stratégique: {selectedHistoryItem.alignment_analysis.alignment_score}%
                  </h4>
                  {selectedHistoryItem.alignment_analysis.top_matches?.length > 0 && <div className="text-xs text-slate-500">
                      Aligné avec: {selectedHistoryItem.alignment_analysis.top_matches.map((m) => m.objective_id).join(", ")}
                    </div>}
                </div>}
              
              {
    /* Date */
  }
              <div className="text-xs text-slate-400 pt-4 border-t border-slate-100">
                Analysé le {new Date(selectedHistoryItem.analyzed_at).toLocaleDateString("fr-FR", {
    day: "2-digit",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  })}
              </div>
            </div>
          </div>
        </div>}
    </div>;
};
var SmartAnalysisPage_default = SmartAnalysisPage;
export {
  SmartAnalysisPage_default as default
};
