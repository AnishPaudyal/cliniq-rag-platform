import { Send, ThumbsDown, ThumbsUp } from "lucide-react";
import { useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function FeedbackBar({ token, queryId }) {
  const [thumbs, setThumbs] = useState("neutral");
  const [comment, setComment] = useState("");
  const [sent, setSent] = useState(false);

  async function submit() {
    if (!queryId) return;
    await fetch(`${API_URL}/feedback`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        query_id: queryId,
        rating: thumbs === "up" ? 5 : thumbs === "down" ? 2 : 3,
        thumbs,
        comment
      })
    });
    setSent(true);
  }

  return (
    <div className="mt-3 flex flex-col gap-2 border-t border-slate-100 pt-3">
      <div className="flex items-center gap-2">
        <button title="Positive feedback" className={`grid h-8 w-8 place-items-center rounded border ${thumbs === "up" ? "border-teal-700 bg-teal-50 text-teal-800" : "border-slate-200 text-slate-600"}`} onClick={() => setThumbs("up")} type="button">
          <ThumbsUp size={16} />
        </button>
        <button title="Negative feedback" className={`grid h-8 w-8 place-items-center rounded border ${thumbs === "down" ? "border-red-600 bg-red-50 text-red-700" : "border-slate-200 text-slate-600"}`} onClick={() => setThumbs("down")} type="button">
          <ThumbsDown size={16} />
        </button>
        <input className="h-8 min-w-0 flex-1 rounded border border-slate-200 px-3 text-sm outline-none focus:border-teal-600" value={comment} onChange={(event) => setComment(event.target.value)} placeholder="Comment" />
        <button title="Submit feedback" className="grid h-8 w-8 place-items-center rounded bg-teal-700 text-white hover:bg-teal-800" onClick={submit} type="button">
          <Send size={15} />
        </button>
      </div>
      {sent ? <p className="text-xs text-teal-700">Feedback stored.</p> : null}
    </div>
  );
}
