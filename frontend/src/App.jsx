import { LogOut, ShieldPlus } from "lucide-react";
import { useState } from "react";
import AuthModal from "./components/AuthModal.jsx";
import ChatWindow from "./components/ChatWindow.jsx";
import SourceCard from "./components/SourceCard.jsx";

export default function App() {
  const [token, setToken] = useState(localStorage.getItem("cliniq_token"));
  const [sources, setSources] = useState([]);

  function logout() {
    localStorage.removeItem("cliniq_token");
    setToken(null);
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      {!token ? <AuthModal onToken={setToken} /> : null}
      <section className="mx-auto flex max-w-7xl flex-col gap-5 px-4 py-5 sm:px-6">
        <header className="flex flex-col gap-3 border-b border-slate-200 pb-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded bg-teal-700 text-white">
              <ShieldPlus size={21} />
            </span>
            <div>
              <h1 className="text-2xl font-semibold tracking-normal text-teal-800">ClinIQ</h1>
              <p className="text-sm text-slate-600">Clinical Knowledge AI Assistant. Not a substitute for professional medical judgment.</p>
            </div>
          </div>
          {token ? (
            <button title="Sign out" className="inline-flex h-9 items-center justify-center gap-2 rounded border border-slate-300 px-3 text-sm text-slate-700 hover:bg-white" onClick={logout} type="button">
              <LogOut size={16} /> Sign out
            </button>
          ) : null}
        </header>
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_380px]">
          <ChatWindow token={token} onSources={setSources} />
          <aside className="min-h-[620px] rounded border border-slate-200 bg-slate-100/60 p-3">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase text-slate-600">Cited Sources</h2>
              <span className="text-xs text-slate-500">{sources.length}</span>
            </div>
            <div className="space-y-3">
              {sources.length ? sources.map((source, index) => <SourceCard key={`${source.pmid}-${source.chunk_index}-${index}`} source={source} index={index} />) : <p className="rounded border border-dashed border-slate-300 bg-white p-4 text-sm text-slate-500">Sources appear after a grounded response.</p>}
            </div>
          </aside>
        </div>
      </section>
    </main>
  );
}
