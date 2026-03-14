export default function LandingPage() {
  return (
    <div className="flex flex-col items-center gap-12 py-20">
      <div className="text-center">
        <h1 className="text-4xl font-bold tracking-tight">
          Your Bittensor Intelligence Platform
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-text-secondary">
          Unified portfolio tracking, predictive analytics, and multi-criteria
          subnet screening. See your complete position, project forward yields,
          and discover opportunities — all in one place.
        </p>
      </div>

      <div className="w-full max-w-lg">
        <label
          htmlFor="coldkey-input"
          className="mb-2 block text-sm font-medium text-text-secondary"
        >
          Paste your coldkey address to get started
        </label>
        <p id="coldkey-hint" className="sr-only">
          SS58 address starting with 5, 47-48 characters
        </p>
        <div className="flex gap-2">
          <input
            id="coldkey-input"
            type="text"
            placeholder="5D..."
            maxLength={48}
            pattern="^5[A-HJ-NP-Za-km-z1-9]{46,47}$"
            aria-describedby="coldkey-hint"
            className="flex-1 rounded-lg border border-border bg-surface px-4 py-3 text-sm font-mono text-text-primary focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-background"
          />
          <button
            type="button"
            disabled
            aria-disabled="true"
            className="rounded-lg bg-primary px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed"
          >
            View Portfolio
          </button>
        </div>
      </div>

      <div className="grid w-full max-w-4xl grid-cols-1 gap-6 md:grid-cols-3">
        <FeatureCard
          title="Portfolio Dashboard"
          description="Complete view of your staking, delegations, alpha tokens, and miner positions across all addresses."
        />
        <FeatureCard
          title="Subnet Screener"
          description="Filter and compare 128+ subnets by emission share, miner count, registration cost, and more."
        />
        <FeatureCard
          title="Predictive Analytics"
          description="Yield projections, scenario calculator, and emission forecasting with confidence intervals."
        />
      </div>
    </div>
  );
}

function FeatureCard({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-surface p-5">
      <h2 className="text-base font-semibold">{title}</h2>
      <p className="mt-2 text-sm text-text-secondary">{description}</p>
    </div>
  );
}
