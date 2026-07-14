export interface Obligation {
  id: string
  doc_id: string
  clause_id: string
  section_number: string | null
  heading: string | null
  text: string
  responsible_party: string | null
  obligation_verb: string
  deadline_text: string | null
  deadline_days: number | null
  page: number
}
