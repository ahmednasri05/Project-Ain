import { useCallback, useEffect } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { RefreshCw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import StatusBadge from "@/components/StatusBadge"
import DangerScoreBar from "@/components/DangerScoreBar"
import { fetchPipelineRuns } from "@/lib/api"
import { supabase } from "@/lib/supabase"
import { Tooltip, TooltipProvider } from "@/components/ui/tooltip"

function formatDuration(ms) {
  if (!ms) return "—"
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

export default function PipelineMonitor() {
  const queryClient = useQueryClient()

  const runsQuery = useQuery({
    queryKey: ["pipeline-runs"],
    queryFn: () => fetchPipelineRuns(50),
    refetchInterval: 10_000,
  })

  // ── Supabase Realtime ─────────────────────────────────────────────────────
  const invalidateRuns = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["pipeline-runs"] })
  }, [queryClient])

  useEffect(() => {
    const channel = supabase
      .channel("pipeline_runs_feed")
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table: "pipeline_runs" },
        (payload) => {
          invalidateRuns()
          if (payload.eventType === "INSERT") {
            toast.info(`مهمة جديدة: ${payload.new.shortcode}`)
          } else if (payload.eventType === "UPDATE" && payload.new.status === "success") {
            toast.success(`اكتملت المعالجة: ${payload.new.shortcode} (خطورة: ${payload.new.danger_score}/10)`)
          } else if (payload.eventType === "UPDATE" && payload.new.status === "error") {
            toast.error(`فشلت المعالجة: ${payload.new.shortcode}`)
          }
        }
      )
      .subscribe()

    return () => { supabase.removeChannel(channel) }
  }, [invalidateRuns])

  const runs = runsQuery.data?.data || []

  return (
    <TooltipProvider>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">المهام الجارية</h1>
            <p className="text-muted-foreground text-sm mt-0.5">
              مراقبة مباشرة عبر Supabase Realtime
            </p>
          </div>
          <Button
            variant="outline" size="sm"
            onClick={() => runsQuery.refetch()}
            disabled={runsQuery.isFetching}
          >
            <RefreshCw className={`w-4 h-4 ml-1 ${runsQuery.isFetching ? "animate-spin" : ""}`} />
            تحديث
          </Button>
        </div>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">سجل المهام (آخر 50)</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {runsQuery.isLoading ? (
              <div className="py-12 text-center text-muted-foreground">جارٍ التحميل...</div>
            ) : !runs.length ? (
              <div className="py-12 text-center text-muted-foreground">لا توجد مهام حتى الآن</div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>التوقيت</TableHead>
                    <TableHead>المعرف</TableHead>
                    <TableHead>الحالة</TableHead>
                    <TableHead>درجة الخطورة</TableHead>
                    <TableHead>الجرائم</TableHead>
                    <TableHead>المدة</TableHead>
                    <TableHead>ملاحظات</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {runs.map(run => (
                    <TableRow key={run.id}>
                      <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                        {new Date(run.triggered_at).toLocaleString("ar-EG")}
                      </TableCell>
                      <TableCell className="font-mono text-xs" dir="ltr">
                        {run.shortcode}
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={run.status} />
                      </TableCell>
                      <TableCell className="min-w-36">
                        {run.danger_score != null
                          ? <DangerScoreBar score={run.danger_score} showLabel={false} />
                          : <span className="text-muted-foreground text-sm">—</span>
                        }
                      </TableCell>
                      <TableCell className="text-sm">
                        {run.crimes_count != null ? run.crimes_count : "—"}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {formatDuration(run.duration_ms)}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground max-w-48 truncate">
                        <Tooltip content={run.error_reason || run.recommended_action || run.sentiment_explanation}>
                          <span className="truncate block">
                            {run.error_reason || run.recommended_action || run.sentiment_explanation || "—"}
                          </span>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </TooltipProvider>
  )
}
