import { Link } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { Building2, Database, FileSearch, ScaleIcon } from "lucide-react"
import { listClients } from "@/api/clients"
import { listKnowledgeBases } from "@/api/knowledgeBases"
import { useTenant } from "@/context/tenant-context"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

export function DashboardPage() {
  const { client } = useTenant()
  const clientsQuery = useQuery({ queryKey: ["clients"], queryFn: listClients })
  const basesQuery = useQuery({
    queryKey: ["knowledge-bases"],
    queryFn: listKnowledgeBases,
    enabled: Boolean(client),
  })

  const published = basesQuery.data?.filter((kb) => kb.status === "PUBLISHED").length ?? 0

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">
          Visão <span className="text-gradient-brand">geral</span>
        </h1>
        <p className="text-sm text-muted">
          Plataforma de RAG jurídico com verificação de conformidade LGPD.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          icon={<Building2 className="size-5" />}
          label="Clientes"
          value={clientsQuery.data?.length ?? "-"}
          to="/clients"
        />
        <StatCard
          icon={<Database className="size-5" />}
          label="Bases de conhecimento"
          value={client ? (basesQuery.data?.length ?? "-") : "-"}
          to="/knowledge-bases"
        />
        <StatCard
          icon={<ScaleIcon className="size-5" />}
          label="Bases publicadas"
          value={client ? published : "-"}
          to="/knowledge-bases"
        />
        <StatCard
          icon={<FileSearch className="size-5" />}
          label="Consultar RAG"
          value="Ir"
          to="/knowledge-bases"
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Como funciona</CardTitle>
            <CardDescription>Fluxo geral da plataforma</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-2 text-sm text-muted">
            <p>1. Crie um cliente (tenant) — cada um tem banco isolado.</p>
            <p>2. Crie uma base de conhecimento.</p>
            <p>3. Na base, envie o schema SQL e o termo de compromisso para gerar o relatório de conformidade LGPD.</p>
            <p>4. Na aba "Consulta RAG" da base, converse com o rascunho e a versão publicada lado a lado.</p>
            <p>5. Publique quando a versão em rascunho estiver validada.</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Próximos passos</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {!client && (
              <Button asChild>
                <Link to="/clients">Selecionar ou criar um cliente</Link>
              </Button>
            )}
            {client && (
              <Button variant="outline" asChild>
                <Link to="/knowledge-bases">Gerenciar bases de conhecimento</Link>
              </Button>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function StatCard({
  icon,
  label,
  value,
  to,
}: {
  icon: React.ReactNode
  label: string
  value: string | number
  to: string
}) {
  return (
    <Link to={to}>
      <Card className="transition-transform hover:-translate-y-0.5 hover:border-purple-500/50">
        <CardContent className="flex items-center gap-3 py-5">
          <div className="flex size-10 items-center justify-center rounded-lg bg-purple-500/15 text-purple-400">
            {icon}
          </div>
          <div>
            <p className="text-xs text-muted">{label}</p>
            <p className="text-xl font-semibold text-foreground">{value}</p>
          </div>
        </CardContent>
      </Card>
    </Link>
  )
}
