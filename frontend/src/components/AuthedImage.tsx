"use client";

import { useEffect, useState } from "react";

import { fetchBlob } from "@/lib/api";

/**
 * An image that lives behind sign-in (saved project photos, thumbnails, the brand logo).
 * A plain <img src> cannot send the sign-in token, so the file is fetched with it and shown from memory.
 * `version` can be changed to force a reload, for example after uploading a new logo.
 */
export function AuthedImage({
  path,
  alt,
  className,
  version,
}: {
  /** Server path such as /api/history/3/thumbnail */
  path: string;
  alt: string;
  className?: string;
  version?: string | number;
}) {
  const [src, setSrc] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;
    setSrc(null);
    setFailed(false);
    fetchBlob(path)
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setSrc(objectUrl);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [path, version]);

  if (!src) {
    // Same box as the finished image, so the layout does not jump while it loads.
    return (
      <div
        className={className}
        role="img"
        aria-label={failed ? `${alt} (could not be loaded)` : `${alt} (loading)`}
        aria-busy={!failed}
      />
    );
  }
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={src} alt={alt} className={className} />;
}
