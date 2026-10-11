import { motion } from 'motion/react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Camera, PawPrint } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { api, type Pet } from '@/lib/api'

export function petAge(birth: string) {
  const b = new Date(birth)
  const now = new Date()
  const months = (now.getFullYear() - b.getFullYear()) * 12 + now.getMonth() - b.getMonth() - (now.getDate() < b.getDate() ? 1 : 0)
  if (months < 12) return `${months} month${months === 1 ? '' : 's'}`
  const y = Math.floor(months / 12)
  return `${y} year${y === 1 ? '' : 's'}`
}

export default function Pets() {
  const [pets, setPets] = useState<Pet[]>()
  useEffect(() => { api<Pet[]>('/pets/').then(setPets) }, [])

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">My pets</h1>
      {!pets && <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-64 rounded-2xl" />)}</div>}
      {pets?.length === 0 && (
        <div className="space-y-4 rounded-3xl border-2 border-dashed p-10 text-center">
          <PawPrint className="mx-auto size-10 text-primary" />
          <p className="text-muted-foreground">Scan your pet, then tap “Save as new pet” to get a care plan made for them.</p>
          <Button asChild className="gap-2"><Link to="/app"><Camera className="size-4" /> Scan my pet</Link></Button>
        </div>
      )}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {pets?.map((p, i) => (
          <motion.div key={p.id} layout initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.05 }} whileHover={{ y: -2 }}>
            <Link to={`/app/pets/${p.id}`} className="block overflow-hidden rounded-2xl border bg-card">
              {p.photo
                ? <img src={p.photo} alt="" className="aspect-[4/3] w-full object-cover" />
                : <div className="grid aspect-[4/3] place-items-center bg-secondary"><PawPrint className="size-10 text-primary/50" /></div>}
              <div className="p-4">
                <p className="font-heading text-lg font-semibold">{p.name}</p>
                <p className="text-sm text-muted-foreground">{p.breed_name ?? 'Unknown breed'} · {petAge(p.birth_date)} · {Number(p.weight_kg)} kg</p>
              </div>
            </Link>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
