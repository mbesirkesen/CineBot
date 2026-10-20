export const GENRE_OPTIONS = [
  { label: "Tüm Türler", value: "" },
  { label: "Bilim Kurgu", value: "Science Fiction" },
  { label: "Aksiyon", value: "Action" },
  { label: "Gerilim", value: "Thriller" },
  { label: "Dram", value: "Drama" },
  { label: "Komedi", value: "Comedy" },
  { label: "Suç", value: "Crime" },
  { label: "Gizem", value: "Mystery" },
  { label: "Animasyon", value: "Animation" },
  { label: "Fantastik", value: "Fantasy" },
  { label: "Korku", value: "Horror" },
  { label: "Romantik", value: "Romance" },
];

export const QUICK_PROMPTS = [
  { label: "Uzay gerilimi", query: "Uzayda geçen karanlık bir gerilim filmi öner" },
  { label: "Beyin yakan gizem", query: "Beyin yakan, zihin bükücü bir gizem filmi öner" },
  { label: "Sürpriz sonlu", query: "Sürpriz sonlu psikolojik bir gerilim filmi öner" },
  { label: "Sıcak animasyon", query: "Sıcak ve büyülü bir animasyon filmi öner" },
];

/** Missing TMDB ratings are stored as 0. Show that as unknown instead of a real score. */
export function ratingLabel(vote: number): string {
  if (!vote || vote <= 0) return "puan yok";
  return vote.toFixed(1);
}

/** FAISS inner product on normalized vectors is cosine similarity, already between 0 and 1. */
export function matchPercent(score: number): number {
  const cosine = Math.max(0, Math.min(1, score));
  return Math.round(cosine * 100);
}

export function trailerSearchUrl(title: string, year?: number | null): string {
  const query = `${title} ${year ?? ""} trailer fragman`.replace(/\s+/g, " ").trim();
  return `https://www.youtube.com/results?search_query=${encodeURIComponent(query)}`;
}

export function openTrailer(title: string, year?: number | null): void {
  window.open(trailerSearchUrl(title, year), "_blank", "noopener,noreferrer");
}

export function recommendationReason(
  title: string,
  reply: string,
  fallback: string,
  year?: number | null,
): string {
  const needle = title.toLocaleLowerCase("tr");
  const lines = reply
    .split("\n")
    .map((line) => line.replace(/^\s*#{1,6}\s*/, "").replace(/#{1,6}\s*/g, "").trim())
    .filter(Boolean);
  const lowered = lines.map((line) => line.toLocaleLowerCase("tr"));
  // Prefer the heading line ("**Title (year)**") so a short title such as "Up"
  // does not latch onto an unrelated sentence that happens to contain the word.
  const headingIndex = lowered.findIndex(
    (line) =>
      line.includes(`**${needle}`) ||
      (year != null && line.includes(needle) && line.includes(`(${year})`)),
  );
  const start = headingIndex >= 0 ? headingIndex : lowered.findIndex((line) => line.includes(needle));
  if (start < 0) return fallback;

  const chunk = [lines[start]];
  const markerCount = (value: string) => value.split("||").length - 1;

  for (const line of lines.slice(start + 1)) {
    const open = markerCount(chunk.join("\n")) % 2 === 1;
    if (open && line.includes("||")) {
      const prefix = line.slice(0, line.indexOf("||") + 2);
      if (prefix.trim()) chunk.push(prefix);
      break;
    }
    const lower = line.toLocaleLowerCase("tr");
    const nextMovie = /\(\d{4}\)/.test(line) && !lower.includes(needle);
    if (nextMovie) break;
    chunk.push(line);
    if (chunk.length >= 6 && markerCount(chunk.join("\n")) % 2 === 0) break;
  }
  return chunk.join("\n\n");
}
