/**
 * Tailwind class fragments. All theme colors live in `colors.css` as `--c-*` CSS variables.
 */

/** Dark: transparent so body + GradientBackground show through; light: solid canvas. */
export const pageShell =
  "bg-transparent text-[var(--c-fg)] light:bg-[var(--c-canvas)]";

export const stickyHeader =
  "border-b border-[color:var(--c-border)] bg-[var(--c-surface-header)] backdrop-blur-md";

export const eyebrowMuted =
  "text-fuchsia-300/80 light:text-fuchsia-700/90";

export const heroTitleGradient =
  "from-purple-100 via-purple-200 to-purple-400 light:from-violet-800 light:via-purple-700 light:to-fuchsia-800";

export const bodyMuted = "text-[var(--c-fg-muted)]";

export const bodyMuted2 = "text-[var(--c-fg-subtle)]";

export const wordmarkGradient =
  "from-purple-100 to-purple-300 light:from-violet-800 light:to-purple-700";

export const navPill =
  "rounded-xl px-2.5 py-1.5 text-xs font-medium transition sm:px-3 sm:text-sm text-[var(--c-fg-muted)] hover:bg-[var(--c-nav-hover-bg)] hover:text-[var(--c-nav-fg-hover)]";

export const cardSurface =
  "rounded-2xl border border-[color:var(--c-border-debaters)] bg-gradient-to-b from-[var(--c-card-from)] to-[var(--c-card-to)] p-6 shadow-lg shadow-[color:var(--c-shadow-card)] backdrop-blur-sm transition hover:border-[color:var(--c-border-strong)]";

/** Smaller promo tiles (auth pages left column). */
export const promoCard =
  "rounded-2xl border border-[color:var(--c-border-debaters)] bg-gradient-to-b from-[var(--c-card-from)] to-[var(--c-card-to)] p-5 shadow-lg shadow-[color:var(--c-shadow-card)] backdrop-blur-sm transition hover:border-[color:var(--c-border-strong)]";

export const reportRow =
  "flex items-center justify-between gap-3 rounded-2xl border border-[color:var(--c-border-soft)] bg-[var(--c-surface-report)] px-5 py-4 text-[var(--c-fg)] backdrop-blur-sm transition hover:border-[color:var(--c-border-strong)] hover:bg-[var(--c-surface-report-hover)]";

export const docLinkHint = "text-xs text-[var(--c-fg-hint)]";

export const ghostLinkBtn =
  "inline-flex items-center rounded-xl border border-[color:var(--c-border-soft)] bg-[var(--c-surface-ghost)] px-4 py-2 text-sm text-[var(--c-fg-muted)] transition hover:border-[color:var(--c-border-strong)] hover:bg-[var(--c-surface-ghost-hover)] hover:text-[var(--c-fg)]";

export const dangerGhostBtn =
  "rounded-xl border border-rose-900/50 bg-[var(--c-surface-danger-ghost)] px-4 py-2 text-sm text-rose-200/95 transition hover:border-rose-600 hover:bg-[var(--c-surface-danger-ghost-hover)] hover:text-rose-100 light:border-rose-400/60 light:text-rose-900 light:hover:border-rose-500 light:hover:bg-[var(--c-surface-danger-ghost-hover)]";

export const formCard =
  "rounded-3xl border border-[color:var(--c-border)] bg-[var(--c-surface-card)] p-6 shadow-xl shadow-[color:var(--c-shadow-form)] backdrop-blur";

export const formHeading = "text-[var(--c-fg)]";

export const formSub = "text-[var(--c-fg-subtle)]";

export const inputField =
  "w-full rounded-2xl border border-[color:var(--c-border-strong)] bg-[var(--c-surface-field)] px-4 py-3 text-sm text-[var(--c-fg)] outline-none transition placeholder:text-[var(--c-placeholder)] focus:border-fuchsia-500 focus:ring-2 focus:ring-fuchsia-500/40 light:focus:border-violet-600 light:focus:ring-violet-500/35";

export const primaryCta =
  "rounded-2xl bg-gradient-to-r from-purple-600 to-fuchsia-600 font-semibold text-white shadow-lg shadow-purple-900/50 transition hover:shadow-fuchsia-500/35 disabled:opacity-60 light:from-violet-600 light:to-fuchsia-600 light:shadow-[color:var(--c-shadow-form)]";

/** Use with `border-t` (e.g. `border-t px-4 ${sectionRule}`). */
export const sectionRule = "border-[color:var(--c-border)]";

export const sectionTitleGradient =
  "from-purple-100 to-purple-300 light:from-violet-800 light:to-purple-700";

export const dividerAccent =
  "from-fuchsia-500/80 to-purple-600/30 light:from-fuchsia-500/70 light:to-violet-500/50";

/** Debate workspace (/app) */
export const debateComposerBar =
  "flex items-end gap-2 rounded-[2rem] border border-[color:var(--c-border-soft)] bg-[var(--c-surface-composer)] py-2.5 pl-5 pr-2 shadow-[0_8px_40px_-12px_rgb(48_12_82_/_0.42)] backdrop-blur-md light:border-[color:var(--c-border-strong)] light:bg-[var(--c-surface-field)] light:shadow-[color:var(--c-shadow-card)]";

export const debateComposerTextarea =
  "max-h-[200px] min-h-[44px] flex-1 resize-none bg-transparent py-2.5 text-sm leading-relaxed text-[var(--c-fg)] placeholder:text-[var(--c-placeholder)] outline-none";

export const debateDockStrip =
  "shrink-0 border-t border-[color:var(--c-border)] bg-[var(--c-surface-dock)] pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-2 backdrop-blur-md motion-reduce:animate-none animate-composer-dock";

export const debateDebatersToggleBtn =
  "inline-flex items-center gap-2 rounded-full border border-[color:var(--c-border-soft)] bg-purple-950/40 px-4 py-1.5 text-xs font-medium text-purple-200 transition-all duration-300 ease-out hover:border-fuchsia-500/45 hover:bg-purple-900/50 hover:text-fuchsia-100 motion-reduce:transition-none active:scale-[0.98] light:border-[color:var(--c-border-strong)] light:bg-[var(--c-surface-chip)] light:text-[var(--c-fg)] light:hover:bg-[var(--c-surface-chip-hover)] light:hover:border-[color:var(--c-border-strong)]";

export const debateDebatersPanel =
  "relative mt-2 overflow-hidden rounded-3xl border border-[color:var(--c-border-debaters)] bg-[var(--c-surface-debaters)] shadow-[0_16px_48px_-20px_rgba(0,0,0,0.75)] motion-reduce:animate-none light:shadow-[color:var(--c-shadow-card)]";

export const debateDebatersPanelHeader =
  "relative border-b border-[color:var(--c-border-debaters)] px-4 py-3 sm:px-5";

export const personaActiveRow =
  "flex items-center gap-3 rounded-xl border border-[color:var(--c-border-soft)] bg-[var(--c-surface-row)] px-3 py-2.5 transition-colors duration-200 light:border-[color:var(--c-border)]";

export const personaActiveIconBox =
  "flex h-10 w-10 items-center justify-center rounded-lg border border-[color:var(--c-border-soft)] bg-[var(--c-surface-tile)] light:border-[color:var(--c-border-strong)]";

export const personaSmallIconBox =
  "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-[color:var(--c-border-soft)] bg-[var(--c-surface-inline)] light:border-[color:var(--c-border-strong)] light:bg-[var(--c-surface-tile)]";

/** HomePage CTA tiles (Log in / Register) */
export const homeCtaTile =
  "flex flex-1 items-center justify-center rounded-3xl border border-[color:var(--c-border-soft)] bg-[var(--c-surface-cta)] px-4 py-4 text-center text-sm font-semibold text-[var(--c-fg)] transition hover:border-[color:var(--c-border-strong)] hover:bg-[var(--c-surface-cta-hover)] active:scale-[0.99] sm:text-base";

export const homeCtaTileFull =
  "flex w-full items-center justify-center rounded-3xl border border-[color:var(--c-border-soft)] bg-[var(--c-surface-cta)] py-4 text-center text-sm font-semibold text-[var(--c-fg)] transition hover:border-[color:var(--c-border-strong)] hover:bg-[var(--c-surface-cta-hover)] active:scale-[0.99] sm:text-base";

export const homeHeroSecondaryCta =
  "inline-flex items-center justify-center gap-3 rounded-2xl border border-[color:var(--c-border-soft)] bg-[var(--c-surface-ghost)] px-8 py-4 text-base font-semibold text-[var(--c-fg)] shadow-lg shadow-[color:var(--c-shadow-card)] backdrop-blur-sm transition hover:border-[color:var(--c-border-strong)] hover:text-[var(--c-fg)] light:hover:bg-[var(--c-surface-cta-hover)]";

/** Profile theme toggle track */
export const appearanceSegmentTrack =
  "flex rounded-2xl border border-[color:var(--c-border-soft)] bg-[var(--c-surface-segment)] p-1 light:border-[color:var(--c-border-strong)]";

/** Google-only password notice card */
export const profileMutedCard =
  `${formCard} bg-[var(--c-surface-muted-overlay)] light:bg-[var(--c-surface-muted-card)]`;
