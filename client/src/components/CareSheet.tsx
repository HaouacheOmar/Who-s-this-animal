import { motion } from 'motion/react'
import { useEffect, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle, Ban, Clock, HeartPulse, MapPin, Sparkles, Utensils } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { api, type CareSheet as Sheet } from '@/lib/api'

const STAGE = { young: { dog: 'Puppy', cat: 'Kitten', bird: 'Young' }, adult: 'Adult', senior: 'Senior' }
const CATEGORY_COLOR: Record<string, string> = {
  meal: 'bg-primary', exercise: 'bg-accent', play: 'bg-amber-400', training: 'bg-sky-400',
  grooming: 'bg-violet-400', rest: 'bg-stone-300', cage: 'bg-teal-400',
}

const range = (v: (number | string | null)[] | null | undefined, unit = '') => {
  if (!v || v[0] == null) return '—'
  const [a, b] = v.map(Number)
  return (a === b || b == null ? `${a}` : `${a}–${b}`) + unit
}

/** Sections stagger in after the result reveal (IMPLEMENTATION.md §3.2). */
function Section({ icon, title, children, i }: { icon: ReactNode; title: string; children: ReactNode; i: number }) {
  return (
    <motion.section
      initial={{ opacity: 0, transform: 'translateY(12px)' }}
      animate={{ opacity: 1, transform: 'translateY(0px)' }}
      transition={{ delay: 0.15 + i * 0.07, type: 'spring', bounce: 0.2, visualDuration: 0.4 }}
      className="rounded-2xl border bg-card p-5 md:p-6"
    >
      <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold">
        <span className="grid size-8 place-items-center rounded-lg bg-secondary text-primary">{icon}</span>
        {title}
      </h3>
      {children}
    </motion.section>
  )
}

function Stat({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="rounded-xl bg-secondary/60 p-3">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-0.5 font-semibold">{value}</dd>
    </div>
  )
}

/** LLM personal notes: loaded separately so the curated sheet renders at once (PRD S5 step 5, S14). */
function PersonalNotes({ query }: { query: string }) {
  const [text, setText] = useState<string | null | undefined>()
  useEffect(() => {
    let live = true
    setText(undefined)
    api<{ text: string }>(`/care-text/?${query}`).then((r) => live && setText(r.text), () => live && setText(null))
    return () => { live = false }
  }, [query])

  if (text === null)
    return <p className="text-sm text-muted-foreground">Personal notes are unavailable right now.</p>
  if (text === undefined)
    return (
      <div className="space-y-2">
        <Skeleton className="h-4 w-full" /><Skeleton className="h-4 w-11/12" /><Skeleton className="h-4 w-4/5" />
      </div>
    )
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-3 leading-relaxed">
      {text.split(/\n+/).map((p, i) => <p key={i}>{p}</p>)}
    </motion.div>
  )
}

export function CareSheet({ care, notesQuery }: { care: Sheet; notesQuery: string }) {
  const { breed, feeding } = care
  const stage = care.life_stage === 'young' ? STAGE.young[breed.species] : STAGE[care.life_stage]
  const bird = breed.species === 'bird'
  let i = 0

  return (
    <div className="space-y-4">
      <Section i={i++} icon={<Sparkles className="size-4" />} title={`About the ${breed.name}`}>
        <div className="mb-3 flex flex-wrap gap-2">
          <Badge variant="secondary">{stage}</Badge>
          {breed.size_class && <Badge variant="secondary" className="capitalize">{breed.size_class}</Badge>}
          {breed.origin && <Badge variant="outline">From {breed.origin}</Badge>}
          {!care.personalised && <Badge variant="outline">Breed average</Badge>}
        </div>
        <dl className="mb-4 grid grid-cols-2 gap-2 sm:grid-cols-3">
          {!bird && <Stat label="Adult weight" value={range(breed.adult_weight_kg, ' kg')} />}
          <Stat label="Life expectancy" value={range(breed.life_expectancy_years, ' yrs')} />
          {breed.exercise_min_per_day != null && <Stat label="Exercise" value={`${breed.exercise_min_per_day} min/day`} />}
        </dl>
        <p className="leading-relaxed text-muted-foreground">{breed.temperament}</p>
      </Section>

      <Section i={i++} icon={<Utensils className="size-4" />} title="Food per day">
        <dl className="mb-4 grid grid-cols-2 gap-2 sm:grid-cols-3">
          {bird
            ? <Stat label="Seed + pellet mix" value={range(feeding.bird_grams_per_day, ' g')} />
            : <Stat label="Daily energy" value={range(feeding.kcal_per_day, ' kcal')} />}
          <Stat label="Meals" value={feeding.meals_per_day ? `${feeding.meals_per_day} per day` : '—'} />
          {feeding.recommended_food_type && <Stat label="Best food type" value={feeding.recommended_food_type} />}
        </dl>
        {feeding.products.length > 0 && (
          <>
            <h4 className="mb-2 text-sm font-semibold">Found in Algeria</h4>
            <ul className="divide-y rounded-xl border">
              {feeding.products.map((p) => (
                <li key={p.brand + p.name} className="flex flex-wrap items-center justify-between gap-2 p-3">
                  <div>
                    <p className="font-medium">{p.brand} <span className="text-muted-foreground">{p.name}</span></p>
                    <p className="text-xs text-muted-foreground">
                      {p.where_to_find}{p.price_dzd_approx ? ` · ~${p.price_dzd_approx.toLocaleString()} DZD` : ''}
                    </p>
                  </div>
                  {p.grams_per_day && (
                    <Badge className="bg-accent text-accent-foreground">
                      {range(p.grams_per_day, ' g/day')}{p.food_type === 'wet' && ' if fed alone'}
                    </Badge>
                  )}
                </li>
              ))}
            </ul>
          </>
        )}
        <Button asChild variant="outline" className="mt-4 gap-2">
          <Link to="/app/shops"><MapPin className="size-4" /> Find shops near me</Link>
        </Button>
      </Section>

      {care.routine.length > 0 && (
        <Section i={i++} icon={<Clock className="size-4" />} title="A typical day">
          <ol className="relative space-y-3 border-l-2 border-dashed border-border pl-6">
            {care.routine.map((r, k) => (
              <li key={k} className="relative">
                <span className={`absolute top-1.5 -left-[31px] size-3 rounded-full ring-4 ring-card ${CATEGORY_COLOR[r.category] ?? 'bg-muted'}`} />
                <p className="text-sm"><span className="font-semibold tabular-nums">{r.time}</span> · {r.activity}</p>
                <p className="text-xs text-muted-foreground"><span className="capitalize">{r.category}</span> · {r.duration_min} min</p>
              </li>
            ))}
          </ol>
        </Section>
      )}

      {care.foods_to_avoid.length > 0 && (
        <Section i={i++} icon={<Ban className="size-4" />} title="Foods to avoid">
          <div className="flex flex-wrap gap-2">
            {care.foods_to_avoid.map((f, k) => <Badge key={k} variant="destructive">{f[0].toUpperCase() + f.slice(1)}</Badge>)}
          </div>
        </Section>
      )}

      {(breed.health_notes || breed.grooming) && (
        <Section i={i++} icon={<HeartPulse className="size-4" />} title="Health & grooming">
          {breed.health_notes && <p className="mb-3 leading-relaxed">{breed.health_notes}</p>}
          {breed.grooming && (
            <p className="leading-relaxed text-muted-foreground">
              {/\s/.test(breed.grooming.trim()) ? breed.grooming : `Grooming needs: ${breed.grooming.toLowerCase()}`}
            </p>
          )}
        </Section>
      )}

      <Section i={i++} icon={<Sparkles className="size-4" />} title="Personal notes">
        <PersonalNotes query={notesQuery} />
      </Section>

      <p className="flex items-start gap-2 rounded-xl bg-secondary/60 p-4 text-sm text-muted-foreground">
        <AlertTriangle className="mt-0.5 size-4 shrink-0" /> {care.disclaimer}
      </p>
    </div>
  )
}
