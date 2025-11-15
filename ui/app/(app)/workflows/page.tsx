export default function WorkflowsPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Workflows</h1>
      <p className="text-text-dim">Your saved workflows will appear here. Run, edit, duplicate, or delete them.</p>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {[1,2,3,4,5,6].map((i) => (
          <div key={i} className="rounded-xl border border-border bg-panel p-4">
            <div className="text-sm text-text-dim">Workflow #{i}</div>
            <div className="mt-2 flex gap-2">
              <button className="bg-gold text-bg rounded-xl px-4 py-2">Run</button>
              <button className="bg-panel-alt text-text rounded-xl px-4 py-2 border border-border">Edit</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
