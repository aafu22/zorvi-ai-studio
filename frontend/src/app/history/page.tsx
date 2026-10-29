import { HistoryList } from "@/components/HistoryList";
import { RequireSignIn } from "@/components/RequireSignIn";

export default function HistoryPage() {
  return (
    <RequireSignIn
      feature="Content History"
      reason="Saved projects belong to your account, so only you can see and reopen them."
    >
      <HistoryList />
    </RequireSignIn>
  );
}
