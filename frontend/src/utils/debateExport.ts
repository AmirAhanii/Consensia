import type { DebateMessage, DebateResult, Persona } from "../types";

export type DebateExportAttachmentMeta = {
  filename: string;
  mime_type: string;
};

export type DebateExportInput = {
  exportedAtIso: string;
  question: string;
  personas: Persona[];
  attachments: DebateExportAttachmentMeta[];
  result: DebateResult;
  messages?: DebateMessage[] | null;
};

function fence(text: string): string {
  const t = text.replace(/\r\n/g, "\n");
  const fenceChar = "`";
  let delim = "```";
  while (t.includes(delim)) delim = fenceChar.repeat(delim.length + 1);
  return `${delim}\n${t}\n${delim}`;
}

function mdEscapeInline(s: string): string {
  return s.replace(/\|/g, "\\|").replace(/\s+/g, " ").trim();
}

function buildCalibrationMd(title: string, rows: { personaName: string; score: number; rationale: string }[]) {
  if (!rows.length) return "";
  const header = `| Persona | Score (0–9) | Note |\n| --- | ---: | --- |\n`;
  const body = rows
    .map((r) => `| ${mdEscapeInline(r.personaName)} | ${r.score} | ${mdEscapeInline(r.rationale)} |`)
    .join("\n");
  return `### ${title}\n\n${header}${body}\n\n`;
}

export function buildDebateMarkdown(input: DebateExportInput): string {
  const { exportedAtIso, question, personas, attachments, result, messages } = input;
  const lines: string[] = [];
  lines.push(`# Consensia debate export`);
  lines.push("");
  lines.push(`_Generated: ${exportedAtIso}_`);
  lines.push("");

  lines.push(`## User question`);
  lines.push("");
  lines.push(fence(question.trim() || "(empty)"));
  lines.push("");

  lines.push(`## Uploaded files`);
  lines.push("");
  if (attachments.length === 0) {
    lines.push(`_No files were attached to this run._`);
  } else {
    lines.push(`| File | MIME type |`);
    lines.push(`| --- | --- |`);
    for (const a of attachments) {
      lines.push(`| ${mdEscapeInline(a.filename)} | ${mdEscapeInline(a.mime_type)} |`);
    }
  }
  lines.push("");

  lines.push(`## Personas`);
  lines.push("");
  for (const p of personas) {
    lines.push(`### ${p.name}`);
    lines.push("");
    lines.push(fence(p.description || ""));
    if (p.personaBasis?.trim()) {
      lines.push("");
      lines.push(`**Basis (truncated in UI):**`);
      lines.push(fence(p.personaBasis.trim()));
    }
    lines.push("");
  }

  if (result.topicRelevanceQa?.length) {
    lines.push(
      buildCalibrationMd(
        "Topic relevance (0–9, before debate)",
        result.topicRelevanceQa.map((r) => ({
          personaName: r.personaName,
          score: r.score,
          rationale: r.rationale,
        }))
      )
    );
  }

  if (result.reasoningQualityQa?.length) {
    lines.push(
      buildCalibrationMd(
        "Reasoning quality (0–9, after debate)",
        result.reasoningQualityQa.map((r) => ({
          personaName: r.personaName,
          score: r.score,
          rationale: r.rationale,
        }))
      )
    );
  }

  lines.push(`## Rounds`);
  lines.push("");
  for (const round of result.rounds) {
    lines.push(`### Round ${round.roundNumber} — ${round.label}`);
    lines.push("");
    for (const pa of round.personaAnswers) {
      lines.push(`#### ${pa.personaName}`);
      lines.push("");
      lines.push(`_${pa.personaDescription}_`);
      lines.push("");
      lines.push(fence(pa.answer));
      lines.push("");
    }
  }

  lines.push(`## Judge verdict`);
  lines.push("");
  lines.push(`### Summary`);
  lines.push("");
  lines.push(fence(result.judge.summary));
  lines.push("");
  lines.push(`### Reasoning`);
  lines.push("");
  lines.push(fence(result.judge.reasoning));
  lines.push("");

  const safeMessages = Array.isArray(messages) ? messages : [];
  if (safeMessages.length > 0) {
    lines.push(`## Thread transcript (stored messages)`);
    lines.push("");
    for (const m of safeMessages) {
      const who = m.author || m.role;
      lines.push(`### ${m.role}: ${who}`);
      lines.push("");
      if (m.roundLabel) lines.push(`_Round: ${m.roundLabel}_`);
      lines.push(fence(m.content));
      lines.push("");
    }
  }

  return lines.join("\n");
}

export function downloadTextFile(filename: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function escHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function calibrationTableHtml(
  title: string,
  rows: { personaName: string; score: number; rationale: string }[],
): string {
  if (!rows.length) return "";
  const head = `<thead><tr><th>Persona</th><th>0–9</th><th>Note</th></tr></thead>`;
  const body = rows
    .map(
      (r) =>
        `<tr><td>${escHtml(r.personaName)}</td><td style="text-align:center">${r.score}</td><td>${escHtml(r.rationale)}</td></tr>`,
    )
    .join("");
  return `<h3>${escHtml(title)}</h3><table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;width:100%;font-size:11px">${head}<tbody>${body}</tbody></table>`;
}

export function buildDebatePrintDocument(input: DebateExportInput): string {
  const { exportedAtIso, question, personas, attachments, result, messages } = input;
  const chunks: string[] = [];
  chunks.push(`<h1>Consensia debate export</h1>`);
  chunks.push(`<p class="meta">${escHtml(`Generated: ${exportedAtIso}`)}</p>`);

  chunks.push(`<h2>User question</h2><pre>${escHtml(question.trim() || "(empty)")}</pre>`);

  chunks.push(`<h2>Uploaded files</h2>`);
  if (attachments.length === 0) {
    chunks.push(`<p class="meta">No files attached to this run.</p>`);
  } else {
    chunks.push(
      `<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;width:100%;font-size:11px"><thead><tr><th>File</th><th>MIME</th></tr></thead><tbody>` +
        attachments
          .map(
            (a) =>
              `<tr><td>${escHtml(a.filename)}</td><td>${escHtml(a.mime_type)}</td></tr>`,
          )
          .join("") +
        `</tbody></table>`,
    );
  }

  chunks.push(`<h2>Personas</h2>`);
  for (const p of personas) {
    chunks.push(`<h3>${escHtml(p.name)}</h3><pre>${escHtml(p.description || "")}</pre>`);
    if (p.personaBasis?.trim()) {
      chunks.push(`<p><strong>Basis</strong></p><pre>${escHtml(p.personaBasis.trim())}</pre>`);
    }
  }

  if (result.topicRelevanceQa?.length) {
    chunks.push(
      calibrationTableHtml(
        "Topic relevance (0–9, before debate)",
        result.topicRelevanceQa.map((r) => ({
          personaName: r.personaName,
          score: r.score,
          rationale: r.rationale,
        })),
      ),
    );
  }
  if (result.reasoningQualityQa?.length) {
    chunks.push(
      calibrationTableHtml(
        "Reasoning quality (0–9, after debate)",
        result.reasoningQualityQa.map((r) => ({
          personaName: r.personaName,
          score: r.score,
          rationale: r.rationale,
        })),
      ),
    );
  }

  chunks.push(`<h2>Rounds</h2>`);
  for (const round of result.rounds) {
    chunks.push(`<h3>${escHtml(`Round ${round.roundNumber} — ${round.label}`)}</h3>`);
    for (const pa of round.personaAnswers) {
      chunks.push(
        `<h4>${escHtml(pa.personaName)}</h4><p class="meta">${escHtml(pa.personaDescription)}</p><pre>${escHtml(pa.answer)}</pre>`,
      );
    }
  }

  chunks.push(`<h2>Judge verdict</h2>`);
  chunks.push(`<h3>Summary</h3><pre>${escHtml(result.judge.summary)}</pre>`);
  chunks.push(`<h3>Reasoning</h3><pre>${escHtml(result.judge.reasoning)}</pre>`);

  const safeMessages = Array.isArray(messages) ? messages : [];
  if (safeMessages.length > 0) {
    chunks.push(`<h2>Thread transcript</h2>`);
    for (const m of safeMessages) {
      const who = m.author || m.role;
      chunks.push(
        `<h4>${escHtml(`${m.role}: ${who}`)}</h4>${m.roundLabel ? `<p class="meta">${escHtml(m.roundLabel)}</p>` : ""}<pre>${escHtml(m.content)}</pre>`,
      );
    }
  }

  const bodyHtml = chunks.join("\n");

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>Consensia — Debate export</title>
  <style>
    body { font-family: ui-sans-serif, system-ui, sans-serif; padding: 24px; color: #111; max-width: 720px; margin: 0 auto; }
    h1 { font-size: 1.35rem; margin: 0 0 12px; }
    h2 { font-size: 1.1rem; margin: 20px 0 8px; border-bottom: 1px solid #ddd; padding-bottom: 4px; }
    h3 { font-size: 1rem; margin: 14px 0 6px; }
    h4 { font-size: 0.95rem; margin: 10px 0 4px; }
    pre { white-space: pre-wrap; background: #f6f6f8; border: 1px solid #e2e2ea; border-radius: 8px; padding: 10px 12px; font-size: 11px; line-height: 1.45; }
    .meta { color: #555; font-size: 12px; }
    @media print {
      body { padding: 0; }
      pre { break-inside: avoid; }
    }
  </style>
</head>
<body>
${bodyHtml}
<script>window.onload=function(){window.focus();window.print();}</script>
</body>
</html>`;
}

/** Opens a print dialog so the user can Save as PDF. */
export function printDebateExport(input: DebateExportInput) {
  const html = buildDebatePrintDocument(input);
  const w = window.open("", "_blank", "noopener,noreferrer,width=900,height=1200");
  if (!w) return false;
  w.document.open();
  w.document.write(html);
  w.document.close();
  return true;
}

export function slugFromQuestion(q: string): string {
  const s = q
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 40);
  return s || "debate";
}
