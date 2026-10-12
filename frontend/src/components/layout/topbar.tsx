import { Link } from "react-router-dom"
import { Building2, ChevronRight } from "lucide-react"
import { useTenant } from "@/context/tenant-context"
import { Badge } from "@/components/ui/badge"

export function Topbar() {
  const { client } = useTenant()

  return (
    <header className="flex h-16 items-center justify-between border-b border-border bg-surface/60 px-6 backdrop-blur-sm">
      <div className="flex items-center gap-2 text-sm text-muted">
        <span>Tenant ativo</span>
        <ChevronRight className="size-3.5" />
        {client ? (
          <Badge variant="accent" className="gap-1.5">
            <Building2 className="size-3.5" />
            {client.name} ({client.slug})
          </Badge>
        ) : (
          <Link to="/clients">
            <Badge variant="warning" className="cursor-pointer">
              Nenhum cliente selecionado — clique para escolher
            </Badge>
          </Link>
        )}
      </div>
    </header>
  )
}
