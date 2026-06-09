import { fetchEventSource } from "@microsoft/fetch-event-source";
import { Loader2, Send } from "lucide-react";
import { useMemo, useState } from "react";
import FeedbackBar from "./FeedbackBar.jsx";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function ChatWindow({ token, onSources }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const sessionId = useMemo(() => crypto.randomUUID(), []);

  async function submit(event) {
    event.preventDefault();
    const query = input.trim();
    if (!query || streaming) return;
    setInput("");
    const assistantId = crypto.randomUUID();
    setMessages((current) => [...current, { role: "user", content: query }, { id: assistantId, role: "assistant", content: "", queryId: null }]);
    setStreaming(true);
    await fetchEventSource(`${API_URL}/query`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ query, session_id: sessionId }),
      onmessage(eventMessage) {
        if (eventMessage.event === "token") {
          setMessages((current) =>
            current.map((message) => (message.id === assistantId ? { ...message, content: `${message.content}${eventMessage.data}` } : message))
          );
        }
        if (eventMessage.event === "done") {
          const data = JSON.parse(eventMessage.data);
          onSources(data.sources || []);
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantId
                ? { ...message, queryId: data.query_id, hallucinationScore: data.hallucination_score }
                : message
            )
          );
          setStreaming(false);
        }
      },
      onerror(error) {
        setStreaming(false);
        throw error;
      }
    });
  }

  return (
    <section className="flex min-h-[620px] flex-col rounded border border-slate-200 bg-white">
      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        {messages.length === 0 ? (
          <div className="grid h-full place-items-center text-center text-sm text-slate-500">
            <p>Ask a clinical or biomedical literature question.</p>
          </div>
        ) : null}
        {messages.map((message, index) => (
          <div key={message.id || `${message.role}-${index}`} className={message.role === "user" ? "ml-auto max-w-[78%]" : "mr-auto max-w-[88%]"}>
            <div className={`rounded px-4 py-3 text-sm leading-6 ${message.role === "user" ? "bg-teal-700 text-white" : "border border-slate-200 bg-slate-50 text-slate-900"}`}>
              {message.content || (message.role === "assistant" && streaming ? <span className="inline-flex items-center gap-2"><Loader2 size={15} className="animate-spin" /> Thinking</span> : null)}
            </div>
            {message.role === "assistant" && message.content ? (
              <>
                {typeof message.hallucinationScore === "number" ? (
                  <p className="mt-2 text-xs text-slate-500">Grounding risk {message.hallucinationScore.toFixed(2)}</p>
                ) : null}
                <FeedbackBar token={token} queryId={message.queryId} />
              </>
            ) : null}
          </div>
        ))}
      </div>
      <form className="flex gap-2 border-t border-slate-200 p-3" onSubmit={submit}>
        <input className="min-w-0 flex-1 rounded border border-slate-300 px-3 text-sm outline-none focus:border-teal-600" value={input} onChange={(event) => setInput(event.target.value)} placeholder="Clinical question" />
        <button title="Send query" className="grid h-10 w-10 place-items-center rounded bg-teal-700 text-white hover:bg-teal-800 disabled:bg-slate-300" disabled={streaming} type="submit">
          {streaming ? <Loader2 size={17} className="animate-spin" /> : <Send size={17} />}
        </button>
      </form>
    </section>
  );
}
