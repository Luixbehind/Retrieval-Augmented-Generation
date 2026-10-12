import { apiClient } from "./client"
import type { RagChatRequest, RagChatResponse } from "@/types/api"

export async function askRagChat(
  knowledgeBaseId: string,
  payload: RagChatRequest,
): Promise<RagChatResponse> {
  const { data } = await apiClient.post<RagChatResponse>(
    `/knowledge-bases/${knowledgeBaseId}/rag-chat`,
    payload,
  )
  return data
}
