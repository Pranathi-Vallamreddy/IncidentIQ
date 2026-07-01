import { useState } from "react";
import { Outlet, useNavigate } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { UploadDialog } from "@/features/upload/UploadDialog";
import { useApp } from "@/store";

export function AppShell() {
  const [uploadOpen, setUploadOpen] = useState(false);
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
        onLoaded={() => {
          setUploadOpen(false);
          refresh();
          navigate("/");
        }}
      />
    </div>
  );
}
