"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import api, { isAuthenticated, getStoredUserEmail } from "./api";

export function useAuthGuard() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [email, setEmail] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }
    setEmail(getStoredUserEmail());
    setLoading(false);
  }, [router]);

  return { loading, email };
}

export function useRedirectIfAuthed() {
  const router = useRouter();

  useEffect(() => {
    if (isAuthenticated()) {
      router.replace("/dashboard");
    }
  }, [router]);
}
