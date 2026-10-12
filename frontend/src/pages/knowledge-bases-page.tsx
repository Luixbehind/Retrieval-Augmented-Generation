import * as React from "react"
import { Link } from "react-router-dom"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { ArrowRight, Database, Plus, Rocket, Trash2 } from "lucide-react"
import { createKnowledgeBase, deleteKnowledgeBase, listKnowledgeBases, publishKnowledgeBase } from "@/api/knowledgeBases"
import { getApiErrorMessage } from "@/api/client"
import { RequireClient } from "@/components/require-client"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
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
import { Textarea } from "@/components/ui/textarea"
import { knowledgeBaseStatusLabel } from "@/lib/utils"
import type { KnowledgeBase, KnowledgeBaseStatus } from "@/types/api"

const statusVariant: Record<KnowledgeBaseStatus, "muted" | "warning" | "success" | "default"> = {
  DRAFT: "muted",
  EDITED: "warning",
  PUBLISHED: "success",
  ARCHIVED: "muted",
}

export function KnowledgeBasesPage() {
  return (
    <RequireClient>
      <KnowledgeBasesContent />
    </RequireClient>
  )
}

function KnowledgeBasesContent() {
  const queryClient = useQueryClient()
  const [open, setOpen] = React.useState(false)
  const [name, setName] = React.useState("")
  const [description, setDescription] = React.useState("")
  const [type, setType] = React.useState("")

  const { data: bases, isLoading } = useQuery({
    queryKey: ["knowledge-bases"],
    queryFn: listKnowledgeBases,
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["knowledge-bases"] })

  const createMutation = useMutation({
    mutationFn: createKnowledgeBase,
    onSuccess: () => {
      toast.success("Base de conhecimento criada")
      invalidate()
      setOpen(false)
      setName("")
      setDescription("")
      setType("")
    },
    onError: (err) => toast.error(getApiErrorMessage(err)),
  })

  const publishMutation = useMutation({
    mutationFn: publishKnowledgeBase,
    onSuccess: () => {
      toast.success("Base publicada com sucesso")
      invalidate()
    },
    onError: (err) => toast.error(getApiErrorMessage(err)),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteKnowledgeBase,
    onSuccess: () => {
      toast.success("Base removida")
      invalidate()
    },
    onError: (err) => toast.error(getApiErrorMessage(err)),
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    createMutation.mutate({ name, description: description || undefined, type: type || undefined })
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Bases de conhecimento</h1>
          <p className="text-sm text-muted">
            Crie uma base, envie o schema do banco e o termo de compromisso, e publique o relatório de
            conformidade como fonte de verdade da RAG.
          </p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus /> Nova base
            </Button>
          </DialogTrigger>
          <DialogContent>
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <DialogHeader>
                <DialogTitle>Nova base de conhecimento</DialogTitle>
              </DialogHeader>
              <div className="flex flex-col gap-2">
                <Label htmlFor="kb-name">Nome</Label>
                <Input id="kb-name" value={name} onChange={(e) => setName(e.target.value)} required />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="kb-type">Tipo (opcional)</Label>
                <Input id="kb-type" value={type} onChange={(e) => setType(e.target.value)} placeholder="ex: contratos" />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="kb-desc">Descrição (opcional)</Label>
                <Textarea
                  id="kb-desc"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={3}
                />
              </div>
              <DialogFooter>
                <Button type="submit" disabled={createMutation.isPending}>
                  {createMutation.isPending ? "Criando..." : "Criar base"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading && <p className="text-sm text-muted">Carregando bases...</p>}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {bases?.map((kb) => (
          <KnowledgeBaseCard
            key={kb.id}
            kb={kb}
            onPublish={() => publishMutation.mutate(kb.id)}
            onDelete={() => deleteMutation.mutate(kb.id)}
          />
        ))}
      </div>

      {bases?.length === 0 && !isLoading && (
        <Card>
          <CardContent className="flex flex-col items-center gap-2 py-10 text-center">
            <Database className="size-8 text-muted" />
            <p className="text-sm text-muted">Nenhuma base de conhecimento criada ainda.</p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function KnowledgeBaseCard({
  kb,
  onPublish,
  onDelete,
}: {
  kb: KnowledgeBase
  onPublish: () => void
  onDelete: () => void
}) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <div>
            <CardTitle>{kb.name}</CardTitle>
            <CardDescription>{kb.type ?? "Sem tipo definido"}</CardDescription>
          </div>
          <Badge variant={statusVariant[kb.status]}>{knowledgeBaseStatusLabel[kb.status]}</Badge>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {kb.description && <p className="text-sm text-muted line-clamp-3">{kb.description}</p>}

        <div className="grid grid-cols-3 gap-2 rounded-lg border border-border bg-surface-2 p-2 text-center text-xs">
          <div>
            <p className="text-muted">top_k</p>
            <p className="font-semibold text-foreground">{kb.config.top_k}</p>
          </div>
          <div>
            <p className="text-muted">BM25</p>
            <p className="font-semibold text-foreground">{kb.config.hybrid_weight_bm25}</p>
          </div>
          <div>
            <p className="text-muted">Vetorial</p>
            <p className="font-semibold text-foreground">{kb.config.hybrid_weight_vector}</p>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <Button size="sm" asChild>
            <Link to={`/knowledge-bases/${kb.id}`}>
              Abrir base <ArrowRight />
            </Link>
          </Button>
          <Button size="sm" variant="accent" onClick={onPublish} disabled={kb.status === "PUBLISHED"}>
            <Rocket /> Publicar
          </Button>
          <Button size="sm" variant="ghost" className="text-danger hover:bg-danger/10" onClick={onDelete}>
            <Trash2 />
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
