import React, { useEffect, useRef } from "react";

export const GradientBackground: React.FC = () => {
  const blobRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let animationFrame: number;
    let angle = 200;

    const animate = () => {
      angle = (angle + 0.2) % 360;
      if (blobRef.current) {
        blobRef.current.style.background = `conic-gradient(from ${angle}deg at 50% 50%, rgba(168, 85, 247, 0.35), rgba(14, 0, 36, 0.05), rgba(236, 72, 153, 0.3))`;
      }
      animationFrame = requestAnimationFrame(animate);
    };

    animationFrame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animationFrame);
  }, []);

  return (
    <>
      {/* Dark (default) */}
      <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden light:hidden">
        {/* Ambient wash — purple/magenta depth (matches classic Consensia workspace) */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_100%_70%_at_50%_100%,rgba(147,51,234,0.22),transparent_58%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_70%_50%_at_50%_35%,rgba(79,70,229,0.12),transparent_60%)]" />
        <div className="absolute -left-1/4 top-[-20%] h-[600px] w-[600px] rounded-full bg-purple-600/35 blur-3xl" />
        <div className="absolute -right-1/3 top-1/4 h-[520px] w-[520px] rounded-full bg-fuchsia-500/26 blur-[160px]" />
        <div
          ref={blobRef}
          className="absolute left-1/2 top-1/2 h-[720px] w-[720px] -translate-x-1/2 -translate-y-1/2 rounded-full opacity-[0.65] blur-3xl transition-[background]"
        />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(79,70,229,0.14),transparent_52%)]" />
      </div>

      {/* Light — lavender wash (no white flash) */}
      <div className="pointer-events-none fixed inset-0 -z-10 hidden overflow-hidden light:block">
        <div className="absolute inset-0 bg-[var(--c-grad-light-fill)]" />
        <div className="absolute -left-1/4 top-[-15%] h-[520px] w-[520px] rounded-full blur-3xl bg-[var(--c-grad-light-a)]" />
        <div className="absolute -right-1/4 top-1/3 h-[480px] w-[480px] rounded-full blur-[140px] bg-[var(--c-grad-light-b)]" />
        <div className="absolute left-1/2 top-1/3 h-[560px] w-[560px] -translate-x-1/2 rounded-full blur-3xl bg-[var(--c-grad-light-c)]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,var(--c-grad-light-radial-a),transparent_55%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_80%_20%,var(--c-grad-light-radial-b),transparent_50%)]" />
      </div>
    </>
  );
};
