import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"
import type { KnowledgeBaseStatus } from "@/types/api"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export const knowledgeBaseStatusLabel: Record<KnowledgeBaseStatus, string> = {
  DRAFT: "Rascunho",
  EDITED: "Editado",
  PUBLISHED: "Publicado",
  ARCHIVED: "Arquivado",
}

export function formatDate(value: string | null | undefined) {
  if (!value) return "-"
  return new Date(value).toLocaleString("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  })
}

export function formatScore(value: number) {
  return `${(value * 100).toFixed(1)}%`
}
