import { apiClient } from "./client"
import type { KnowledgeBase, KnowledgeBaseCreate, KnowledgeBaseUpdate } from "@/types/api"

export async function listKnowledgeBases(): Promise<KnowledgeBase[]> {
  const { data } = await apiClient.get<{ bases: KnowledgeBase[] }>("/knowledge-bases")
  return data.bases
}

export async function createKnowledgeBase(payload: KnowledgeBaseCreate): Promise<KnowledgeBase> {
  const { data } = await apiClient.post<KnowledgeBase>("/knowledge-bases", payload)
  return data
}

export async function updateKnowledgeBase(
  id: string,
  payload: KnowledgeBaseUpdate,
): Promise<KnowledgeBase> {
  const { data } = await apiClient.patch<KnowledgeBase>(`/knowledge-bases/${id}`, payload)
  return data
}

export async function publishKnowledgeBase(id: string): Promise<KnowledgeBase> {
  const { data } = await apiClient.post<KnowledgeBase>(`/knowledge-bases/${id}/publish`)
  return data
}

export async function deleteKnowledgeBase(id: string): Promise<void> {
  await apiClient.delete(`/knowledge-bases/${id}`)
}
