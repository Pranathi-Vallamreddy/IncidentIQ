import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, UploadCloud } from "lucide-react";
import { Button } from "@/components/ui/primitives";

export function Topbar({ onUpload }: { onUpload: () => void }) {
  const [q, setQ] = useState("");
  const navigate = useNavigate();

  function submit() {
    const term = q.trim();
    navigate(term ? `/incidents?q=${encodeURIComponent(term)}` : "/incidents");
  }

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-4 border-b border-hairline bg-canvas/80 px-6 backdrop-blur">
      <div className="relative flex-1 max-w-2xl">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-faint" />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          placeholder="Search incidents by title, service, or cluster…"
          className="h-10 w-full rounded-lg border border-hairline bg-card pl-10 pr-16 text-sm text-ink placeholder:text-faint focus:border-white/20 focus:outline-none"
        />
        {q.trim() && (
          <button
            onClick={submit}
            className="absolute right-2 top-1/2 -translate-y-1/2 rounded border border-hairline px-1.5 py-0.5 text-[10px] text-muted hover:text-ink"
          >
            ↵ Enter
          </button>
        )}
      </div>

      <Button variant="outline" onClick={onUpload}>
        <UploadCloud className="h-4 w-4" />
        Upload logs
      </Button>

      <div className="flex items-center gap-2.5">
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-violet-500 to-indigo-600 text-xs font-semibold text-white">
          PV
        </div>
        <span className="hidden text-sm font-medium text-ink sm:block">Pranathi Vallamreddy</span>
      </div>
    </header>
  );
}
