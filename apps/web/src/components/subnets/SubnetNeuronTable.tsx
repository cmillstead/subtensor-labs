import type { SubnetNeuron } from "@/types";

function truncateKey(key: string): string {
  if (key.length <= 14) return key;
  return `${key.slice(0, 6)}...${key.slice(-6)}`;
}

interface SubnetNeuronTableProps {
  neurons: SubnetNeuron[];
  title: string;
}

export function SubnetNeuronTable({ neurons, title }: SubnetNeuronTableProps) {
  if (neurons.length === 0) {
    return (
      <div>
        <h3 className="mb-3 text-lg font-semibold text-text-primary">{title}</h3>
        <p className="text-sm text-text-muted">No data available.</p>
      </div>
    );
  }

  return (
    <div>
      <h3 id={`neuron-table-${title.replace(/\s+/g, "-").toLowerCase()}`} className="mb-3 text-lg font-semibold text-text-primary">{title}</h3>
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-sm" aria-labelledby={`neuron-table-${title.replace(/\s+/g, "-").toLowerCase()}`}>
          <thead>
            <tr className="border-b border-border bg-surface">
              <th className="px-3 py-2 text-left text-xs font-medium text-text-muted">
                UID
              </th>
              <th className="px-3 py-2 text-left text-xs font-medium text-text-muted">
                Hotkey
              </th>
              <th className="px-3 py-2 text-right text-xs font-medium text-text-muted">
                Stake (τ)
              </th>
              <th className="px-3 py-2 text-right text-xs font-medium text-text-muted">
                Incentive
              </th>
              <th className="px-3 py-2 text-right text-xs font-medium text-text-muted">
                Trust
              </th>
              <th className="px-3 py-2 text-center text-xs font-medium text-text-muted">
                Status
              </th>
            </tr>
          </thead>
          <tbody>
            {neurons.map((neuron) => (
              <tr
                key={neuron.uid}
                className="border-b border-border transition-colors hover:bg-zinc-800/50"
              >
                <td className="px-3 py-2 font-mono text-text-primary">
                  {neuron.uid}
                </td>
                <td className="px-3 py-2 font-mono text-text-secondary" title={neuron.hotkey}>
                  {truncateKey(neuron.hotkey)}
                </td>
                <td className="px-3 py-2 text-right font-mono text-text-primary">
                  {neuron.stake.toLocaleString("en-US", {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })}
                </td>
                <td className="px-3 py-2 text-right font-mono text-text-primary">
                  {neuron.incentive.toFixed(4)}
                </td>
                <td className="px-3 py-2 text-right font-mono text-text-primary">
                  {neuron.trust.toFixed(4)}
                </td>
                <td className="px-3 py-2 text-center">
                  <span
                    className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                      neuron.is_active
                        ? "bg-emerald-500/20 text-emerald-400"
                        : "bg-zinc-500/20 text-zinc-400"
                    }`}
                  >
                    {neuron.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
