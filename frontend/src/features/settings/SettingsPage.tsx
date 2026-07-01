import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyState } from "@/components/ui/primitives";

export function SettingsPage() {
  return (
    <>
      <PageHeader title="Settings" subtitle="Manage detection thresholds and notifications." />
      <EmptyState title="Settings coming online" hint="This page is wired in a later slice." />
    </>
  );
}
