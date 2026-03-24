/**
 * Default researcher cards shipped with the app (matches backend/data/raw_authors examples).
 * Always shown; the API can refresh/enrich the same IDs or append extras.
 */
export type ResearchSnapshotRow = {
  scholar_id: string;
  name: string | null;
  affiliation: string | null;
  preview?: string | null;
  filename: string;
};

export const BUNDLED_RESEARCH_SNAPSHOTS: ResearchSnapshotRow[] = [
  {
    scholar_id: "Fac_e58AAAAJ",
    name: "Steffen Herbold",
    affiliation: "University of Passau",
    filename: "Fac_e58AAAAJ_raw.json",
    preview:
      "ChatGPT and similar generative AI models have attracted hundreds of millions of users. We systematically assess AI-generated content through a large-scale study comparing…",
  },
  {
    scholar_id: "VlSBMuIAAAAJ",
    name: "Alexander Trautsch",
    affiliation: "University of Passau",
    filename: "VlSBMuIAAAAJ_raw.json",
    preview:
      "ChatGPT and similar generative AI models have attracted hundreds of millions of users. We systematically assess AI-generated content through a large-scale study comparing…",
  },
  {
    scholar_id: "WH-L4NoAAAAJ",
    name: "Alireza Aghamohammadi",
    affiliation: "Sharif University of Technology",
    filename: "WH-L4NoAAAAJ_raw.json",
    preview:
      "Tangled commits are changes to software that address multiple concerns at once. We estimate that between 17% and 32% of all changes in bug fixing commits modify the source…",
  },
];

export function mergeBundledResearchSnapshots(
  fromApi: ResearchSnapshotRow[]
): ResearchSnapshotRow[] {
  const apiById = new Map(fromApi.map((r) => [r.scholar_id, r]));
  const merged = BUNDLED_RESEARCH_SNAPSHOTS.map((b) => {
    const a = apiById.get(b.scholar_id);
    if (!a) return b;
    return {
      ...b,
      ...a,
      filename: a.filename || b.filename,
    };
  });
  const bundledIds = new Set(
    BUNDLED_RESEARCH_SNAPSHOTS.map((r) => r.scholar_id)
  );
  const extras = fromApi.filter((r) => !bundledIds.has(r.scholar_id));
  return [...merged, ...extras];
}
