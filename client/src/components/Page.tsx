import { motion } from 'motion/react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { PawPrint } from 'lucide-react'

/** Route-change fade/slide (IMPLEMENTATION.md §3.2). Keyed by the parent on pathname. */
export function FadeIn({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, transform: 'translateY(8px)' }}
      animate={{ opacity: 1, transform: 'translateY(0px)' }}
      exit={{ opacity: 0, transform: 'translateY(-8px)' }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
    >
      {children}
    </motion.div>
  )
}

export function Logo({ className = '' }: { className?: string }) {
  return (
    <Link to="/" className={`flex items-center gap-2 font-heading text-xl font-bold whitespace-nowrap ${className}`}>
      <span className="grid size-9 place-items-center rounded-xl bg-primary text-primary-foreground">
        <PawPrint className="size-5" />
      </span>
      Who's This Animal
    </Link>
  )
}

/** Centered card layout for the public auth pages. */
export function Page({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-8 px-4 py-10">
      <Logo />
      <FadeIn className="w-full max-w-sm">{children}</FadeIn>
    </div>
  )
}
