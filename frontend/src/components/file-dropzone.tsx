import * as React from "react"
import { File as FileIcon, Upload, X } from "lucide-react"
import { toast } from "sonner"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"

const MAX_SIZE_MB = 10

interface FileDropzoneProps {
  label: string
  hint: string
  acceptedExtensions: string[]
  value: File | null
  onChange: (file: File | null) => void
}

export function FileDropzone({ label, hint, acceptedExtensions, value, onChange }: FileDropzoneProps) {
  const [dragOver, setDragOver] = React.useState(false)
  const inputRef = React.useRef<HTMLInputElement>(null)

  function validateAndSet(files: FileList | File[]) {
    const file = Array.from(files)[0]
    if (!file) return
    const ext = `.${file.name.split(".").pop()?.toLowerCase()}`
    if (!acceptedExtensions.includes(ext)) {
      toast.error(`Formato não suportado: ${file.name}. Use ${acceptedExtensions.join(" ou ")}`)
      return
    }
    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      toast.error(`Arquivo muito grande (máx ${MAX_SIZE_MB}MB): ${file.name}`)
      return
    }
    onChange(file)
  }

  return (
    <div className="flex flex-col gap-2">
      <label className="text-sm font-medium text-foreground">{label}</label>

      {value ? (
        <div className="flex items-center justify-between gap-3 rounded-lg border border-border-strong bg-surface-2 px-3 py-2.5">
          <div className="flex min-w-0 items-center gap-2">
            <FileIcon className="size-4 shrink-0 text-purple-400" />
            <span className="truncate text-sm text-foreground">{value.name}</span>
            <span className="shrink-0 text-xs text-muted">{(value.size / 1024).toFixed(0)} KB</span>
          </div>
          <Button
            type="button"
            size="icon"
            variant="ghost"
            className="size-7 shrink-0 text-danger hover:bg-danger/10"
            onClick={() => onChange(null)}
          >
            <X className="size-4" />
          </Button>
        </div>
      ) : (
        <div
          onDragOver={(e) => {
            e.preventDefault()
            setDragOver(true)
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault()
            setDragOver(false)
            validateAndSet(e.dataTransfer.files)
          }}
          onClick={() => inputRef.current?.click()}
          className={cn(
            "flex cursor-pointer flex-col items-center gap-2 rounded-lg border border-dashed border-border-strong bg-surface-2 px-4 py-6 text-center transition-colors hover:border-purple-500/60",
            dragOver && "border-purple-500 shadow-glow-purple",
          )}
        >
          <Upload className="size-5 text-purple-400" />
          <p className="text-sm text-foreground">Arraste o arquivo aqui ou clique para selecionar</p>
          <input
            ref={inputRef}
            type="file"
            className="hidden"
            accept={acceptedExtensions.join(",")}
            onChange={(e) => e.target.files && validateAndSet(e.target.files)}
          />
        </div>
      )}
      <p className="text-xs text-muted">{hint}</p>
    </div>
  )
}
