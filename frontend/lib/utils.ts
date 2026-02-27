import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const WARMTH_LEVELS = {
  0: { label: "잔잔", color: "text-[#E8D5C4]",  bg: "bg-[#E8D5C4]/20",  border: "border-[#E8D5C4]/50" },
  1: { label: "따뜻", color: "text-[#F4A67B]", bg: "bg-[#F4A67B]/30", border: "border-[#F4A67B]/60" },
  2: { label: "뭉클", color: "text-[#E8846A]", bg: "bg-[#E8846A]/40", border: "border-[#E8846A]/80" },
  3: { label: "감동", color: "text-[#F2B63B]",    bg: "bg-[#F2B63B]/50",    border: "border-[#F2B63B]/90" },
} as const;

export const SOURCE_TIERS = {
  A: { label: "공식", color: "text-yellow-400", bg: "bg-yellow-400/10" },
  B: { label: "검증", color: "text-slate-400", bg: "bg-slate-400/10" },
  C: { label: "일반", color: "text-amber-700", bg: "bg-amber-700/10" },
  D: { label: "미확인", color: "text-gray-500", bg: "bg-gray-500/10" },
} as const;

export const TOPIC_LABELS: Record<string, string> = {
  kindness:  "선의",
  reunion:   "재회",
  rescue:    "구출",
  community: "연대",
  recovery:  "회복",
  children:  "아이들",
  health:    "건강",
  animals:   "동물",
  elderly:   "어르신",
  peace:     "평화",
  unknown:   "기타",
};
