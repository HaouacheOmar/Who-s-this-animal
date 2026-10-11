import { AnimatePresence, motion } from 'motion/react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { HelpCircle, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { api, type Page, type Scan } from '@/lib/api'

export function ScanCard({ scan, onDelete }: { scan: Scan; onDelete?: () => void }) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.96 }}
      whileHover={{ y: -2 }}
      className="group relative overflow-hidden rounded-2xl border bg-card"
    >
      <Link to={`/app/scans/${scan.id}`} className="block">
        <img src={scan.image} alt="" className="aspect-[4/3] w-full object-cover" loading="lazy" />
        <div className="space-y-1 p-3">
          <p className="flex items-center gap-1.5 font-semibold">
            {scan.breed_name ?? <><HelpCircle className="size-4 text-muted-foreground" /> Not recognized</>}
          </p>
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            {scan.confidence != null && scan.breed && <span>{Math.round(scan.confidence * 100)}%</span>}
            <span>{new Date(scan.created_at).toLocaleDateString()}</span>
            {scan.pet_name && <Badge variant="secondary">{scan.pet_name}</Badge>}
          </div>
        </div>
      </Link>
      {onDelete && (
        <Button
          size="icon"
          variant="secondary"
          aria-label="Delete scan"
          className="absolute top-2 right-2 opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100 max-md:opacity-100"
          onClick={onDelete}
        >
          <Trash2 className="size-4" />
        </Button>
      )}
    </motion.div>
  )
}

export default function History() {
  const [scans, setScans] = useState<Scan[]>()
  const [next, setNext] = useState<number | null>(null)

  const load = (page: number) =>
    api<Page<Scan>>(`/scans/?page=${page}`).then((p) => {
      setScans((prev) => (page === 1 ? p.results : [...(prev ?? []), ...p.results]))
      setNext(p.next ? page + 1 : null)
    })

  useEffect(() => { load(1) }, [])

  const remove = async (scan: Scan) => {
    if (!confirm('Delete this scan? Its photo will be removed.')) return // PRD S15
    await api(`/scans/${scan.id}/`, { method: 'DELETE' })
    setScans((s) => s?.filter((x) => x.id !== scan.id))
    toast.success('Scan deleted')
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">History</h1>
      {scans?.length === 0 && (
        <p className="text-muted-foreground">No scans yet. <Link to="/app" className="text-primary underline">Scan your pet</Link></p>
      )}
      <motion.div layout className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <AnimatePresence>
          {scans?.map((s) => <ScanCard key={s.id} scan={s} onDelete={() => remove(s)} />)}
        </AnimatePresence>
      </motion.div>
      {next && (
        <div className="text-center">
          <Button variant="outline" onClick={() => load(next)}>Load more</Button>
        </div>
      )}
    </div>
  )
}
