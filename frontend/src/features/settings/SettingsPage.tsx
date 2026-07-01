import { useEffect, useState } from "react";
import { User, SlidersHorizontal, Check, Sparkles, Github } from "lucide-react";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/useAsync";
import { PageHeader } from "@/components/ui/PageHeader";
import { LoadFailed } from "@/components/ui/LoadFailed";
import { Card, Button, Toggle, Spinner } from "@/components/ui/primitives";
import { cn } from "@/lib/utils";
import type { Settings } from "@/types";

const TABS = [
  { key: "detection", label: "Detection", icon: SlidersHorizontal },
  { key: "profile", label: "Profile", icon: User },
];

function Row({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-6 py-4">
      <div>
        <div className="text-sm font-medium text-ink">{title}</div>
        {hint && <div className="mt-0.5 text-xs text-muted">{hint}</div>}
      </div>
      {children}
    </div>
  );
}

export function SettingsPage() {
  const { data, loading, error, reload } = useAsync(() => api.settings(), []);
  const [tab, setTab] = useState("detection");
  const [draft, setDraft] = useState<Settings | null>(null);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (data) setDraft(data);
  }, [data]);

  async function save() {
    if (!draft) return;
    setSaving(true);
    try {
      const next = await api.updateSettings({
        anomaly_sensitivity: draft.anomaly_sensitivity,
        ai_root_cause: draft.ai_root_cause,
      });
      setDraft(next);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  }

  if (error && !draft) {
    return (
      <>
        <PageHeader title="Settings" subtitle="Detection thresholds that feed the analysis engine." />
        <LoadFailed onRetry={reload} />
      </>
    );
  }
  if (loading || !draft) return <Spinner label="Loading settings…" />;

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="Settings"
        subtitle="Detection thresholds that feed the analysis engine on the next run."
        right={
          tab === "detection" ? (
            <Button variant="primary" size="sm" onClick={save} disabled={saving}>
              {saved ? <Check className="h-4 w-4" /> : null}
              {saved ? "Saved" : saving ? "Saving…" : "Save changes"}
            </Button>
          ) : undefined
        }
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[220px_1fr]">
        <nav className="flex flex-col gap-1">
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                tab === t.key ? "bg-elevated text-ink" : "text-muted hover:text-ink hover:bg-white/5",
              )}
            >
              <t.icon className="h-4 w-4" />
              {t.label}
            </button>
          ))}
        </nav>

        <div className="space-y-4">
          {tab === "detection" && (
            <Card className="p-6">
              <h3 className="text-base font-semibold">Detection thresholds</h3>
              <p className="mt-0.5 text-xs text-muted">
                These values are read by the engine on the next analysis run.
              </p>
              <div className="mt-4 divide-y divide-hairline">
                <div className="py-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-sm font-medium">Anomaly sensitivity</div>
                      <div className="mt-0.5 text-xs text-muted">
                        Higher values lower the z-score threshold and surface subtler spikes.
                      </div>
                    </div>
                    <span className="tabular-nums text-sm text-ink">
                      {draft.anomaly_sensitivity.toFixed(2)}
                    </span>
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={1}
                    step={0.05}
                    value={draft.anomaly_sensitivity}
                    onChange={(e) =>
                      setDraft({ ...draft, anomaly_sensitivity: Number(e.target.value) })
                    }
                    className="mt-3 w-full accent-white"
                  />
                </div>
                <Row
                  title="AI root cause analysis"
                  hint="Use Gemini to explain incidents when a key is configured; otherwise the deterministic explainer is used."
                >
                  <Toggle
                    checked={draft.ai_root_cause}
                    onChange={(v) => setDraft({ ...draft, ai_root_cause: v })}
                  />
                </Row>
              </div>
              <div className="mt-4 flex items-start gap-2 rounded-lg border border-hairline bg-card px-3 py-2.5 text-xs text-muted">
                <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-violet-400" />
                <span>
                  {draft.ai_available ? (
                    <>
                      Gemini is configured — live explanations use{" "}
                      <span className="font-mono text-ink">{draft.ai_model}</span>.
                    </>
                  ) : (
                    <>
                      No <span className="font-mono">GEMINI_API_KEY</span> set — explanations use the
                      deterministic engine-based explainer. Both produce the same structured output.
                    </>
                  )}
                </span>
              </div>
            </Card>
          )}

          {tab === "profile" && (
            <Card className="p-6">
              <h3 className="text-base font-semibold">Project author</h3>
              <div className="mt-4 flex items-center gap-4">
                <div className="flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-violet-500 to-indigo-600 text-lg font-semibold text-white">
                  PV
                </div>
                <div>
                  <div className="text-sm font-medium">Pranathi Vallamreddy</div>
                  <div className="text-xs text-muted">Software Engineer · IncidentIQ author</div>
                </div>
              </div>
              <a
                href="https://github.com/Pranathi-Vallamreddy"
                target="_blank"
                rel="noreferrer"
                className="mt-5 inline-flex items-center gap-2 rounded-lg border border-hairline px-3 py-2 text-sm text-ink hover:bg-white/5"
              >
                <Github className="h-4 w-4" />
                github.com/Pranathi-Vallamreddy
              </a>
              <p className="mt-4 text-xs text-muted">
                IncidentIQ is a single-workspace demo — there is no multi-user auth. This page shows the
                project author rather than editable account fields.
              </p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
