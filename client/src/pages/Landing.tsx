import { motion, type Variants } from 'motion/react'
import { Link, Navigate } from 'react-router-dom'
import { Camera, Clock, History, MapPin, ScanSearch, Sparkles, Utensils } from 'lucide-react'
import { Logo } from '@/components/Page'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/lib/auth'

const fadeUp: Variants = {
  hidden: { opacity: 0, transform: 'translateY(16px)' },
  show: { opacity: 1, transform: 'translateY(0px)', transition: { type: 'spring', bounce: 0.2, visualDuration: 0.5 } },
}
const stagger: Variants = { hidden: {}, show: { transition: { staggerChildren: 0.1 } } }

const STEPS = [
  { icon: Camera, title: 'Snap', text: 'Take a photo of your dog, cat or bird with your phone.' },
  { icon: ScanSearch, title: 'Identify', text: 'Our model recognises 150+ breeds and pet bird species.' },
  { icon: Sparkles, title: 'Care plan', text: 'Get food per day, a daily routine and where to buy food near you.' },
]

const FEATURES = [
  { icon: Utensils, title: 'Exact food per day', text: 'Grams per day for your pet’s weight, age and activity, with brands sold in Algeria.' },
  { icon: Clock, title: 'A day with your pet', text: 'Meals, walks, play, grooming and rest, laid out hour by hour.' },
  { icon: MapPin, title: 'Shops & vets nearby', text: 'A map of pet shops and veterinarians around you.' },
  { icon: History, title: 'Every scan saved', text: 'Your history and your pets’ profiles in one workspace.' },
]

/** Static preview of a result: shows what the app gives before signing up. */
function SampleCard() {
  return (
    <motion.div
      initial={{ opacity: 0, transform: 'translateY(24px) rotate(2deg)' }}
      animate={{ opacity: 1, transform: 'translateY(0px) rotate(2deg)' }}
      transition={{ delay: 0.4, type: 'spring', bounce: 0.25, visualDuration: 0.7 }}
      className="relative mx-auto w-full max-w-sm"
    >
      <motion.div
        animate={{ transform: ['translateY(0px)', 'translateY(-8px)', 'translateY(0px)'] }}
        transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}
        className="space-y-4 rounded-3xl border bg-card p-6 shadow-2xl shadow-primary/15"
      >
        <div className="flex items-center gap-4">
          <div className="grid size-16 place-items-center rounded-2xl bg-secondary text-4xl" aria-hidden>🐕</div>
          <div>
            <p className="text-xs tracking-wide text-muted-foreground uppercase">This looks like a</p>
            <p className="font-heading text-2xl font-bold">Golden Retriever</p>
          </div>
        </div>
        <div className="space-y-1">
          <div className="flex justify-between text-xs"><span className="text-muted-foreground">Confidence</span><b>94%</b></div>
          <div className="h-2 overflow-hidden rounded-full bg-secondary">
            <motion.div className="h-full rounded-full bg-primary" initial={{ width: 0 }} animate={{ width: '94%' }}
                        transition={{ delay: 0.9, duration: 0.9, ease: 'easeOut' }} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="rounded-xl bg-secondary/70 p-3"><p className="text-xs text-muted-foreground">Food per day</p><b>310 g · 2 meals</b></div>
          <div className="rounded-xl bg-secondary/70 p-3"><p className="text-xs text-muted-foreground">Exercise</p><b>60 min/day</b></div>
        </div>
        <ul className="space-y-1.5 text-sm">
          {[['07:00', 'Morning walk'], ['08:00', 'Breakfast'], ['18:30', 'Play & training']].map(([t, a]) => (
            <li key={t} className="flex gap-3"><span className="font-semibold tabular-nums">{t}</span><span className="text-muted-foreground">{a}</span></li>
          ))}
        </ul>
      </motion.div>
      <div className="absolute -top-6 -right-4 -z-10 size-32 rounded-full bg-accent/40 blur-2xl" />
      <div className="absolute -bottom-8 -left-6 -z-10 size-40 rounded-full bg-primary/25 blur-2xl" />
    </motion.div>
  )
}

export default function Landing() {
  const { user } = useAuth()
  if (user) return <Navigate to="/app" replace />

  return (
    <div className="overflow-x-clip">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-4 py-5 md:px-8">
        <Logo />
        <nav className="flex gap-2">
          <Button asChild variant="ghost"><Link to="/login">Log in</Link></Button>
          <Button asChild><Link to="/signup">Get started</Link></Button>
        </nav>
      </header>

      <section className="mx-auto grid max-w-6xl items-center gap-14 px-4 pt-10 pb-20 md:grid-cols-2 md:px-8 md:pt-16">
        <motion.div variants={stagger} initial="hidden" animate="show" className="space-y-6">
          <motion.p variants={fadeUp} className="inline-flex items-center gap-2 rounded-full bg-secondary px-3 py-1 text-sm font-medium">
            🐾 For first-time pet owners in Algeria
          </motion.p>
          <motion.h1 variants={fadeUp} className="text-5xl leading-[1.05] font-bold md:text-6xl">
            Know your pet. <span className="text-primary">Care for it right.</span>
          </motion.h1>
          <motion.p variants={fadeUp} className="max-w-md text-lg text-muted-foreground">
            Take a photo, learn your pet’s breed, and get a care plan: how much to feed each day, what its day should look like, and where to buy food nearby.
          </motion.p>
          <motion.div variants={fadeUp} className="flex flex-wrap gap-3">
            <Button asChild className="h-12 gap-2 px-6 text-base"><Link to="/signup"><Camera className="size-5" /> Scan my pet, free</Link></Button>
            <Button asChild variant="outline" className="h-12 px-6 text-base"><Link to="/login">I have an account</Link></Button>
          </motion.div>
        </motion.div>
        <SampleCard />
      </section>

      <section className="bg-card/60 py-20">
        <div className="mx-auto max-w-6xl px-4 md:px-8">
          <h2 className="mb-10 text-center text-3xl font-bold md:text-4xl">How it works</h2>
          <motion.ol variants={stagger} initial="hidden" whileInView="show" viewport={{ once: true, amount: 0.3 }}
                     className="grid gap-6 md:grid-cols-3">
            {STEPS.map(({ icon: Icon, title, text }, i) => (
              <motion.li key={title} variants={fadeUp} className="relative rounded-3xl border bg-background p-6">
                <span className="absolute top-5 right-6 font-heading text-5xl font-bold text-secondary">{i + 1}</span>
                <span className="mb-4 grid size-12 place-items-center rounded-2xl bg-primary text-primary-foreground"><Icon className="size-6" /></span>
                <h3 className="mb-1 text-xl font-semibold">{title}</h3>
                <p className="text-muted-foreground">{text}</p>
              </motion.li>
            ))}
          </motion.ol>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-20 md:px-8">
        <motion.div variants={stagger} initial="hidden" whileInView="show" viewport={{ once: true, amount: 0.2 }}
                    className="grid gap-5 sm:grid-cols-2">
          {FEATURES.map(({ icon: Icon, title, text }) => (
            <motion.div key={title} variants={fadeUp} className="flex gap-4 rounded-3xl border bg-card p-6">
              <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-accent/30 text-accent-foreground"><Icon className="size-5" /></span>
              <div><h3 className="mb-1 text-lg font-semibold">{title}</h3><p className="text-muted-foreground">{text}</p></div>
            </motion.div>
          ))}
        </motion.div>
        <div className="mt-16 rounded-3xl bg-primary p-10 text-center text-primary-foreground">
          <h2 className="text-3xl font-bold">Ready to meet your pet properly?</h2>
          <Button asChild variant="secondary" className="mt-6 h-12 px-6 text-base"><Link to="/signup">Create a free account</Link></Button>
        </div>
      </section>

      <footer className="border-t py-8 text-center text-sm text-muted-foreground">
        General guidance, not veterinary advice. Map data © OpenStreetMap contributors.
      </footer>
    </div>
  )
}
