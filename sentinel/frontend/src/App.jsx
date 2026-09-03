import React from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink, Navigate } from 'react-router-dom';
import { useWebSocket } from './hooks/useWebSocket';
import { Activity, LayoutDashboard, Briefcase, Shield, LogOut, ShieldAlert } from 'lucide-react';

// Pages
import Feed from './pages/Feed';
import Dashboard from './pages/Dashboard';
import Cases from './pages/Cases';
import Graph from './pages/Graph';

import SystemStatusBar from './components/SystemStatusBar';
import AttackModeToggle from './components/AttackModeToggle';
import AutomateModeToggle from './components/AutomateModeToggle';
import LiveAlertToast from './components/LiveAlertToast';

import ActionTakenToast from './components/ActionTakenToast';
import ErrorBoundary from './components/ErrorBoundary';
import Login from './components/Login';
import { getRole } from './roleStore';

const App = () => {
  const { connectionStatus } = useWebSocket();
  const role = getRole();
  const [automateMode, setAutomateMode] = React.useState(false);

  React.useEffect(() => {
    fetch('/automation-mode')
      .then((res) => res.json())
      .then((data) => setAutomateMode(Boolean(data.automate_mode)))
      .catch(() => {});

    const handleModeChange = (e) => {
      if (e.detail && e.detail.automate_mode !== undefined) {
        setAutomateMode(Boolean(e.detail.automate_mode));
      }
    };
    window.addEventListener('sentinel_automation_mode_changed', handleModeChange);
    return () => window.removeEventListener('sentinel_automation_mode_changed', handleModeChange);
  }, []);

  if (!role) {
    return <Login />;
  }

  const handleLogout = () => {
    localStorage.removeItem("sentinel_role");
    window.location.reload();
  };

  const navItemClass = ({ isActive }) =>
    `flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-xs font-medium transition-all duration-150 relative ${
      isActive
        ? 'bg-primary/10 text-primary font-semibold border-l-2 border-primary shadow-sm'
        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
    }`;

  return (
    <Router>
      <div className="flex min-h-screen bg-background text-foreground relative font-sans antialiased overflow-hidden">
        <LiveAlertToast />
        <ActionTakenToast />

        
        {/* Navigation Sidebar */}
        <aside className="w-64 border-r border-border bg-card flex flex-col justify-between shrink-0 select-none z-20 shadow-xl">
          <div className="p-5 space-y-6">
            {/* Header & Logo */}
            <div className="flex items-center justify-between pt-1">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-primary/15 border border-primary/30 flex items-center justify-center text-primary shadow-inner">
                  <Shield className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <h2 className="text-base font-bold tracking-tight text-slate-100 flex items-center gap-1.5 leading-none">
                    SENTINEL
                  </h2>
                  <span className="text-[9px] font-mono text-slate-500 uppercase tracking-widest block mt-1">
                    Security Operations
                  </span>
                </div>
              </div>
            </div>

            {/* Role Badge & Status */}
            <div className="space-y-3 bg-muted/40 p-3 rounded-xl border border-border/60">
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">Access Tier</span>
                <span className={`text-[10px] font-mono font-semibold uppercase px-2 py-0.5 rounded border ${
                  role === 'admin' 
                    ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' 
                    : 'bg-slate-500/10 text-slate-400 border-slate-500/20'
                }`}>
                  {role}
                </span>
              </div>
              <SystemStatusBar status={connectionStatus} />
            </div>

            {/* Controls Section */}
            <div className="pt-1 space-y-2">
              <AutomateModeToggle />
              {automateMode ? (
                <div className="p-2.5 rounded-xl bg-emerald-950/40 border border-emerald-500/30 text-[10px] font-mono space-y-1">
                  <div className="text-emerald-300 font-bold tracking-wide flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                    AUTONOMOUS ACTIONS: ACTIVE
                  </div>
                  <div className="text-amber-300/90 font-medium tracking-tight">
                    FREEZE: OPERATOR APPROVAL REQUIRED
                  </div>
                </div>
              ) : (
                <div className="p-2 bg-slate-900/60 border border-slate-800 rounded-lg text-[10px] font-mono text-slate-400 text-center font-bold tracking-wide">
                  AUTONOMOUS ACTIONS: OFF
                </div>

              )}
              <AttackModeToggle />
            </div>



            {/* Navigation Menu */}
            <nav className="space-y-1 pt-2">
              <div className="px-3 pb-2 text-[10px] font-medium text-slate-500 uppercase tracking-widest">
                Monitoring Console
              </div>
              <NavLink to="/feed" className={navItemClass}>
                <Activity className="w-4 h-4 shrink-0" />
                <span>Real-time Feed</span>
              </NavLink>
              <NavLink to="/dashboard" className={navItemClass}>
                <LayoutDashboard className="w-4 h-4 shrink-0" />
                <span>Analytics</span>
              </NavLink>
              <NavLink to="/cases" className={navItemClass}>
                <Briefcase className="w-4 h-4 shrink-0" />
                <span>Cases</span>
              </NavLink>
            </nav>
          </div>

          {/* Sidebar Footer */}
          <div className="p-4 border-t border-border/80 space-y-3 bg-card/50">
            <button 
              onClick={handleLogout}
              className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg bg-muted/50 hover:bg-muted text-slate-300 hover:text-slate-100 text-xs font-medium transition-all duration-150 border border-border/50"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Logout System</span>
            </button>
            <div className="flex items-center justify-between text-[9px] text-slate-500 font-mono">
              <span>v1.4.0 • Enterprise</span>
              <span className="flex items-center gap-1 text-emerald-500 font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                ACTIVE
              </span>
            </div>
          </div>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 overflow-hidden bg-background flex flex-col h-full">
          <div className="flex-1 h-full overflow-hidden">
            <Routes>
              <Route path="/" element={<Navigate to="/feed" replace />} />
              <Route path="/feed" element={<Feed />} />
              <Route path="/dashboard" element={<ErrorBoundary><Dashboard /></ErrorBoundary>} />
              <Route path="/cases" element={<Cases />} />
              <Route path="/graph/:caseId" element={<ErrorBoundary><Graph /></ErrorBoundary>} />
            </Routes>
          </div>
        </main>
      </div>
    </Router>
  );
};

export default App;

