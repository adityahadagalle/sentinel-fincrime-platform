import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('[SENTINEL ErrorBoundary] Caught render exception:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center h-full p-8 text-center bg-[#020617] border border-rose-500/30 rounded-xl m-6 space-y-3 font-sans">
          <AlertTriangle className="w-8 h-8 text-rose-400" />
          <div className="font-mono text-xs font-bold text-rose-400 uppercase tracking-wider">
            WORKSPACE RENDER ERROR
          </div>
          <div className="text-xs text-slate-400 max-w-md">
            {this.state.error?.message || 'An unexpected error occurred while rendering this investigation module.'}
          </div>
          <button
            onClick={this.handleReset}
            className="flex items-center gap-2 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-sky-400 text-xs font-mono font-semibold border border-slate-700 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>RETRY WORKSPACE</span>
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
