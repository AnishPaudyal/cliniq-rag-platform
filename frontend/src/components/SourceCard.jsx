import { ChevronDown, ExternalLink } from "lucide-react";
import { useState } from "react";

export default function SourceCard({ source, index }) {
  const [open, setOpen] = useState(index === 0);
  const score = source.rerank_score ?? source.fusion_score ?? source.dense_score ?? 0;

  return (
    <article className="rounded border border-slate-200 bg-white">
      <button className="flex w-full items-start justify-between gap-3 px-4 py-3 text-left" onClick={() => setOpen(!open)} type="button">
        <span>
          <span className="block text-xs font-semibold uppercase text-teal-700">PMID {source.pmid || "unknown"}</span>
          <span className="mt-1 block text-sm font-medium text-slate-950">{source.title || "Untitled source"}</span>
        </span>
        <ChevronDown size={16} className={`mt-1 shrink-0 text-slate-500 transition ${open ? "rotate-180" : ""}`} />
      </button>
      {open ? (
        <div className="border-t border-slate-100 px-4 py-3 text-sm text-slate-700">
          <p className="mb-2 text-xs text-slate-500">{Array.isArray(source.authors) ? source.authors.slice(0, 4).join(", ") : "Authors unavailable"}</p>
          <p className="mb-3 rounded bg-teal-50 px-3 py-2 text-slate-800">{source.chunk_text}</p>
          <div className="flex items-center justify-between gap-3 text-xs">
            <span>Relevance {Number(score).toFixed(3)}</span>
            {source.source_url ? (
              <a className="inline-flex items-center gap-1 font-medium text-teal-700 hover:text-teal-900" href={source.source_url} target="_blank" rel="noreferrer">
                PubMed <ExternalLink size={13} />
              </a>
            ) : null}
          </div>
        </div>
      ) : null}
    </article>
  );
}
