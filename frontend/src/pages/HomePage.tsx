import React, { useEffect } from "react";
import { Link } from "react-router-dom";
const projectReports = [
  [
    "Project Information Form",
    "/assets/CS491_Project_Information_Form (2).pdf",
  ],
  ["Assessment of Innovation Form", "/assets/Assessment_Innovation_Expert.pdf"],
  [
    "Project Specification Document",
    "/assets/T2526_Project_Specification_Document.pdf",
  ],
  [
    "Analysis and Requirements Report",
    "/assets/T2526_Analysis_and_Requirements_Report.docx.pdf",
  ],
] as const;
const minuteReports = [
  [
    "Meeting Minute 01",
    "/assets/TeamID_MeetingMinutesReport_01_26102025_v1 (1).pdf",
  ],
  [
    "Meeting Minute 02",
    "/assets/T2526_MeetingMinutesReport_02_24112025_v1.doc",
  ],
] as const;
const teamMembers = [
  "Amir Hossein Ahani",
  "Ahmed Hatem Haikal",
  "Türker Köken",
  "İrfan Hakan Karakoç",
  "Mehmet Hakan Yavuz",
];
export default function Homepage() {
  useEffect(() => {
    document.title =
      "Consensia — Multi-agent reasoning and evaluation for software engineering";
  }, []);
  const year = new Date().getFullYear();
  return (
    <div className="relative min-h-screen overflow-x-hidden bg-[#0d0618] text-[#F5F3FF]">
      {" "}
      <div className="pointer-events-none absolute inset-0">
        {" "}
        <div className="absolute left-0 top-0 h-[420px] w-[420px] bg-purple-400/10 blur-3xl" />{" "}
        <div className="absolute right-0 top-0 h-[420px] w-[420px] bg-fuchsia-500/10 blur-3xl" />{" "}
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(167,139,250,0.10),transparent_40%)]" />{" "}
      </div>{" "}
      <header className="sticky top-0 z-50 border-b border-purple-300/15 bg-[#0d0618]/85 backdrop-blur-md">
        {" "}
        <div className="mx-auto flex max-w-[1080px] items-center justify-between gap-4 px-6 py-4">
          {" "}
          <div className="flex items-center gap-3 text-[20px] font-extrabold tracking-[0.3px]">
            {" "}
            <div className="flex h-[38px] w-[38px] items-center justify-center">
              {" "}
              <svg
                viewBox="0 0 64 64"
                xmlns="http://www.w3.org/2000/svg"
                className="h-[38px] w-[38px]"
              >
                {" "}
                <defs>
                  {" "}
                  <linearGradient
                    id="consensia-logo-gradient"
                    x1="0"
                    y1="0"
                    x2="1"
                    y2="1"
                  >
                    {" "}
                    <stop offset="0" stopColor="#C4B5FD" />{" "}
                    <stop offset="1" stopColor="#8B5CF6" />{" "}
                  </linearGradient>{" "}
                </defs>{" "}
                <path
                  d="M8 18 L28 32 L8 46"
                  fill="none"
                  stroke="url(#consensia-logo-gradient)"
                  strokeWidth="6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />{" "}
                <path
                  d="M56 18 L36 32 L56 46"
                  fill="none"
                  stroke="url(#consensia-logo-gradient)"
                  strokeWidth="6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />{" "}
                <circle
                  cx="32"
                  cy="32"
                  r="3.6"
                  fill="url(#consensia-logo-gradient)"
                />{" "}
              </svg>{" "}
            </div>{" "}
            <span className="bg-gradient-to-r from-[#F5F3FF] to-[#C7B8FF] bg-clip-text text-transparent">
              {" "}
              Consensia{" "}
            </span>{" "}
          </div>{" "}
          <nav className="hidden items-center gap-2 md:flex">
            {" "}
            {[
              ["Overview", "#overview"],
              ["Prototype & Approach", "#prototype"],
              ["Project Reports", "#reports"],
              ["Team", "#team"],
            ].map(([label, href]) => (
              <a
                key={href}
                href={href}
                className="rounded-[10px] px-[14px] py-2 text-[15px] font-medium text-[#C7B8FF] transition hover:bg-purple-400/10 hover:text-white"
              >
                {" "}
                {label}{" "}
              </a>
            ))}{" "}
            <Link
              to="/register"
              className="ml-2 rounded-lg border border-purple-300/20 bg-purple-500/10 px-4 py-2 text-sm font-semibold text-purple-100 transition hover:bg-purple-400/20 hover:text-white"
            >
              Sign Up
            </Link>
          </nav>{" "}
        </div>{" "}
      </header>{" "}
      <main className="relative z-10">
        {" "}
        <section id="overview" className="px-6 py-20 md:py-24">
          {" "}
          <div className="mx-auto max-w-[1080px] text-center">
            {" "}
            <h1 className="bg-gradient-to-br from-[#F5F3FF] to-[#C7B8FF] bg-clip-text text-[clamp(32px,5vw,56px)] font-bold leading-[1.1] text-transparent">
              {" "}
              Consensia{" "}
            </h1>{" "}
            <p className="mx-auto mt-4 max-w-[820px] text-[20px] leading-relaxed text-[#d0c2ff]">
              {" "}
              Multi-agent reasoning and evaluation for software engineering.{" "}
              <br /> <em>Because truth deserves more than one mind.</em>{" "}
            </p>{" "}
            <div className="mt-8">
              {" "}
              <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
                <Link
                  to="/register"
                  className="inline-flex items-center justify-center rounded-xl border border-purple-300/20 bg-gradient-to-r from-purple-500/20 to-fuchsia-500/20 px-8 py-4 text-lg font-semibold text-purple-50 shadow-lg shadow-purple-950/40 transition hover:-translate-y-0.5 hover:border-purple-300/40 hover:from-purple-500/30 hover:to-fuchsia-500/30"
                >
                  Sign Up
                </Link>

                <Link
                  to="/app"
                  className="inline-flex items-center justify-center rounded-xl border border-purple-800/40 bg-black/40 px-8 py-4 text-lg font-semibold text-purple-200 transition hover:border-purple-600 hover:text-white"
                >
                  Open Prototype
                </Link>
              </div>
            </div>{" "}
          </div>{" "}
        </section>{" "}
        <section id="prototype" className="px-6 py-20">
          {" "}
          <div className="mx-auto max-w-[1080px]">
            {" "}
            <h2 className="inline-block bg-gradient-to-r from-[#F5F3FF] to-[#C7B8FF] bg-clip-text text-[clamp(24px,3vw,36px)] font-bold text-transparent">
              {" "}
              Prototype &amp; Approach{" "}
            </h2>{" "}
            <div className="mt-2 h-[3px] w-[60px] rounded bg-gradient-to-r from-[#A78BFA] to-transparent" />{" "}
            <p className="mt-6 max-w-[900px] text-[18px] leading-[1.6] text-[#d3c8ff]">
              {" "}
              Our prototype allows users to create multiple AI personas with
              different software-engineering and business roles — such as{" "}
              <strong>CTO</strong>, <strong>Software Architect</strong>,{" "}
              <strong>Senior Developer</strong>, <strong>QA</strong>,{" "}
              <strong>SRE</strong>, <strong>Security Engineer</strong>, as well
              as <strong>Product Manager</strong>, <strong>Finance/CFO</strong>,
              and <strong>Operations/Management</strong>. Each agent answers a
              technical or strategic question; a <strong>Judge LLM</strong>{" "}
              analyzes all outputs and scores them for{" "}
              <em>consistency, fairness, and reasoning clarity</em>. The judge’s
              consensus is then validated against human-tagged data.{" "}
            </p>{" "}
            <div className="mt-7 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
              {" "}
              <div className="rounded-[18px] border border-purple-300/20 bg-gradient-to-b from-[rgba(38,18,68,0.6)] to-[rgba(22,12,40,0.7)] p-6 shadow-[0_10px_35px_rgba(0,0,0,0.5)] transition hover:-translate-y-1 hover:border-purple-300/35">
                {" "}
                <h3 className="text-xl font-semibold text-[#E9E4FF]">
                  System Concept
                </h3>{" "}
                <p className="mt-3 text-[18px] leading-[1.6] text-[#e3dcff]">
                  {" "}
                  Multi-agent discussion leading to a final, explainable verdict
                  generated by the Judge LLM, combining text reasoning with
                  evidence from tools.{" "}
                </p>{" "}
              </div>{" "}
              <div className="rounded-[18px] border border-purple-300/20 bg-gradient-to-b from-[rgba(38,18,68,0.6)] to-[rgba(22,12,40,0.7)] p-6 shadow-[0_10px_35px_rgba(0,0,0,0.5)] transition hover:-translate-y-1 hover:border-purple-300/35">
                {" "}
                <h3 className="text-xl font-semibold text-[#E9E4FF]">
                  Stakeholders
                </h3>{" "}
                <p className="mt-3 text-[18px] leading-[1.6] text-[#e3dcff]">
                  {" "}
                  Technical roles (CTO, Architect, Dev, QA, SRE, Security)
                  balanced with business roles (Product, Finance/CFO,
                  Ops/Management) to reflect real enterprise trade-offs.{" "}
                </p>{" "}
              </div>{" "}
              <div className="rounded-[18px] border border-purple-300/20 bg-gradient-to-b from-[rgba(38,18,68,0.6)] to-[rgba(22,12,40,0.7)] p-6 shadow-[0_10px_35px_rgba(0,0,0,0.5)] transition hover:-translate-y-1 hover:border-purple-300/35">
                {" "}
                <h3 className="text-xl font-semibold text-[#E9E4FF]">
                  Architecture
                </h3>{" "}
                <p className="mt-3 text-[18px] leading-[1.6] text-[#e3dcff]">
                  {" "}
                  Event-driven orchestration for scalability and real-time
                  updates. Frontend in <strong>React</strong>, backend with{" "}
                  <strong>Python</strong>, automation via <strong>n8n</strong>
                  .{" "}
                </p>{" "}
              </div>{" "}
            </div>{" "}
          </div>{" "}
        </section>{" "}
        <section id="reports" className="px-6 py-20">
          {" "}
          <div className="mx-auto max-w-[1080px]">
            {" "}
            <h2 className="inline-block bg-gradient-to-r from-[#F5F3FF] to-[#C7B8FF] bg-clip-text text-[clamp(24px,3vw,36px)] font-bold text-transparent">
              {" "}
              Project Reports{" "}
            </h2>{" "}
            <div className="mt-2 h-[3px] w-[60px] rounded bg-gradient-to-r from-[#A78BFA] to-transparent" />{" "}
            <p
              className="mt-6 text-[18px] leading-[1.6] text-[#d3c8ff]"
              style={{ marginBottom: 28 }}
            >
              {" "}
              Official documentation submitted so far.{" "}
            </p>{" "}
            <div className="max-w-[800px] space-y-3">
              {" "}
              {projectReports.map(([label, href]) => (
                <a
                  key={href}
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between rounded-xl bg-purple-400/10 px-5 py-[18px] text-[#F5F3FF] transition hover:translate-x-1.5 hover:bg-purple-400/15"
                >
                  {" "}
                  <span className="font-medium text-[#E9E4FF]">
                    {label}
                  </span>{" "}
                </a>
              ))}{" "}
            </div>{" "}
            <h2
              className="inline-block bg-gradient-to-r from-[#F5F3FF] to-[#C7B8FF] bg-clip-text text-[clamp(24px,3vw,36px)] font-bold text-transparent"
              style={{ marginTop: 60, marginBottom: 28 }}
            >
              {" "}
              Minute Reports{" "}
            </h2>{" "}
            <div className="max-w-[800px] space-y-3">
              {" "}
              {minuteReports.map(([label, href]) => (
                <a
                  key={href}
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between rounded-xl bg-purple-400/10 px-5 py-[18px] text-[#F5F3FF] transition hover:translate-x-1.5 hover:bg-purple-400/15"
                >
                  {" "}
                  <span className="font-medium text-[#E9E4FF]">
                    {label}
                  </span>{" "}
                </a>
              ))}{" "}
            </div>{" "}
          </div>{" "}
        </section>{" "}
        <section id="team" className="px-6 py-20">
          {" "}
          <div className="mx-auto max-w-[1080px]">
            {" "}
            <h2 className="inline-block bg-gradient-to-r from-[#F5F3FF] to-[#C7B8FF] bg-clip-text text-[clamp(24px,3vw,36px)] font-bold text-transparent">
              {" "}
              Team &amp; Advisors{" "}
            </h2>{" "}
            <div className="mt-7 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
              {" "}
              <div className="rounded-[18px] border border-purple-300/20 bg-gradient-to-b from-[rgba(38,18,68,0.6)] to-[rgba(22,12,40,0.7)] p-6 shadow-[0_10px_35px_rgba(0,0,0,0.5)]">
                {" "}
                <h3 className="text-xl font-semibold text-[#E9E4FF]">
                  Project Team
                </h3>{" "}
                <ul className="mt-3 space-y-2 leading-[1.8]">
                  {" "}
                  {teamMembers.map((member) => (
                    <li key={member} className="text-[#e3dcff]">
                      {" "}
                      {member}{" "}
                    </li>
                  ))}{" "}
                </ul>{" "}
              </div>{" "}
              <div className="rounded-[18px] border border-purple-300/20 bg-gradient-to-b from-[rgba(38,18,68,0.6)] to-[rgba(22,12,40,0.7)] p-6 shadow-[0_10px_35px_rgba(0,0,0,0.5)]">
                {" "}
                <h3 className="text-xl font-semibold text-[#E9E4FF]">
                  {" "}
                  Supervisors &amp; Advisors{" "}
                </h3>{" "}
                <div className="mb-6 mt-4 border-b border-purple-300/10 pb-5">
                  {" "}
                  <h4 className="mb-2 text-[13px] font-semibold uppercase tracking-[1px] text-[#C7B8FF]">
                    {" "}
                    Supervisors{" "}
                  </h4>{" "}
                  <ul className="space-y-1">
                    {" "}
                    <li className="text-[#e3dcff]">Mert Bıçakçı</li>{" "}
                    <li className="text-[#e3dcff]">İlker Burak Kurt</li>{" "}
                  </ul>{" "}
                </div>{" "}
                <div className="mb-6 border-b border-purple-300/10 pb-5">
                  {" "}
                  <h4 className="mb-2 text-[13px] font-semibold uppercase tracking-[1px] text-[#C7B8FF]">
                    {" "}
                    Advisor{" "}
                  </h4>{" "}
                  <ul>
                    {" "}
                    <li className="text-[#e3dcff]">
                      {" "}
                      Prof. Anıl Koyuncu{" "}
                      <span className="mt-1 block text-[0.9em] font-normal opacity-75">
                        {" "}
                        Department of Computer Engineering <br /> Bilkent
                        University{" "}
                      </span>{" "}
                    </li>{" "}
                  </ul>{" "}
                </div>{" "}
                <div>
                  {" "}
                  <h4 className="mb-2 text-[13px] font-semibold uppercase tracking-[1px] text-[#C7B8FF]">
                    {" "}
                    Innovation Expert{" "}
                  </h4>{" "}
                  <ul>
                    {" "}
                    <li className="text-[#e3dcff]">Haluk Altunel</li>{" "}
                  </ul>{" "}
                </div>{" "}
              </div>{" "}
              <div className="rounded-[18px] border border-purple-300/20 bg-gradient-to-b from-[rgba(38,18,68,0.6)] to-[rgba(22,12,40,0.7)] p-6 shadow-[0_10px_35px_rgba(0,0,0,0.5)]">
                {" "}
                <h3 className="text-xl font-semibold text-[#E9E4FF]">
                  Project Roadmap
                </h3>{" "}
                <p className="mt-3 text-[18px] leading-[1.6] text-[#e3dcff]">
                  {" "}
                  Research → UI design → Features → LLM self-judging automation
                  → Prototype → Analysis &amp; statistics → Evaluation → MVP →
                  Publication{" "}
                </p>{" "}
              </div>{" "}
            </div>{" "}
          </div>{" "}
        </section>{" "}
      </main>{" "}
      <footer className="px-6 py-10 text-center text-[#cfc3ff]">
        {" "}
        <div className="mb-6 text-center">
          {" "}
          <a
            href="https://github.com/AmirAhanii/Consensia"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center rounded-xl border border-purple-300/25 bg-gradient-to-r from-purple-500/15 to-fuchsia-500/15 px-8 py-[18px] text-lg font-semibold text-white transition hover:-translate-y-0.5 hover:border-purple-300/40"
          >
            {" "}
            <svg
              width="36"
              height="36"
              viewBox="0 0 24 24"
              fill="currentColor"
              className="mr-4"
            >
              {" "}
              <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />{" "}
            </svg>{" "}
            <span>GitHub</span>{" "}
          </a>{" "}
        </div>{" "}
        <p>
          {" "}
          © {year} Consensia — Multi-agent reasoning and evaluation for software
          engineering{" "}
        </p>{" "}
      </footer>{" "}
    </div>
  );
}
