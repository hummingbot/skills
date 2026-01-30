import { SkillsData, Skill } from "./types";
import { promises as fs } from "fs";
import path from "path";

interface SkillFrontmatter {
  name: string;
  description: string;
  metadata?: {
    author?: string;
  };
}

function parseFrontmatter(content: string): SkillFrontmatter | null {
  const match = content.match(/^---\n([\s\S]*?)\n---/);
  if (!match) return null;

  const yaml = match[1];
  const result: SkillFrontmatter = { name: "", description: "" };

  // Parse name
  const nameMatch = yaml.match(/^name:\s*(.+)$/m);
  if (nameMatch) result.name = nameMatch[1].trim();

  // Parse description
  const descMatch = yaml.match(/^description:\s*(.+)$/m);
  if (descMatch) result.description = descMatch[1].trim();

  // Parse metadata.author
  const authorMatch = yaml.match(/^\s+author:\s*(.+)$/m);
  if (authorMatch) {
    result.metadata = { author: authorMatch[1].trim() };
  }

  return result;
}

const categoryMap: Record<string, { id: string; name: string }> = {
  "hummingbot-api-setup": { id: "infrastructure", name: "Infrastructure" },
  "keys-manager": { id: "configuration", name: "Configuration" },
  "executor-creator": { id: "trading", name: "Trading" },
  "candles-feed": { id: "data", name: "Data" },
  "portfolio": { id: "data", name: "Data" },
};

export async function getSkillsData(): Promise<SkillsData> {
  try {
    const skillsDir = path.join(process.cwd(), "..", "skills");
    const entries = await fs.readdir(skillsDir, { withFileTypes: true });

    const skills: Skill[] = [];

    for (const entry of entries) {
      if (!entry.isDirectory()) continue;

      const skillPath = path.join(skillsDir, entry.name, "SKILL.md");
      try {
        const content = await fs.readFile(skillPath, "utf-8");
        const frontmatter = parseFrontmatter(content);

        if (frontmatter && frontmatter.name) {
          const category = categoryMap[entry.name] || { id: "other", name: "Other" };
          skills.push({
            id: entry.name,
            name: frontmatter.name,
            description: frontmatter.description,
            category: category.id,
            triggers: [],
            path: `skills/${entry.name}`,
            installs: { total: 0, weekly: 0, by_agent: {} },
            first_seen: "2026-01-26T00:00:00Z",
            status: "active",
            creatorGithubHandle: frontmatter.metadata?.author,
          });
        }
      } catch {
        // Skip skills without SKILL.md
      }
    }

    // Sort by name
    skills.sort((a, b) => a.name.localeCompare(b.name));

    return {
      repo: {
        owner: "hummingbot",
        name: "skills",
        url: "https://github.com/hummingbot/skills"
      },
      skills,
      categories: [
        { id: "infrastructure", name: "Infrastructure", icon: "server" },
        { id: "configuration", name: "Configuration", icon: "settings" },
        { id: "trading", name: "Trading", icon: "chart-line" },
        { id: "data", name: "Data", icon: "database" }
      ]
    };
  } catch {
    return {
      repo: {
        owner: "hummingbot",
        name: "skills",
        url: "https://github.com/hummingbot/skills"
      },
      skills: [],
      categories: []
    };
  }
}

export function formatNumber(num: number): string {
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + "K";
  }
  return num.toString();
}

export async function getSkillReadme(skillPath: string): Promise<string> {
  try {
    // Read from local file
    const filePath = path.join(process.cwd(), "..", skillPath, "SKILL.md");
    const content = await fs.readFile(filePath, "utf-8");
    // Remove frontmatter (YAML between ---)
    const frontmatterRegex = /^---[\s\S]*?---\n*/;
    return content.replace(frontmatterRegex, "");
  } catch {
    return "";
  }
}
