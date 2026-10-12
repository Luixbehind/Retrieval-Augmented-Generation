import { apiClient } from "./client"
import type {
  EvaluationRun,
  EvaluationRunDetail,
  EvaluationRunListResponse,
  GoldenDatasetGenerateRequest,
  GoldenQuestion,
  GoldenQuestionCreate,
  GoldenQuestionListResponse,
} from "@/types/api"

export async function listGoldenQuestions(knowledgeBaseId: string): Promise<GoldenQuestion[]> {
  const { data } = await apiClient.get<GoldenQuestionListResponse>(
    `/knowledge-bases/${knowledgeBaseId}/golden-questions`,
  )
  return data.questions
}

export async function createGoldenQuestion(
  knowledgeBaseId: string,
  payload: GoldenQuestionCreate,
): Promise<GoldenQuestion> {
  const { data } = await apiClient.post<GoldenQuestion>(
    `/knowledge-bases/${knowledgeBaseId}/golden-questions`,
    payload,
  )
  return data
}

export async function deleteGoldenQuestion(knowledgeBaseId: string, goldenQuestionId: string): Promise<void> {
  await apiClient.delete(`/knowledge-bases/${knowledgeBaseId}/golden-questions/${goldenQuestionId}`)
}

export async function generateGoldenDataset(
  knowledgeBaseId: string,
  payload: GoldenDatasetGenerateRequest = {},
): Promise<GoldenQuestion[]> {
  const { data } = await apiClient.post<GoldenQuestionListResponse>(
    `/knowledge-bases/${knowledgeBaseId}/golden-questions/generate`,
    payload,
  )
  return data.questions
}

export async function startEvaluationRun(knowledgeBaseId: string): Promise<EvaluationRun> {
  const { data } = await apiClient.post<EvaluationRun>(`/knowledge-bases/${knowledgeBaseId}/evaluations/runs`)
  return data
}

export async function listEvaluationRuns(knowledgeBaseId: string): Promise<EvaluationRun[]> {
  const { data } = await apiClient.get<EvaluationRunListResponse>(
    `/knowledge-bases/${knowledgeBaseId}/evaluations/runs`,
  )
  return data.runs
}

export async function getEvaluationRun(
  knowledgeBaseId: string,
  runId: string,
): Promise<EvaluationRunDetail> {
  const { data } = await apiClient.get<EvaluationRunDetail>(
    `/knowledge-bases/${knowledgeBaseId}/evaluations/runs/${runId}`,
  )
  return data
}
