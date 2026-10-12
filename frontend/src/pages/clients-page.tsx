import * as React from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Building2, Check, Plus, Trash2 } from "lucide-react"
import { createClient, deleteClient, listClients } from "@/api/clients"
import { getApiErrorMessage } from "@/api/client"
import { useTenant } from "@/context/tenant-context"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { formatDate } from "@/lib/utils"
import type { Client } from "@/types/api"

function slugify(value: string) {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
}

export function ClientsPage() {
  const queryClient = useQueryClient()
  const { client: activeClient, setClient } = useTenant()
  const [open, setOpen] = React.useState(false)
  const [name, setName] = React.useState("")
  const [slug, setSlug] = React.useState("")
  const [slugTouched, setSlugTouched] = React.useState(false)

  const { data: clients, isLoading } = useQuery({
    queryKey: ["clients"],
    queryFn: listClients,
  })

  const createMutation = useMutation({
    mutationFn: createClient,
    onSuccess: (created) => {
      toast.success(`Cliente "${created.name}" criado`)
      queryClient.invalidateQueries({ queryKey: ["clients"] })
      setClient(created)
      setOpen(false)
      setName("")
      setSlug("")
      setSlugTouched(false)
    },
    onError: (err) => toast.error(getApiErrorMessage(err)),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteClient,
    onSuccess: (_, id) => {
      toast.success("Cliente removido")
      queryClient.invalidateQueries({ queryKey: ["clients"] })
      if (activeClient?.id === id) setClient(null)
    },
    onError: (err) => toast.error(getApiErrorMessage(err)),
  })

  function handleNameChange(value: string) {
    setName(value)
    if (!slugTouched) setSlug(slugify(value))
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    createMutation.mutate({ name, slug })
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Clientes</h1>
          <p className="text-sm text-muted">
            Cada cliente é um tenant isolado com seu próprio banco de dados.
          </p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus /> Novo cliente
            </Button>
          </DialogTrigger>
          <DialogContent>
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <DialogHeader>
                <DialogTitle>Novo cliente</DialogTitle>
              </DialogHeader>
              <div className="flex flex-col gap-2">
                <Label htmlFor="name">Nome</Label>
                <Input
                  id="name"
                  value={name}
                  onChange={(e) => handleNameChange(e.target.value)}
                  placeholder="Empresa Exemplo Ltda"
                  required
                />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="slug">Slug</Label>
                <Input
                  id="slug"
                  value={slug}
                  onChange={(e) => {
                    setSlug(slugify(e.target.value))
                    setSlugTouched(true)
                  }}
                  placeholder="empresa-exemplo"
                  pattern="^[a-z0-9]+(?:-[a-z0-9]+)*$"
                  required
                />
                <p className="text-xs text-muted">
                  Usado no header X-Client-Slug. Apenas letras minúsculas, números e hífens.
                </p>
              </div>
              <DialogFooter>
                <Button type="submit" disabled={createMutation.isPending}>
                  {createMutation.isPending ? "Criando..." : "Criar cliente"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading && <p className="text-sm text-muted">Carregando clientes...</p>}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {clients?.map((c) => (
          <ClientCard
            key={c.id}
            client={c}
            active={activeClient?.id === c.id}
            onSelect={() => {
              setClient(c)
              toast.success(`Tenant ativo: ${c.name}`)
            }}
            onDelete={() => deleteMutation.mutate(c.id)}
          />
        ))}
      </div>

      {clients?.length === 0 && !isLoading && (
        <Card>
          <CardContent className="flex flex-col items-center gap-2 py-10 text-center">
            <Building2 className="size-8 text-muted" />
            <p className="text-sm text-muted">Nenhum cliente cadastrado ainda.</p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function ClientCard({
  client,
  active,
  onSelect,
  onDelete,
}: {
  client: Client
  active: boolean
  onSelect: () => void
  onDelete: () => void
}) {
  return (
    <Card className={active ? "ring-1 ring-purple-500/60 shadow-glow-purple" : ""}>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle>{client.name}</CardTitle>
            <CardDescription>{client.slug}</CardDescription>
          </div>
          {active && (
            <Badge variant="accent">
              <Check className="size-3" /> Ativo
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <p className="text-xs text-muted">Criado em {formatDate(client.created_at)}</p>
        <div className="flex gap-2">
          <Button size="sm" variant={active ? "outline" : "default"} onClick={onSelect}>
            {active ? "Selecionado" : "Selecionar"}
          </Button>
          <Button size="sm" variant="ghost" className="text-danger hover:bg-danger/10" onClick={onDelete}>
            <Trash2 />
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
