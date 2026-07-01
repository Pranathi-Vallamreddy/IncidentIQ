import { useState } from "react";
import { Outlet, useNavigate } from "react-router-dom";
import { CheckCircle2 } from "lucide-react";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { UploadDialog } from "@/features/upload/UploadDialog";
import { useApp } from "@/store";

export function AppShell() {
  const [uploadOpen, setUploadOpen] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const { refresh } = useApp();
  const navigate = useNavigate();

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar onUpload={() => setUploadOpen(true)} />
        <main className="scrollbar-thin flex-1 overflow-y-auto">
          <div className="mx-auto max-w-[1400px] px-8 py-8">
            <Outlet />
          </div>
        </main>
      </div>

      <UploadDialog
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        onLoaded={(source) => {
          setUploadOpen(false);
          refresh();
          navigate("/");
          setToast(`Analyzed ${source}`);
          window.setTimeout(() => setToast(null), 3500);
        }}
      />

      {toast && (
        <div className="fixed bottom-6 right-6 z-50 flex animate-fade-in items-center gap-2 rounded-lg border border-hairline bg-elevated px-4 py-3 text-sm shadow-2xl">
          <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          <span className="text-ink">{toast}</span>
          <span className="text-xs text-muted">— dashboard updated</span>
        </div>
      )}
    </div>
  );
}
