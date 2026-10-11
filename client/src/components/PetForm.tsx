import { useEffect, useState, type FormEvent } from 'react'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Switch } from '@/components/ui/switch'
import { Field } from '@/pages/Auth'
import { api, ApiError, type Pet } from '@/lib/api'

type Breed = { id: number; name: string; species: string }

const today = () => new Date().toISOString().slice(0, 10)

/** "Approximate age" -> birth date, for owners who don't know it (PRD S9). */
function birthFromAge(years: number, months: number) {
  const d = new Date()
  d.setMonth(d.getMonth() - (years * 12 + months))
  return d.toISOString().slice(0, 10)
}

function Choice({ name, value, options, onChange }: { name: string; value: string; options: string[]; onChange: (v: string) => void }) {
  return (
    <RadioGroup value={value} onValueChange={onChange} className="flex flex-wrap gap-2" name={name} aria-label={name}>
      {options.map((o) => (
        <Label key={o} className="flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 capitalize has-[[data-state=checked]]:border-primary has-[[data-state=checked]]:bg-secondary">
          <RadioGroupItem value={o} /> {o}
        </Label>
      ))}
    </RadioGroup>
  )
}

export function PetForm({ pet, breedId, fromScan, onSaved }: {
  pet?: Pet
  breedId?: number | null
  fromScan?: number
  onSaved: (pet: Pet) => void
}) {
  const [breeds, setBreeds] = useState<Breed[]>([])
  const [breed, setBreed] = useState(String(pet?.breed ?? breedId ?? ''))
  const [search, setSearch] = useState('')
  const [knowsBirth, setKnowsBirth] = useState(!!pet)
  const [sex, setSex] = useState<string>(pet?.sex ?? 'unknown')
  const [activity, setActivity] = useState<string>(pet?.activity_level ?? 'normal')
  const [neutered, setNeutered] = useState(pet?.neutered ?? false)
  const [errors, setErrors] = useState<ApiError | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => api<Breed[]>(`/breeds/?search=${encodeURIComponent(search)}`).then(setBreeds, () => {}), 200)
    return () => clearTimeout(t)
  }, [search])

  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const f = Object.fromEntries(new FormData(e.currentTarget)) as Record<string, string>
    const body = {
      name: f.name,
      breed: breed ? Number(breed) : null,
      birth_date: knowsBirth ? f.birth_date : birthFromAge(Number(f.age_years || 0), Number(f.age_months || 0)),
      sex,
      neutered,
      weight_kg: f.weight_kg,
      activity_level: activity,
      ...(fromScan ? { from_scan: fromScan } : {}),
    }
    setBusy(true)
    setErrors(null)
    try {
      onSaved(await api<Pet>(pet ? `/pets/${pet.id}/` : '/pets/', { method: pet ? 'PATCH' : 'POST', body }))
    } catch (err) {
      if (err instanceof ApiError) setErrors(err)
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <Field label="Name" name="name" required defaultValue={pet?.name} error={errors?.field('name')} />

      <div className="space-y-1.5">
        <Label htmlFor="breed">Breed</Label>
        <input
          className="h-9 w-full rounded-lg border bg-transparent px-3 text-sm"
          placeholder="Search breeds…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Search breeds"
        />
        <select id="breed" value={breed} onChange={(e) => setBreed(e.target.value)}
                className="h-11 w-full rounded-lg border bg-card px-3">
          <option value="">Unknown</option>
          {pet?.breed && !breeds.some((b) => b.id === pet.breed) && <option value={pet.breed}>{pet.breed_name}</option>}
          {breedId && !breeds.some((b) => b.id === breedId) && pet?.breed !== breedId && <option value={breedId}>Identified breed</option>}
          {breeds.map((b) => <option key={b.id} value={b.id}>{b.name} ({b.species})</option>)}
        </select>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium">Age</span>
          <button type="button" className="text-xs text-primary underline" onClick={() => setKnowsBirth(!knowsBirth)}>
            {knowsBirth ? "I don't know the birth date" : 'I know the birth date'}
          </button>
        </div>
        {knowsBirth ? (
          <Field label="Birth date" name="birth_date" type="date" required max={today()} defaultValue={pet?.birth_date}
                 error={errors?.field('birth_date')} />
        ) : (
          <div className="grid grid-cols-2 gap-3">
            <Field label="Years" name="age_years" type="number" min={0} max={40} defaultValue={1} required />
            <Field label="Months" name="age_months" type="number" min={0} max={11} defaultValue={0} required />
          </div>
        )}
      </div>

      <Field label="Weight (kg)" name="weight_kg" type="number" step="any" min="0.01" required
             defaultValue={pet?.weight_kg} error={errors?.field('weight_kg')} />

      <div className="space-y-2">
        <Label>Sex</Label>
        <Choice name="Sex" value={sex} options={['male', 'female', 'unknown']} onChange={setSex} />
      </div>
      <div className="space-y-2">
        <Label>Activity level</Label>
        <Choice name="Activity level" value={activity} options={['low', 'normal', 'high']} onChange={setActivity} />
      </div>
      {/* Not wrapped in <Label>: the switch is a button, so a wrapping label would toggle it twice */}
      <div className="flex items-center justify-between rounded-lg border p-3">
        <Label htmlFor="neutered">Neutered / spayed</Label>
        <Switch id="neutered" checked={neutered} onCheckedChange={setNeutered} />
      </div>

      {errors && !errors.data?.name && !errors.data?.weight_kg && !errors.data?.birth_date && (
        <p role="alert" className="text-sm text-destructive">{errors.message}</p>
      )}
      <Button className="h-11 w-full" disabled={busy}>{pet ? 'Save changes' : 'Save pet'}</Button>
    </form>
  )
}
