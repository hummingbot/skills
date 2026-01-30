import { getSkillsData, getSkillReadme } from "@/lib/skills";
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

  const readme = await getSkillReadme(skill.path);

  return (
    <main className="max-w-6xl mx-auto px-6 py-12">
      {/* Breadcrumb */}
      <Breadcrumb className="mb-8">
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbLink asChild>
              <Link href="/" className="text-muted-foreground hover:text-foreground transition-colors">
                skills
              </Link>
            </BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator className="text-muted-foreground/50">/</BreadcrumbSeparator>
          <BreadcrumbItem>
            <BreadcrumbPage className="text-foreground">{skill.name}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      {/* Header */}
      <div className="mb-12">
        <h1 className="text-3xl sm:text-4xl font-medium text-foreground mb-6">
          {skill.name}
        </h1>

        {/* Install Command */}
        <div className="bg-muted border border-border rounded-lg px-4 py-3 font-mono text-sm mb-6">
          <code>
            <span className="text-muted-foreground">$ </span>
            <span className="text-foreground">npx skills add hummingbot/skills --skill {skill.name}</span>
          </code>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-12">
        {/* Main Content - SKILL.md */}
        <div className="lg:col-span-2">
          <div className="flex items-center gap-2 text-muted-foreground mb-4">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <span className="font-mono text-xs">SKILL.md</span>
          </div>

          {readme ? (
            <article className="prose prose-sm max-w-none dark:prose-invert prose-headings:text-foreground prose-p:text-muted-foreground prose-li:text-muted-foreground prose-code:text-foreground prose-code:bg-muted prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-pre:bg-muted prose-pre:border prose-pre:border-border prose-a:text-blue-500 dark:prose-a:text-blue-400 prose-strong:text-foreground prose-th:text-muted-foreground prose-td:text-muted-foreground prose-table:text-sm">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {readme}
              </ReactMarkdown>
            </article>
          ) : (
            <div className="text-muted-foreground">
              <p>No documentation available.</p>
              <a
                href={`${data.repo.url}/tree/main/${skill.path}/SKILL.md`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 mt-4 text-foreground hover:underline"
              >
                View on GitHub
              </a>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="lg:col-span-1">
          <div className="bg-muted border border-border rounded-lg p-6">
            <h3 className="text-muted-foreground font-mono text-xs tracking-widest uppercase mb-4">
              Details
            </h3>
            <dl className="space-y-4">
              <div>
                <dt className="text-muted-foreground text-sm mb-1">GitHub</dt>
                <dd>
                  <a
                    href={`${data.repo.url}/tree/main/${skill.path}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-muted-foreground hover:text-foreground text-sm transition-colors"
                  >
                    {skill.path}
                  </a>
                </dd>
              </div>
              {skill.author && (
                <div>
                  <dt className="text-muted-foreground text-sm mb-1">Creator</dt>
                  <dd>
                    <a
                      href={`https://github.com/${skill.author}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
                    >
                      <img
                        src={`https://github.com/${skill.author}.png?size=32`}
                        alt={skill.author}
                        className="w-6 h-6 rounded-full"
                      />
                      <span className="text-sm">{skill.author}</span>
                    </a>
                  </dd>
                </div>
              )}
            </dl>
          </div>
        </div>
      </div>
    </main>
  );
}
