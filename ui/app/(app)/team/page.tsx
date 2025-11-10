export default function TeamPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Team</h1>
      <div className="rounded-xl border border-border bg-panel overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-panel-alt text-text-dim">
            <tr>
              <th className="text-left px-4 py-2">User</th>
              <th className="text-left px-4 py-2">Role</th>
              <th className="text-left px-4 py-2">Status</th>
              <th className="px-4 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {["Avery","Sam","Casey"].map((name, i) => (
              <tr key={i} className="border-t border-border">
                <td className="px-4 py-2">{name}</td>
                <td className="px-4 py-2"><span className="rounded-full bg-panel-alt px-2 py-1 text-xs">Admin</span></td>
                <td className="px-4 py-2 text-text-dim">Active</td>
                <td className="px-4 py-2 text-right"><button className="bg-panel-alt text-text rounded-xl px-3 py-1 border border-border">Edit</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <button className="bg-gold text-bg rounded-xl px-4 py-2">Invite User</button>
    </div>
  );
}
