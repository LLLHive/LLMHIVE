export default function ProvidersPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Providers</h1>
      <div className="rounded-xl border border-border bg-panel p-4 space-y-3">
        {["OpenAI","Anthropic","Google","OpenRouter"].map((p) => (
          <div key={p} className="flex items-center justify-between border border-border rounded-lg p-3 bg-panel-alt/50">
            <div>
              <div className="font-medium">{p}</div>
              <div className="text-sm text-text-dim">Configure API key and enable models</div>
            </div>
            <div className="flex gap-2">
              <button className="bg-panel-alt text-text rounded-xl px-3 py-1 border border-border">Configure</button>
              <button className="bg-gold text-bg rounded-xl px-3 py-1">Enable</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
