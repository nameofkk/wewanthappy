"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { completeTossStoreLogin } from "@/lib/auth";
import { Loader2 } from "lucide-react";

export default function TossCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get("code");
    const state = searchParams.get("state");
    const savedState = sessionStorage.getItem("toss_oauth_state");

    if (!code) {
      setError("인가코드가 없습니다.");
      return;
    }
    if (state && savedState && state !== savedState) {
      setError("잘못된 요청입니다. (state 불일치)");
      return;
    }

    sessionStorage.removeItem("toss_oauth_state");

    completeTossStoreLogin(code)
      .then(({ isNewUser }) => {
        router.replace(isNewUser ? "/auth/register" : "/");
      })
      .catch((err) => {
        setError(err.message || "토스 로그인에 실패했습니다.");
      });
  }, [searchParams, router]);

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center space-y-4">
          <p className="text-red-500 text-sm">{error}</p>
          <button
            onClick={() => router.replace("/login")}
            className="text-sm text-primary underline"
          >
            로그인으로 돌아가기
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center space-y-3">
        <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
        <p className="text-sm text-muted-foreground">토스 로그인 처리 중...</p>
      </div>
    </div>
  );
}
