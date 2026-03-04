import { useState } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { RefreshCw, RotateCcw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { fetchFailedRequests, retryFailedRequest } from "@/lib/api"
import { Tooltip, TooltipProvider } from "@/components/ui/tooltip"

export default function FailedRequests() {
    const queryClient = useQueryClient()
    const [retrying, setRetrying] = useState(null)

    const failedQuery = useQuery({
        queryKey: ["failed-requests"],
        queryFn: fetchFailedRequests,
        refetchInterval: 30_000,
    })

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

    const failed = failedQuery.data?.data || []

    return (
        <TooltipProvider>
            <div className="space-y-6">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold">الطلبات الفاشلة</h1>
                        <p className="text-muted-foreground text-sm mt-0.5">
                            طلبات فشلت أثناء المعالجة وتحتاج إلى مراجعة
                        </p>
                    </div>
                    <Button
                        variant="outline" size="sm"
                        onClick={() => failedQuery.refetch()}
                        disabled={failedQuery.isFetching}
                    >
                        <RefreshCw className={`w-4 h-4 ml-1 ${failedQuery.isFetching ? "animate-spin" : ""}`} />
                        تحديث
                    </Button>
                </div>

                <Card>
                    <CardHeader className="pb-3">
                        <CardTitle className="text-base flex items-center gap-2">
                            الطلبات الفاشلة
                            {failed.length > 0 && (
                                <span className="text-xs bg-destructive text-destructive-foreground rounded-full px-2 py-0.5">
                                    {failed.length}
                                </span>
                            )}
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="p-0">
                        {failedQuery.isLoading ? (
                            <div className="py-12 text-center text-muted-foreground">جارٍ التحميل...</div>
                        ) : !failed.length ? (
                            <div className="py-12 text-center text-muted-foreground text-sm">
                                لا توجد طلبات فاشلة 🎉
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
                                                <Tooltip content={req.last_error}>
                                                    <span className="truncate block">{req.last_error}</span>
                                                </Tooltip>
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
        </TooltipProvider>
    )
}
