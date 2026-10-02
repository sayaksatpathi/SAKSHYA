import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom';
import { useEffect } from 'react';
import { 
  LayoutDashboard, 
  Briefcase, 
  Film, 
  Search, 
  Clock, 
  ShieldCheck, 
  FileText, 
  Settings,
  Shield,
  LogOut
} from 'lucide-react';

export default function Layout() {
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const token = localStorage.getItem('sakshya_token');
    if (!token && location.pathname !== '/login') {
      navigate('/login');
    }
  }, [navigate, location]);

  const handleLogout = () => {
    localStorage.removeItem('sakshya_token');
    navigate('/login');
  };

  const navItems = [
    { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/cases', icon: Briefcase, label: 'Cases' },
    { to: '/evidence', icon: Film, label: 'Evidence' },
    { to: '/cameras', icon: Search, label: 'Cameras' },
    { to: '/investigation', icon: Search, label: 'Investigation' },
    { to: '/timeline', icon: Clock, label: 'Timeline' },
    { to: '/integrity', icon: ShieldCheck, label: 'Integrity' },
    { to: '/reports', icon: FileText, label: 'Reports' },
  ];

  return (
    <div className="flex h-screen bg-slate-950 text-slate-200">
      {/* Sidebar */}
      <aside className="w-64 border-r border-slate-800 bg-slate-900 flex flex-col">
        <div className="h-20 flex flex-col justify-center px-6 border-b border-slate-800">
          <div className="flex items-center">
            <Shield className="w-6 h-6 text-indigo-500 mr-3" />
            <span className="font-bold text-lg tracking-wider">SAKSHYA</span>
          </div>
          <div className="mt-2 bg-amber-500/10 border border-amber-500/50 text-amber-500 text-[10px] uppercase font-bold text-center py-0.5 px-1 rounded truncate">
            SYNTHETIC DEMONSTRATION DATA
          </div>
        </div>
        
        <nav className="flex-1 py-6 px-3 space-y-1 overflow-y-auto">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive 
                    ? 'bg-indigo-500/10 text-indigo-400' 
                    : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                }`
              }
            >
              <item.icon className="w-5 h-5 mr-3" />
              {item.label}
            </NavLink>
          ))}
        </nav>
        
        <div className="p-4 border-t border-slate-800">
          <div className="flex items-center px-3 py-2 text-sm font-medium text-slate-400 hover:bg-slate-800 hover:text-slate-200 rounded-md cursor-pointer">
            <Settings className="w-5 h-5 mr-3" />
            Settings
          </div>
          <div 
            onClick={handleLogout}
            className="mt-1 flex items-center px-3 py-2 text-sm font-medium text-red-400 hover:bg-red-900/20 hover:text-red-300 rounded-md cursor-pointer"
          >
            <LogOut className="w-5 h-5 mr-3" />
            Logout
          </div>
          <div className="mt-4 flex items-center px-3">
            <div className="w-2 h-2 rounded-full bg-emerald-500 mr-2"></div>
            <span className="text-xs text-slate-500 uppercase tracking-wider">System Online</span>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Topbar */}
        <header className="h-16 border-b border-slate-800 bg-slate-900/50 flex items-center justify-between px-8">
          <div className="flex items-center text-sm">
            <span className="text-slate-500">Forensic Investigation Platform</span>
          </div>
          <div className="flex items-center space-x-4">
            <div className="flex items-center px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-medium">
              <ShieldCheck className="w-3.5 h-3.5 mr-1.5" />
              Trust Service Connected
            </div>
            <div className="h-8 w-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-sm font-medium">
              JD
            </div>
          </div>
        </header>
        
        {/* Main Content */}
        <main className="flex-1 overflow-auto bg-slate-950 p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
