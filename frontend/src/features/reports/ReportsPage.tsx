import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyState } from "@/components/ui/primitives";

export function ReportsPage() {
  return (
    <>
      <PageHeader title="Reports" subtitle="Shareable, export-ready incident reports and postmortems." />
      <EmptyState title="Reports coming online" hint="This page is wired in a later slice." />
    </>
  );
}
