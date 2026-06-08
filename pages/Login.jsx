import { useState, useEffect } from "react";
import { UserRole } from "../types";
import { UserCircle, Users, ShieldCheck, Loader2, AlertCircle, ChevronDown, Eye, EyeOff, LogIn, UserPlus } from "lucide-react";
import { AuthService } from "../services/authService";
const Login = ({ onLogin }) => {
  const [mode, setMode] = useState("select");
  const [selectedRole, setSelectedRole] = useState(null);
  const [managers, setManagers] = useState([]);
  const [loadingManagers, setLoadingManagers] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [selectedManagerId, setSelectedManagerId] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [checkingSession, setCheckingSession] = useState(true);
  useEffect(() => {
    const checkSession = async () => {
      const user = await AuthService.validateSession();
      if (user) {
        onLogin(user);
      }
      setCheckingSession(false);
    };
    checkSession();
  }, [onLogin]);
  useEffect(() => {
    if (selectedRole === UserRole.COLLAB && mode !== "select") {
      loadManagers();
    }
  }, [selectedRole, mode]);
  const loadManagers = async () => {
    setLoadingManagers(true);
    const mgrs = await AuthService.getManagers();
    setManagers(mgrs);
    setLoadingManagers(false);
  };
  const roles = [
    {
      role: UserRole.COLLAB,
      label: "Collaborateur",
      desc: "D\xE9finissez et analysez vos objectifs personnels.",
      icon: <UserCircle className="text-emerald-500" size={32} />,
      bgColor: "hover:border-emerald-500 hover:bg-emerald-50",
      requiresManager: true
    },
    {
      role: UserRole.MANAGER,
      label: "Manager",
      desc: "G\xE9rez les objectifs de votre \xE9quipe et l'alignement.",
      icon: <Users className="text-teal-500" size={32} />,
      bgColor: "hover:border-teal-500 hover:bg-teal-50",
      requiresManager: false
    },
    {
      role: UserRole.HR,
      label: "RH",
      desc: "Pilotez la strat\xE9gie et le catalogue entreprise.",
      icon: <ShieldCheck className="text-green-500" size={32} />,
      bgColor: "hover:border-green-500 hover:bg-green-50",
      requiresManager: false
    }
  ];
  const handleSelectRole = (role) => {
    setSelectedRole(role);
    setMode("login");
    setError(null);
    if (role === UserRole.MANAGER) {
      setEmail("manager.digital@bmci.co.ma");
      setPassword("REDACTED_DEMO_PWD");
    } else if (role === UserRole.HR) {
      setEmail("rh@bmci.co.ma");
      setPassword("REDACTED_DEMO_PWD");
    } else {
      setEmail("");
      setPassword("");
    }
  };
  const handleLogin = async (e) => {
    e.preventDefault();
    setError(null);
    if (!email || !password) {
      setError("Veuillez remplir tous les champs.");
      return;
    }
    if (selectedRole === UserRole.COLLAB && !selectedManagerId) {
      setError("Veuillez s\xE9lectionner votre manager.");
      return;
    }
    setIsLoading(true);
    const result = await AuthService.login({
      email,
      password,
      manager_id: selectedRole === UserRole.COLLAB ? selectedManagerId : void 0
    });
    setIsLoading(false);
    if (result.success && result.user) {
      onLogin(result.user);
    } else {
      setError(result.error || "Erreur de connexion.");
    }
  };
  const handleRegister = async (e) => {
    e.preventDefault();
    setError(null);
    if (!email || !password || !name) {
      setError("Veuillez remplir tous les champs.");
      return;
    }
    if (selectedRole === UserRole.COLLAB && !selectedManagerId) {
      setError("Veuillez s\xE9lectionner votre manager.");
      return;
    }
    if (password.length < 6) {
      setError("Le mot de passe doit contenir au moins 6 caract\xE8res.");
      return;
    }
    setIsLoading(true);
    const result = await AuthService.register({
      email,
      password,
      name,
      role: selectedRole || "COLLAB",
      manager_id: selectedRole === UserRole.COLLAB ? selectedManagerId : void 0
    });
    setIsLoading(false);
    if (result.success && result.user) {
      onLogin(result.user);
    } else {
      setError(result.error || "Erreur lors de l'inscription.");
    }
  };
  const handleBack = () => {
    setMode("select");
    setSelectedRole(null);
    setEmail("");
    setPassword("");
    setName("");
    setSelectedManagerId("");
    setError(null);
  };
  if (checkingSession) {
    return <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="animate-spin text-emerald-600" size={48} />
          <p className="text-slate-500">Vérification de la session...</p>
        </div>
      </div>;
  }
  return <div className="min-h-screen flex items-center justify-center bg-slate-50 p-6">
      <div className="max-w-4xl w-full">
        {
    /* Header */
  }
        <div className="text-center mb-12">
          <div className="inline-block bg-emerald-700 p-4 rounded-3xl mb-6 shadow-xl shadow-emerald-100 flex items-center justify-center">
            <div className="grid grid-cols-2 gap-1">
              <div className="w-3 h-3 bg-white rounded-full" />
              <div className="w-3 h-3 bg-white rounded-full opacity-60" />
              <div className="w-3 h-3 bg-white rounded-full opacity-80" />
              <div className="w-3 h-3 bg-white rounded-full" />
            </div>
          </div>
          <h1 className="text-4xl font-black text-emerald-900 tracking-tight mb-2">BMCI</h1>
          <p className="text-slate-500 text-lg">Plateforme d'Analyse d'Objectifs SMART</p>
        </div>

        {
    /* Role Selection */
  }
        {mode === "select" && <div className="grid md:grid-cols-3 gap-6">
            {roles.map((item) => <button
    key={item.role}
    onClick={() => handleSelectRole(item.role)}
    className={`bg-white border-2 border-slate-200 p-8 rounded-2xl text-left transition-all duration-300 group ${item.bgColor} transform hover:-translate-y-1 shadow-sm hover:shadow-md`}
  >
                <div className="mb-4 bg-slate-50 inline-block p-3 rounded-xl transition-colors group-hover:bg-white">
                  {item.icon}
                </div>
                <h3 className="text-xl font-bold text-slate-800 mb-2">{item.label}</h3>
                <p className="text-slate-500 text-sm leading-relaxed">{item.desc}</p>
              </button>)}
          </div>}

        {
    /* Login/Register Form */
  }
        {mode !== "select" && selectedRole && <div className="max-w-md mx-auto">
            <div className="bg-white p-8 rounded-2xl shadow-lg border border-slate-100">
              {
    /* Back button */
  }
              <button
    onClick={handleBack}
    className="text-sm text-slate-500 hover:text-slate-700 mb-6 flex items-center gap-1"
  >
                ← Retour à la sélection
              </button>

              {
    /* Role indicator */
  }
              <div className="flex items-center gap-3 mb-6 pb-6 border-b border-slate-100">
                {roles.find((r) => r.role === selectedRole)?.icon}
                <div>
                  <div className="font-bold text-slate-800">{roles.find((r) => r.role === selectedRole)?.label}</div>
                  <div className="text-xs text-slate-500">
                    {mode === "login" ? "Connexion" : "Inscription"}
                  </div>
                </div>
              </div>

              {
    /* Error message */
  }
              {error && <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 flex items-center gap-3 text-red-700">
                  <AlertCircle size={20} />
                  <p className="text-sm">{error}</p>
                </div>}

              {
    /* Form */
  }
              <form onSubmit={mode === "login" ? handleLogin : handleRegister} className="space-y-4">
                {
    /* Name (register only) */
  }
                {mode === "register" && <div>
                    <label className="block text-xs font-bold text-slate-500 uppercase mb-2">
                      Nom complet
                    </label>
                    <input
    type="text"
    value={name}
    onChange={(e) => setName(e.target.value)}
    className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 transition-all"
    placeholder="Jean Dupont"
  />
                  </div>}

                {
    /* Email */
  }
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase mb-2">
                    Email
                  </label>
                  <input
    type="email"
    value={email}
    onChange={(e) => setEmail(e.target.value)}
    className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 transition-all"
    placeholder="email@bmci.co.ma"
  />
                </div>

                {
    /* Password */
  }
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase mb-2">
                    Mot de passe
                  </label>
                  <div className="relative">
                    <input
    type={showPassword ? "text" : "password"}
    value={password}
    onChange={(e) => setPassword(e.target.value)}
    className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 transition-all pr-12"
    placeholder="••••••••"
  />
                    <button
    type="button"
    onClick={() => setShowPassword(!showPassword)}
    className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
  >
                      {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </div>

                {
    /* Manager Selection (COLLAB only) */
  }
                {selectedRole === UserRole.COLLAB && <div>
                    <label className="block text-xs font-bold text-slate-500 uppercase mb-2">
                      Choisir votre Manager <span className="text-red-500">*</span>
                    </label>
                    {loadingManagers ? <div className="flex items-center gap-2 text-slate-400 py-3">
                        <Loader2 className="animate-spin" size={16} />
                        <span className="text-sm">Chargement des managers...</span>
                      </div> : <div className="relative">
                        <select
    value={selectedManagerId}
    onChange={(e) => setSelectedManagerId(e.target.value)}
    className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 transition-all appearance-none bg-white"
  >
                          <option value="">-- Sélectionnez votre manager --</option>
                          {managers.map((mgr) => <option key={mgr.id} value={mgr.id}>
                              {mgr.name} - {mgr.team || mgr.email}
                            </option>)}
                        </select>
                        <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" size={18} />
                      </div>}
                    <p className="text-xs text-slate-400 mt-2">
                      Cette sélection est obligatoire pour garantir le suivi par votre manager.
                    </p>
                  </div>}

                {
    /* Submit Button */
  }
                <button
    type="submit"
    disabled={isLoading}
    className="w-full bg-emerald-600 text-white py-3 rounded-xl font-bold hover:bg-emerald-700 transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed mt-6"
  >
                  {isLoading ? <>
                      <Loader2 className="animate-spin" size={18} />
                      {mode === "login" ? "Connexion..." : "Inscription..."}
                    </> : <>
                      {mode === "login" ? <LogIn size={18} /> : <UserPlus size={18} />}
                      {mode === "login" ? "Se connecter" : "S'inscrire"}
                    </>}
                </button>
              </form>

              {
    /* Toggle login/register */
  }
              <div className="mt-6 text-center">
                {mode === "login" ? <p className="text-sm text-slate-500">
                    Pas encore de compte ?{" "}
                    <button
    onClick={() => {
      setMode("register");
      setError(null);
    }}
    className="text-emerald-600 font-bold hover:underline"
  >
                      S'inscrire
                    </button>
                  </p> : <p className="text-sm text-slate-500">
                    Déjà inscrit ?{" "}
                    <button
    onClick={() => {
      setMode("login");
      setError(null);
    }}
    className="text-emerald-600 font-bold hover:underline"
  >
                      Se connecter
                    </button>
                  </p>}
              </div>

              {
    /* Demo credentials for Manager/HR */
  }
              {(selectedRole === UserRole.MANAGER || selectedRole === UserRole.HR) && mode === "login" && <div className="mt-6 p-4 bg-slate-50 rounded-xl">
                  <p className="text-xs text-slate-500 font-bold uppercase mb-2">Compte de test</p>
                  <p className="text-xs text-slate-600">
                    {selectedRole === UserRole.MANAGER ? "Email: manager.digital@bmci.co.ma / MDP: REDACTED_DEMO_PWD" : "Email: rh@bmci.co.ma / MDP: REDACTED_DEMO_PWD"}
                  </p>
                </div>}
            </div>
          </div>}
        
        {
    /* Footer */
  }
        <div className="mt-16 text-center text-slate-400 text-xs space-y-1">
          <div>Propulsé par Qwen AI • BMCI © 2026 • Groupe BNP Paribas</div>
          <div className="font-semibold uppercase tracking-wider text-[10px]">
            Développé par des étudiants de l'École Centrale Casablanca
          </div>
        </div>
      </div>
    </div>;
};
var Login_default = Login;
export {
  Login_default as default
};
