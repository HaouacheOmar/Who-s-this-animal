import { useEffect, useState, type FormEvent } from 'react'
import { CircleMarker, MapContainer, Popup, TileLayer } from 'react-leaflet'
import { ExternalLink, LocateFixed, Search, Store, Stethoscope } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'

// Browser -> OSM directly: the owner's location never reaches our backend (IMPLEMENTATION.md §8).
type Place = { id: number; lat: number; lon: number; name: string; kind: 'shop' | 'vet'; address?: string; hours?: string; km: number }
type LatLon = [number, number]

function km([a, b]: LatLon, [c, d]: LatLon) {
  const r = Math.PI / 180
  const h = Math.sin(((c - a) * r) / 2) ** 2 + Math.cos(a * r) * Math.cos(c * r) * Math.sin(((d - b) * r) / 2) ** 2
  return 12742 * Math.asin(Math.sqrt(h))
}

type OsmElement = { id: number; lat?: number; lon?: number; center?: { lat: number; lon: number }; tags?: Record<string, string> }

async function overpass(center: LatLon, radius: number): Promise<Place[]> {
  const [lat, lon] = center
  const q = `[out:json][timeout:10];(nwr["shop"="pet"](around:${radius},${lat},${lon});nwr["amenity"="veterinary"](around:${radius},${lat},${lon}););out center tags;`
  // The public Overpass server is often overloaded; give up after 12 s and use the Nominatim fallback.
  const r = await fetch('https://overpass-api.de/api/interpreter', {
    method: 'POST', body: new URLSearchParams({ data: q }), signal: AbortSignal.timeout(12000),
  })
  if (!r.ok) throw new Error('overpass')
  const { elements } = (await r.json()) as { elements: OsmElement[] }
  return elements
    .map((e) => {
      const p = { lat: e.lat ?? e.center!.lat, lon: e.lon ?? e.center!.lon }
      const t = e.tags ?? {}
      const address = [t['addr:housenumber'], t['addr:street'], t['addr:city']].filter(Boolean).join(' ') || undefined
      return {
        id: e.id, ...p, address, hours: t.opening_hours,
        kind: t.amenity === 'veterinary' ? 'vet' : 'shop',
        name: t.name ?? (t.amenity === 'veterinary' ? 'Veterinary clinic' : 'Pet shop'),
        km: km(center, [p.lat, p.lon]),
      } as Place
    })
    .sort((a, b) => a.km - b.km)
}

type NominatimHit = { place_id: number; lat: string; lon: string; name: string; type: string; display_name: string }

/** Fallback when Overpass is down: Nominatim POI search inside a box. "vétérinaire" because Algerian vets are named in French. */
async function nominatim(center: LatLon, radius: number): Promise<Place[]> {
  const [lat, lon] = center
  const d = radius / 1000 / 111
  const box = [lon - d, lat + d, lon + d, lat - d].join(',')
  const places: Place[] = []
  for (const [term, type, kind] of [['pet shop', 'pet', 'shop'], ['vétérinaire', 'veterinary', 'vet']] as const) {
    const r = await fetch(`https://nominatim.openstreetmap.org/search?format=jsonv2&limit=40&countrycodes=dz&bounded=1&viewbox=${box}&q=${encodeURIComponent(term)}`)
    if (!r.ok) throw new Error('nominatim')
    for (const h of (await r.json()) as NominatimHit[]) {
      if (h.type !== type) continue
      const p: LatLon = [Number(h.lat), Number(h.lon)]
      places.push({
        id: h.place_id, lat: p[0], lon: p[1], kind,
        name: h.name || (kind === 'vet' ? 'Veterinary clinic' : 'Pet shop'),
        address: h.display_name.split(', ').slice(1, 3).join(', '),
        km: km(center, p),
      })
    }
    await new Promise((res) => setTimeout(res, 1100)) // Nominatim usage policy: max 1 request/s
  }
  return places.filter((p) => p.km <= radius / 1000).sort((a, b) => a.km - b.km)
}

const findPlaces = (center: LatLon, radius: number) => overpass(center, radius).catch(() => nominatim(center, radius))

export default function Shops() {
  const [center, setCenter] = useState<LatLon | null>(null)
  const [places, setPlaces] = useState<Place[]>()
  const [status, setStatus] = useState<'locating' | 'denied' | 'loading' | 'ready' | 'error'>('locating')
  const [radius, setRadius] = useState(5)

  useEffect(() => {
    if (!navigator.geolocation) return setStatus('denied')
    navigator.geolocation.getCurrentPosition(
      (p) => setCenter([p.coords.latitude, p.coords.longitude]),
      () => setStatus('denied'), // PRD S13 2a
      { timeout: 10000 },
    )
  }, [])

  useEffect(() => {
    if (!center) return
    setStatus('loading')
    // PRD S13 3a: widen 5 km -> 15 km when empty
    findPlaces(center, 5000)
      .then(async (found) => {
        if (found.length) return [found, 5] as const
        return [await findPlaces(center, 15000), 15] as const
      })
      .then(([found, r]) => { setPlaces(found); setRadius(r); setStatus('ready') }, () => setStatus('error'))
  }, [center])

  const search = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const q = new FormData(e.currentTarget).get('q')
    const r = await fetch(`https://nominatim.openstreetmap.org/search?format=json&limit=1&countrycodes=dz&q=${encodeURIComponent(String(q))}`)
    const [hit] = r.ok ? await r.json() : []
    if (hit) setCenter([Number(hit.lat), Number(hit.lon)])
    else setStatus('denied')
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Pet shops & vets near you</h1>
        <p className="mt-1 text-muted-foreground">Data from OpenStreetMap. Coverage in Algeria can be patchy.</p>
      </div>

      <form onSubmit={search} className="flex gap-2">
        <Input name="q" required placeholder="City or neighbourhood, e.g. Bab Ezzouar, Alger" className="h-11" />
        <Button className="h-11 gap-2"><Search className="size-4" /> Search</Button>
      </form>

      {status === 'locating' && <p className="flex items-center gap-2 text-sm text-muted-foreground"><LocateFixed className="size-4 animate-pulse" /> Finding your location…</p>}
      {status === 'denied' && !center && <p className="text-sm text-muted-foreground">Location is off. Search for your city or neighbourhood above.</p>}
      {status === 'error' && <p role="alert" className="text-sm text-destructive">Map service unavailable, try again later.</p>}

      {center && (
        <div className="grid gap-4 lg:grid-cols-[1fr_340px]">
          <MapContainer key={center.join()} center={center} zoom={radius === 5 ? 13 : 11} className="z-0 h-[420px] rounded-2xl border">
            <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                       url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" />
            <CircleMarker center={center} radius={8} pathOptions={{ color: '#fff', weight: 3, fillColor: '#2563eb', fillOpacity: 1 }}>
              <Popup>You are here</Popup>
            </CircleMarker>
            {places?.map((p) => (
              <CircleMarker key={p.id} center={[p.lat, p.lon]} radius={9}
                            pathOptions={{ color: '#fff', weight: 2, fillOpacity: 1, fillColor: p.kind === 'vet' ? '#6b9e7f' : '#c2633a' }}>
                <Popup><b>{p.name}</b><br />{p.kind === 'vet' ? 'Veterinary' : 'Pet shop'} · {p.km.toFixed(1)} km</Popup>
              </CircleMarker>
            ))}
          </MapContainer>

          <div className="max-h-[420px] space-y-2 overflow-y-auto">
            {status === 'loading' && [0, 1, 2].map((i) => <Skeleton key={i} className="h-20 rounded-xl" />)}
            {status === 'ready' && !places?.length && (
              <p className="rounded-xl bg-card p-4 text-sm text-muted-foreground">
                No shops found nearby on OpenStreetMap. Ask a local vet where to buy pet food.
              </p>
            )}
            {status === 'ready' && places?.map((p) => (
              <a key={p.id} href={`https://www.openstreetmap.org/?mlat=${p.lat}&mlon=${p.lon}#map=18/${p.lat}/${p.lon}`}
                 target="_blank" rel="noreferrer"
                 className="flex items-start gap-3 rounded-xl border bg-card p-3 transition-colors hover:bg-secondary">
                <span className={`grid size-9 shrink-0 place-items-center rounded-lg ${p.kind === 'vet' ? 'bg-accent/30 text-accent-foreground' : 'bg-primary/15 text-primary'}`}>
                  {p.kind === 'vet' ? <Stethoscope className="size-4" /> : <Store className="size-4" />}
                </span>
                <span className="min-w-0 flex-1 text-sm">
                  <span className="block truncate font-semibold">{p.name}</span>
                  {p.address && <span className="block truncate text-muted-foreground">{p.address}</span>}
                  {p.hours && <span className="block truncate text-xs text-muted-foreground">{p.hours}</span>}
                </span>
                <span className="flex items-center gap-1 text-xs whitespace-nowrap text-muted-foreground">
                  {p.km.toFixed(1)} km <ExternalLink className="size-3" />
                </span>
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
