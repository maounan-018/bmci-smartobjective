const SmartBadge = ({ letter, active, label }) => {
  return (
    <div className="flex flex-col items-center gap-1 group relative">
      <div
        className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-lg transition-all duration-300 ${
          active
            ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-100'
            : 'bg-slate-100 text-slate-300 border-2 border-slate-200'
        }`}
      >
        {letter}
      </div>
      {label && <span className="text-[10px] font-bold text-slate-500 uppercase tracking-tighter">{label}</span>}

      {/* Tooltip */}
      {label && (
        <div className="absolute bottom-full mb-2 hidden group-hover:block bg-emerald-900 text-white text-[10px] font-bold px-2 py-1 rounded whitespace-nowrap z-10 shadow-lg">
          {label}: {active ? 'CONFORME' : 'À REVOIR'}
        </div>
      )}
    </div>
  );
};

export default SmartBadge;
