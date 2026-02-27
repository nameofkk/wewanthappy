"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { type Lang } from "@/lib/i18n";

// HScore 구간별 색상 (0-10 스케일, 따뜻한 톤)
function hscoreColor(hscore: number): string {
  if (hscore >= 7.0) return "#F2B63B"; // 웜골드 (감동)
  if (hscore >= 5.0) return "#E8846A"; // 웜코랄 (뭉클)
  if (hscore >= 3.0) return "#F4A67B"; // 피치 (따뜻)
  return "#E8D5C4"; // 베이지 (잔잔)
}

interface HScorePoint {
  time: string;
  hscore: number;
}

interface HScoreHistoryChartProps {
  data: HScorePoint[];
  range: "7d" | "30d" | "90d";
  lang: Lang;
}

function formatDate(isoStr: string, range: "7d" | "30d" | "90d", lang: Lang) {
  const locale = lang === "en" ? "en-US" : "ko-KR";
  const d = new Date(isoStr);
  if (range === "7d") {
    return d.toLocaleString(locale, { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" });
  }
  return d.toLocaleString(locale, { month: "short", day: "numeric" });
}

interface TooltipPayloadItem {
  payload: HScorePoint;
}

function CustomTooltip({
  active,
  payload,
  lang,
}: {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  lang: Lang;
}) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  const color = hscoreColor(d.hscore);
  const locale = lang === "en" ? "en-US" : "ko-KR";

  return (
    <div className="rounded-lg border border-border bg-card/95 backdrop-blur-sm px-3 py-2 text-xs shadow-lg">
      <p className="text-muted-foreground mb-1">{new Date(d.time).toLocaleString(locale)}</p>
      <p className="font-bold" style={{ color }}>
        HScore <span className="font-normal text-foreground">{d.hscore.toFixed(1)}</span>
      </p>
    </div>
  );
}

export function HScoreHistoryChart({ data, range, lang }: HScoreHistoryChartProps) {
  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-32 text-xs text-muted-foreground">
        {lang === "ko" ? "데이터가 없습니다" : "No data available"}
      </div>
    );
  }

  const maxHscore = Math.max(...data.map((d) => d.hscore));
  const lineColor = hscoreColor(maxHscore);

  return (
    <div className="w-full overflow-hidden">
      <div className="h-36">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E8D5C4" vertical={false} />

            {/* HScore 구간 경계선 (0-10 스케일) */}
            <ReferenceLine y={3.0} stroke="#F4A67B" strokeDasharray="4 4" strokeOpacity={0.4} />
            <ReferenceLine y={5.0} stroke="#E8846A" strokeDasharray="4 4" strokeOpacity={0.4} />
            <ReferenceLine y={7.0} stroke="#F2B63B" strokeDasharray="4 4" strokeOpacity={0.4} />

            <XAxis
              dataKey="time"
              tickFormatter={(v) => formatDate(v, range, lang)}
              tick={{ fontSize: 9, fill: "#6b7280" }}
              axisLine={false}
              tickLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              domain={[0, Math.max(10, maxHscore + 1)]}
              tick={{ fontSize: 9, fill: "#6b7280" }}
              axisLine={false}
              tickLine={false}
              ticks={[0, 3, 5, 7, 10]}
            />
            <Tooltip content={<CustomTooltip lang={lang} />} />
            <Line
              type="monotone"
              dataKey="hscore"
              stroke={lineColor}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: lineColor }}
              animationDuration={400}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* 범례 (0-10 스케일, 따뜻한 톤) */}
      <div className="flex items-center justify-center gap-3 mt-1 mb-1">
        {[
          { label: lang === "ko" ? "잔잔" : "Quiet",     color: "#E8D5C4", range: "< 3" },
          { label: lang === "ko" ? "따뜻" : "Warm",      color: "#F4A67B", range: "3~5" },
          { label: lang === "ko" ? "뭉클" : "Touching",  color: "#E8846A", range: "5~7" },
          { label: lang === "ko" ? "감동" : "Moving",    color: "#F2B63B", range: "7+" },
        ].map(({ label, color, range: r }) => (
          <span key={r} className="flex items-center gap-1 text-[9px] text-muted-foreground">
            <span className="inline-block w-2 h-2 rounded-full" style={{ background: color }} />
            {label}
          </span>
        ))}
      </div>
    </div>
  );
}
