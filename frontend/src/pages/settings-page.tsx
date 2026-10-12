import * as React from "react"
import { toast } from "sonner"
import { KeyRound, Save } from "lucide-react"
import { useTenant } from "@/context/tenant-context"
import { API_BASE_URL } from "@/api/client"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"

export function SettingsPage() {
  const { reportApiKey, setReportApiKey, client } = useTenant()
  const [value, setValue] = React.useState(reportApiKey)

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Configurações</h1>
        <p className="text-sm text-muted">Preferências locais do painel (armazenadas neste navegador).</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Conexão com a API</CardTitle>
          <CardDescription>Endpoint base configurado via VITE_API_URL.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-2 text-sm">
          <p>
            <span className="text-muted">URL base: </span>
            <span className="font-mono text-foreground">{API_BASE_URL}</span>
          </p>
          <p>
            <span className="text-muted">Tenant ativo: </span>
            <span className="font-mono text-foreground">{client ? client.slug : "nenhum"}</span>
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <KeyRound className="size-4" /> API Key de download de relatórios
          </CardTitle>
          <CardDescription>
            Usada apenas no header X-API-Key ao baixar relatórios de compliance LGPD. Necessária
            somente se o servidor tiver `report_download_api_key` configurado.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex flex-col gap-2">
            <Label htmlFor="api-key">API Key</Label>
            <Input
              id="api-key"
              type="password"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder="Deixe em branco se não configurado no servidor"
            />
          </div>
          <Button
            className="self-start"
            onClick={() => {
              setReportApiKey(value)
              toast.success("Configuração salva")
            }}
          >
            <Save /> Salvar
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
