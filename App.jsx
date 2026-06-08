import { useState } from 'react';
import { HashRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { UserRole } from './types';
import Login from './pages/Login';
import Navbar from './components/Navbar';
import CollaboratorDashboard from './pages/CollaboratorDashboard';
import ManagerDashboard from './pages/ManagerDashboard';
import HrDashboard from './pages/HrDashboard';
import SmartAnalysisPage from './pages/SmartAnalysisPage';
import { AuthService } from './services/authService';

const App = () => {
  const [user, setUser] = useState(null);

  const handleLogin = (u) => setUser(u);

  const handleLogout = async () => {
    await AuthService.logout();
    setUser(null);
  };

  if (!user) {
    return <Login onLogin={handleLogin} />;
  }

  return (
    <Router>
      <div className="min-h-screen flex flex-col">
        <Navbar user={user} onLogout={handleLogout} />

        <main className="flex-1 bg-slate-50">
          <Routes>
            <Route path="/" element={<Navigate to={getDefaultPath(user.role)} />} />

            {user.role === UserRole.COLLAB && (
              <Route path="/dashboard" element={<CollaboratorDashboard user={user} />} />
            )}

            {user.role === UserRole.MANAGER && (
              <Route path="/manager" element={<ManagerDashboard user={user} />} />
            )}

            {user.role === UserRole.HR && (
              <Route path="/hr" element={<HrDashboard user={user} />} />
            )}

            {user.role === UserRole.HR && (
              <Route path="/smart-analysis" element={<SmartAnalysisPage user={user} />} />
            )}

            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        </main>

        <footer className="bg-white border-t border-slate-200 py-8 px-8 flex flex-col md:flex-row justify-between items-center text-slate-400 text-xs gap-4">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-emerald-600 rounded-sm flex items-center justify-center">
               <div className="w-1.5 h-1.5 bg-white rounded-full"></div>
            </div>
            <span className="font-bold text-slate-600 uppercase tracking-widest">BMCI SMART</span>
          </div>
          <div className="text-center">
            <div>© 2024 BMCI. Tous droits réservés. Groupe BNP Paribas.</div>
          </div>
          <div className="flex gap-6">
            <a href="#" className="hover:text-emerald-600 font-bold transition-colors">Documentation</a>
            <a href="#" className="hover:text-emerald-600 font-bold transition-colors">Politique de Confidentialité</a>
            <a href="#" className="hover:text-emerald-600 font-bold transition-colors">Support IT</a>
          </div>
        </footer>
      </div>
    </Router>
  );
};

function getDefaultPath(role) {
  switch (role) {
    case UserRole.COLLAB: return '/dashboard';
    case UserRole.MANAGER: return '/manager';
    case UserRole.HR: return '/hr';
    default: return '/';
  }
}

export default App;
