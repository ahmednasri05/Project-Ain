import { useState, useEffect, useCallback } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { RefreshCw, RotateCcw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import StatusBadge from "@/components/StatusBadge"
import DangerScoreBar from "@/components/DangerScoreBar"
import { fetchPipelineRuns, fetchFailedRequests, retryFailedRequest } from "@/lib/api"
import { supabase } from "@/lib/supabase"

export default function PipelineMonitor() {
  const queryClient = useQueryClient()
  const [retrying, setRetrying] = useState(null)

  const runsQuery = useQuery({
    queryKey: ["pipeline-runs"],
    queryFn: () => fetchPipelineRuns(50),
    refetchInterval: 10_000,
  })

  const failedQuery = useQuery({
    queryKey: ["failed-requests"],
    queryFn: fetchFailedRequests,
    refetchInterval: 30_000,
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

  async function handleRetry(id, shortcode) {
    setRetrying(id)
    try {
      await retryFailedRequest(id)
      toast.success(`تمت إعادة إضافة ${shortcode} للمعالجة`)
      queryClient.invalidateQueries({ queryKey: ["failed-requests"] })
      queryClient.invalidateQueries({ queryKey: ["pipeline-runs"] })
    } catch (err) {
      toast.error(`فشلت إعادة المحاولة: ${err.message}`)
    } finally {
      setRetrying(null)
    }
  }

  const runs = runsQuery.data?.data || []
  const failed = failedQuery.data?.data || []

  function formatDuration(ms) {
    if (!ms) return "—"
    if (ms < 1000) return `${ms}ms`
    return `${(ms / 1000).toFixed(1)}s`
  }

  return (
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

      {/* Pipeline runs */}
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
                      {run.error_reason || run.recommended_action || run.sentiment_explanation || "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Failed requests */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              الطلبات الفاشلة
              {failed.length > 0 && (
                <span className="text-xs bg-destructive text-destructive-foreground rounded-full px-2 py-0.5">
                  {failed.length}
                </span>
              )}
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {failedQuery.isLoading ? (
            <div className="py-8 text-center text-muted-foreground">جارٍ التحميل...</div>
          ) : !failed.length ? (
            <div className="py-8 text-center text-muted-foreground text-sm">
              لا توجد طلبات فاشلة
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>المعرف</TableHead>
                  <TableHead>الخطوة</TableHead>
                  <TableHead>المحاولات</TableHead>
                  <TableHead>الخطأ</TableHead>
                  <TableHead>التاريخ</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {failed.map(req => (
                  <TableRow key={req.id}>
                    <TableCell className="font-mono text-xs" dir="ltr">
                      {req.shortcode}
                    </TableCell>
                    <TableCell className="text-xs font-mono text-muted-foreground">
                      {req.step_failed}
                    </TableCell>
                    <TableCell className="text-sm">{req.attempts}</TableCell>
                    <TableCell className="text-xs text-destructive max-w-56 truncate">
                      {req.last_error}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                      {new Date(req.failed_at).toLocaleString("ar-EG")}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="outline" size="sm"
                        disabled={retrying === req.id}
                        onClick={() => handleRetry(req.id, req.shortcode)}
                      >
                        <RotateCcw className={`w-3.5 h-3.5 ml-1 ${retrying === req.id ? "animate-spin" : ""}`} />
                        إعادة
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
