import React, { useEffect } from "react";
import { Link } from "react-router-dom";
import { GradientBackground } from "../components/GradientBackground";
import { publicAssetUrl } from "../publicAsset";
import {
  bodyMuted,
  bodyMuted2,
  cardSurface,
  dividerAccent,
  docLinkHint,
  eyebrowMuted,
  formHeading,
  heroTitleGradient,
  homeCtaTile,
  homeCtaTileFull,
  homeHeroSecondaryCta,
  navPill,
  pageShell,
  reportRow,
  sectionRule,
  sectionTitleGradient,
  stickyHeader,
  wordmarkGradient,
} from "../theme/themeClasses";

const projectReports = [
  [
    "Project Information Form",
    "assets/CS491_Project_Information_Form (2).pdf",
  ],
  ["Assessment of Innovation Form", "assets/Assessment_Innovation_Expert.pdf"],
  [
    "Project Specification Document",
    "assets/T2526_Project_Specification_Document.pdf",
  ],
  [
    "Analysis and Requirements Report",
    "assets/T2526_Analysis_and_Requirements_Report.docx.pdf",
  ],
  ["Detailed Design Report", "assets/T2526_Detailed_Design_Report.pdf"],
  ["Final Report", "assets/T2526_Final_Report.pdf"],
] as const;

const minuteReports = [
  [
    "Meeting Minute 01",
    "assets/TeamID_MeetingMinutesReport_01_26102025_v1 (1).pdf",
  ],
  [
    "Meeting Minute 02",
    "assets/T2526_MeetingMinutesReport_02_24112025_v1.doc",
  ],
  [
    "Meeting Minute 03",
    "assets/T2526_MeetingMinutesReport_03_11032026_v1.pdf",
  ],
  [
    "Meeting Minute 04",
    "assets/T2526_MeetingMinutesReport_04_29042026.pdf",
  ],
] as const;

const teamMembers = [
  "Amir Hossein Ahani",
  "Ahmed Hatem Haikal",
  "Türker Köken",
  "İrfan Hakan Karakoç",
  "Mehmet Hakan Yavuz",
];

function LogoMark() {
  return (
    <div className="flex h-9 w-9 shrink-0 items-center justify-center sm:h-10 sm:w-10">
      <svg
        viewBox="0 0 64 64"
        xmlns="http://www.w3.org/2000/svg"
        className="h-full w-full"
        aria-hidden
      >
        <defs>
          <linearGradient
            id="home-consensia-logo-gradient"
            x1="0"
            y1="0"
            x2="1"
            y2="1"
          >
            <stop offset="0" stopColor="#C4B5FD" />
            <stop offset="1" stopColor="#8B5CF6" />
          </linearGradient>
        </defs>
        <path
          d="M8 18 L28 32 L8 46"
          fill="none"
          stroke="url(#home-consensia-logo-gradient)"
          strokeWidth="6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path
          d="M56 18 L36 32 L56 46"
          fill="none"
          stroke="url(#home-consensia-logo-gradient)"
          strokeWidth="6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <circle cx="32" cy="32" r="3.6" fill="url(#home-consensia-logo-gradient)" />
      </svg>
    </div>
  );
}

export default function Homepage() {
  useEffect(() => {
    document.title =
      "Consensia — Multi-agent reasoning and evaluation for software engineering";
  }, []);

  const year = new Date().getFullYear();

  return (
    <>
      <GradientBackground />

      <div
        className={`relative z-10 min-h-screen overflow-x-hidden ${pageShell}`}
      >
        <header className={`sticky top-0 z-50 backdrop-blur-md ${stickyHeader}`}>
          <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:gap-4 sm:px-6 sm:py-4">
            <div className="flex min-w-0 items-center gap-2.5 sm:gap-3">
              <LogoMark />
              <span
                className={`truncate bg-gradient-to-r bg-clip-text text-lg font-extrabold tracking-tight text-transparent sm:text-xl ${wordmarkGradient}`}
              >
                Consensia
              </span>
            </div>

            <nav className="flex flex-wrap items-center justify-end gap-1.5 sm:gap-2">
              {(
                [
                  ["Overview", "#overview"],
                  ["Approach", "#approach"],
                  ["Reports", "#reports"],
                  ["Team", "#team"],
                ] as const
              ).map(([label, href]) => (
                <a
                  key={href}
                  href={href}
                  className={navPill}
                >
                  {label}
                </a>
              ))}
            </nav>
          </div>
        </header>

        <main>
          <section id="overview" className="px-4 py-16 sm:px-6 sm:py-20 md:py-24">
            <div className="mx-auto max-w-6xl text-center">
              <p
                className={`text-sm font-semibold uppercase tracking-[0.2em] ${eyebrowMuted}`}
              >
                CS492 · Bilkent University
              </p>
              <h1
                className={`mt-4 bg-gradient-to-br bg-clip-text text-[clamp(2rem,5vw,3.5rem)] font-bold leading-tight tracking-tight text-transparent ${heroTitleGradient}`}
              >
                Consensia
              </h1>
              <p
                className={`mx-auto mt-5 max-w-2xl text-lg leading-relaxed sm:text-xl ${bodyMuted}`}
              >
                Run structured, multi-persona debates on technical questions, attach evidence, and
                get a judge-written consensus you can inspect—not a single black-box answer.
                <br />
                <em className={bodyMuted2}>Built for transparent trade-off thinking in software teams.</em>
              </p>
              <div className="mx-auto mt-12 w-full max-w-sm space-y-3.5 sm:max-w-md">
                <div className="flex gap-3.5">
                  <Link
                    to="/register"
                    className="flex flex-1 items-center justify-center rounded-3xl bg-gradient-to-r from-purple-600 to-fuchsia-600 px-4 py-4 text-center text-sm font-semibold text-white shadow-md shadow-black/25 transition hover:opacity-95 active:scale-[0.99] light:shadow-violet-300/40 sm:text-base"
                  >
                    Sign up
                  </Link>
                  <Link to="/login" className={homeCtaTile}>
                    Log in
                  </Link>
                </div>
                <Link to="/app" className={homeCtaTileFull}>
                  Open workspace
                </Link>
              </div>
            </div>
          </section>

          <section
            id="approach"
            className={`border-t px-4 py-16 sm:px-6 sm:py-20 ${sectionRule}`}
          >
            <div className="mx-auto max-w-6xl">
              <p
                className={`text-sm font-semibold uppercase tracking-[0.2em] ${eyebrowMuted}`}
              >
                How it works
              </p>
              <h2
                className={`mt-2 bg-gradient-to-r bg-clip-text text-3xl font-bold tracking-tight text-transparent md:text-4xl ${sectionTitleGradient}`}
              >
                Approach
              </h2>
              <div
                className={`mt-2 h-0.5 w-14 rounded-full bg-gradient-to-r ${dividerAccent}`}
              />
              <p className={`mt-6 max-w-3xl text-lg leading-relaxed ${bodyMuted}`}>
                Serious software choices—architecture, implementation, testing, security, scalability, usability,
                cost—usually mean <strong className="text-purple-100 light:text-violet-900">trade-offs</strong>, not a
                single “right” answer. In real teams, people with different roles argue it out, but those conversations
                are <strong className="text-purple-100 light:text-violet-900">slow</strong>, ad hoc, and hard to replay in
                a structured way. A lone chatbot reply can hide assumptions and bury alternatives. Consensia is built to
                make AI-assisted decisions more{" "}
                <strong className="text-purple-100 light:text-violet-900">transparent and inspectable</strong>: you see
                competing lines of reasoning before accepting a recommendation.
              </p>
              <p className={`mt-5 max-w-3xl text-lg leading-relaxed ${bodyMuted}`}>
                In practice, you assemble a <strong className="text-purple-100 light:text-violet-900">council</strong> of
                personas—defaults you can edit, profiles from a <strong className="text-purple-100 light:text-violet-900">CV</strong>, or grounded{" "}
                <strong className="text-purple-100 light:text-violet-900">researcher-style</strong> personas from
                publication data. Each persona answers in parallel; you can run{" "}
                <strong className="text-purple-100 light:text-violet-900">multi-round</strong> debates so later rounds
                see the prior transcript. A <strong className="text-purple-100 light:text-violet-900">Judge</strong> model
                produces a consensus with explicit summary and reasoning.{" "}
                <strong className="text-purple-100 light:text-violet-900">Two-pass calibration</strong> scores topic
                relevance and argument quality so the judge weights stronger, on-topic contributions. Attach{" "}
                <strong className="text-purple-100 light:text-violet-900">PDFs, DOCX, or images</strong> as evidence;
                signed-in users get <strong className="text-purple-100 light:text-violet-900">saved sessions</strong> with
                history and a rolling context window for follow-ups.
              </p>
              <div className="mt-10 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
                <div className={cardSurface}>
                  <h3 className={`text-lg font-semibold ${formHeading}`}>
                    Debate &amp; consensus
                  </h3>
                  <p className={`mt-3 text-sm leading-relaxed sm:text-base ${bodyMuted}`}>
                    Parallel persona calls per round, optional multi-round rebuttals, then a judge synthesis with
                    summary and reasoning—so you can compare viewpoints instead of trusting one opaque answer.
                  </p>
                </div>
                <div className={cardSurface}>
                  <h3 className={`text-lg font-semibold ${formHeading}`}>
                    Personas &amp; evidence
                  </h3>
                  <p className={`mt-3 text-sm leading-relaxed sm:text-base ${bodyMuted}`}>
                    Manual personas and curated defaults, CV-driven generation, researcher-backed profiles, favorites,
                    and file attachments so answers stay tied to the material you provide.
                  </p>
                </div>
                <div className={cardSurface}>
                  <h3 className={`text-lg font-semibold ${formHeading}`}>
                    Platform &amp; delivery
                  </h3>
                  <p className={`mt-3 text-sm leading-relaxed sm:text-base ${bodyMuted}`}>
                    <strong className="text-purple-100 light:text-violet-900">React</strong>,{" "}
                    <strong className="text-purple-100 light:text-violet-900">TypeScript</strong>, and{" "}
                    <strong className="text-purple-100 light:text-violet-900">Vite</strong> on the frontend;{" "}
                    <strong className="text-purple-100 light:text-violet-900">FastAPI</strong> and{" "}
                    <strong className="text-purple-100 light:text-violet-900">PostgreSQL</strong> on the backend;
                    configurable LLM providers; <strong className="text-purple-100 light:text-violet-900">Docker Compose</strong>{" "}
                    for a consistent dev stack. Accounts, email verification, daily quotas, and an admin stats view round
                    out the product surface.
                  </p>
                </div>
              </div>
            </div>
          </section>

          <section
            id="reports"
            className={`border-t px-4 py-16 sm:px-6 sm:py-20 ${sectionRule}`}
          >
            <div className="mx-auto max-w-6xl">
              <p
                className={`text-sm font-semibold uppercase tracking-[0.2em] ${eyebrowMuted}`}
              >
                Documentation
              </p>
              <h2
                className={`mt-2 bg-gradient-to-r bg-clip-text text-3xl font-bold tracking-tight text-transparent md:text-4xl ${sectionTitleGradient}`}
              >
                Reports &amp; minutes
              </h2>
              <div
                className={`mt-2 h-0.5 w-14 rounded-full bg-gradient-to-r ${dividerAccent}`}
              />
              <p className={`mt-6 max-w-3xl text-lg leading-relaxed ${bodyMuted}`}>
                Official course documents and meeting minutes — open each file in a new tab.
              </p>

              <div className="mt-10 grid gap-10 lg:grid-cols-2 lg:gap-12">
                <div className="min-w-0">
                  <h3
                    className={`text-xl font-bold tracking-tight text-transparent bg-gradient-to-r bg-clip-text md:text-2xl ${sectionTitleGradient}`}
                  >
                    Project reports
                  </h3>
                  <div
                    className={`mt-2 h-0.5 w-10 rounded-full bg-gradient-to-r ${dividerAccent}`}
                  />
                  <div className="mt-5 space-y-3">
                    {projectReports.map(([label, path]) => (
                      <a
                        key={path}
                        href={publicAssetUrl(path)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={reportRow}
                      >
                        <span className="min-w-0 flex-1 pr-3 font-medium text-[var(--c-fg)]">
                          {label}
                        </span>
                        <span className={`shrink-0 ${docLinkHint}`} aria-hidden>
                          PDF →
                        </span>
                      </a>
                    ))}
                  </div>
                </div>

                <div className="min-w-0">
                  <h3
                    className={`text-xl font-bold tracking-tight text-transparent bg-gradient-to-r bg-clip-text md:text-2xl ${sectionTitleGradient}`}
                  >
                    Meeting minutes
                  </h3>
                  <div
                    className={`mt-2 h-0.5 w-10 rounded-full bg-gradient-to-r ${dividerAccent}`}
                  />
                  <div className="mt-5 space-y-3">
                    {minuteReports.map(([label, path]) => (
                      <a
                        key={path}
                        href={publicAssetUrl(path)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={reportRow}
                      >
                        <span className="min-w-0 flex-1 pr-3 font-medium text-[var(--c-fg)]">
                          {label}
                        </span>
                        <span className={`shrink-0 ${docLinkHint}`} aria-hidden>
                          Open →
                        </span>
                      </a>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section
            id="team"
            className={`border-t px-4 py-16 sm:px-6 sm:py-20 ${sectionRule}`}
          >
            <div className="mx-auto max-w-6xl">
              <p
                className={`text-sm font-semibold uppercase tracking-[0.2em] ${eyebrowMuted}`}
              >
                People
              </p>
              <h2
                className={`mt-2 bg-gradient-to-r bg-clip-text text-3xl font-bold tracking-tight text-transparent md:text-4xl ${sectionTitleGradient}`}
              >
                Team &amp; advisors
              </h2>
              <div
                className={`mt-2 h-0.5 w-14 rounded-full bg-gradient-to-r ${dividerAccent}`}
              />
              <div className="mt-10 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
                <div className={cardSurface}>
                  <h3 className={`text-lg font-semibold ${formHeading}`}>
                    Project team
                  </h3>
                  <ul className={`mt-4 space-y-2 ${bodyMuted}`}>
                    {teamMembers.map((member) => (
                      <li key={member}>{member}</li>
                    ))}
                  </ul>
                </div>
                <div className={cardSurface}>
                  <h3 className={`text-lg font-semibold ${formHeading}`}>
                    Supervisors &amp; advisors
                  </h3>
                  <div className="mt-4 border-b border-purple-300/10 pb-5 light:border-violet-200/70">
                    <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-fuchsia-300/80 light:text-fuchsia-800">
                      Supervisor
                    </h4>
                    <ul>
                      <li className={bodyMuted}>
                        Prof. Anıl Koyuncu
                        <span className="mt-1 block text-sm font-normal text-purple-400/90 light:text-violet-600">
                          Department of Computer Engineering
                          <br />
                          Bilkent University
                        </span>
                      </li>
                    </ul>
                  </div>
                  <div>
                    <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-fuchsia-300/80 light:text-fuchsia-800">
                      Innovation expert
                    </h4>
                    <ul>
                      <li className={bodyMuted}>Haluk Altunel</li>
                    </ul>
                  </div>
                </div>
                <div className={cardSurface}>
                  <h3 className={`text-lg font-semibold ${formHeading}`}>
                    Project roadmap
                  </h3>
                  <p className={`mt-3 text-sm leading-relaxed sm:text-base ${bodyMuted}`}>
                    Requirements and architecture → core debate and judge flow → persona sources (CV, researcher)
                    and attachments → auth, sessions, quotas, and admin → integration testing and deployment hardening
                    → optional follow-ons such as streaming responses and richer inter-persona debate.
                  </p>
                </div>
              </div>
            </div>
          </section>
        </main>

        <footer
          className={`border-t px-4 py-12 text-center sm:px-6 ${sectionRule}`}
        >
          <div className="mx-auto max-w-6xl">
            <a
              href="https://github.com/AmirAhanii/Consensia"
              target="_blank"
              rel="noopener noreferrer"
              className={homeHeroSecondaryCta}
            >
              <svg
                width="28"
                height="28"
                viewBox="0 0 24 24"
                fill="currentColor"
                className="text-[var(--c-fg-hint)]"
                aria-hidden
              >
                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
              </svg>
              <span>GitHub</span>
            </a>
            <p className={`mt-8 text-sm ${bodyMuted2}`}>
              © {year} Consensia — Multi-agent reasoning and evaluation for software engineering
            </p>
          </div>
        </footer>
      </div>
    </>
  );
}
