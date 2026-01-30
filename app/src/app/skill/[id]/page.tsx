import { getSkillsData, getSkillReadme, formatNumber } from "@/lib/skills";
import { Badge } from "@/components/ui/badge";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import Link from "next/link";
import { notFound } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Props {
  params: Promise<{ id: string }>;
}

export async function generateStaticParams() {
  const data = await getSkillsData();
  return data.skills.map((skill) => ({
    id: skill.id,
  }));
}

export default async function SkillPage({ params }: Props) {
  const { id } = await params;
  const data = await getSkillsData();
  const skill = data.skills.find((s) => s.id === id);

  if (!skill) {
    notFound();
  }

  const category = data.categories.find((c) => c.id === skill.category);
  const readme = await getSkillReadme(skill.path);

  return (
    <main className="max-w-6xl mx-auto px-6 py-12">
      {/* Breadcrumb */}
      <Breadcrumb className="mb-8">
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbLink asChild>
              <Link href="/" className="text-white/50 hover:text-white">
                skills
              </Link>
            </BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator className="text-white/30">/</BreadcrumbSeparator>
          <BreadcrumbItem>
            <BreadcrumbPage className="text-white">{skill.name}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      {/* Header */}
      <div className="mb-12">
        <h1 className="text-3xl sm:text-4xl font-medium text-white mb-4">
          {skill.name}
        </h1>
        <div className="flex flex-wrap items-center gap-4 text-sm text-white/50 mb-6">
          <span className="flex items-center gap-1">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            {formatNumber(skill.installs.total)} installs
          </span>
          <a
            href={`${data.repo.url}/tree/main/${skill.path}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 hover:text-white"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
            </svg>
            GitHub
          </a>
        </div>

        {/* Install Command */}
        <div className="bg-white/5 border border-white/10 rounded-lg px-4 py-3 font-mono text-sm mb-6">
          <code>
            <span className="text-white/40">$ </span>
            <span className="text-white">npx skills add hummingbot/skills --skill {skill.name}</span>
          </code>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-12">
        {/* Main Content - SKILL.md */}
        <div className="lg:col-span-2">
          <div className="flex items-center gap-2 text-white/50 mb-4">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <span className="font-mono text-xs">SKILL.md</span>
          </div>

          {readme ? (
            <article className="prose prose-invert prose-sm max-w-none prose-headings:text-white prose-p:text-white/70 prose-li:text-white/70 prose-code:text-white/90 prose-code:bg-white/10 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-pre:bg-white/5 prose-pre:border prose-pre:border-white/10 prose-a:text-blue-400 prose-strong:text-white prose-th:text-white/70 prose-td:text-white/60 prose-table:text-sm">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {readme}
              </ReactMarkdown>
            </article>
          ) : (
            <div className="text-white/50">
              <p>No documentation available.</p>
              <a
                href={`${data.repo.url}/tree/main/${skill.path}/SKILL.md`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 mt-4 text-white hover:underline"
              >
                View on GitHub
              </a>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="lg:col-span-1">
          <div className="bg-white/5 border border-white/10 rounded-lg p-6">
            <h3 className="text-white/50 font-mono text-xs tracking-widest uppercase mb-4">
              Details
            </h3>
            <dl className="space-y-4">
              <div>
                <dt className="text-white/50 text-sm mb-1">Category</dt>
                <dd>
                  <Badge variant="secondary" className="bg-white/10 text-white/70 hover:bg-white/10 font-mono text-xs">
                    {category?.name || skill.category}
                  </Badge>
                </dd>
              </div>
              <div>
                <dt className="text-white/50 text-sm mb-1">Status</dt>
                <dd>
                  <Badge
                    variant={skill.status === "active" ? "default" : "outline"}
                    className={
                      skill.status === "active"
                        ? "bg-green-500/20 text-green-400 hover:bg-green-500/20"
                        : "text-white/40 border-white/20"
                    }
                  >
                    {skill.status}
                  </Badge>
                </dd>
              </div>
              <div>
                <dt className="text-white/50 text-sm mb-1">Weekly Installs</dt>
                <dd className="text-white font-mono">
                  {formatNumber(skill.installs.weekly)}
                </dd>
              </div>
              <div>
                <dt className="text-white/50 text-sm mb-1">Total Installs</dt>
                <dd className="text-white font-mono">
                  {formatNumber(skill.installs.total)}
                </dd>
              </div>
              <div>
                <dt className="text-white/50 text-sm mb-1">Repository</dt>
                <dd>
                  <a
                    href={data.repo.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-white/70 hover:text-white text-sm"
                  >
                    {data.repo.owner}/{data.repo.name}
                  </a>
                </dd>
              </div>
            </dl>
          </div>
        </div>
      </div>
    </main>
  );
}
