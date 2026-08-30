import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("UI Error Caught by Boundary:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="bg-background text-on-surface min-h-screen flex flex-col items-center justify-center p-4 text-center">
          <span className="material-symbols-outlined text-[64px] text-error mb-4">gpp_bad</span>
          <h2 className="text-headline-lg font-headline-lg text-error mb-2">Something went wrong</h2>
          <p className="text-body-md text-on-surface-variant max-w-md mb-6">
            We've encountered an unexpected UI error. Please refresh the page or return home.
          </p>
          <div className="flex gap-4">
            <button 
              onClick={() => window.location.reload()} 
              className="bg-primary text-on-primary px-6 py-2 rounded-full font-label-sm font-bold hover:bg-primary-container transition-colors"
            >
              Refresh Page
            </button>
            <button 
              onClick={() => window.location.href = '/'} 
              className="border border-primary text-primary px-6 py-2 rounded-full font-label-sm font-bold hover:bg-surface-container transition-colors"
            >
              Go Home
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
