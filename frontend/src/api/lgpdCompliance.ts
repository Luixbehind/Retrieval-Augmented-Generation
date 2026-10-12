import axios from "axios"
import { apiClient, STORAGE_KEYS } from "./client"
import type { LgpdComplianceStatusResponse } from "@/types/api"

export interface AnalyzeLgpdCompliancePayload {
  knowledgeBaseId: string
  schemaFile: File
  termsFile: File
}

export async function analyzeLgpdCompliance(
  payload: AnalyzeLgpdCompliancePayload,
): Promise<LgpdComplianceStatusResponse> {
  const form = new FormData()
  form.append("knowledge_base_id", payload.knowledgeBaseId)
  form.append("schema_file", payload.schemaFile)
  form.append("terms_file", payload.termsFile)

  const { data } = await apiClient.post<LgpdComplianceStatusResponse>("/lgpd-compliance/analyze", form, {
    headers: { "Content-Type": "multipart/form-data" },
  })
  return data
}

export async function getComplianceReportStatus(reportId: string): Promise<LgpdComplianceStatusResponse> {
  const { data } = await apiClient.get<LgpdComplianceStatusResponse>(`/lgpd-compliance/report/${reportId}/status`)
  return data
}

export async function getLatestComplianceReport(
  knowledgeBaseId: string,
): Promise<LgpdComplianceStatusResponse | null> {
  try {
    const { data } = await apiClient.get<LgpdComplianceStatusResponse>(
      `/lgpd-compliance/knowledge-bases/${knowledgeBaseId}/latest-report`,
    )
    return data
  } catch (err) {
    if (axios.isAxiosError(err) && err.response?.status === 404) return null
    throw err
  }
}

export async function downloadComplianceReport(
  reportId: string,
  format: "pdf" | "html",
): Promise<Blob> {
  const apiKey = localStorage.getItem(STORAGE_KEYS.reportApiKey)
  const { data } = await apiClient.get(`/lgpd-compliance/report/${reportId}/download`, {
    params: { format },
    responseType: "blob",
    headers: apiKey ? { "X-API-Key": apiKey } : undefined,
  })
  return data
}
