import axios from "axios"
import type { ApiErrorPayload } from "@/types/api"

export const API_BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1"

export const STORAGE_KEYS = {
  clientSlug: "rag_client_slug",
  reportApiKey: "rag_report_api_key",
} as const

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
})

apiClient.interceptors.request.use((config) => {
  const slug = localStorage.getItem(STORAGE_KEYS.clientSlug)
  if (slug && !config.headers["X-Client-Slug"]) {
    config.headers["X-Client-Slug"] = slug
  }
  return config
})

export function getApiErrorMessage(error: unknown): string {
  if (axios.isAxiosError<ApiErrorPayload>(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === "string") return detail
    if (Array.isArray(detail)) return detail.map((d) => d.msg).join(", ")
    if (error.message) return error.message
  }
  if (error instanceof Error) return error.message
  return "Erro inesperado"
}
