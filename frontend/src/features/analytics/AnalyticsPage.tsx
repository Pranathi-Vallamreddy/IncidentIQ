import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyState } from "@/components/ui/primitives";

export function AnalyticsPage() {
  return (
    <>
      <PageHeader title="Analytics" subtitle="Trends, cluster frequency, and service health." />
      <EmptyState title="Analytics coming online" hint="This page is wired in a later slice." />
    </>
  );
}
