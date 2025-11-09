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
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className="absolute -left-1/4 top-[-20%] h-[600px] w-[600px] rounded-full blur-3xl bg-purple-600/30" />
      <div className="absolute -right-1/3 top-1/4 h-[520px] w-[520px] rounded-full bg-fuchsia-500/20 blur-[160px]" />
      <div
        ref={blobRef}
        className="absolute left-1/2 top-1/2 h-[720px] w-[720px] -translate-x-1/2 -translate-y-1/2 rounded-full opacity-60 blur-3xl transition-[background]"
      />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(79,70,229,0.16),transparent_55%)]" />
    </div>
  );
};

