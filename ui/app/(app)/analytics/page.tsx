export default function AnalyticsPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Analytics</h1>
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {label: "Prompts (24h)", value: "1,284"},
          {label: "Tokens (24h)", value: "3.2M"},
          {label: "Cost (24h)", value: "$42.18"},
          {label: "Avg Latency", value: "1.8s"},
        ].map((c) => (
          <div key={c.label} className="rounded-xl border border-border bg-panel p-4">
            <div className="text-sm text-text-dim">{c.label}</div>
            <div className="text-2xl font-semibold mt-1">{c.value}</div>
          </div>
        ))}
      </div>
      <div className="grid lg:grid-cols-2 gap-4">
        <div className="rounded-xl border border-border bg-panel p-4">
          <div className="font-semibold">Usage Trend</div>
          <div className="text-sm text-text-dim mt-2">Connect charts later; placeholder.</div>
          <div className="h-48 bg-panel-alt/50 rounded-lg mt-3" />
        </div>
        <div className="rounded-xl border border-border bg-panel p-4">
          <div className="font-semibold">Cost by Provider</div>
          <div className="text-sm text-text-dim mt-2">Placeholder.</div>
          <div className="h-48 bg-panel-alt/50 rounded-lg mt-3" />
        </div>
      </div>
    </div>
  );
}
