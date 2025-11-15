export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Settings</h1>
      <section className="rounded-xl border border-border bg-panel p-4">
        <div className="font-semibold">Profile</div>
        <div className="grid sm:grid-cols-2 gap-3 mt-3">
          <input className="bg-panel-alt border border-border rounded-xl px-3 py-2" placeholder="Full name" />
          <input className="bg-panel-alt border border-border rounded-xl px-3 py-2" placeholder="Email" />
        </div>
        <div className="mt-3"><button className="bg-gold text-bg rounded-xl px-4 py-2">Save Profile</button></div>
      </section>
      <section className="rounded-xl border border-border bg-panel p-4">
        <div className="font-semibold">Appearance</div>
        <div className="mt-3 text-text-dim text-sm">Dark mode enforced by tokens.</div>
      </section>
    </div>
  );
}
