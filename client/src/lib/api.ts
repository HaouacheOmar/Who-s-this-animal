// Thin fetch wrapper: same-origin session cookie + Django CSRF header (IMPLEMENTATION.md §3.3).

export class ApiError extends Error {
  status: number
  data: Record<string, unknown> | null
  constructor(status: number, data: Record<string, unknown> | null) {
    super(typeof data?.detail === 'string' ? data.detail : `Request failed (${status})`)
    this.status = status
    this.data = data
  }
  /** First message for a form field, e.g. err.field('password'). */
  field(name: string): string | undefined {
    const v = this.data?.[name]
    return Array.isArray(v) ? String(v[0]) : undefined
  }
}

function cookie(name: string) {
  return document.cookie.split('; ').find((c) => c.startsWith(name + '='))?.split('=')[1]
}

export async function api<T = unknown>(path: string, opts: { method?: string; body?: unknown } = {}): Promise<T> {
  const method = opts.method ?? (opts.body ? 'POST' : 'GET')
  const headers: Record<string, string> = {}
  if (method !== 'GET') headers['X-CSRFToken'] = cookie('csrftoken') ?? ''
  let body: BodyInit | undefined
  if (opts.body instanceof FormData) body = opts.body
  else if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(opts.body)
  }
  const r = await fetch('/api' + path, { method, headers, body, credentials: 'include' })
  const data = r.status === 204 ? null : await r.json().catch(() => null)
  if (!r.ok) throw new ApiError(r.status, data)
  return data as T
}

// ---- API shapes (server/*/views.py) ----

export type User = { id: number; email: string; email_verified: boolean }

export type RoutineItem = { time: string; activity: string; duration_min: number; category: string }

export type Product = {
  brand: string
  name: string
  food_type: string
  grams_per_day: number[] | null
  where_to_find: string
  price_dzd_approx: number | null
}

export type CareSheet = {
  personalised: boolean
  life_stage: 'young' | 'adult' | 'senior'
  breed: {
    id: number
    name: string
    species: 'dog' | 'cat' | 'bird'
    origin: string
    size_class: string | null
    adult_weight_kg: (string | null)[]
    life_expectancy_years: number[] | null
    temperament: string
    exercise_min_per_day: number | null
    grooming: string
    health_notes: string
  }
  feeding: {
    kcal_per_day: number[] | null
    bird_grams_per_day: number[] | null
    meals_per_day: number | null
    recommended_food_type: string | null
    products: Product[]
  }
  foods_to_avoid: string[]
  routine: RoutineItem[]
  disclaimer: string
}

export type Scan = {
  id: number
  image: string
  breed: number | null
  breed_name: string | null
  confidence: number | null
  top_k: { label: string; confidence: number; name?: string | null }[]
  is_possible_mix: boolean
  reject_reason: string | null
  model_version: string | null
  pet: number | null
  pet_name: string | null
  created_at: string
  care?: CareSheet | null
}

export type Pet = {
  id: number
  name: string
  breed: number | null
  breed_name: string | null
  birth_date: string
  sex: 'male' | 'female' | 'unknown'
  neutered: boolean
  weight_kg: string
  activity_level: 'low' | 'normal' | 'high'
  photo: string | null
  weight_warning: string | null
  care?: CareSheet | null
  scans?: { id: number; created_at: string; confidence: number | null }[]
}

export type Page<T> = { count: number; next: string | null; results: T[] }
