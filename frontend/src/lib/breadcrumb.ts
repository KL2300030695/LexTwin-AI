import type { Clause } from '../types/document'

export interface BreadcrumbItem {
  sectionNumber: string
  heading: string | null
}

/** Walks a clause's parent_section chain within the same document, resolving
 * each ancestor's heading, so a citation can show e.g. "4 > 4.2 > 4.2.1"
 * instead of just the leaf section number. */
export function buildBreadcrumb(clause: Clause, siblingClauses: Clause[]): BreadcrumbItem[] {
  const bySection = new Map(
    siblingClauses.filter((c) => c.section_number).map((c) => [c.section_number as string, c]),
  )
  const chain: BreadcrumbItem[] = []
  const seen = new Set<string>()
  let current: Clause | undefined = clause

  while (current?.section_number && !seen.has(current.section_number)) {
    seen.add(current.section_number)
    chain.unshift({ sectionNumber: current.section_number, heading: current.heading })
    if (!current.parent_section) break
    current = bySection.get(current.parent_section)
  }

  return chain
}
