import { apiClient } from "./client"
import type { Client, ClientCreate } from "@/types/api"

export async function listClients(): Promise<Client[]> {
  const { data } = await apiClient.get<{ clients: Client[] }>("/clients")
  return data.clients
}

export async function createClient(payload: ClientCreate): Promise<Client> {
  const { data } = await apiClient.post<Client>("/clients", payload)
  return data
}

export async function deleteClient(clientId: string): Promise<void> {
  await apiClient.delete(`/clients/${clientId}`)
}
