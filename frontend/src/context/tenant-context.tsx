import * as React from "react"
import { STORAGE_KEYS } from "@/api/client"
import type { Client } from "@/types/api"

interface TenantContextValue {
  client: Client | null
  setClient: (client: Client | null) => void
  reportApiKey: string
  setReportApiKey: (key: string) => void
}

const TenantContext = React.createContext<TenantContextValue | undefined>(undefined)

function readStoredClient(): Client | null {
  const raw = localStorage.getItem("rag_client_object")
  if (!raw) return null
  try {
    return JSON.parse(raw) as Client
  } catch {
    return null
  }
}

export function TenantProvider({ children }: { children: React.ReactNode }) {
  const [client, setClientState] = React.useState<Client | null>(readStoredClient)
  const [reportApiKey, setReportApiKeyState] = React.useState<string>(
    () => localStorage.getItem(STORAGE_KEYS.reportApiKey) ?? "",
  )

  const setClient = React.useCallback((next: Client | null) => {
    setClientState(next)
    if (next) {
      localStorage.setItem(STORAGE_KEYS.clientSlug, next.slug)
      localStorage.setItem("rag_client_object", JSON.stringify(next))
    } else {
      localStorage.removeItem(STORAGE_KEYS.clientSlug)
      localStorage.removeItem("rag_client_object")
    }
  }, [])

  const setReportApiKey = React.useCallback((key: string) => {
    setReportApiKeyState(key)
    if (key) {
      localStorage.setItem(STORAGE_KEYS.reportApiKey, key)
    } else {
      localStorage.removeItem(STORAGE_KEYS.reportApiKey)
    }
  }, [])

  const value = React.useMemo(
    () => ({ client, setClient, reportApiKey, setReportApiKey }),
    [client, setClient, reportApiKey, setReportApiKey],
  )

  return <TenantContext.Provider value={value}>{children}</TenantContext.Provider>
}

export function useTenant() {
  const ctx = React.useContext(TenantContext)
  if (!ctx) throw new Error("useTenant deve ser usado dentro de TenantProvider")
  return ctx
}
