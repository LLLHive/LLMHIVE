'use client';
import { useState } from "react";

export default function ComparePage() {
  const [prompt, setPrompt] = useState("");
  const models = ["GPT-5 Pro", "Claude 3.5", "Gemini 1.5"];
  const [selected, setSelected] = useState<string[]>([models[0], models[1]]);
  const toggle = (m: string) => setSelected((s) => (s.includes(m) ? s.filter((x) => x !== m) : [...s, m]));
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Model Comparison</h1>
      <div className="rounded-xl border border-border bg-panel p-4 space-y-3">
        <textarea className="w-full bg-panel-alt border border-border rounded-xl p-3 outline-none min-h-[90px]" placeholder="Enter a test prompt…" value={prompt} onChange={(e) => setPrompt(e.target.value)} />
        <div className="flex flex-wrap gap-2">
          {models.map((m) => (
            <button key={m} type="button" onClick={() => toggle(m)} className={`rounded-full px-3 py-1 text-sm border ${selected.includes(m) ? "bg-gold text-bg border-gold" : "bg-panel-alt text-text border-border"}`}>{m}</button>
          ))}
        </div>
        <div><button className="bg-gold text-bg rounded-xl px-4 py-2" disabled={!prompt.trim()}>Compare</button></div>
      </div>
      {selected.length > 0 && (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {selected.map((m) => (
            <div key={m} className="rounded-xl border border-border bg-panel p-4">
              <div className="text-sm text-text-dim">{m}</div>
              <div className="mt-2 text-sm">(Connect real outputs later; placeholder now.)</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
