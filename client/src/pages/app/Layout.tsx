import { AnimatePresence } from 'motion/react'
import { NavLink, useLocation, useNavigate, useOutlet } from 'react-router-dom'
import { Camera, History, LogOut, MapPin, PawPrint } from 'lucide-react'
import { FadeIn, Logo } from '@/components/Page'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/lib/auth'
import { cn } from '@/lib/utils'

const NAV = [
  { to: '/app', label: 'Scan', icon: Camera, end: true },
  { to: '/app/history', label: 'History', icon: History },
  { to: '/app/pets', label: 'My pets', icon: PawPrint },
  { to: '/app/shops', label: 'Shops', icon: MapPin },
]

/** Workspace shell: left sidebar from md: up, bottom tab bar on phones (IMPLEMENTATION.md §3.1). */
export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const outlet = useOutlet()

  const signOut = async () => {
    await logout()
    navigate('/')
  }

  return (
    <div className="min-h-svh md:grid md:grid-cols-[240px_1fr]">
      <aside className="sticky top-0 hidden h-svh flex-col gap-8 border-r bg-card/60 p-5 md:flex">
        <Logo className="text-lg" />
        <nav className="flex flex-col gap-1">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn('flex items-center gap-3 rounded-xl px-3 py-2.5 font-medium text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground',
                  isActive && 'bg-secondary text-foreground')}
            >
              <Icon className="size-5" /> {label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto space-y-2 text-sm">
          <p className="truncate text-muted-foreground">{user?.email}</p>
          <Button variant="ghost" className="w-full justify-start gap-2 px-3" onClick={signOut}>
            <LogOut className="size-4" /> Log out
          </Button>
        </div>
      </aside>

      <div className="flex min-h-svh flex-col">
        <header className="flex items-center justify-between border-b px-4 py-3 md:hidden">
          <Logo className="text-base" />
          <Button variant="ghost" size="icon" aria-label="Log out" onClick={signOut}>
            <LogOut className="size-5" />
          </Button>
        </header>
        <main className="mx-auto w-full max-w-5xl flex-1 px-4 pt-6 pb-28 md:px-8 md:pt-10 md:pb-12">
          <AnimatePresence mode="wait">
            <FadeIn key={location.pathname}>{outlet}</FadeIn>
          </AnimatePresence>
        </main>
      </div>

      <nav className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-4 border-t bg-card/95 pb-[env(safe-area-inset-bottom)] backdrop-blur md:hidden">
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn('flex flex-col items-center gap-1 py-2.5 text-xs font-medium text-muted-foreground',
                isActive && 'text-primary')}
          >
            <Icon className="size-5" /> {label}
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
