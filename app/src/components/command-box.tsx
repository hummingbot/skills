import { CopyButton } from "@/components/copy-button";

interface CommandBoxProps {
  command: string;
}

export function CommandBox({ command }: CommandBoxProps) {
  return (
    <div className="bg-muted border border-border rounded-lg px-4 py-3 font-mono text-sm flex items-center justify-between">
      <code>
        <span className="text-muted-foreground">$ </span>
        <span className="text-foreground">{command}</span>
      </code>
      <CopyButton text={command} />
    </div>
  );
}
