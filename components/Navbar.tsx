
import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { User, UserRole } from '../types';
import { LayoutDashboard, Target, Briefcase, Users, LogOut, ClipboardCheck } from 'lucide-react';

interface NavbarProps {
  user: User | null;
  onLogout: () => void;
}

const Navbar: React.FC<NavbarProps> = ({ user, onLogout }) => {
  const location = useLocation();

  if (!user) return null;

  const links = [
    { 
      to: '/dashboard', 
      label: 'Mon Espace', 
      icon: <LayoutDashboard size={20} />, 
      roles: [UserRole.COLLAB] 
    },
    { 
      to: '/manager', 
      label: 'Mon Dashboard', 
      icon: <Users size={20} />, 
      roles: [UserRole.MANAGER] 
    },
    { 
      to: '/hr', 
      label: 'Dashboard RH', 
      icon: <Briefcase size={20} />, 
      roles: [UserRole.HR] 
    },
    { 
      to: '/smart-analysis', 
      label: 'Mon Analyse', 
      icon: <ClipboardCheck size={20} />, 
      roles: [UserRole.HR] 
    }
  ].filter(link => link.roles.includes(user.role));

  return (
    <nav className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between sticky top-0 z-50 shadow-sm">
      <div className="flex items-center gap-8">
        <Link to="/" className="flex items-center gap-2">
          <div className="bg-emerald-700 p-1.5 rounded-lg flex items-center justify-center">
            <div className="grid grid-cols-2 gap-0.5">
              <div className="w-1.5 h-1.5 bg-white rounded-full"></div>
              <div className="w-1.5 h-1.5 bg-white rounded-full opacity-60"></div>
              <div className="w-1.5 h-1.5 bg-white rounded-full opacity-80"></div>
              <div className="w-1.5 h-1.5 bg-white rounded-full"></div>
            </div>
          </div>
          <div className="flex flex-col leading-tight">
            <span className="font-black text-xl tracking-tight text-emerald-800">
              BMCI
            </span>
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Objectif SMART</span>
          </div>
        </Link>

        <div className="hidden md:flex items-center gap-1">
          {links.map(link => (
            <Link 
              key={link.to}
              to={link.to}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                location.pathname === link.to 
                  ? 'bg-emerald-50 text-emerald-700' 
                  : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
              }`}
            >
              {link.icon}
              {link.label}
            </Link>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex flex-col items-end mr-2 hidden sm:flex">
          <span className="text-sm font-semibold text-slate-800">{user.name}</span>
          <span className="text-[10px] px-1.5 py-0.5 bg-emerald-100 text-emerald-700 rounded uppercase font-bold">{user.role}</span>
        </div>
        <button 
          onClick={onLogout}
          className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all"
          title="Déconnexion"
        >
          <LogOut size={20} />
        </button>
      </div>
    </nav>
  );
};

export default Navbar;
