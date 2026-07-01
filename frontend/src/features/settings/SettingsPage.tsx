import { useEffect, useState } from "react";
import { User, SlidersHorizontal, Bell, Plug, ShieldCheck, KeyRound, Check, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/useAsync";
import { PageHeader } from "@/components/ui/PageHeader";
import { LoadFailed } from "@/components/ui/LoadFailed";
import { Card, Button, Toggle, Spinner } from "@/components/ui/primitives";
import { cn } from "@/lib/utils";
import type { Settings } from "@/types";

const TABS = [
  { key: "profile", label: "Profile", icon: User },
  { key: "detection", label: "Detection", icon: SlidersHorizontal },
  { key: "notifications", label: "Notifications", icon: Bell },
  { key: "integrations", label: "Integrations", icon: Plug },
  { key: "security", label: "Security", icon: ShieldCheck },
  { key: "apikeys", label: "API keys", icon: KeyRound },
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

function Field({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <label className="text-xs text-muted">{label}</label>
      <input
        defaultValue={value}
        className={cn(
          "mt-1.5 h-10 w-full rounded-lg border border-hairline bg-card px-3 text-sm text-ink focus:border-white/20 focus:outline-none",
          mono && "font-mono",
        )}
      />
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
        auto_cluster: draft.auto_cluster,
        ai_root_cause: draft.ai_root_cause,
        page_on_critical: draft.page_on_critical,
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
        <PageHeader title="Settings" subtitle="Manage your workspace, detection thresholds, and notifications." />
        <LoadFailed onRetry={reload} />
      </>
    );
  }
  if (loading || !draft) return <Spinner label="Loading settings…" />;

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="Settings"
        subtitle="Manage your workspace, detection thresholds, and notifications."
        right={
          <Button variant="primary" size="sm" onClick={save} disabled={saving}>
            {saved ? <Check className="h-4 w-4" /> : null}
            {saved ? "Saved" : saving ? "Saving…" : "Save changes"}
          </Button>
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
                These values feed the engine directly on the next analysis run.
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
                <Row title="Auto-cluster similar errors" hint="Group matching templates into a single incident">
                  <Toggle
                    checked={draft.auto_cluster}
                    onChange={(v) => setDraft({ ...draft, auto_cluster: v })}
                  />
                </Row>
                <Row title="AI root cause analysis" hint="Generate explanations and suggested fixes">
                  <Toggle
                    checked={draft.ai_root_cause}
                    onChange={(v) => setDraft({ ...draft, ai_root_cause: v })}
                  />
                </Row>
              </div>
              <div className="mt-4 flex items-center gap-2 rounded-lg border border-hairline bg-card px-3 py-2 text-xs text-muted">
                <Sparkles className="h-3.5 w-3.5 text-violet-400" />
                Gemini {draft.ai_available ? "is configured — live explanations enabled." : "key not set — using the deterministic explainer."}
              </div>
            </Card>
          )}

          {tab === "notifications" && (
            <Card className="p-6">
              <h3 className="text-base font-semibold">Notifications</h3>
              <div className="mt-2 divide-y divide-hairline">
                <Row title="Critical incidents" hint="Page on-call immediately">
                  <Toggle
                    checked={draft.page_on_critical}
                    onChange={(v) => setDraft({ ...draft, page_on_critical: v })}
                  />
                </Row>
                <Row title="Weekly reliability digest" hint="Emailed summary every Monday">
                  <Toggle checked onChange={() => {}} disabled />
                </Row>
                <Row title="Anomaly cluster alerts" hint="Notify when a new anomaly cluster forms">
                  <Toggle checked={false} onChange={() => {}} disabled />
                </Row>
              </div>
            </Card>
          )}

          {tab === "profile" && (
            <Card className="p-6">
              <h3 className="text-base font-semibold">Profile</h3>
              <div className="mt-4 flex items-center gap-4">
                <div className="flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-zinc-500 to-zinc-700 text-lg font-semibold text-white">
                  AR
                </div>
                <div>
                  <div className="text-sm font-medium">Alex Rivera</div>
                  <div className="text-xs text-muted">Site Reliability Engineer</div>
                </div>
              </div>
              <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Field label="Full name" value="Alex Rivera" />
                <Field label="Email" value="alex@incidentiq.io" />
                <Field label="Team" value="Platform Reliability" />
                <Field label="Timezone" value="UTC-05:00 (Eastern)" />
              </div>
            </Card>
          )}

          {["integrations", "security", "apikeys"].includes(tab) && (
            <Card className="p-6">
              <h3 className="text-base font-semibold capitalize">{TABS.find((t) => t.key === tab)?.label}</h3>
              <p className="mt-1 text-sm text-muted">
                Presentational in this build — the engineering focus is the detection pipeline.
              </p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
