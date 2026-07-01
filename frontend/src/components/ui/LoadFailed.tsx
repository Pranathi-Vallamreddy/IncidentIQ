import { CloudOff } from "lucide-react";
import { Button, EmptyState } from "./primitives";

export function LoadFailed({ onRetry }: { onRetry: () => void }) {
  return (
    <EmptyState
      icon={<CloudOff className="h-8 w-8" />}
      title="Couldn't reach the analysis service"
      hint="The backend may be waking up from idle — this can take up to a minute on free hosting. Try again in a moment."
      action={
        <Button variant="outline" size="sm" onClick={onRetry}>
          Retry
        </Button>
      }
    />
  );
}
