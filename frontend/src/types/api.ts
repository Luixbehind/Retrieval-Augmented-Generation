// Tipos espelhando os schemas Pydantic da API (src/app/schemas/*.py)

export interface Client {
  id: string
  slug: string
  name: string
  created_at: string
  updated_at: string
  deleted_at: string | null
}

export interface ClientCreate {
  slug: string
  name: string
}

export type KnowledgeBaseStatus = "DRAFT" | "PUBLISHED" | "EDITED" | "ARCHIVED"
export type GoldenDatasetStatus = "IDLE" | "PENDING" | "COMPLETED" | "FAILED"

export interface KnowledgeBaseConfig {
  top_k: number
  hybrid_weight_bm25: number
  hybrid_weight_vector: number
  similarity_threshold: number
  golden_dataset_size: number
}

export interface KnowledgeBase {
  id: string
  name: string
  description: string | null
  type: string | null
  config: KnowledgeBaseConfig
  status: KnowledgeBaseStatus
  golden_dataset_status: GoldenDatasetStatus
  golden_dataset_error_message: string | null
  created_at: string
  updated_at: string
  deleted_at: string | null
}

export interface KnowledgeBaseCreate {
  name: string
  description?: string
  type?: string
  config?: Partial<KnowledgeBaseConfig>
}

export interface KnowledgeBaseUpdate {
  name?: string
  description?: string
  config?: Partial<KnowledgeBaseConfig>
}

export type DocumentType = "PDF" | "TXT" | "DOCS" | "JSON"
export type ProcessingStatus = "PENDING" | "COMPLETED" | "FAILED"
export type ContentEnvironment = "EDIT" | "PUBLISHED"

export interface KnowledgeDocument {
  id: string
  knowledge_base_id: string | null
  title: string | null
  type: string | null
  summary: string | null
  document_type: DocumentType | null
  processing_status: ProcessingStatus
  environment: ContentEnvironment
  created_at: string
  updated_at: string
  deleted_at: string | null
}

export interface KnowledgeDocumentStatus {
  id: string
  processing_status: ProcessingStatus
  summary: string | null
  deleted_at: string | null
}

export interface RetrievedChunk {
  id: string
  content?: string
  title?: string
  summary?: string
  article?: string
  section?: string
  score: number
  source: string
}

export interface RagChatRequest {
  query: string
}

export interface RagChatResponse {
  similarity_threshold: number
  latency_ms: number
  edited: RetrievedChunk[]
  edited_answer?: string
  published: RetrievedChunk[]
  published_answer?: string
}

export interface ApplicableArticle {
  article: string
  description: string
}

export type LgpdComplianceProcessingStatus = "PENDING" | "COMPLETED" | "FAILED"

export interface LgpdComplianceStatusResponse {
  report_id: string
  processing_status: LgpdComplianceProcessingStatus
  error_message?: string | null
  result?: LgpdComplianceResponse | null
  schema_file_name?: string | null
  terms_file_name?: string | null
}

export interface LgpdComplianceResponse {
  overall_status: string
  summary: string
  points_correct: string[]
  points_outside_law: string[]
  applicable_articles: ApplicableArticle[]
  risks: string[]
  recommendations: string[]
  report_id?: string
}

export interface GoldenQuestion {
  id: string
  knowledge_base_id: string
  question: string
  reference_answer: string
  created_at: string | null
  updated_at: string | null
}

export interface GoldenQuestionCreate {
  question: string
  reference_answer: string
}

export interface GoldenQuestionListResponse {
  questions: GoldenQuestion[]
}

export interface GoldenDatasetGenerateRequest {
  num_questions?: number
}

export type EvaluationRunStatus = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED"

export interface EvaluationResult {
  id: string
  golden_question_id: string | null
  question: string
  generated_answer: string | null
  retrieved_contexts: string[]
  latency_ms: number | null
  faithfulness: number | null
  answer_relevancy: number | null
  context_precision: number | null
  context_recall: number | null
  created_at: string | null
}

export interface EvaluationRun {
  id: string
  knowledge_base_id: string
  status: EvaluationRunStatus
  environment: string
  judge_model: string | null
  embedding_model: string | null
  avg_faithfulness: number | null
  avg_answer_relevancy: number | null
  avg_context_precision: number | null
  avg_context_recall: number | null
  error_message: string | null
  started_at: string | null
  finished_at: string | null
  created_at: string | null
}

export interface EvaluationRunDetail extends EvaluationRun {
  results: EvaluationResult[]
}

export interface EvaluationRunListResponse {
  runs: EvaluationRun[]
}

export interface ApiErrorPayload {
  detail?: string | { msg: string }[]
}
