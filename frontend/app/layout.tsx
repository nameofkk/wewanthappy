import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Providers } from "./providers";
import { OnboardingGuard } from "@/components/ui/onboarding-guard";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://www.wewanthappy.live";

export const metadata: Metadata = {
  title: {
    default: "WeWantHappy",
    template: "%s | WeWantHappy",
  },
  description: "따뜻한 세상 이야기 · 온기 지수 · 감동 알림",
  manifest: "/manifest.json",
  metadataBase: new URL(SITE_URL),
  openGraph: {
    type: "website",
    locale: "ko_KR",
    url: SITE_URL,
    siteName: "WeWantHappy",
    title: "WeWantHappy — 따뜻한 세상 이야기",
    description: "온기 지수 · 감동 알림 · 실시간 지도",
    // images는 app/opengraph-image.png 파일 기반 메타데이터가 자동 적용됨
  },
  twitter: {
    card: "summary_large_image",
    title: "WeWantHappy — 따뜻한 세상 이야기",
    description: "온기 지수 · 감동 알림 · 실시간 지도",
    // images는 app/twitter-image.png 파일 기반 메타데이터가 자동 적용됨
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "WeWantHappy",
  },
  formatDetection: {
    telephone: false,
  },
  robots: {
    index: true,
    follow: true,
  },
};

export const viewport: Viewport = {
  themeColor: "#0f1729",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko" className="dark">
      <head>
        <link rel="icon" href="/favicon.ico" sizes="any" />
        <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
      </head>
      <body className="min-h-screen bg-background antialiased">
        {/* 인라인 스플래시: JS 번들 로드 전 빈 화면 방지 (React 하이드레이션 후 제거됨) */}
        <div
          id="__splash"
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 9999,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            background: "linear-gradient(135deg, #FFF8F0 0%, #FBF0D9 50%, #FFF8F0 100%)",
          }}
        >
          {/* 따뜻한 파동 + 로고 */}
          <div style={{ position: "relative", display: "flex", alignItems: "center", justifyContent: "center", width: 184, height: 80 }}>
            <div className="splash-breathe" style={{ position: "absolute", top: "50%", left: "50%", width: 40, height: 40, borderRadius: "50%", border: "1px solid rgba(232,132,106,0.25)", transform: "translate(-50%,-50%)", animation: "splash-radar 3s ease-out infinite" }} />
            <div style={{ position: "absolute", top: "50%", left: "50%", width: 40, height: 40, borderRadius: "50%", border: "1px solid rgba(242,182,59,0.2)", transform: "translate(-50%,-50%)", animation: "splash-radar 3s ease-out 1.5s infinite" }} />
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/logo-eye.png"
              alt=""
              width={184}
              height={80}
              style={{ position: "relative", zIndex: 1, height: 80, width: "auto", objectFit: "contain" }}
            />
          </div>
          <style dangerouslySetInnerHTML={{ __html: `
            @keyframes splash-radar {
              0% { transform: translate(-50%,-50%) scale(0.5); opacity: 0.6; }
              100% { transform: translate(-50%,-50%) scale(3); opacity: 0; }
            }
          ` }} />
          <p
            style={{
              marginTop: 12,
              fontSize: 20,
              fontWeight: 900,
              letterSpacing: "-0.025em",
              color: "#3d2b1f",
            }}
          >
            WeWantHappy
          </p>
        </div>
        <Providers>
          <OnboardingGuard>
            {children}
          </OnboardingGuard>
        </Providers>
      </body>
    </html>
  );
}
