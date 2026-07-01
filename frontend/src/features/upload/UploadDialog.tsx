import { useRef, useState } from "react";
import { UploadCloud, X, FileText, Loader2, Database } from "lucide-react";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/useAsync";
import { Button } from "@/components/ui/primitives";
import { cn } from "@/lib/utils";

export function UploadDialog({
  open,
  onClose,
  onLoaded,
}: {
  open: boolean;
  onClose: () => void;
  onLoaded: (source: string) => void;
}) {
  const samples = useAsync(() => api.samples(), []);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  if (!open) return null;

  async function runSample(name: string) {
    setBusy(name);
    setError(null);
    try {
      await api.loadSample(name);
      onLoaded(name);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  }

  async function runUpload(file: File) {
    setBusy("__upload__");
    setError(null);
    try {
      await api.uploadLogs(file);
      onLoaded(file.name);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
      <div className="w-full max-w-2xl animate-fade-in rounded-xl border border-hairline bg-panel shadow-2xl">
        <div className="flex items-center justify-between border-b border-hairline px-6 py-4">
          <div>
            <h2 className="text-base font-semibold">Analyze logs</h2>
            <p className="text-xs text-muted">
              Upload a log file or load a bundled dataset. The engine parses, clusters,
              scores and correlates it on ingest.
            </p>
          </div>
          <button onClick={onClose} className="text-muted hover:text-ink">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-5 p-6">
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragging(false);
              const file = e.dataTransfer.files?.[0];
              if (file) runUpload(file);
            }}
            onClick={() => inputRef.current?.click()}
            className={cn(
              "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border border-dashed py-10 transition-colors",
              dragging ? "border-white/40 bg-white/5" : "border-hairline hover:border-white/20",
            )}
          >
            {busy === "__upload__" ? (
              <Loader2 className="h-6 w-6 animate-spin text-muted" />
            ) : (
              <UploadCloud className="h-6 w-6 text-muted" />
            )}
            <p className="text-sm text-ink">Drop a log file here, or click to browse</p>
            <p className="text-xs text-faint">.log, .txt, .ndjson — up to 25 MB</p>
            <input
              ref={inputRef}
              type="file"
              accept=".log,.txt,.ndjson,.json,text/plain"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) runUpload(file);
              }}
            />
          </div>

          <div className="flex items-center gap-3 text-xs text-faint">
            <div className="h-px flex-1 bg-hairline" />
            or load a bundled dataset
            <div className="h-px flex-1 bg-hairline" />
          </div>

          <div className="space-y-2">
            {samples.loading && <p className="text-sm text-muted">Loading samples…</p>}
            {samples.data?.map((s) => (
              <div
                key={s.name}
                className="flex items-center justify-between gap-4 rounded-lg border border-hairline bg-card px-4 py-3"
              >
                <div className="flex min-w-0 items-start gap-3">
                  <FileText className="mt-0.5 h-4 w-4 shrink-0 text-muted" />
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="truncate font-mono text-sm text-ink">{s.name}</span>
                      <span className="rounded bg-white/5 px-1.5 py-0.5 text-[10px] uppercase text-faint">
                        {s.fmt}
                      </span>
                      <span className="text-[10px] text-faint">{s.size_kb} KB</span>
                    </div>
                    <p className="mt-0.5 line-clamp-2 text-xs text-muted">{s.description}</p>
                  </div>
                </div>
                <Button
                  size="sm"
                  variant="primary"
                  disabled={!!busy}
                  onClick={() => runSample(s.name)}
                >
                  {busy === s.name ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Database className="h-3.5 w-3.5" />
                  )}
                  Analyze
                </Button>
              </div>
            ))}
          </div>

          {error && (
            <p className="rounded-lg border border-sev-critical/30 bg-sev-critical/10 px-3 py-2 text-xs text-sev-critical">
              {error}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
