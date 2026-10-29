import { PhotoAssistant } from "@/components/PhotoAssistant";
import { RequireSignIn } from "@/components/RequireSignIn";

export default function PhotoAssistantPage() {
  return (
    <RequireSignIn
      feature="the AI Photo Assistant"
      reason="Each photo analysis uses a paid AI model, so it needs an account to keep usage fair."
    >
      <PhotoAssistant />
    </RequireSignIn>
  );
}
