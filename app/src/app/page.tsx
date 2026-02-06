import { getSkillsData } from "@/lib/skills";
import { Input } from "@/components/ui/input";
import { CommandBox } from "@/components/command-box";
import { AsciiBanner } from "@/components/ascii-banner";
import Link from "next/link";

export default async function Home() {
  const data = await getSkillsData();

  return (
    <main className="max-w-6xl mx-auto px-6 py-12">
      {/* Hero */}
      <div className="mb-16">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-8">
          <div>
            <AsciiBanner />
          </div>
          <p className="text-muted-foreground text-lg lg:text-xl max-w-md lg:text-right">
            Skills for algorithmic trading powered by <a href="https://hummingbot.org/hummingbot-api/" target="_blank" rel="noopener noreferrer" className="text-foreground hover:underline">Hummingbot API</a>. Install them with a single command to enhance your AI agents.
          </p>
        </div>
      </div>

      {/* Install Command */}
      <div className="mb-12">
        <p className="text-muted-foreground font-mono text-xs tracking-widest uppercase mb-3">
          Install in one command
        </p>
        <CommandBox command="npx skills add hummingbot/skills" />
      </div>

      {/* Stats */}
      <div className="flex gap-8 mb-12">
        <div>
          <p className="text-muted-foreground font-mono text-xs tracking-widest uppercase mb-1">Skills</p>
          <p className="text-foreground font-mono text-2xl">{data.skills.length}</p>
        </div>
      </div>

      {/* Search */}
      <div className="mb-8">
        <p className="text-muted-foreground font-mono text-xs tracking-widest uppercase mb-3">
          Skills Directory
        </p>
        <Input
          type="search"
          placeholder="Search skills..."
          className="bg-muted border-border text-foreground placeholder:text-muted-foreground font-mono"
        />
      </div>

      {/* Skills Table */}
      <div className="border border-border rounded-lg overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left px-4 py-3 text-muted-foreground font-mono text-xs tracking-widest uppercase">
                Skill
              </th>
              <th className="text-left px-4 py-3 text-muted-foreground font-mono text-xs tracking-widest uppercase hidden md:table-cell">
                Creator
              </th>
            </tr>
          </thead>
          <tbody>
            {data.skills.map((skill) => (
              <tr
                key={skill.id}
                className="border-b border-border/50 hover:bg-muted transition-colors"
              >
                <td className="px-4 py-4">
                  <Link href={`/skill/${skill.id}`} className="block">
                    <p className="text-foreground font-medium mb-1">{skill.name}</p>
                    <p className="text-muted-foreground text-sm line-clamp-1">
                      {skill.description}
                    </p>
                  </Link>
                </td>
                <td className="px-4 py-4 hidden md:table-cell">
                  {skill.author && (
                    <a
                      href={`https://github.com/${skill.author}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
                    >
                      <img
                        src={`https://github.com/${skill.author}.png?size=24`}
                        alt={skill.author}
                        className="w-5 h-5 rounded-full"
                      />
                      <span className="text-sm">{skill.author}</span>
                    </a>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

    </main>
  );
}
