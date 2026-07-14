export type DiffOpType = 'equal' | 'insert' | 'delete'

export interface DiffOp {
  type: DiffOpType
  text: string
}

export interface RedlineSuggestion {
  doc_id: string
  clause_id: string
  original_text: string
  suggested_text: string
  rationale: string
  diff: DiffOp[]
  diff_markdown: string
}
