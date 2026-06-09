export default function App() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <section className="mx-auto flex max-w-6xl flex-col gap-6 px-6 py-8">
        <header className="border-b border-slate-200 pb-4">
          <h1 className="text-2xl font-semibold tracking-normal text-teal-800">ClinIQ</h1>
          <p className="text-sm text-slate-600">
            Clinical Knowledge AI Assistant. Not a substitute for professional medical judgment.
          </p>
        </header>
        <div className="rounded border border-slate-200 bg-white p-6 text-sm text-slate-700">
          Frontend scaffold. Streaming chat UI is implemented in Phase 7.
        </div>
      </section>
    </main>
  );
}
