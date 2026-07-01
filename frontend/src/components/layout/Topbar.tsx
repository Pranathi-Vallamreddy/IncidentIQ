import { Search, UploadCloud, Bell, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/primitives";

export function Topbar({ onUpload }: { onUpload: () => void }) {
  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-4 border-b border-hairline bg-canvas/80 px-6 backdrop-blur">
      <div className="relative flex-1 max-w-2xl">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-faint" />
        <input
          placeholder="Search incidents, clusters, services…"
          className="h-10 w-full rounded-lg border border-hairline bg-card pl-10 pr-16 text-sm text-ink placeholder:text-faint focus:border-white/20 focus:outline-none"
        />
        <kbd className="absolute right-3 top-1/2 -translate-y-1/2 rounded border border-hairline px-1.5 py-0.5 text-[10px] text-faint">
          ⌘K
        </kbd>
      </div>

      <button className="flex h-9 items-center gap-2 rounded-lg border border-hairline px-3 text-sm text-muted hover:text-ink">
        Last 24 hours
        <ChevronDown className="h-4 w-4" />
      </button>

      <Button variant="outline" onClick={onUpload}>
        <UploadCloud className="h-4 w-4" />
        Upload logs
      </Button>

      <button className="text-muted hover:text-ink">
        <Bell className="h-5 w-5" />
      </button>

      <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-zinc-500 to-zinc-700 text-xs font-semibold text-white">
        AR
      </div>
    </header>
  );
}
