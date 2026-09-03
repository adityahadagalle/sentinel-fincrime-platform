import React, { useState } from 'react';
import { setRoleGlobal } from '../roleStore';
import { Shield, Lock, User, ArrowRight, KeyRound } from 'lucide-react';

const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    // Simulated validation delay for premium feel
    setTimeout(() => {
      if (username === 'admin' && password === 'admin123') {
        setRoleGlobal('admin');
      } else if (username === 'viewer' && password === 'viewer123') {
        setRoleGlobal('viewer');
      } else {
        setError('Invalid credentials. Access denied.');
        setLoading(false);
      }
    }, 600);
  };

  const handleQuickViewer = () => {
    setRoleGlobal('viewer');
  };

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-background z-50 font-sans antialiased overflow-hidden select-none">
      {/* Background Glows */}
      <div className="absolute top-[-10%] left-[-10%] w-[45%] h-[45%] bg-sky-500/10 blur-[130px] rounded-full pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[45%] h-[45%] bg-blue-600/10 blur-[130px] rounded-full pointer-events-none" />

      <div className="w-full max-w-md p-8 sm:p-10 rounded-2xl border border-border/80 bg-card/80 backdrop-blur-xl shadow-2xl relative overflow-hidden">
        {/* Top Accent Line */}
        <div className="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-transparent via-sky-400 to-transparent" />
        
        {/* Header */}
        <div className="text-center space-y-2 mb-8">
          <div className="flex justify-center mb-4">
            <div className="w-14 h-14 bg-sky-500/10 rounded-2xl flex items-center justify-center border border-sky-500/20 shadow-inner text-sky-400">
              <Shield className="w-7 h-7" />
            </div>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">SENTINEL</h1>
          <p className="text-xs text-slate-400">Enterprise Fraud Security Operations Console</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-[11px] font-medium text-slate-400 flex items-center gap-1.5 ml-0.5">
              <User className="w-3.5 h-3.5 text-slate-400" />
              Terminal Identity
            </label>
            <input 
              type="text" 
              placeholder="Username (admin / viewer)" 
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-3 bg-slate-900/60 border border-border/80 rounded-xl text-xs font-medium focus:ring-2 focus:ring-sky-500/30 focus:border-sky-500/60 outline-none transition-all placeholder:text-slate-500 text-slate-100"
              required
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-[11px] font-medium text-slate-400 flex items-center gap-1.5 ml-0.5">
              <KeyRound className="w-3.5 h-3.5 text-slate-400" />
              Access Cipher
            </label>
            <input 
              type="password" 
              placeholder="Password" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-3 bg-slate-900/60 border border-border/80 rounded-xl text-xs font-medium focus:ring-2 focus:ring-sky-500/30 focus:border-sky-500/60 outline-none transition-all placeholder:text-slate-500 text-slate-100"
              required
            />
          </div>

          {error && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl text-xs font-medium text-rose-400 text-center animate-in fade-in duration-200">
              ⚠️ {error}
            </div>
          )}

          <button 
            type="submit"
            disabled={loading}
            className="w-full py-3.5 rounded-xl bg-primary hover:bg-primary/90 text-white text-xs font-semibold tracking-wide transition-all shadow-lg shadow-sky-500/20 disabled:opacity-50 cursor-pointer mt-2 flex items-center justify-center gap-2"
          >
            <span>{loading ? 'Authenticating...' : 'Establish Secure Link'}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>

        <div className="mt-6 pt-6 border-t border-border/60 text-center space-y-3">
          <button 
            onClick={handleQuickViewer}
            className="text-xs text-sky-400 font-medium hover:underline transition-all"
          >
            Bypass with Public Viewer Access →
          </button>
          <p className="text-[10px] font-mono text-slate-400">
            SENTINEL PROD-1.4.0 • Encrypted Operations
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login;

