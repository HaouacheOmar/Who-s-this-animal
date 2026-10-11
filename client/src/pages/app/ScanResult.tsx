import { motion } from 'motion/react'
import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { Camera, HelpCircle, Link2, Plus, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { CareSheet } from '@/components/CareSheet'
import { PetForm } from '@/components/PetForm'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { api, type Pet, type Scan } from '@/lib/api'

const TIPS: Record<string, string> = {
  unreadable: "This file isn't a readable image.",
  too_small: 'This photo is too small. Use a larger photo.',
  blurry: 'This photo is blurry. Hold still and try again.',
  too_dark: 'This photo is too dark. Try in better light.',
  low_confidence: "We couldn't identify this animal.",
}

/** Breed name pops in, confidence bar fills 0 → value (IMPLEMENTATION.md §3.2). */
function Identification({ scan }: { scan: Scan }) {
  const [bar, setBar] = useState(0)
  const pct = Math.round((scan.confidence ?? 0) * 100)
  useEffect(() => { const t = setTimeout(() => setBar(pct), 150); return () => clearTimeout(t) }, [pct])
  const [first, second] = scan.top_k

  return (
    <div className="grid items-center gap-6 md:grid-cols-[minmax(0,320px)_1fr]">
      <motion.img
        src={scan.image}
        alt=""
        initial={{ opacity: 0, transform: 'scale(0.96)' }}
        animate={{ opacity: 1, transform: 'scale(1)' }}
        className="aspect-square w-full rounded-3xl object-cover shadow-xl shadow-primary/10"
      />
      <div className="space-y-4">
        <p className="text-sm font-medium tracking-wide text-muted-foreground uppercase">
          {scan.is_possible_mix ? 'Possibly a mix of' : 'This looks like a'}
        </p>
        <motion.h1
          initial={{ opacity: 0, transform: 'scale(0.8)' }}
          animate={{ opacity: 1, transform: 'scale(1)' }}
          transition={{ type: 'spring', bounce: 0.45, visualDuration: 0.5 }}
          className="origin-left text-4xl font-bold md:text-5xl"
        >
          {scan.is_possible_mix ? `${first?.name} & ${second?.name}` : scan.breed_name}
        </motion.h1>
        <div className="max-w-sm space-y-1.5">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Confidence</span>
            <span className="font-semibold tabular-nums">{pct}%</span>
          </div>
          <Progress value={bar} className="h-2.5 [&>*]:transition-transform [&>*]:duration-700" />
        </div>
        {scan.is_possible_mix && (
          <p className="text-sm text-muted-foreground">
            {first?.name} {Math.round(first.confidence * 100)}% · {second?.name} {Math.round(second.confidence * 100)}%.
            The care sheet below uses {first?.name}.
          </p>
        )}
      </div>
    </div>
  )
}

function Rejected({ scan }: { scan: Scan }) {
  return (
    <div className="mx-auto max-w-md space-y-6 text-center">
      <img src={scan.image} alt="" className="mx-auto aspect-square w-56 rounded-3xl object-cover opacity-80" />
      <div className="space-y-2">
        <HelpCircle className="mx-auto size-10 text-muted-foreground" />
        <h1 className="text-2xl font-bold">{TIPS[scan.reject_reason ?? 'low_confidence']}</h1>
      </div>
      {/* PRD S7 photo tips */}
      <ul className="space-y-1.5 rounded-2xl bg-card p-5 text-left text-sm">
        <li>📸 Fill the frame with your pet</li>
        <li>☀️ Use good, even light</li>
        <li>🐾 Show the face and body</li>
        <li>1️⃣ One animal per photo</li>
      </ul>
      <Button asChild className="h-11 gap-2"><Link to="/app"><Camera className="size-4" /> Try again</Link></Button>
    </div>
  )
}

export default function ScanResult() {
  const { id } = useParams()
  const navigate = useNavigate()
  const initial = useLocation().state as Scan | null
  const [scan, setScan] = useState<Scan | null>(initial?.id === Number(id) ? initial : null)
  const [dialog, setDialog] = useState<'new' | 'attach' | null>(null)
  const [pets, setPets] = useState<Pet[]>([])

  useEffect(() => {
    if (!scan) api<Scan>(`/scans/${id}/`).then(setScan, () => navigate('/app/history', { replace: true }))
  }, [id, scan, navigate])

  useEffect(() => {
    if (dialog === 'attach') api<Pet[]>('/pets/').then(setPets)
  }, [dialog])

  const attach = async (pet: Pet) => {
    const r = await api<Scan & { breed_differs: boolean }>(`/scans/${scan!.id}/attach/`, { body: { pet_id: pet.id } })
    setScan(r)
    setDialog(null)
    toast.success(`Added to ${pet.name}`)
    // PRD S10 step 3
    if (r.breed_differs && confirm(`Update ${pet.name}'s breed to ${r.breed_name}?`)) {
      await api(`/pets/${pet.id}/`, { method: 'PATCH', body: { breed: r.breed } })
      toast.success(`${pet.name} is now a ${r.breed_name}`)
    }
  }

  const remove = async () => {
    if (!confirm('Delete this scan? Its photo will be removed.')) return
    await api(`/scans/${scan!.id}/`, { method: 'DELETE' })
    navigate('/app/history')
  }

  if (!scan) return <Skeleton className="h-80 w-full rounded-3xl" />
  if (!scan.breed || !scan.care) return <Rejected scan={scan} />

  return (
    <div className="space-y-8">
      <Identification scan={scan} />

      <div className="flex flex-wrap gap-3">
        {scan.pet ? (
          <Button asChild variant="secondary"><Link to={`/app/pets/${scan.pet}`}>Saved to {scan.pet_name}</Link></Button>
        ) : (
          <>
            <Button className="h-11 gap-2" onClick={() => setDialog('new')}><Plus className="size-4" /> Save as new pet</Button>
            <Button variant="outline" className="h-11 gap-2" onClick={() => setDialog('attach')}><Link2 className="size-4" /> Attach to a pet</Button>
          </>
        )}
        <Button variant="ghost" className="h-11 gap-2 text-muted-foreground" onClick={remove}><Trash2 className="size-4" /> Delete</Button>
      </div>

      <CareSheet care={scan.care} notesQuery={`scan=${scan.id}`} />

      <Dialog open={dialog !== null} onOpenChange={(o) => !o && setDialog(null)}>
        <DialogContent className="max-h-[90svh] overflow-y-auto sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="font-heading text-xl">{dialog === 'new' ? 'Save as new pet' : 'Attach to a pet'}</DialogTitle>
            <DialogDescription>
              {dialog === 'new' ? 'Feeding amounts will be calculated for this exact pet.' : 'Pick one of your pets.'}
            </DialogDescription>
          </DialogHeader>
          {dialog === 'new' && (
            <PetForm breedId={scan.breed} fromScan={scan.id} onSaved={(p) => navigate(`/app/pets/${p.id}`)} />
          )}
          {dialog === 'attach' && (
            pets.length ? (
              <ul className="space-y-2">
                {pets.map((p) => (
                  <li key={p.id}>
                    <button onClick={() => attach(p)} className="flex w-full items-center gap-3 rounded-xl border p-3 text-left hover:bg-secondary">
                      {p.photo ? <img src={p.photo} alt="" className="size-10 rounded-lg object-cover" /> : <span className="size-10 rounded-lg bg-secondary" />}
                      <span><b>{p.name}</b><br /><span className="text-sm text-muted-foreground">{p.breed_name ?? 'Unknown breed'}</span></span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : <p className="text-sm text-muted-foreground">You have no pets yet. Save this scan as a new pet instead.</p>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
