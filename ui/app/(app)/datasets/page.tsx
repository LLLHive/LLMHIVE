export default function DatasetsPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Datasets</h1>
      <div className="rounded-xl border border-border bg-panel overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-panel-alt text-text-dim">
            <tr>
              <th className="text-left px-4 py-2">Name</th>
              <th className="text-left px-4 py-2">Type</th>
              <th className="text-left px-4 py-2">Status</th>
              <th className="text-left px-4 py-2">Size</th>
              <th className="px-4 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {[1,2,3].map((i) => (
              <tr key={i} className="border-t border-border">
                <td className="px-4 py-2">Dataset {i}</td>
                <td className="px-4 py-2 text-text-dim">Documents</td>
                <td className="px-4 py-2 text-text-dim">Indexed</td>
                <td className="px-4 py-2 text-text-dim">1.2 GB</td>
                <td className="px-4 py-2 text-right">
                  <button className="bg-panel-alt text-text rounded-xl px-3 py-1 border border-border">Re-index</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <button className="bg-gold text-bg rounded-xl px-4 py-2">Add Data Source</button>
    </div>
  );
}
