export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatCitation {
  clause_id: string
  doc_id: string
  section_number: string | null
  heading: string | null
}

export interface ChatRequest {
  doc_ids: string[]
  question: string
  history: ChatMessage[]
}

export interface ChatResponse {
  answer: string
  citations: ChatCitation[]
}
