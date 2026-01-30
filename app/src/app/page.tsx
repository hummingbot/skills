import { getSkillsData } from "@/lib/skills";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { CopyButton } from "@/components/copy-button";
import Link from "next/link";

export default async function Home() {
  const data = await getSkillsData();
  const activeSkills = data.skills.filter((s) => s.status === "active");

  return (
    <main className="max-w-6xl mx-auto px-6 py-12">
      {/* Hero */}
      <div className="mb-16">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-8">
          <div>
            <pre className="text-foreground font-mono text-[10px] sm:text-xs leading-tight mb-4">
{"    __                              _             __          __ \n   / /_  __  ______ ___  ____ ___  (_)___  ____ _/ /_  ____  / /_\n  / __ \\/ / / / __ `__ \\/ __ `__ \\/ / __ \\/ __ `/ __ \\/ __ \\/ __/\n / / / / /_/ / / / / / / / / / / / / / / / /_/ / /_/ / /_/ / /_  \n/_/ /_/\\__,_/_/ /_/ /_/_/ /_/ /_/_/_/ /_/\\__, /_.___/\\____/\\__/  \n         __   _ ____                    /____/                   \n   _____/ /__(_) / /____                                         \n  / ___/ //_/ / / / ___/                                         \n (__  ) ,< / / / (__  )                                          \n/____/_/|_/_/_/_/____/                                           "}
            </pre>
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
        <div className="bg-muted border border-border rounded-lg px-4 py-3 font-mono text-sm flex items-center justify-between">
          <code>
            <span className="text-muted-foreground">$ </span>
            <span className="text-foreground">npx skills add hummingbot/skills</span>
          </code>
          <CopyButton text="npx skills add hummingbot/skills" />
        </div>
      </div>

      {/* Stats */}
      <div className="flex gap-8 mb-12">
        <div>
          <p className="text-muted-foreground font-mono text-xs tracking-widest uppercase mb-1">Skills</p>
          <p className="text-foreground font-mono text-2xl">{activeSkills.length}</p>
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
              <th className="text-left px-4 py-3 text-muted-foreground font-mono text-xs tracking-widest uppercase hidden sm:table-cell">
                Category
              </th>
              <th className="text-left px-4 py-3 text-muted-foreground font-mono text-xs tracking-widest uppercase hidden md:table-cell">
                Creator
              </th>
            </tr>
          </thead>
          <tbody>
            {activeSkills.map((skill) => (
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
                <td className="px-4 py-4 hidden sm:table-cell">
                  <Badge variant="secondary" className="font-mono text-xs">
                    {skill.category}
                  </Badge>
                </td>
                <td className="px-4 py-4 hidden md:table-cell">
                  {skill.creatorGithubHandle && (
                    <a
                      href={`https://github.com/${skill.creatorGithubHandle}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
                    >
                      <img
                        src={`https://github.com/${skill.creatorGithubHandle}.png?size=24`}
                        alt={skill.creatorGithubHandle}
                        className="w-5 h-5 rounded-full"
                      />
                      <span className="text-sm">{skill.creatorGithubHandle}</span>
                    </a>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Planned Skills */}
      {data.skills.filter((s) => s.status === "planned").length > 0 && (
        <div className="mt-12">
          <p className="text-muted-foreground font-mono text-xs tracking-widest uppercase mb-4">
            Coming Soon
          </p>
          <div className="grid gap-3">
            {data.skills
              .filter((s) => s.status === "planned")
              .map((skill) => (
                <div
                  key={skill.id}
                  className="bg-muted border border-border rounded-lg px-4 py-3 flex items-center justify-between"
                >
                  <div>
                    <p className="text-muted-foreground font-medium">{skill.name}</p>
                    <p className="text-muted-foreground/60 text-sm">{skill.description}</p>
                  </div>
                  <Badge variant="outline" className="text-muted-foreground border-border">
                    planned
                  </Badge>
                </div>
              ))}
          </div>
        </div>
      )}
    </main>
  );
}
