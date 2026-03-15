import type { Metadata } from "next";
import { engineFetch, EngineClientError } from "@/lib/engine-client";
import type { EngineResponse, SubnetDetailResult } from "@/types";

interface LayoutProps {
  children: React.ReactNode;
  params: Promise<{ netuid: string }>;
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ netuid: string }>;
}): Promise<Metadata> {
  const { netuid } = await params;
  const nid = parseInt(netuid, 10);
  if (isNaN(nid) || nid < 0 || netuid !== String(nid)) return { title: "Subnet Not Found | Subtensor Labs" };

  try {
    const response = await engineFetch<EngineResponse<SubnetDetailResult>>(
      `/subnets/${nid}`,
    );
    const { detail } = response.data;
    const name = detail.name;
    const title = name
      ? `SN${nid} · ${name} | Subtensor Labs`
      : `SN${nid} | Subtensor Labs`;
    const description = `Subnet ${nid}${name ? ` (${name})` : ""} — ${detail.miner_count} miners, ${detail.validator_count} validators, ${(detail.emission_share * 100).toFixed(2)}% emission share, τ${detail.alpha_price.toFixed(4)} alpha price.`;

    return {
      title,
      description,
      openGraph: {
        title,
        description,
        type: "website",
      },
    };
  } catch (err) {
    if (err instanceof EngineClientError && err.statusCode === 404) {
      return { title: "Subnet Not Found | Subtensor Labs" };
    }
    return { title: `SN${nid} | Subtensor Labs` };
  }
}

export default function SubnetLayout({ children }: LayoutProps) {
  return children;
}
