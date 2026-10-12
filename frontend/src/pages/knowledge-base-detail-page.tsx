import * as React from "react"
import { Link, useParams } from "react-router-dom"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Download,
  FlaskConical,
  Loader2,
  MessagesSquare,
  Play,
  Plus,
  Rocket,
  ScaleIcon,
  Send,
  ShieldAlert,
  Sparkles,
  Trash2,
  XCircle,
} from "lucide-react"
import {
  deleteKnowledgeBase,
  listKnowledgeBases,
  publishKnowledgeBase,
  updateKnowledgeBase,
} from "@/api/knowledgeBases"
import { askRagChat } from "@/api/ragChat"
import {
  analyzeLgpdCompliance,
  downloadComplianceReport,
  getLatestComplianceReport,
} from "@/api/lgpdCompliance"
import {
  createGoldenQuestion,
  deleteGoldenQuestion,
  generateGoldenDataset,
  getEvaluationRun,
  listEvaluationRuns,
  listGoldenQuestions,
  startEvaluationRun,
} from "@/api/evaluations"
import { getApiErrorMessage } from "@/api/client"
import { RequireClient } from "@/components/require-client"
import { FileDropzone } from "@/components/file-dropzone"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { cn, formatScore, knowledgeBaseStatusLabel } from "@/lib/utils"
import type {
  EvaluationRunStatus,
  GoldenDatasetStatus,
  KnowledgeBase,
  KnowledgeBaseStatus,
  LgpdComplianceResponse,
  RagChatResponse,
  RetrievedChunk,
} from "@/types/api"

const statusVariant: Record<KnowledgeBaseStatus, "muted" | "warning" | "success" | "default"> = {
  DRAFT: "muted",
  EDITED: "warning",
  PUBLISHED: "success",
  ARCHIVED: "muted",
}

export function KnowledgeBaseDetailPage() {
  return (
    <RequireClient>
      <KnowledgeBaseDetailContent />
    </RequireClient>
  )
}

function KnowledgeBaseDetailContent() {
  const { knowledgeBaseId } = useParams<{ knowledgeBaseId: string }>()
  const queryClient = useQueryClient()

  const { data: bases, isLoading } = useQuery({
    queryKey: ["knowledge-bases"],
    queryFn: listKnowledgeBases,
    // Enquanto a base atual estiver com golden_dataset_status PENDING (regeneração em background
    // disparada pelo publish, ou pela geração manual), poll a cada 3s até virar COMPLETED/FAILED.
    refetchInterval: (query) => {
      const current = query.state.data?.find((b) => b.id === knowledgeBaseId)
      return current?.golden_dataset_status === "PENDING" ? 3000 : false
    },
  })
  const kb = bases?.find((b) => b.id === knowledgeBaseId)

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["knowledge-bases"] })

  const publishMutation = useMutation({
    mutationFn: publishKnowledgeBase,
    onSuccess: () => {
      toast.success(
        "Base publicada com sucesso. O golden dataset está sendo regenerado em segundo plano a " +
          "partir do novo relatório publicado — confira em alguns instantes na aba Avaliação.",
      )
      invalidate()
    },
    onError: (err) => toast.error(getApiErrorMessage(err)),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteKnowledgeBase,
    onSuccess: () => toast.success("Base removida"),
    onError: (err) => toast.error(getApiErrorMessage(err)),
  })

  const complianceQueryKey = ["compliance-report", knowledgeBaseId, "latest"] as const

  // Persistida no backend (não em estado local) — sobrevive a troca de aba, navegação para
  // outra página e reload, porque reflete o LegalDocument PENDING/COMPLETED/FAILED no banco.
  const complianceQuery = useQuery({
    queryKey: complianceQueryKey,
    queryFn: () => getLatestComplianceReport(knowledgeBaseId!),
    enabled: Boolean(knowledgeBaseId),
    refetchInterval: (query) => (query.state.data?.processing_status === "PENDING" ? 4000 : false),
  })
  const compliance = complianceQuery.data ?? null

  const previousStatusRef = React.useRef<string | null>(null)
  React.useEffect(() => {
    const status = compliance?.processing_status ?? null
    const previous = previousStatusRef.current
    if (previous === "PENDING" && status === "COMPLETED") {
      toast.success("Análise de conformidade concluída — relatório pronto para download")
    } else if (previous === "PENDING" && status === "FAILED") {
      toast.error(`Análise de conformidade falhou: ${compliance?.error_message ?? "erro desconhecido"}`)
    }
    previousStatusRef.current = status
  }, [compliance?.processing_status, compliance?.error_message])

  const previousGoldenDatasetStatusRef = React.useRef<string | null>(null)
  React.useEffect(() => {
    const status = kb?.golden_dataset_status ?? null
    const previous = previousGoldenDatasetStatusRef.current
    if (previous === "PENDING" && status === "COMPLETED") {
      queryClient.invalidateQueries({ queryKey: ["golden-questions", knowledgeBaseId] })
      toast.success("Golden dataset pronto — já dá pra rodar a avaliação.")
    } else if (previous === "PENDING" && status === "FAILED") {
      toast.error(`Geração do golden dataset falhou: ${kb?.golden_dataset_error_message ?? "erro desconhecido"}`)
    }
    previousGoldenDatasetStatusRef.current = status
  }, [kb?.golden_dataset_status, kb?.golden_dataset_error_message, knowledgeBaseId, queryClient])

  const analyzeMutation = useMutation({
    mutationFn: analyzeLgpdCompliance,
    onSuccess: (data) => {
      queryClient.setQueryData(complianceQueryKey, data)
      toast.success("Análise iniciada em segundo plano — acompanhe o status acima.")
    },
    onError: (err) => toast.error(getApiErrorMessage(err)),
  })

  const downloadMutation = useMutation({
    mutationFn: (format: "pdf" | "html") => downloadComplianceReport(compliance!.report_id, format),
    onSuccess: (blob, format) => {
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `relatorio-lgpd.${format}`
      a.click()
      URL.revokeObjectURL(url)
    },
    onError: (err) => toast.error(getApiErrorMessage(err)),
  })

  if (isLoading) {
    return <p className="text-sm text-muted">Carregando base...</p>
  }

  if (!kb) {
    return (
      <Card className="mx-auto mt-12 max-w-md text-center">
        <CardContent className="flex flex-col items-center gap-2 py-10">
          <p className="text-sm text-muted">Base de conhecimento não encontrada.</p>
          <Button asChild variant="outline" size="sm">
            <Link to="/knowledge-bases">Voltar</Link>
          </Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Button variant="ghost" size="sm" asChild className="mb-2 -ml-2">
          <Link to="/knowledge-bases">
            <ArrowLeft /> Voltar
          </Link>
        </Button>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-semibold text-foreground">{kb.name}</h1>
              <Badge variant={statusVariant[kb.status]}>{knowledgeBaseStatusLabel[kb.status]}</Badge>
            </div>
            {kb.description && <p className="text-sm text-muted">{kb.description}</p>}
          </div>
          <div className="flex gap-2">
            <Button
              variant="accent"
              onClick={() => publishMutation.mutate(kb.id)}
              disabled={kb.status === "PUBLISHED" || publishMutation.isPending}
            >
              <Rocket /> Publicar
            </Button>
            <Button
              variant="ghost"
              className="text-danger hover:bg-danger/10"
              onClick={() => deleteMutation.mutate(kb.id)}
            >
              <Trash2 /> Excluir
            </Button>
          </div>
        </div>
      </div>

      {compliance?.processing_status === "PENDING" && (
        <Card className="border-electric-500/40 bg-electric-500/5">
          <CardContent className="flex items-center gap-3 py-3.5">
            <Loader2 className="size-5 shrink-0 animate-spin text-electric-400" />
            <div className="text-sm">
              <p className="font-medium text-foreground">Analisando conformidade em segundo plano…</p>
              <p className="text-muted">
                Pode levar alguns minutos. Fique à vontade para navegar por outras telas — o status
                fica salvo e retomamos o acompanhamento quando você voltar aqui.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {compliance?.processing_status === "FAILED" && (
        <Card className="border-danger/40 bg-danger/5">
          <CardContent className="flex items-center gap-3 py-3.5">
            <XCircle className="size-5 shrink-0 text-danger" />
            <div className="text-sm">
              <p className="font-medium text-foreground">A última análise de conformidade falhou</p>
              <p className="text-muted">{compliance.error_message ?? "Erro desconhecido."} Tente novamente.</p>
            </div>
          </CardContent>
        </Card>
      )}

      {compliance?.processing_status === "COMPLETED" && compliance.result && (
        <Card className="border-success/40 bg-success/5">
          <CardContent className="flex flex-wrap items-center justify-between gap-3 py-3.5">
            <div className="flex items-center gap-3 text-sm">
              <CheckCircle2 className="size-5 shrink-0 text-success" />
              <div>
                <p className="font-medium text-foreground">Relatório de conformidade pronto</p>
                <p className="text-muted">Status: {compliance.result.overall_status}</p>
              </div>
            </div>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                disabled={downloadMutation.isPending}
                onClick={() => downloadMutation.mutate("pdf")}
              >
                <Download /> PDF
              </Button>
              <Button
                size="sm"
                variant="outline"
                disabled={downloadMutation.isPending}
                onClick={() => downloadMutation.mutate("html")}
              >
                <Download /> HTML
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <Tabs defaultValue="compliance">
        <TabsList>
          <TabsTrigger value="compliance">Análise de conformidade</TabsTrigger>
          <TabsTrigger value="chat">Consulta RAG</TabsTrigger>
          <TabsTrigger value="config">Configuração de retrieval</TabsTrigger>
          <TabsTrigger value="evaluation">Avaliação</TabsTrigger>
        </TabsList>

        <TabsContent value="compliance">
          <ComplianceTab
            knowledgeBaseId={kb.id}
            onAnalyze={(payload) => analyzeMutation.mutate(payload)}
            analyzing={analyzeMutation.isPending || compliance?.processing_status === "PENDING"}
            lastSchemaFileName={compliance?.schema_file_name ?? null}
            lastTermsFileName={compliance?.terms_file_name ?? null}
            result={compliance?.processing_status === "COMPLETED" ? compliance.result ?? null : null}
          />
        </TabsContent>

        <TabsContent value="chat">
          <ChatTab knowledgeBaseId={kb.id} />
        </TabsContent>

        <TabsContent value="config">
          <ConfigTab kb={kb} onSaved={invalidate} />
        </TabsContent>

        <TabsContent value="evaluation">
          <EvaluationTab
            knowledgeBaseId={kb.id}
            defaultGoldenDatasetSize={kb.config.golden_dataset_size}
            goldenDatasetStatus={kb.golden_dataset_status}
            goldenDatasetErrorMessage={kb.golden_dataset_error_message}
          />
        </TabsContent>
      </Tabs>
    </div>
  )
}

function ComplianceTab({
  knowledgeBaseId,
  onAnalyze,
  analyzing,
  lastSchemaFileName,
  lastTermsFileName,
  result,
}: {
  knowledgeBaseId: string
  onAnalyze: (payload: {
    knowledgeBaseId: string
    schemaFile: File
    termsFile: File
  }) => void
  analyzing: boolean
  lastSchemaFileName: string | null
  lastTermsFileName: string | null
  result: LgpdComplianceResponse | null
}) {
  const [schemaFile, setSchemaFile] = React.useState<File | null>(null)
  const [termsFile, setTermsFile] = React.useState<File | null>(null)

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!schemaFile || !termsFile) {
      toast.error("Envie os dois arquivos: schema do banco e termo de compromisso")
      return
    }
    onAnalyze({
      knowledgeBaseId,
      schemaFile,
      termsFile,
    })
  }

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Enviar schema e termo de compromisso</CardTitle>
          <CardDescription>
            Os dois arquivos abaixo alimentam o pipeline que compara seu banco de dados com a LGPD e gera
            o relatório que passa a ser a fonte de verdade da RAG desta base.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {(lastSchemaFileName || lastTermsFileName) && (
            <div className="mb-4 flex flex-col gap-1 rounded-lg border border-border bg-surface-2 p-3 text-xs text-muted">
              <p className="font-medium text-foreground">Últimos arquivos enviados para análise</p>
              <p>Schema: {lastSchemaFileName ?? "—"}</p>
              <p>Termo de compromisso: {lastTermsFileName ?? "—"}</p>
            </div>
          )}
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <FileDropzone
              label="Schema do banco de dados"
              hint="Formatos aceitos: .sql (DDL) ou .json (dump de tabelas/colunas) · máx 10MB"
              acceptedExtensions={[".sql", ".json"]}
              value={schemaFile}
              onChange={setSchemaFile}
            />

            <FileDropzone
              label="Termo de compromisso / tratamento de dados"
              hint="Formatos aceitos: .pdf ou .docx · máx 10MB"
              acceptedExtensions={[".pdf", ".docx"]}
              value={termsFile}
              onChange={setTermsFile}
            />

            <Button type="submit" disabled={analyzing} className="self-start">
              <ScaleIcon /> {analyzing ? "Analisando..." : "Analisar conformidade"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {result && <ComplianceResult result={result} />}
    </div>
  )
}

function ComplianceResult({
  result,
}: {
  result: LgpdComplianceResponse
}) {
  return (
    <Card className="border-purple-500/30">
      <CardHeader>
        <CardTitle>Resultado da análise</CardTitle>
        <CardDescription>{result.overall_status}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <p className="text-sm text-foreground">{result.summary}</p>

        <div className="grid gap-4 md:grid-cols-2">
          <ListBlock icon={<CheckCircle2 className="size-4 text-success" />} title="Pontos corretos" items={result.points_correct} variant="success" />
          <ListBlock icon={<AlertTriangle className="size-4 text-danger" />} title="Pontos fora da lei" items={result.points_outside_law} variant="danger" />
        </div>

        <div>
          <h4 className="mb-2 text-sm font-semibold text-foreground">Artigos aplicáveis</h4>
          <div className="flex flex-col gap-2">
            {result.applicable_articles.map((a, i) => (
              <div key={i} className="rounded-lg border border-border bg-surface-2 p-3">
                <Badge variant="default" className="mb-1">{a.article}</Badge>
                <p className="text-xs text-muted">{a.description}</p>
              </div>
            ))}
          </div>
        </div>

        <ListBlock icon={<ShieldAlert className="size-4 text-warning" />} title="Riscos identificados" items={result.risks} variant="warning" />
        <ListBlock icon={<CheckCircle2 className="size-4 text-electric-400" />} title="Recomendações" items={result.recommendations} variant="accent" />
      </CardContent>
    </Card>
  )
}

function ListBlock({
  icon,
  title,
  items,
  variant,
}: {
  icon: React.ReactNode
  title: string
  items: string[]
  variant: "success" | "danger" | "warning" | "accent"
}) {
  if (items.length === 0) return null
  return (
    <div>
      <h4 className="mb-2 flex items-center gap-2 text-sm font-semibold text-foreground">
        {icon}
        {title}
      </h4>
      <ul className="flex flex-col gap-1.5">
        {items.map((item, i) => (
          <li key={i} className="flex items-start gap-2 text-xs text-muted">
            <Badge variant={variant} className="mt-0.5 shrink-0">{i + 1}</Badge>
            {item}
          </li>
        ))}
      </ul>
    </div>
  )
}

interface ChatTurn {
  id: string
  query: string
  result?: RagChatResponse
  error?: string
}

function ChatTab({ knowledgeBaseId }: { knowledgeBaseId: string }) {
  const [input, setInput] = React.useState("")
  const [turns, setTurns] = React.useState<ChatTurn[]>([])
  const bottomRef = React.useRef<HTMLDivElement>(null)

  const mutation = useMutation({
    mutationFn: (payload: { id: string; query: string }) =>
      askRagChat(knowledgeBaseId, { query: payload.query }),
  })

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" })
  }, [turns])

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const query = input.trim()
    if (!query || mutation.isPending) return

    const id = crypto.randomUUID()
    setTurns((prev) => [...prev, { id, query }])
    setInput("")

    mutation.mutate(
      { id, query },
      {
        onSuccess: (result) => {
          setTurns((prev) => prev.map((t) => (t.id === id ? { ...t, result } : t)))
        },
        onError: (err) => {
          const message = getApiErrorMessage(err)
          setTurns((prev) => prev.map((t) => (t.id === id ? { ...t, error: message } : t)))
          toast.error(message)
        },
      },
    )
  }

  return (
    <Card className="flex h-[70vh] flex-col overflow-hidden">
      <CardHeader className="shrink-0 border-b border-border">
        <CardTitle className="flex items-center gap-2 text-base">
          <MessagesSquare className="size-4" /> Consulta RAG
        </CardTitle>
        <CardDescription>
          Converse como num chat. Cada pergunta é respondida pela versão em rascunho (EDIT) e, quando
          houver uma versão publicada, as duas respostas aparecem lado a lado para comparação.
        </CardDescription>
      </CardHeader>

      <div className="flex-1 overflow-y-auto p-4">
        {turns.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-sm text-muted">
            <MessagesSquare className="size-8 text-muted/60" />
            <p>Envie uma pergunta para consultar esta base de conhecimento.</p>
          </div>
        )}

        <div className="flex flex-col gap-6">
          {turns.map((turn) => (
            <ChatTurnView key={turn.id} turn={turn} pending={mutation.isPending && !turn.result && !turn.error} />
          ))}
        </div>
        <div ref={bottomRef} />
      </div>

      <form onSubmit={handleSubmit} className="flex shrink-0 gap-2 border-t border-border p-4">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Digite sua pergunta..."
          className="flex-1"
        />
        <Button type="submit" disabled={mutation.isPending || !input.trim()}>
          <Send /> Enviar
        </Button>
      </form>
    </Card>
  )
}

function ChatTurnView({ turn, pending }: { turn: ChatTurn; pending: boolean }) {
  const hasEdited = Boolean(
    turn.result && (turn.result.edited_answer || turn.result.edited.length > 0),
  )
  const hasPublished = Boolean(
    turn.result && (turn.result.published_answer || turn.result.published.length > 0),
  )
  const showBoth = hasEdited && hasPublished

  return (
    <div className="flex flex-col gap-3">
      <div className="ml-auto max-w-[80%] rounded-2xl rounded-tr-sm bg-purple-500/20 px-4 py-2.5 text-sm text-foreground">
        {turn.query}
      </div>

      {pending && (
        <div className="flex items-center gap-2 text-sm text-muted">
          <Loader2 className="size-4 animate-spin" /> Consultando...
        </div>
      )}

      {turn.error && (
        <div className="flex items-center gap-2 rounded-lg border border-danger/40 bg-danger/5 px-3 py-2 text-sm text-danger">
          <XCircle className="size-4 shrink-0" /> {turn.error}
        </div>
      )}

      {turn.result && (
        <div className="flex flex-col gap-1.5">
          <span className="text-[11px] text-muted">Respondido em {turn.result.latency_ms} ms</span>
          <div className={cn("grid gap-3", showBoth ? "lg:grid-cols-2" : "lg:grid-cols-1")}>
            {(showBoth || !hasPublished) && (
              <ResultColumn
                title={showBoth ? "Rascunho" : "Resposta"}
                chunks={turn.result.edited}
                answer={turn.result.edited_answer}
                accent="default"
                similarityThreshold={turn.result.similarity_threshold}
              />
            )}
            {hasPublished && (
              <ResultColumn
                title={showBoth ? "Publicado" : "Resposta"}
                chunks={turn.result.published}
                answer={turn.result.published_answer}
                accent="accent"
                similarityThreshold={turn.result.similarity_threshold}
              />
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function ResultColumn({
  title,
  chunks,
  answer,
  accent,
  similarityThreshold,
}: {
  title: string
  chunks: RetrievedChunk[]
  answer?: string
  accent: "default" | "accent"
  similarityThreshold: number
}) {
  const [showChunks, setShowChunks] = React.useState(false)

  return (
    <div className="flex max-w-[80%] flex-col gap-2 rounded-2xl rounded-tl-sm border border-border bg-surface-2 p-3">
      <div className="flex items-center justify-between gap-2">
        <span
          className={cn(
            "text-xs font-semibold uppercase tracking-wide",
            accent === "accent" ? "text-electric-400" : "text-purple-400",
          )}
        >
          {title}
        </span>
        <span className="text-[11px] text-muted">Limiar configurado: {formatScore(similarityThreshold)}</span>
      </div>
      {answer && <p className="text-sm text-foreground">{answer}</p>}
      {chunks.length === 0 && <p className="text-xs text-muted">Nenhum resultado.</p>}
      {chunks.length > 0 && (
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="self-start"
          onClick={() => setShowChunks((v) => !v)}
        >
          {showChunks ? <ChevronUp /> : <ChevronDown />}
          {showChunks ? "Ocultar" : "Ver"} trechos recuperados ({chunks.length})
        </Button>
      )}
      {showChunks &&
        chunks.map((chunk) => (
          <div key={chunk.id} className="rounded-lg border border-border bg-background/40 p-2.5">
            <div className="mb-1 flex items-center justify-between gap-2">
              <span className="text-xs font-medium text-foreground">{chunk.title ?? chunk.article ?? "Trecho"}</span>
              <Badge variant={accent} title="Score de similaridade deste trecho">
                {formatScore(chunk.score)}
              </Badge>
            </div>
            <p className="line-clamp-3 text-xs text-muted">{chunk.content ?? chunk.summary}</p>
          </div>
        ))}
    </div>
  )
}

function ConfigTab({ kb, onSaved }: { kb: KnowledgeBase; onSaved: () => void }) {
  const [topK, setTopK] = React.useState(kb.config.top_k)
  const [bm25, setBm25] = React.useState(kb.config.hybrid_weight_bm25)
  const [vector, setVector] = React.useState(kb.config.hybrid_weight_vector)
  const [similarityThreshold, setSimilarityThreshold] = React.useState(kb.config.similarity_threshold)
  const [goldenDatasetSize, setGoldenDatasetSize] = React.useState(kb.config.golden_dataset_size)

  const mutation = useMutation({
    mutationFn: () =>
      updateKnowledgeBase(kb.id, {
        config: {
          top_k: topK,
          hybrid_weight_bm25: bm25,
          hybrid_weight_vector: vector,
          similarity_threshold: similarityThreshold,
          golden_dataset_size: goldenDatasetSize,
        },
      }),
    onSuccess: () => {
      toast.success("Configuração atualizada")
      onSaved()
    },
    onError: (err) => toast.error(getApiErrorMessage(err)),
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle>Pesos de retrieval híbrido</CardTitle>
        <CardDescription>Ajusta como os resultados da LGPD são combinados na busca.</CardDescription>
      </CardHeader>
      <CardContent>
        <form
          className="flex max-w-sm flex-col gap-4"
          onSubmit={(e) => {
            e.preventDefault()
            mutation.mutate()
          }}
        >
          <div className="flex flex-col gap-2">
            <Label>top_k</Label>
            <Input type="number" min={1} value={topK} onChange={(e) => setTopK(Number(e.target.value))} />
          </div>
          <div className="flex flex-col gap-2">
            <Label>Peso BM25 (0-1)</Label>
            <Input type="number" step={0.1} min={0} max={1} value={bm25} onChange={(e) => setBm25(Number(e.target.value))} />
          </div>
          <div className="flex flex-col gap-2">
            <Label>Peso vetorial (0-1)</Label>
            <Input type="number" step={0.1} min={0} max={1} value={vector} onChange={(e) => setVector(Number(e.target.value))} />
          </div>
          <div className="flex flex-col gap-2">
            <Label>Limiar mínimo de similaridade (0-1)</Label>
            <Input
              type="number"
              step={0.05}
              min={0}
              max={1}
              value={similarityThreshold}
              onChange={(e) => setSimilarityThreshold(Number(e.target.value))}
            />
            <p className="text-xs text-muted">
              Score mínimo de similaridade de cosseno para um trecho aparecer na Consulta RAG. Modelos como o
              bge-m3 tendem a gerar scores baixos mesmo para trechos relevantes — valores entre 0.1 e 0.3
              costumam funcionar melhor que 0.5+.
            </p>
          </div>
          <div className="flex flex-col gap-2">
            <Label>Tamanho padrão do golden dataset gerado por IA</Label>
            <Input
              type="number"
              step={1}
              min={3}
              max={20}
              value={goldenDatasetSize}
              onChange={(e) => setGoldenDatasetSize(Number(e.target.value))}
            />
            <p className="text-xs text-muted">
              Quantidade de perguntas propostas pelo botão "Gerar perguntas com IA" na aba Avaliação, quando
              nenhuma quantidade é informada na hora de gerar.
            </p>
          </div>
          <Button type="submit" className="self-start" disabled={mutation.isPending}>
            Salvar
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}

const evaluationRunStatusVariant: Record<EvaluationRunStatus, "muted" | "warning" | "success" | "danger"> = {
  PENDING: "muted",
  RUNNING: "warning",
  COMPLETED: "success",
  FAILED: "danger",
}

const evaluationRunStatusLabel: Record<EvaluationRunStatus, string> = {
  PENDING: "Pendente",
  RUNNING: "Rodando",
  COMPLETED: "Concluído",
  FAILED: "Falhou",
}

function EvaluationTab({
  knowledgeBaseId,
  defaultGoldenDatasetSize,
  goldenDatasetStatus,
  goldenDatasetErrorMessage,
}: {
  knowledgeBaseId: string
  defaultGoldenDatasetSize: number
  goldenDatasetStatus: GoldenDatasetStatus
  goldenDatasetErrorMessage: string | null
}) {
  const goldenDatasetPending = goldenDatasetStatus === "PENDING"
  const queryClient = useQueryClient()
  const [question, setQuestion] = React.useState("")
  const [referenceAnswer, setReferenceAnswer] = React.useState("")
  const [selectedRunId, setSelectedRunId] = React.useState<string | null>(null)
  const [generateCount, setGenerateCount] = React.useState(defaultGoldenDatasetSize)

  const goldenQuestionsQueryKey = ["golden-questions", knowledgeBaseId] as const
  const runsQueryKey = ["evaluation-runs", knowledgeBaseId] as const

  const goldenQuestionsQuery = useQuery({
    queryKey: goldenQuestionsQueryKey,
    queryFn: () => listGoldenQuestions(knowledgeBaseId),
  })

  const runsQuery = useQuery({
    queryKey: runsQueryKey,
    queryFn: () => listEvaluationRuns(knowledgeBaseId),
    refetchInterval: (query) => {
      const latest = query.state.data?.[0]
      return latest && (latest.status === "PENDING" || latest.status === "RUNNING") ? 5000 : false
    },
  })

  const createQuestionMutation = useMutation({
    mutationFn: () => createGoldenQuestion(knowledgeBaseId, { question, reference_answer: referenceAnswer }),
    onSuccess: () => {
      setQuestion("")
      setReferenceAnswer("")
      queryClient.invalidateQueries({ queryKey: goldenQuestionsQueryKey })
      toast.success("Pergunta adicionada ao golden dataset")
    },
    onError: (err) => toast.error(getApiErrorMessage(err)),
  })

  const deleteQuestionMutation = useMutation({
    mutationFn: (goldenQuestionId: string) => deleteGoldenQuestion(knowledgeBaseId, goldenQuestionId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: goldenQuestionsQueryKey }),
    onError: (err) => toast.error(getApiErrorMessage(err)),
  })

  const generateQuestionsMutation = useMutation({
    mutationFn: () => generateGoldenDataset(knowledgeBaseId, { num_questions: generateCount }),
    onSuccess: (created) => {
      queryClient.invalidateQueries({ queryKey: goldenQuestionsQueryKey })
      toast.success(`${created.length} pergunta(s) gerada(s) a partir do relatório publicado`)
    },
    onError: (err) => toast.error(getApiErrorMessage(err)),
  })

  const startRunMutation = useMutation({
    mutationFn: () => startEvaluationRun(knowledgeBaseId),
    onSuccess: (run) => {
      queryClient.invalidateQueries({ queryKey: runsQueryKey })
      setSelectedRunId(run.id)
      toast.success("Avaliação iniciada em segundo plano — pode levar alguns minutos.")
    },
    onError: (err) => toast.error(getApiErrorMessage(err)),
  })

  const runs = runsQuery.data ?? []
  const latestRun = runs[0]
  const isRunInProgress = latestRun?.status === "PENDING" || latestRun?.status === "RUNNING"
  const effectiveSelectedRunId = selectedRunId ?? latestRun?.id ?? null

  const runDetailQuery = useQuery({
    queryKey: ["evaluation-run", knowledgeBaseId, effectiveSelectedRunId] as const,
    queryFn: () => getEvaluationRun(knowledgeBaseId, effectiveSelectedRunId!),
    enabled: Boolean(effectiveSelectedRunId),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === "PENDING" || status === "RUNNING" ? 5000 : false
    },
  })

  function handleCreateQuestion(e: React.FormEvent) {
    e.preventDefault()
    if (!question.trim() || !referenceAnswer.trim()) {
      toast.error("Preencha a pergunta e a resposta de referência")
      return
    }
    createQuestionMutation.mutate()
  }

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FlaskConical className="size-4" /> Golden dataset
          </CardTitle>
          <CardDescription>
            Perguntas de referência (com resposta esperada) usadas para calcular as métricas RAGAS
            (faithfulness, answer_relevancy, context_precision, context_recall) contra o conteúdo
            publicado (PUBLISHED) desta base.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-5">
          {goldenDatasetPending && (
            <div className="flex items-center gap-3 rounded-lg border border-electric-500/40 bg-electric-500/5 px-3 py-2.5">
              <Loader2 className="size-4 shrink-0 animate-spin text-electric-400" />
              <p className="text-sm text-foreground">
                Golden dataset sendo (re)gerado em segundo plano — o botão "Rodar avaliação" libera
                assim que terminar.
              </p>
            </div>
          )}

          {goldenDatasetStatus === "FAILED" && (
            <div className="flex items-center gap-3 rounded-lg border border-danger/40 bg-danger/5 px-3 py-2.5">
              <XCircle className="size-4 shrink-0 text-danger" />
              <p className="text-sm text-danger">
                A última geração do golden dataset falhou: {goldenDatasetErrorMessage ?? "erro desconhecido"}
              </p>
            </div>
          )}

          <div className="flex flex-col gap-3 rounded-lg border border-purple-500/30 bg-purple-500/5 p-3">
            <div>
              <p className="text-sm font-medium text-foreground">Gerar perguntas com IA</p>
              <p className="text-xs text-muted">
                Usa o relatório de compliance publicado (PUBLISHED) desta base para propor perguntas e
                respostas de referência prontas para avaliar — revise, edite ou exclua qualquer item
                gerado antes de rodar a avaliação. Chamar de novo só acrescenta perguntas às existentes.
              </p>
            </div>
            <div className="flex flex-wrap items-end gap-3">
              <div className="flex flex-col gap-2">
                <Label>Quantidade</Label>
                <Input
                  type="number"
                  min={3}
                  max={20}
                  className="w-24"
                  value={generateCount}
                  onChange={(e) => setGenerateCount(Number(e.target.value))}
                />
              </div>
              <Button
                type="button"
                variant="accent"
                disabled={generateQuestionsMutation.isPending || goldenDatasetPending}
                onClick={() => generateQuestionsMutation.mutate()}
              >
                {generateQuestionsMutation.isPending || goldenDatasetPending ? (
                  <Loader2 className="animate-spin" />
                ) : (
                  <Sparkles />
                )}
                {generateQuestionsMutation.isPending || goldenDatasetPending ? "Gerando..." : "Gerar perguntas com IA"}
              </Button>
            </div>
          </div>

          <form onSubmit={handleCreateQuestion} className="flex flex-col gap-3">
            <div className="flex flex-col gap-2">
              <Label>Pergunta</Label>
              <Textarea
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ex: Quais dados pessoais a tabela de usuários armazena?"
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label>Resposta de referência (ground truth)</Label>
              <Textarea
                value={referenceAnswer}
                onChange={(e) => setReferenceAnswer(e.target.value)}
                placeholder="Resposta esperada, usada para comparar com a resposta gerada pela RAG"
              />
            </div>
            <Button type="submit" className="self-start" disabled={createQuestionMutation.isPending}>
              <Plus /> Adicionar pergunta
            </Button>
          </form>

          {goldenQuestionsQuery.isLoading && <p className="text-sm text-muted">Carregando...</p>}

          {!goldenQuestionsQuery.isLoading && (goldenQuestionsQuery.data?.length ?? 0) === 0 && (
            <p className="text-sm text-muted">Nenhuma pergunta cadastrada ainda.</p>
          )}

          {(goldenQuestionsQuery.data?.length ?? 0) > 0 && (
            <div className="flex flex-col gap-2">
              {goldenQuestionsQuery.data!.map((gq) => (
                <div
                  key={gq.id}
                  className="flex items-start justify-between gap-3 rounded-lg border border-border bg-surface-2 p-3"
                >
                  <div className="flex flex-col gap-1 text-sm">
                    <p className="font-medium text-foreground">{gq.question}</p>
                    <p className="text-xs text-muted">{gq.reference_answer}</p>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="shrink-0 text-danger hover:bg-danger/10"
                    onClick={() => deleteQuestionMutation.mutate(gq.id)}
                  >
                    <Trash2 />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3">
          <div>
            <CardTitle>Execuções de avaliação</CardTitle>
            <CardDescription>
              Roda o golden dataset contra o pipeline RAG (retrieval + geração) da versão publicada e
              calcula as métricas via RAGAS, usando o Ollama local como LLM-judge.
            </CardDescription>
          </div>
          <Button
            onClick={() => startRunMutation.mutate()}
            disabled={
              startRunMutation.isPending ||
              isRunInProgress ||
              goldenDatasetPending ||
              (goldenQuestionsQuery.data?.length ?? 0) === 0
            }
          >
            {isRunInProgress ? <Loader2 className="animate-spin" /> : <Play />}
            {isRunInProgress ? "Rodando..." : "Rodar avaliação"}
          </Button>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {runs.length === 0 && <p className="text-sm text-muted">Nenhuma execução ainda.</p>}

          {runs.length > 0 && (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Status</TableHead>
                  <TableHead>Faithfulness</TableHead>
                  <TableHead>Answer relevancy</TableHead>
                  <TableHead>Context precision</TableHead>
                  <TableHead>Context recall</TableHead>
                  <TableHead>Criado em</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {runs.map((run) => (
                  <TableRow
                    key={run.id}
                    className={cn("cursor-pointer", effectiveSelectedRunId === run.id && "bg-surface-2")}
                    onClick={() => setSelectedRunId(run.id)}
                  >
                    <TableCell>
                      <Badge variant={evaluationRunStatusVariant[run.status]}>
                        {evaluationRunStatusLabel[run.status]}
                      </Badge>
                    </TableCell>
                    <TableCell>{formatMetric(run.avg_faithfulness)}</TableCell>
                    <TableCell>{formatMetric(run.avg_answer_relevancy)}</TableCell>
                    <TableCell>{formatMetric(run.avg_context_precision)}</TableCell>
                    <TableCell>{formatMetric(run.avg_context_recall)}</TableCell>
                    <TableCell className="text-xs text-muted">
                      {run.created_at ? new Date(run.created_at).toLocaleString() : "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {effectiveSelectedRunId && runDetailQuery.data && (
        <EvaluationRunDetailCard run={runDetailQuery.data} />
      )}
    </div>
  )
}

function formatMetric(value: number | null): string {
  return value === null || value === undefined ? "—" : value.toFixed(2)
}

function EvaluationRunDetailCard({ run }: { run: Awaited<ReturnType<typeof getEvaluationRun>> }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          Detalhe da execução
          <Badge variant={evaluationRunStatusVariant[run.status]}>{evaluationRunStatusLabel[run.status]}</Badge>
        </CardTitle>
        <CardDescription>
          Judge: {run.judge_model ?? "—"} · Embeddings: {run.embedding_model ?? "—"} · Ambiente:{" "}
          {run.environment}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {run.status === "RUNNING" && (
          <div className="flex items-center gap-2 text-sm text-muted">
            <Loader2 className="size-4 animate-spin" /> Avaliação em andamento...
          </div>
        )}

        {run.status === "FAILED" && (
          <div className="flex items-center gap-2 rounded-lg border border-danger/40 bg-danger/5 px-3 py-2 text-sm text-danger">
            <XCircle className="size-4 shrink-0" /> {run.error_message ?? "Erro desconhecido"}
          </div>
        )}

        {run.results.length > 0 && (
          <div className="flex flex-col gap-3">
            {run.results.map((result) => (
              <div key={result.id} className="rounded-lg border border-border bg-surface-2 p-3">
                <p className="text-sm font-medium text-foreground">{result.question}</p>
                {result.generated_answer && (
                  <p className="mt-1 text-xs text-muted">{result.generated_answer}</p>
                )}
                <div className="mt-2 flex flex-wrap gap-2 text-[11px]">
                  <Badge variant="default">faithfulness: {formatMetric(result.faithfulness)}</Badge>
                  <Badge variant="default">answer_relevancy: {formatMetric(result.answer_relevancy)}</Badge>
                  <Badge variant="default">context_precision: {formatMetric(result.context_precision)}</Badge>
                  <Badge variant="default">context_recall: {formatMetric(result.context_recall)}</Badge>
                  {result.latency_ms !== null && <Badge variant="muted">{result.latency_ms} ms</Badge>}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
