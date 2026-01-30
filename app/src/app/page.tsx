import { getSkillsData, formatNumber } from "@/lib/skills";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import Link from "next/link";

export default async function Home() {
  const data = await getSkillsData();
  const activeSkills = data.skills.filter((s) => s.status === "active");
  const totalInstalls = data.skills.reduce((sum, s) => sum + s.installs.total, 0);

  return (
    <main className="max-w-6xl mx-auto px-6 py-12">
      {/* Hero */}
      <div className="mb-16">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-8">
          <div>
            <pre className="text-white font-mono text-2xl sm:text-3xl leading-tight mb-4">
{`██╗  ██╗██████╗
██║  ██║██╔══██╗
███████║██████╔╝
██╔══██║██╔══██╗
██║  ██║██████╔╝
╚═╝  ╚═╝╚═════╝`}
            </pre>
            <p className="text-white/50 font-mono text-sm tracking-widest uppercase">
              Hummingbot Skills
            </p>
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
          <button className="text-white/40 hover:text-white p-1">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2" strokeWidth="2"/>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" strokeWidth="2"/>
            </svg>
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="flex gap-8 mb-12">
        <div>
          <p className="text-white/50 font-mono text-xs tracking-widest uppercase mb-1">Skills</p>
          <p className="text-white font-mono text-2xl">{activeSkills.length}</p>
        </div>
        <div>
          <p className="text-white/50 font-mono text-xs tracking-widest uppercase mb-1">Total Installs</p>
          <p className="text-white font-mono text-2xl">{formatNumber(totalInstalls)}</p>
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
              <th className="text-right px-4 py-3 text-white/50 font-mono text-xs tracking-widest uppercase">
                Installs
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
                <td className="px-4 py-4 text-right">
                  <span className="text-white/70 font-mono text-sm">
                    {formatNumber(skill.installs.total)}
                  </span>
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
