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
            <pre className="text-white font-mono text-[10px] sm:text-xs leading-tight mb-4">
{"    __                              _             __          __ \n   / /_  __  ______ ___  ____ ___  (_)___  ____ _/ /_  ____  / /_\n  / __ \\/ / / / __ `__ \\/ __ `__ \\/ / __ \\/ __ `/ __ \\/ __ \\/ __/\n / / / / /_/ / / / / / / / / / / / / / / / /_/ / /_/ / /_/ / /_  \n/_/ /_/\\__,_/_/ /_/ /_/_/ /_/ /_/_/_/ /_/\\__, /_.___/\\____/\\__/  \n         __   _ ____                    /____/                   \n   _____/ /__(_) / /____                                         \n  / ___/ //_/ / / / ___/                                         \n (__  ) ,< / / / (__  )                                          \n/____/_/|_/_/_/_/____/                                           "}
            </pre>
          </div>
          <p className="text-white/70 text-lg lg:text-xl max-w-md lg:text-right">
            AI agent skills for algorithmic trading. Install them with a single command to enhance your agents.
          </p>
        </div>
      </div>

      {/* Install Command */}
      <div className="mb-12">
        <p className="text-white/50 font-mono text-xs tracking-widest uppercase mb-3">
          Install in one command
        </p>
        <div className="bg-white/5 border border-white/10 rounded-lg px-4 py-3 font-mono text-sm flex items-center justify-between">
          <code>
            <span className="text-white/40">$ </span>
            <span className="text-white">npx skills add hummingbot/skills</span>
          </code>
          <CopyButton text="npx skills add hummingbot/skills" />
        </div>
      </div>

      {/* Stats */}
      <div className="flex gap-8 mb-12">
        <div>
          <p className="text-white/50 font-mono text-xs tracking-widest uppercase mb-1">Skills</p>
          <p className="text-white font-mono text-2xl">{activeSkills.length}</p>
        </div>
      </div>

      {/* Search */}
      <div className="mb-8">
        <p className="text-white/50 font-mono text-xs tracking-widest uppercase mb-3">
          Skills Directory
        </p>
        <Input
          type="search"
          placeholder="Search skills..."
          className="bg-white/5 border-white/10 text-white placeholder:text-white/30 font-mono"
        />
      </div>

      {/* Skills Table */}
      <div className="border border-white/10 rounded-lg overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/10">
              <th className="text-left px-4 py-3 text-white/50 font-mono text-xs tracking-widest uppercase">
                Skill
              </th>
              <th className="text-left px-4 py-3 text-white/50 font-mono text-xs tracking-widest uppercase hidden sm:table-cell">
                Category
              </th>
              <th className="text-left px-4 py-3 text-white/50 font-mono text-xs tracking-widest uppercase hidden md:table-cell">
                Creator
              </th>
            </tr>
          </thead>
          <tbody>
            {activeSkills.map((skill, index) => (
              <tr
                key={skill.id}
                className="border-b border-white/5 hover:bg-white/5 transition-colors"
              >
                <td className="px-4 py-4">
                  <Link href={`/skill/${skill.id}`} className="block">
                    <p className="text-white font-medium mb-1">{skill.name}</p>
                    <p className="text-white/50 text-sm line-clamp-1">
                      {skill.description}
                    </p>
                  </Link>
                </td>
                <td className="px-4 py-4 hidden sm:table-cell">
                  <Badge variant="secondary" className="bg-white/10 text-white/70 hover:bg-white/10 font-mono text-xs">
                    {skill.category}
                  </Badge>
                </td>
                <td className="px-4 py-4 hidden md:table-cell">
                  {skill.creatorGithubHandle && (
                    <a
                      href={`https://github.com/${skill.creatorGithubHandle}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 text-white/70 hover:text-white"
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
          <p className="text-white/50 font-mono text-xs tracking-widest uppercase mb-4">
            Coming Soon
          </p>
          <div className="grid gap-3">
            {data.skills
              .filter((s) => s.status === "planned")
              .map((skill) => (
                <div
                  key={skill.id}
                  className="bg-white/5 border border-white/10 rounded-lg px-4 py-3 flex items-center justify-between"
                >
                  <div>
                    <p className="text-white/70 font-medium">{skill.name}</p>
                    <p className="text-white/40 text-sm">{skill.description}</p>
                  </div>
                  <Badge variant="outline" className="text-white/40 border-white/20">
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
