import { useParams, useNavigate } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import {
  ArrowRight, MapPin, Mic, Video, Users,
  Car, Sword, FileText, AlertCircle,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import SeverityBadge from "@/components/SeverityBadge"
import { fetchReport } from "@/lib/api"

// ── Color helpers (mirrors report_generator.py) ───────────────────────────────

const CLASSIFICATION_COLORS = {
  "جناية":  { fg: "#dc2626", bg: "#fef2f2" },
  "جنحة":   { fg: "#ea580c", bg: "#fff7ed" },
  "مخالفة": { fg: "#ca8a04", bg: "#fef9c3" },
  "لا شيء": { fg: "#94a3b8", bg: "#f1f5f9" },
}

function classificationColor(cls) {
  return CLASSIFICATION_COLORS[cls] || { fg: "#94a3b8", bg: "#f1f5f9" }
}

const SENTIMENT_COLORS = {
  anger:      { fg: "#dc2626", bg: "#fef2f2" },
  aggression: { fg: "#dc2626", bg: "#fef2f2" },
  distress:   { fg: "#ea580c", bg: "#fff7ed" },
  fear:       { fg: "#7c3aed", bg: "#f5f3ff" },
  calm:       { fg: "#16a34a", bg: "#dcfce7" },
  neutral:    { fg: "#475569", bg: "#f1f5f9" },
  unknown:    { fg: "#6b7280", bg: "#f9fafb" },
  error:      { fg: "#6b7280", bg: "#f9fafb" },
}

function sentimentColor(sentiment) {
  const key = (sentiment || "").toLowerCase().split("/")[0].trim()
  return SENTIMENT_COLORS[key] || { fg: "#475569", bg: "#f1f5f9" }
}

const INTENSITY_CLASSES = {
  low:    "bg-green-100 text-green-800",
  medium: "bg-yellow-100 text-yellow-800",
  high:   "bg-red-100 text-red-800",
}
const INTENSITY_LABELS = { low: "منخفض", medium: "متوسط", high: "مرتفع" }

// ── Sub-components ────────────────────────────────────────────────────────────

function Section({ icon: Icon, title, children }) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Icon className="w-4 h-4 text-muted-foreground" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  )
}

function InfoRow({ label, value }) {
  if (!value) return null
  return (
    <div className="flex gap-3 py-1.5 border-b last:border-0 text-sm">
      <span className="text-muted-foreground w-36 shrink-0">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  )
}

function DangerScoreSection({ score, classification, inEgypt }) {
  const isOutside  = inEgypt === "لا"
  const isUnknown  = inEgypt === "غير محدد" || !inEgypt
  const isInEgypt  = inEgypt === "نعم"

  const { fg, bg } = isOutside
    ? { fg: "#94a3b8", bg: "#f1f5f9" }
    : classificationColor(classification)

  const barWidth   = isOutside ? "0%" : `${score * 10}%`
  const barOpacity = isUnknown ? 0.45 : 1

  return (
    <Card className="col-span-1" style={{ borderRightWidth: 6, borderRightColor: fg, borderRightStyle: "solid" }}>
      <CardContent className="p-5 space-y-3">
        {/* Jurisdiction banner */}
        {isOutside && (
          <div className="flex items-center gap-2 text-xs font-semibold rounded-lg px-3 py-2 bg-slate-50 border border-slate-200 text-slate-500">
            <span>⚠️</span>
            الجريمة خارج نطاق الاختصاص المصري — درجة الخطورة غير مفعّلة
          </div>
        )}
        {isUnknown && (
          <div className="flex items-center gap-2 text-xs font-semibold rounded-lg px-3 py-2 bg-amber-50 border border-amber-200 text-amber-800">
            <span>ℹ️</span>
            موقع الجريمة غير محدد — يُعرض التقييم للاستئناس فقط
          </div>
        )}

        {/* Score number */}
        <div className="flex items-center gap-3">
          <div
            className="text-4xl font-extrabold rounded-xl px-4 py-2 leading-none"
            style={{ color: fg, background: bg }}
          >
            {score}<span className="text-lg font-medium opacity-70">/10</span>
          </div>
          <div className="text-xs font-semibold text-muted-foreground">
            التصنيف القانوني:{" "}
            <span style={{ color: fg }}>{classification || "لا شيء"}</span>
          </div>
        </div>

        {/* Bar */}
        <div style={{ opacity: barOpacity }}>
          <div className="h-3 rounded-full bg-slate-200 overflow-hidden" dir="ltr">
            <div
              className="h-full rounded-full transition-all"
              style={{ width: barWidth, background: fg }}
            />
          </div>
          {/* Range segments */}
          <div className="flex mt-1.5 rounded overflow-hidden text-[10px] font-semibold" dir="ltr">
            <div className="flex flex-col items-center px-1 py-0.5 bg-slate-100 text-slate-400" style={{ width: "10%" }}>
              <span>لا شيء</span><span className="opacity-70">0</span>
            </div>
            <div className="flex flex-col items-center px-1 py-0.5 bg-yellow-100 text-yellow-800" style={{ width: "30%" }}>
              <span>مخالفة</span><span className="opacity-70">1–3</span>
            </div>
            <div className="flex flex-col items-center px-1 py-0.5 bg-orange-100 text-orange-800" style={{ width: "30%" }}>
              <span>جنحة</span><span className="opacity-70">4–6</span>
            </div>
            <div className="flex flex-col items-center px-1 py-0.5 bg-rose-100 text-rose-800" style={{ width: "30%" }}>
              <span>جناية</span><span className="opacity-70">7–10</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ReportDetail() {
  const { id } = useParams()
  const navigate = useNavigate()

  const { data: report, isLoading, isError, error } = useQuery({
    queryKey: ["report", id],
    queryFn: () => fetchReport(id),
  })

  if (isLoading) {
    return <div className="py-24 text-center text-muted-foreground">جارٍ تحميل التقرير...</div>
  }

  if (isError) {
    return (
      <div className="py-24 text-center">
        <AlertCircle className="w-8 h-8 text-destructive mx-auto mb-2" />
        <p className="text-destructive">{error.message}</p>
        <Button variant="outline" className="mt-4" onClick={() => navigate(-1)}>عودة</Button>
      </div>
    )
  }

  const raw      = report.raw_analysis_data
  const video    = raw?.video_analysis
  const audio    = raw?.audio_analysis
  const entities = video?.detected_entities
  const scene    = video?.scene_landmarks

  const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
  const bucket      = import.meta.env.VITE_SUPABASE_BUCKET || "videos"
  const videoUrl    = supabaseUrl
    ? `${supabaseUrl}/storage/v1/object/public/${bucket}/videos/${report.reel_shortcode}.mp4`
    : null

  const sentimentClr = sentimentColor(audio?.sentiment)

  return (
    <div className="space-y-6">
      {/* Back + header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
            <ArrowRight className="w-4 h-4" />
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold">تقرير التحليل</h1>
              <span className="font-mono text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded" dir="ltr">
                {report.reel_shortcode}
              </span>
            </div>
            <p className="text-sm text-muted-foreground mt-0.5">
              {new Date(report.processed_at).toLocaleString("ar-EG")}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <SeverityBadge severity={report.severity} />
          <span className="text-sm">{report.crime_classification || "—"}</span>
        </div>
      </div>

      {/* Overview grid */}
      <div className="grid grid-cols-3 gap-4">
        {/* Danger score — jurisdiction-aware */}
        <DangerScoreSection
          score={report.danger_score}
          classification={report.crime_classification}
          inEgypt={report.in_egypt}
        />

        {/* Key info */}
        <Card className="col-span-2">
          <CardContent className="p-5">
            <InfoRow label="الموقع التقريبي"  value={report.approximate_location} />
            <InfoRow label="الجريمة الأساسية" value={report.rule_violated} />
            <InfoRow label="داخل مصر"          value={report.in_egypt} />
            <InfoRow label="التصنيف القانوني"  value={report.crime_classification} />
          </CardContent>
        </Card>
      </div>

      {/* Overall assessment + recommended action */}
      {report.overall_assessment && (
        <Card className="border-r-4 border-r-primary">
          <CardContent className="p-5 space-y-3">
            <p className="text-sm text-muted-foreground">التقييم العام</p>
            <p className="leading-relaxed">{report.overall_assessment}</p>
            {report.recommended_action && (
              <div className="border-r-4 border-r-blue-500 bg-blue-50 rounded-lg px-4 py-3 text-sm text-blue-900">
                <p className="text-[10px] font-bold uppercase tracking-widest text-blue-400 mb-1">الإجراء الموصى به</p>
                {report.recommended_action}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Video player */}
      {videoUrl && (
        <Section icon={Video} title="الفيديو">
          <video src={videoUrl} controls className="w-full max-h-96 rounded-md bg-black" />
        </Section>
      )}

      {/* Video description */}
      {video?.description && (
        <Section icon={FileText} title="وصف الفيديو">
          <p className="text-sm leading-relaxed">{video.description}</p>
        </Section>
      )}

      {/* Crimes */}
      {video?.possible_crimes?.length > 0 && (
        <Section icon={AlertCircle} title={`الجرائم المرصودة (${video.possible_crimes.length})`}>
          <div className="space-y-4">
            {video.possible_crimes.map((crime, i) => (
              <div key={i} className="border rounded-lg p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <SeverityBadge severity={crime.severity} />
                    <span className="font-semibold">{crime.rule_violated}</span>
                  </div>
                  <span className="text-xs text-muted-foreground font-mono">@ {crime.timestamp}</span>
                </div>
                <p className="text-sm text-muted-foreground">{crime.content}</p>

                {crime.matched_articles?.length > 0 && (
                  <div className="space-y-2 pt-2 border-t border-dashed">
                    <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                      المواد القانونية ذات الصلة
                    </p>
                    {crime.matched_articles.map((art, j) => (
                      <div key={j} className="bg-muted/50 border border-border border-r-4 border-r-blue-400 rounded-md p-3 text-sm space-y-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-bold text-blue-700">المادة {art.article_number}</span>
                          <span className="text-xs text-muted-foreground flex-1">{art.chapter_title}</span>
                          <span className="text-[10px] font-semibold bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
                            {Math.round(art.similarity * 100)}% تطابق
                          </span>
                        </div>
                        <p className="text-muted-foreground leading-relaxed">{art.article_text}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Detected entities */}
      {entities && (
        <div className="grid grid-cols-3 gap-4">
          {/* People */}
          <Card>
            <CardContent className="p-5 flex flex-col items-center justify-center gap-2 text-center">
              <Users className="w-6 h-6 text-muted-foreground" />
              <p className="text-3xl font-bold">{entities.people_count}</p>
              <p className="text-sm text-muted-foreground">أشخاص مرصودون</p>
            </CardContent>
          </Card>

          {/* Weapons */}
          <Card className={entities.weapons?.length ? "border-red-200 bg-red-50/40" : ""}>
            <CardContent className="p-5">
              <div className="flex items-center gap-2 mb-3">
                <Sword className={`w-4 h-4 ${entities.weapons?.length ? "text-red-500" : "text-muted-foreground"}`} />
                <p className="font-medium text-sm">الأسلحة ({entities.weapons?.length || 0})</p>
              </div>
              {entities.weapons?.length ? (
                <div className="space-y-2">
                  {entities.weapons.map((w, i) => (
                    <div key={i} className="text-sm bg-red-50 border border-red-100 rounded px-2 py-1.5 flex items-center justify-between">
                      <span className="font-medium text-red-800">
                        {w.type}{w.description ? ` — ${w.description}` : ""}
                      </span>
                      <div className="flex items-center gap-2 text-xs text-red-400">
                        <span>{Math.round(w.confidence * 100)}% ثقة</span>
                        <span className="font-mono">@ {w.timestamp}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">لم يُرصد شيء</p>
              )}
            </CardContent>
          </Card>

          {/* Vehicles */}
          <Card>
            <CardContent className="p-5">
              <div className="flex items-center gap-2 mb-3">
                <Car className="w-4 h-4 text-muted-foreground" />
                <p className="font-medium text-sm">المركبات ({entities.vehicles?.length || 0})</p>
              </div>
              {entities.vehicles?.length ? (
                <div className="space-y-2">
                  {entities.vehicles.map((v, i) => (
                    <div key={i} className="text-sm space-y-0.5">
                      <div>{v.color} {v.type}{v.timestamp ? ` @ ${v.timestamp}` : ""}</div>
                      {v.license_plate?.raw_text ? (
                        <div className="text-xs text-muted-foreground font-mono" dir="ltr">
                          {v.license_plate.raw_text}
                          {v.license_plate.governorate_guess && ` — ${v.license_plate.governorate_guess}`}
                        </div>
                      ) : (
                        <div className="text-xs text-muted-foreground">لا لوحة</div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">لم يُرصد شيء</p>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Scene / Location */}
      {scene && (scene.approximate_location || scene.identified_landmark || scene.location_hints?.length) && (
        <Section icon={MapPin} title="الموقع والمشهد">
          <div className="space-y-1">
            <InfoRow label="الموقع التقريبي"  value={scene.approximate_location} />
            <InfoRow label="المعلم المُحدد"   value={scene.identified_landmark} />
            <InfoRow label="الطراز المعماري"  value={scene.architectural_style} />
            {scene.location_hints?.length > 0 && (
              <div className="flex gap-3 py-1.5 text-sm">
                <span className="text-muted-foreground w-36 shrink-0">إشارات الموقع</span>
                <ul className="space-y-0.5">
                  {scene.location_hints.map((h, i) => <li key={i}>• {h}</li>)}
                </ul>
              </div>
            )}
          </div>
        </Section>
      )}

      {/* Audio */}
      {audio && (
        <Section icon={Mic} title="تحليل الصوت">
          <div className="space-y-4">
            {/* Sentiment — colored badge */}
            <div className="flex gap-3 py-1.5 border-b text-sm items-center">
              <span className="text-muted-foreground w-36 shrink-0">المشاعر العامة</span>
              <span
                className="font-semibold px-3 py-0.5 rounded-full text-xs"
                style={{ color: sentimentClr.fg, background: sentimentClr.bg }}
              >
                {audio.sentiment}
              </span>
              {audio.confidence > 0 && (
                <span className="text-xs text-muted-foreground">
                  ({Math.round(audio.confidence * 100)}% ثقة)
                </span>
              )}
            </div>
            <InfoRow label="اللغة" value={audio.language?.toUpperCase()} />

            {/* Audio events */}
            {audio.audio_events?.length > 0 && (
              <div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-2">
                  الأحداث الصوتية
                </p>
                <div className="space-y-1.5">
                  {audio.audio_events.map((ev, i) => {
                    const intensityKey = (ev.intensity || "").toLowerCase()
                    const intensityCls = INTENSITY_CLASSES[intensityKey] || "bg-muted text-muted-foreground"
                    const intensityLabel = INTENSITY_LABELS[intensityKey] || ev.intensity
                    return (
                      <div key={i} className="flex items-center gap-3 text-sm bg-muted/50 rounded px-3 py-1.5">
                        <span className="font-mono text-xs text-muted-foreground w-10">{ev.timestamp}</span>
                        <span className="flex-1">{ev.event.replace(/_/g, " ")}</span>
                        {intensityLabel && (
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${intensityCls}`}>
                            {intensityLabel}
                          </span>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Transcript */}
            {audio.transcript && !audio.transcript.startsWith("[") && (
              <div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-2">
                  النص المفرغ
                </p>
                <p className="text-sm bg-muted/50 rounded-md p-3 leading-loose whitespace-pre-wrap">
                  {audio.transcript}
                </p>
              </div>
            )}
          </div>
        </Section>
      )}
    </div>
  )
}
