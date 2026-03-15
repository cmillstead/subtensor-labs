import Link from "next/link";
import { notFound } from "next/navigation";
import { engineFetch, EngineClientError } from "@/lib/engine-client";
import { LastUpdated } from "@/components/common/LastUpdated";
import { SubnetMetrics } from "@/components/subnets/SubnetMetrics";
import { SubnetNeuronTable } from "@/components/subnets/SubnetNeuronTable";
import { SubnetChartSection } from "@/components/subnets/SubnetChartSection";
import type { EngineResponse, SubnetDetailResult } from "@/types";

interface PageProps {
  params: Promise<{ netuid: string }>;
}

/**
 * Build JSON-LD structured data from server-side subnet data.
 * All values originate from our own engine (not user input), so the
 * resulting JSON string is safe for embedding.
 */
function buildJsonLd(netuid: number, detail: SubnetDetailResult["detail"]): string {
  const obj = {
    "@context": "https://schema.org",
    "@type": "Dataset",
    name: `Bittensor Subnet ${netuid}${detail.name ? ` — ${detail.name}` : ""}`,
    description: `Real-time metrics for Bittensor subnet ${netuid}: ${detail.miner_count} miners, ${detail.validator_count} validators, ${(detail.emission_share * 100).toFixed(2)}% emission share.`,
    url: `https://subtensorlabs.com/subnets/${netuid}`,
  };
  return JSON.stringify(obj);
}

export default async function SubnetDetailPage({ params }: PageProps) {
  const { netuid: rawNetuid } = await params;
  const netuid = parseInt(rawNetuid, 10);

  if (isNaN(netuid) || netuid < 0 || rawNetuid !== String(netuid)) {
    notFound();
  }

  let response: EngineResponse<SubnetDetailResult>;
  try {
    response = await engineFetch<EngineResponse<SubnetDetailResult>>(
      `/subnets/${netuid}`,
    );
  } catch (err) {
    if (err instanceof EngineClientError && err.statusCode === 404) {
      notFound();
    }
    return (
      <div className="py-12 text-center">
        <h1 className="text-2xl font-bold text-text-primary">
          Unable to load subnet data
        </h1>
        <p className="mt-2 text-text-secondary">
          The data service is temporarily unavailable. Please try again later.
        </p>
      </div>
    );
  }

  const { data, meta } = response;
  const { detail, miners, validators } = data;
  const name = detail.name;
  const title = name ? `SN${netuid} · ${name}` : `SN${netuid}`;

  return (
    <>
      {/* JSON-LD structured data — values from our engine, not user input */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: buildJsonLd(netuid, detail) }}
      />

      <div className="space-y-8">
        {/* Header */}
        <div>
          <Link
            href="/screener"
            className="text-sm text-text-muted hover:text-text-primary transition-colors"
          >
            ← Back to Screener
          </Link>
          <h1 className="mt-2 text-3xl font-bold text-text-primary">{title}</h1>
          {detail.description && (
            <p className="mt-1 text-text-secondary">{detail.description}</p>
          )}
        </div>

        {/* Metrics grid */}
        <SubnetMetrics detail={detail} />

        {/* Historical charts */}
        <SubnetChartSection initialData={data} netuid={netuid} />

        {/* Neuron tables */}
        <div className="grid gap-8 lg:grid-cols-2">
          <SubnetNeuronTable neurons={miners} title="Top Miners" />
          <SubnetNeuronTable neurons={validators} title="Top Validators" />
        </div>

        {/* Footer */}
        <div className="border-t border-border pt-4">
          <LastUpdated timestamp={meta.last_updated} />
        </div>
      </div>
    </>
  );
}
