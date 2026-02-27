"use client";

import { useEffect, useState } from "react";
import Image from "next/image";

interface SplashScreenProps {
  visible: boolean;
}

export function SplashScreen({ visible }: SplashScreenProps) {
  const [mounted, setMounted] = useState(true);

  useEffect(() => {
    if (!visible) {
      // fade-out 애니메이션 후 DOM에서 제거
      const timer = setTimeout(() => setMounted(false), 500);
      return () => clearTimeout(timer);
    }
  }, [visible]);

  useEffect(() => {
    // React 스플래시가 마운트되면 인라인 HTML 스플래시 제거
    const el = document.getElementById("__splash");
    if (el) el.remove();
  }, []);

  if (!mounted) return null;

  return (
    <div
      className={`fixed inset-0 z-[9999] flex flex-col items-center justify-center ${
        visible ? "" : "splash-fade-out"
      }`}
      style={{ background: "linear-gradient(135deg, #FFF8F0 0%, #FBF0D9 50%, #FFF8F0 100%)" }}
    >
      <div className="splash-breathe">
        <Image
          src="/logo-eye.png"
          alt="WeWantHappy"
          width={184}
          height={80}
          className="h-20 w-auto"
          priority
        />
      </div>
      <p className="mt-3 text-xl font-black tracking-tight" style={{ color: "#3d2b1f" }}>
        WeWantHappy
      </p>
      <div className="mt-8 flex gap-1.5">
        <span className="splash-dot h-2 w-2 rounded-full" style={{ backgroundColor: "#E8846A", animationDelay: "0ms" }} />
        <span className="splash-dot h-2 w-2 rounded-full" style={{ backgroundColor: "#F2B63B", animationDelay: "150ms" }} />
        <span className="splash-dot h-2 w-2 rounded-full" style={{ backgroundColor: "#E8846A", animationDelay: "300ms" }} />
      </div>
    </div>
  );
}
