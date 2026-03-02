import { Link, useLocation } from "react-router-dom"
import { LayoutDashboard, Activity, AlertTriangle } from "lucide-react"
import { cn } from "@/lib/utils"

const navItems = [
  { to: "/", label: "لوحة التحكم", icon: LayoutDashboard },
  { to: "/pipeline", label: "المهام الجارية", icon: Activity },
  { to: "/failed", label: "الطلبات الفاشلة", icon: AlertTriangle },
]

export default function Layout({ children }) {
  const { pathname } = useLocation()

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Top bar */}
      <header className="border-b bg-card sticky top-0 z-50">
        <div className="max-w-screen-xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xl font-bold tracking-tight">مشروع عين</span>
            <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded-full">
              نظام رصد الجرائم
            </span>
          </div>
          <nav className="flex items-center gap-1">
            {navItems.map(({ to, label, icon: Icon }) => (
              <Link
                key={to}
                to={to}
                className={cn(
                  "flex items-center gap-2 px-3 py-1.5 rounded-md text-sm transition-colors",
                  pathname === to
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                )}
              >
                <Icon className="w-4 h-4" />
                {label}
              </Link>
            ))}
          </nav>
        </div>
      </header>

      {/* Page content */}
      <main className="flex-1 max-w-screen-xl mx-auto w-full px-6 py-6">
        {children}
      </main>
    </div>
  )
}
