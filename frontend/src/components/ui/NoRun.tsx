import { Inbox } from "lucide-react";
import { EmptyState } from "./primitives";

export function NoRun({ hint }: { hint?: string }) {
  return (
    <EmptyState
      icon={<Inbox className="h-8 w-8" />}
      title="No analysis yet"
      hint={hint ?? "Click “Upload logs” to analyze a file or load a bundled dataset."}
    />
  );
}
