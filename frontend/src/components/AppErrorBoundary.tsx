import React from "react";

type Props = {
  children: React.ReactNode;
};

type State = {
  error: Error | null;
};

export class AppErrorBoundary extends React.Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error) {
    // eslint-disable-next-line no-console
    console.error("App crashed:", error);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="min-h-screen bg-black px-6 py-10 text-white light:bg-[var(--c-bg)] light:text-[var(--c-fg)]">
          <div className="mx-auto max-w-3xl rounded-2xl border border-rose-500/40 bg-rose-500/10 p-5 light:border-rose-400/50 light:bg-rose-100/80">
            <p className="text-xs font-semibold uppercase tracking-widest text-rose-200 light:text-rose-700">
              UI error
            </p>
            <h1 className="mt-2 text-lg font-semibold">Something crashed while loading.</h1>
            <p className="mt-2 text-sm text-rose-100/90 light:text-rose-900">
              {this.state.error.message}
            </p>
            {this.state.error.stack ? (
              <pre className="mt-4 max-h-[40vh] overflow-auto rounded-xl border border-rose-500/30 bg-black/40 p-3 text-[11px] leading-relaxed text-rose-100/90 light:border-rose-400/40 light:bg-white/70 light:text-rose-950">
                {this.state.error.stack}
              </pre>
            ) : null}
            <p className="mt-4 text-xs text-rose-200/80 light:text-rose-800/80">
              Open DevTools → Console for the full stack trace.
            </p>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

