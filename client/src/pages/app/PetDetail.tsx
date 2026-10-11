import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { AlertTriangle, Pencil, PawPrint, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { CareSheet } from '@/components/CareSheet'
import { PetForm } from '@/components/PetForm'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Skeleton } from '@/components/ui/skeleton'
import { api, type Pet } from '@/lib/api'
import { petAge } from '@/pages/app/Pets'

export default function PetDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [pet, setPet] = useState<Pet>()
  const [editing, setEditing] = useState(false)

  const load = () => api<Pet>(`/pets/${id}/`).then(setPet, () => navigate('/app/pets', { replace: true }))
  useEffect(() => { load() }, [id]) // eslint-disable-line react-hooks/exhaustive-deps

  const remove = async () => {
    if (!confirm(`${pet!.name} will be removed. Its scans stay in your history.`)) return // PRD S15
    await api(`/pets/${pet!.id}/`, { method: 'DELETE' })
    toast.success(`${pet!.name} removed`)
    navigate('/app/pets')
  }

  if (!pet) return <Skeleton className="h-80 w-full rounded-3xl" />

  // Profile version in the query: editing weight/age refetches personal notes (PRD S11).
  const notesQuery = `pet=${pet.id}&v=${pet.weight_kg}-${pet.birth_date}-${pet.neutered}-${pet.activity_level}-${pet.breed}`

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-6 sm:flex-row sm:items-center">
        {pet.photo
          ? <img src={pet.photo} alt="" className="size-32 rounded-3xl object-cover shadow-lg shadow-primary/10" />
          : <div className="grid size-32 place-items-center rounded-3xl bg-secondary"><PawPrint className="size-10 text-primary/50" /></div>}
        <div className="flex-1 space-y-2">
          <h1 className="text-4xl font-bold">{pet.name}</h1>
          <div className="flex flex-wrap gap-2">
            <Badge variant="secondary">{pet.breed_name ?? 'Unknown breed'}</Badge>
            <Badge variant="outline">{petAge(pet.birth_date)}</Badge>
            <Badge variant="outline">{Number(pet.weight_kg)} kg</Badge>
            <Badge variant="outline" className="capitalize">{pet.sex === 'unknown' ? 'Sex unknown' : pet.sex}</Badge>
            {pet.neutered && <Badge variant="outline">Neutered</Badge>}
            <Badge variant="outline">{pet.activity_level[0].toUpperCase() + pet.activity_level.slice(1)} activity</Badge>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" className="gap-2" onClick={() => setEditing(true)}><Pencil className="size-4" /> Edit</Button>
          <Button variant="ghost" size="icon" aria-label={`Delete ${pet.name}`} onClick={remove}><Trash2 className="size-4" /></Button>
        </div>
      </div>

      {pet.weight_warning && (
        <p className="flex items-center gap-2 rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
          <AlertTriangle className="size-4 shrink-0" /> {pet.weight_warning}
        </p>
      )}

      {pet.care
        ? <CareSheet care={pet.care} notesQuery={notesQuery} />
        : <p className="text-muted-foreground">Set a breed to get {pet.name}'s care plan.</p>}

      {!!pet.scans?.length && (
        <section>
          <h2 className="mb-3 text-xl font-semibold">Scans of {pet.name}</h2>
          <ul className="flex flex-wrap gap-2">
            {pet.scans.map((s) => (
              <li key={s.id}>
                <Link to={`/app/scans/${s.id}`} className="block rounded-lg border bg-card px-3 py-2 text-sm hover:bg-secondary">
                  {new Date(s.created_at).toLocaleDateString()}
                  {s.confidence != null && <span className="text-muted-foreground"> · {Math.round(s.confidence * 100)}%</span>}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      <Dialog open={editing} onOpenChange={setEditing}>
        <DialogContent className="max-h-[90svh] overflow-y-auto sm:max-w-md">
          <DialogHeader><DialogTitle className="font-heading text-xl">Edit {pet.name}</DialogTitle></DialogHeader>
          <PetForm pet={pet} onSaved={() => { setEditing(false); load(); toast.success('Saved') }} />
        </DialogContent>
      </Dialog>
    </div>
  )
}
