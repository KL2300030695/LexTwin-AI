export type DocType = 'MSA' | 'SOW' | 'OTHER'

export type ReferenceType =
  | 'section'
  | 'exhibit'
  | 'appendix'
  | 'annexure'
  | 'schedule'
  | 'external_doc'

export interface Reference {
  raw_text: string
  type: ReferenceType
  target_section: string | null
  target_label: string | null
  is_notwithstanding: boolean
  char_start: number
  char_end: number
  context: string
}

export interface TableModel {
  id: string
  clause_id: string | null
  page: number
  rows: string[][]
  header: string[] | null
}

export interface Clause {
  id: string
  doc_id: string
  doc_type: DocType
  section_number: string | null
  parent_section: string | null
  level: number
  heading: string | null
  text: string
  page_start: number
  page_end: number
  references: Reference[]
  table_ids: string[]
}

export interface ParsedDocument {
  doc_id: string
  filename: string
  doc_type: DocType
  clauses: Clause[]
  tables: TableModel[]
  page_count: number
  known_exhibit_labels: string[]
  available_exhibit_labels: string[]
}
