import React from "react";

type QuestionPanelProps = {
  question: string;
  onChange: (value: string) => void;
};

export const QuestionPanel: React.FC<QuestionPanelProps> = ({ question, onChange }) => {
  return (
    <article className="rounded-3xl border border-purple-900/40 bg-black/60 p-6 shadow-xl shadow-purple-950/30 backdrop-blur">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-purple-100">Question</h2>
          <p className="text-sm text-purple-300/70">What challenge should the personas collaborate on?</p>
        </div>
        <span className="rounded-full border border-purple-800/40 px-3 py-1 text-xs font-medium uppercase tracking-wide text-purple-300/70">
          {question.length} characters
        </span>
      </div>
      <textarea
        className="mt-4 min-h-[180px] w-full rounded-2xl border border-purple-900/50 bg-black/70 px-4 py-3 text-sm text-purple-100 outline-none transition focus:border-fuchsia-500 focus:ring-2 focus:ring-fuchsia-500/40"
        placeholder="Describe the scenario for the personas to analyze..."
        value={question}
        onChange={(event) => onChange(event.target.value)}
      />
      <div className="mt-3 text-xs text-purple-300/70">
        Prompt hint: keep it concise but include key constraints or goals so the judge can evaluate trade-offs.
      </div>
    </article>
  );
};

