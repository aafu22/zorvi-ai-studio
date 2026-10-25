import { Suspense } from "react";

import { VerifyEmail } from "@/components/VerifyEmail";

export default function VerifyEmailPage() {
  // useSearchParams() needs a Suspense boundary for production builds.
  return (
    <Suspense fallback={null}>
      <VerifyEmail />
    </Suspense>
  );
}
