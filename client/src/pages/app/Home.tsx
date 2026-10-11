import { AnimatePresence, motion } from 'motion/react'
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Camera, ImagePlus, RotateCcw } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { ScanCard } from '@/pages/app/History'
import { api, ApiError, type Page, type Scan } from '@/lib/api'

const MAX_BYTES = 10 * 1024 * 1024

/** Photo preview with a pulsing ring and a sweeping scan line while the model works (IMPLEMENTATION.md §3.2). */
function Scanning({ src, busy }: { src: string; busy: boolean }) {
  return (
    <div className="relative mx-auto aspect-square w-full max-w-sm">
      {busy && (
        <motion.div
          className="absolute -inset-3 rounded-[2rem] border-4 border-primary/50"
          animate={{ transform: ['scale(1)', 'scale(1.04)', 'scale(1)'], opacity: [0.9, 0.4, 0.9] }}
          transition={{ duration: 1.6, repeat: Infinity, ease: 'easeInOut' }}
        />
      )}
      <div className="relative size-full overflow-hidden rounded-3xl shadow-xl shadow-primary/10">
        <img src={src} alt="Your pet" className="size-full object-cover" />
        {busy && (
          <>
            <div className="absolute inset-0 bg-primary/10" />
            <motion.div
              className="absolute inset-x-0 top-0 h-1/4 bg-gradient-to-b from-transparent via-primary/40 to-transparent"
              animate={{ transform: ['translateY(-100%)', 'translateY(400%)'] }}
              transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut', repeatType: 'reverse' }}
            />
          </>
        )}
      </div>
    </div>
  )
}

export default function Home() {
  const navigate = useNavigate()
  const [file, setFile] = useState<File>()
  const [preview, setPreview] = useState<string>()
  const [busy, setBusy] = useState(false)
  const [recent, setRecent] = useState<Scan[]>([])

  useEffect(() => {
    api<Page<Scan>>('/scans/').then((p) => setRecent(p.results.slice(0, 3)), () => {})
  }, [])
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview) }, [preview])

  const pick = (f?: File) => {
    if (!f) return
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(f.type) || f.size > MAX_BYTES) {
      toast.error('Please upload a JPEG, PNG or WEBP image under 10 MB.') // PRD S8
      return
    }
    setFile(f)
    setPreview(URL.createObjectURL(f))
  }

  const identify = async () => {
    if (!file) return
    setBusy(true)
    const body = new FormData()
    body.append('image', file)
    try {
      const scan = await api<Scan>('/scans/', { body })
      navigate(`/app/scans/${scan.id}`, { state: scan })
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : 'Network error, try again.')
      setBusy(false)
    }
  }

  return (
    <div className="space-y-10">
      <div>
        <h1 className="text-3xl font-bold md:text-4xl">Who's this animal?</h1>
        <p className="mt-2 text-muted-foreground">Take a clear photo of your pet: one animal, good light, face visible.</p>
      </div>

      <AnimatePresence mode="wait">
        {preview ? (
          <motion.div key="preview" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-6">
            <Scanning src={preview} busy={busy} />
            <div className="flex justify-center gap-3">
              <Button variant="outline" className="h-11 gap-2" disabled={busy} onClick={() => { setFile(undefined); setPreview(undefined) }}>
                <RotateCcw className="size-4" /> Choose another
              </Button>
              <Button className="h-11 gap-2 px-6" disabled={busy} onClick={identify}>
                {busy ? 'Identifying…' : 'Identify'}
              </Button>
            </div>
          </motion.div>
        ) : (
          <motion.label
            key="pick"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            whileHover={{ transform: 'translateY(-2px)' }}
            className="group mx-auto flex aspect-square w-full max-w-sm cursor-pointer flex-col items-center justify-center gap-4 rounded-3xl border-2 border-dashed border-primary/40 bg-card text-center transition-colors hover:border-primary hover:bg-secondary/40 focus-within:ring-4 focus-within:ring-ring/40"
          >
            <span className="grid size-20 place-items-center rounded-full bg-primary text-primary-foreground shadow-lg shadow-primary/30 transition-transform group-hover:scale-105">
              <Camera className="size-9" />
            </span>
            <span className="font-heading text-xl font-semibold">Scan my pet</span>
            <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
              <ImagePlus className="size-4" /> Camera on phones, file picker on computers
            </span>
            {/* capture="environment": opens the rear camera on phones, file picker on desktop */}
            <input type="file" accept="image/jpeg,image/png,image/webp" capture="environment" className="sr-only"
                   onChange={(e) => pick(e.target.files?.[0])} />
          </motion.label>
        )}
      </AnimatePresence>

      {recent.length > 0 && (
        <section>
          <div className="mb-4 flex items-baseline justify-between">
            <h2 className="text-xl font-semibold">Recent scans</h2>
            <Link to="/app/history" className="text-sm font-medium text-primary hover:underline">See all</Link>
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            {recent.map((s) => <ScanCard key={s.id} scan={s} />)}
          </div>
        </section>
      )}
    </div>
  )
}
