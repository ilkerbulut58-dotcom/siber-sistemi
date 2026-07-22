"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth-provider";

export function RedirectIfAuthed({ to = "/dashboard" }: { to?: string }) {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && user) {
      router.replace(to);
    }
  }, [isLoading, user, router, to]);

  return null;
}
