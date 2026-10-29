import { BrandKitEditor } from "@/components/BrandKitEditor";
import { RequireSignIn } from "@/components/RequireSignIn";

export default function BrandKitPage() {
  return (
    <RequireSignIn
      feature="your Brand Kit"
      reason="Your brand colours, font, tone and logo are saved to your account and applied to your graphics."
    >
      <BrandKitEditor />
    </RequireSignIn>
  );
}
