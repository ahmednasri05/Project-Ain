import { cn } from "@/lib/utils"

const STATUS_MAP = {
  scraping:          { label: "جارٍ (Apify)", className: "bg-sky-100 text-sky-800 border-sky-200", pulse: true },
  running:           { label: "جارٍ", className: "bg-blue-100 text-blue-800 border-blue-200", pulse: true },
  success:           { label: "نجح", className: "bg-green-100 text-green-800 border-green-200" },
  error:             { label: "خطأ", className: "bg-red-100 text-red-800 border-red-200" },
  already_processed: { label: "مكرر", className: "bg-muted text-muted-foreground border-border" },
  repost:            { label: "إعادة نشر", className: "bg-purple-100 text-purple-800 border-purple-200" },
  filtered:          { label: "مفلتر", className: "bg-yellow-100 text-yellow-800 border-yellow-200" },
}

export default function StatusBadge({ status, className }) {
  const config = STATUS_MAP[status] || { label: status || "—", className: "bg-muted text-muted-foreground border-border" }
  return (
    <span className={cn("inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium border", config.className, className)}>
      {config.pulse && (
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500" />
        </span>
      )}
      {config.label}
    </span>
  )
}
