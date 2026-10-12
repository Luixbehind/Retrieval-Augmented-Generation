import { Link } from "react-router-dom"
import { Building2 } from "lucide-react"
import { useTenant } from "@/context/tenant-context"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

export function RequireClient({ children }: { children: React.ReactNode }) {
  const { client } = useTenant()

  if (!client) {
    return (
      <Card className="mx-auto mt-12 max-w-md text-center">
        <CardHeader className="items-center">
          <div className="mx-auto mb-2 flex size-12 items-center justify-center rounded-full bg-purple-500/15 text-purple-400">
            <Building2 className="size-6" />
          </div>
          <CardTitle>Selecione um cliente</CardTitle>
          <CardDescription>
            Esta área exige um tenant ativo (header X-Client-Slug). Escolha ou crie um cliente para
            continuar.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild>
            <Link to="/clients">Ir para Clientes</Link>
          </Button>
        </CardContent>
      </Card>
    )
  }

  return <>{children}</>
}
