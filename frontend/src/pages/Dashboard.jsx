import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import { toast } from "sonner"
import {
  FileText, TrendingUp, AlertTriangle, Shield,
  Search, RotateCcw, Send, ChevronUp, ChevronDown,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
function getSeverityFromScore(score) {
  if (score == null) return { label: "—", fg: "#6b7280", bg: "#f3f4f6" }
  if (score >= 8) return { label: "حرج", fg: "#dc2626", bg: "#fef2f2" }
  if (score >= 6) return { label: "شديد", fg: "#ea580c", bg: "#fff7ed" }
  if (score >= 4) return { label: "متوسط", fg: "#ca8a04", bg: "#fef9c3" }
  return { label: "بسيط", fg: "#16a34a", bg: "#dcfce7" }
}

function DangerChip({ score }) {
  const { label, fg, bg } = getSeverityFromScore(score)
  return (
    <span
      className="inline-flex flex-col items-center font-bold text-xs px-2 py-0.5 rounded leading-tight"
      style={{ color: fg, background: bg }}
    >
      <span className="text-sm">{label}</span>
      <span className="font-normal opacity-70">{score != null ? `${score}/10` : ""}</span>
    </span>
  )
}

function CrimeCategoryPills({ categories }) {
  if (!categories?.length) return <span className="text-muted-foreground">—</span>
  return (
    <div className="flex flex-wrap gap-1">
      {categories.map(id => (
        <span
          key={id}
          className="inline-block text-xs px-1.5 py-0.5 rounded-full bg-primary/10 text-primary font-medium leading-tight"
        >
          {CRIME_CATEGORIES[id] ?? `فئة ${id}`}
        </span>
      ))}
    </div>
  )
}

import { fetchReports, fetchStats, analyzeUrl } from "@/lib/api"

const EMPTY = "all"

const CRIME_CATEGORIES = {
  1: "أعمال العنف والمشاجرات",
  2: "أعمال البلطجة وترويع المواطنين",
  3: "الاستخدام غير القانوني للأسلحة",
  4: "الجرائم المرورية وتعريض الأرواح للخطر",
  5: "التعدي على الآداب والقيم العامة",
  6: "السرقة والنشل والسطو",
  7: "تعاطي أو ترويج المخدرات",
  8: "التحرش الجسدي واللفظي",
  9: "لا شيء",
  10: "اخري",
}

// Maps dropdown key → API min/max danger params
const DANGER_RANGES = {
  "8-10": { min_danger: 8, max_danger: 10 },
  "6-7": { min_danger: 6, max_danger: 7 },
  "4-5": { min_danger: 4, max_danger: 5 },
  "0-3": { min_danger: 0, max_danger: 3 },
}

function StatCard({ title, value, sub, icon: Icon, color }) {
  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm text-muted-foreground">{title}</p>
            <p className="text-3xl font-bold mt-1">{value ?? "—"}</p>
            {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
          </div>
          <div className={`p-2 rounded-lg ${color}`}>
            <Icon className="w-5 h-5 text-white" />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function SortIcon({ field, sortBy, sortOrder }) {
  if (sortBy !== field) return null
  return sortOrder === "asc"
    ? <ChevronUp className="w-3 h-3 inline ms-1" />
    : <ChevronDown className="w-3 h-3 inline ms-1" />
}

export default function Dashboard() {
  const navigate = useNavigate()

  // ── Filters ──────────────────────────────────────────────────────────────
  const [page, setPage] = useState(1)
  const [dangerRange, setDangerRange] = useState(EMPTY)
  const [classification, setClassification] = useState(EMPTY)
  const [inEgypt, setInEgypt] = useState(EMPTY)
  const [crimeCategory, setCrimeCategory] = useState(EMPTY)
  const [sortBy, setSortBy] = useState("processed_at")
  const [sortOrder, setSortOrder] = useState("desc")
  const [urlInput, setUrlInput] = useState("")
  const [submitting, setSubmitting] = useState(false)

  const limit = 20

  function toggleSort(field) {
    if (sortBy === field) {
      setSortOrder(o => (o === "desc" ? "asc" : "desc"))
    } else {
      setSortBy(field)
      setSortOrder("desc")
    }
    setPage(1)
  }

  function resetFilters() {
    setDangerRange(EMPTY)
    setClassification(EMPTY)
    setInEgypt(EMPTY)
    setCrimeCategory(EMPTY)
    setSortBy("processed_at")
    setSortOrder("desc")
    setPage(1)
  }

  // ── Queries ───────────────────────────────────────────────────────────────
  const statsQuery = useQuery({
    queryKey: ["stats"],
    queryFn: fetchStats,
    staleTime: 30_000,
  })

  const reportsQuery = useQuery({
    queryKey: ["reports", page, dangerRange, classification, inEgypt, crimeCategory, sortBy, sortOrder],
    queryFn: () => {
      const rangeParams = dangerRange !== EMPTY ? DANGER_RANGES[dangerRange] : {}
      return fetchReports({
        page,
        limit,
        ...rangeParams,
        crime_classification: classification !== EMPTY ? classification : undefined,
        in_egypt: inEgypt !== EMPTY ? inEgypt : undefined,
        crime_category: crimeCategory !== EMPTY ? crimeCategory : undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
      })
    },
    keepPreviousData: true,
  })

  const stats = statsQuery.data
  const reports = reportsQuery.data

  const totalPages = reports ? Math.ceil(reports.total / limit) : 1

  // ── Analyze form ──────────────────────────────────────────────────────────
  async function handleAnalyze(e) {
    e.preventDefault()
    if (!urlInput.trim()) return
    setSubmitting(true)
    try {
      const res = await analyzeUrl(urlInput.trim())
      toast.success(
        res.type === "full"
          ? `تمت إضافة الرابط للمعالجة الكاملة (${res.identifier})`
          : `تمت إضافة الرابط للمعالجة المباشرة (${res.identifier})`
      )
      setUrlInput("")
    } catch (err) {
      toast.error(`فشل الإرسال: ${err.message}`)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">لوحة التحكم</h1>
          <p className="text-muted-foreground text-sm mt-0.5">نظام رصد الجرائم الإلكترونية</p>
        </div>
        {/* Analyze form */}
        <form onSubmit={handleAnalyze} className="flex gap-2 items-center">
          <Input
            value={urlInput}
            onChange={e => setUrlInput(e.target.value)}
            placeholder="رابط Instagram أو رابط مباشر للفيديو..."
            className="w-96 text-start"
            dir="ltr"
          />
          <Button type="submit" disabled={submitting || !urlInput.trim()}>
            <Send className="w-4 h-4" />
            {submitting ? "جارٍ..." : "تحليل"}
          </Button>
        </form>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          title="إجمالي التقارير"
          value={stats?.total_reports}
          icon={FileText}
          color="bg-primary"
        />
        <StatCard
          title="متوسط درجة الخطورة"
          value={stats ? `${stats.avg_danger_score}/10` : null}
          icon={TrendingUp}
          color="bg-orange-500"
        />
        <StatCard
          title="جنايات"
          value={stats?.by_classification?.["جناية"]}
          sub="جريمة جنائية"
          icon={AlertTriangle}
          color="bg-red-500"
        />
        <StatCard
          title="حرجة"
          value={stats?.by_severity?.critical}
          sub="مستوى خطر حرج"
          icon={Shield}
          color="bg-rose-600"
        />
      </div>

      {/* Filter bar */}
      <Card>
        <CardHeader className="pb-3 pt-4 px-4">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">الفلاتر</CardTitle>
            <Button variant="ghost" size="sm" onClick={resetFilters}>
              <RotateCcw className="w-3.5 h-3.5 ml-1" />
              إعادة تعيين
            </Button>
          </div>
        </CardHeader>
        <CardContent className="px-4 pb-4">
          <div className="flex gap-4 flex-wrap items-start">
            <div className="flex flex-col gap-1">
              <label className="text-xs text-muted-foreground">مستوى الخطورة</label>
              <Select value={dangerRange} onValueChange={v => { setDangerRange(v); setPage(1) }}>
                <SelectTrigger className="w-40">
                  <SelectValue placeholder="الكل" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={EMPTY}>كل المستويات</SelectItem>
                  <SelectItem value="8-10">حرج ‏(8 – 10)</SelectItem>
                  <SelectItem value="6-7">شديد ‏(6 – 7)</SelectItem>
                  <SelectItem value="4-5">متوسط ‏(4 – 5)</SelectItem>
                  <SelectItem value="0-3">بسيط ‏(0 – 3)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs text-muted-foreground">التصنيف القانوني</label>
              <Select value={classification} onValueChange={v => { setClassification(v); setPage(1) }}>
                <SelectTrigger className="w-40">
                  <SelectValue placeholder="الكل" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={EMPTY}>كل التصنيفات</SelectItem>
                  <SelectItem value="جناية">جناية</SelectItem>
                  <SelectItem value="جنحة">جنحة</SelectItem>
                  <SelectItem value="مخالفة">مخالفة</SelectItem>
                  <SelectItem value="لا شيء">لا شيء</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs text-muted-foreground">داخل مصر</label>
              <Select value={inEgypt} onValueChange={v => { setInEgypt(v); setPage(1) }}>
                <SelectTrigger className="w-36">
                  <SelectValue placeholder="الكل" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={EMPTY}>الكل</SelectItem>
                  <SelectItem value="نعم">نعم</SelectItem>
                  <SelectItem value="لا">لا</SelectItem>
                  <SelectItem value="غير محدد">غير محدد</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs text-muted-foreground">فئة الجريمة</label>
              <Select value={crimeCategory} onValueChange={v => { setCrimeCategory(v); setPage(1) }}>
                <SelectTrigger className="w-52">
                  <SelectValue placeholder="الكل" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={EMPTY}>كل الفئات</SelectItem>
                  {Object.entries(CRIME_CATEGORIES).map(([k, v]) => (
                    <SelectItem key={k} value={k}>{v}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Reports table */}
      <Card>
        <CardContent className="p-0">
          {reportsQuery.isLoading ? (
            <div className="py-16 text-center text-muted-foreground">جارٍ التحميل...</div>
          ) : reportsQuery.isError ? (
            <div className="py-16 text-center text-destructive">
              فشل تحميل التقارير: {reportsQuery.error.message}
            </div>
          ) : !reports?.data?.length ? (
            <div className="py-16 text-center text-muted-foreground">
              <Search className="w-8 h-8 mx-auto mb-2 opacity-40" />
              <p>لا توجد تقارير</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="cursor-pointer select-none" onClick={() => toggleSort("processed_at")}>
                    التاريخ <SortIcon field="processed_at" sortBy={sortBy} sortOrder={sortOrder} />
                  </TableHead>
                  <TableHead>المعرف</TableHead>
                  <TableHead className="cursor-pointer select-none w-24" onClick={() => toggleSort("danger_score")}>
                    مستوى الخطورة <SortIcon field="danger_score" sortBy={sortBy} sortOrder={sortOrder} />
                  </TableHead>
                  <TableHead>التصنيف</TableHead>
                  <TableHead>داخل مصر</TableHead>
                  <TableHead>فئة الجريمة</TableHead>
                  <TableHead className="cursor-pointer select-none w-20" onClick={() => toggleSort("mention_count")}>
                    الإشارات <SortIcon field="mention_count" sortBy={sortBy} sortOrder={sortOrder} />
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {reports.data.map(r => (
                  <TableRow
                    key={r.id}
                    className="cursor-pointer hover:bg-accent/50 transition-colors"
                    onClick={() => navigate(`/reports/${r.id}`)}
                  >
                    <TableCell className="text-sm text-muted-foreground whitespace-nowrap">
                      {new Date(r.processed_at).toLocaleString("ar-EG")}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground" dir="ltr">
                      {r.reel_shortcode}
                    </TableCell>
                    <TableCell>
                      <DangerChip score={r.danger_score} />
                    </TableCell>
                    <TableCell className="text-sm">
                      {r.crime_classification || "—"}
                    </TableCell>
                    <TableCell className="text-sm">
                      {r.in_egypt || "—"}
                    </TableCell>
                    <TableCell className="text-sm max-w-[220px]">
                      <CrimeCategoryPills categories={r.crime_category} />
                    </TableCell>
                    <TableCell className="text-sm text-center font-medium">
                      {r.mention_count ?? 1}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="outline" size="sm"
            disabled={page === 1}
            onClick={() => setPage(p => p - 1)}
          >
            السابق
          </Button>
          <span className="text-sm text-muted-foreground">
            {page} / {totalPages} ({reports?.total} نتيجة)
          </span>
          <Button
            variant="outline" size="sm"
            disabled={page >= totalPages}
            onClick={() => setPage(p => p + 1)}
          >
            التالي
          </Button>
        </div>
      )}
    </div>
  )
}
