import { cn } from "@/lib/utils"

const SEVERITY_MAP = {
  critical: { label: "حرج", className: "bg-red-100 text-red-800 border-red-200" },
  severe:   { label: "شديد", className: "bg-orange-100 text-orange-800 border-orange-200" },
  moderate: { label: "متوسط", className: "bg-yellow-100 text-yellow-800 border-yellow-200" },
  minor:    { label: "بسيط", className: "bg-green-100 text-green-800 border-green-200" },
}

export default function SeverityBadge({ severity, className }) {
  const config = SEVERITY_MAP[severity] || { label: severity || "—", className: "bg-muted text-muted-foreground" }
  return (
    <span className={cn("inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border", config.className, className)}>
      {config.label}
    </span>
  )
}
