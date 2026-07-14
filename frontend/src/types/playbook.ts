export interface TopicRule {
  topic: string
  patterns: string[]
}

export interface ReferenceCategory {
  source: string
  category: string
  example_clauses: string[]
  hypothesis?: string
}
