import { cn } from "@/lib/utils"

function scoreColor(score) {
  if (score >= 8) return "bg-red-500"
  if (score >= 6) return "bg-orange-500"
  if (score >= 4) return "bg-yellow-500"
  return "bg-green-500"
}

function scoreLabel(score) {
  if (score >= 8) return "حرج"
  if (score >= 6) return "خطير"
  if (score >= 4) return "متوسط"
  return "منخفض"
}

export default function DangerScoreBar({ score, showLabel = true, className }) {
  const pct = (score / 10) * 100
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden min-w-16">
        <div
          className={cn("h-full rounded-full transition-all", scoreColor(score))}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-sm font-semibold w-8 text-center shrink-0">{score}/10</span>
      {showLabel && (
        <span className={cn("text-xs px-1.5 py-0.5 rounded font-medium text-white shrink-0", scoreColor(score))}>
          {scoreLabel(score)}
        </span>
      )}
    </div>
  )
}
