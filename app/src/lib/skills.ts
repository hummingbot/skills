import { SkillsData } from "./types";
import { promises as fs } from "fs";
import path from "path";

const fallbackData: SkillsData = {
  repo: {
    owner: "hummingbot",
    name: "skills",
    url: "https://github.com/hummingbot/skills"
  },
  skills: [
    {
      id: "hummingbot-api-setup",
      name: "hummingbot-api-setup",
      description: "Deploy Hummingbot API infrastructure",
      category: "infrastructure",
      triggers: ["install hummingbot", "setup trading", "deploy api", "docker setup"],
      path: "skills/hummingbot-api-setup",
      installs: { total: 0, weekly: 0, by_agent: {} },
      first_seen: "2026-01-26T00:00:00Z",
      status: "active",
      creatorGithubHandle: "david-hummingbot"
    },
    {
      id: "keys-manager",
      name: "keys-manager",
      description: "Manage spot and perpetual exchange API keys",
      category: "configuration",
      triggers: ["add api key", "configure exchange", "setup binance", "add credentials"],
      path: "skills/keys-manager",
      installs: { total: 0, weekly: 0, by_agent: {} },
      first_seen: "2026-01-26T00:00:00Z",
      status: "active",
      creatorGithubHandle: "cardosofede"
    },
    {
      id: "executor-creator",
      name: "executor-creator",
      description: "Create and manage trading executors (position, grid, DCA, TWAP)",
      category: "trading",
      triggers: ["create executor", "position executor", "grid trading", "dca order", "start trading"],
      path: "skills/executor-creator",
      installs: { total: 0, weekly: 0, by_agent: {} },
      first_seen: "2026-01-26T00:00:00Z",
      status: "active",
      creatorGithubHandle: "cardosofede"
    },
    {
      id: "candles-feed",
      name: "candles-feed",
      description: "Fetch market data and calculate technical indicators (RSI, EMA, MACD, Bollinger Bands)",
      category: "data",
      triggers: ["get candles", "calculate rsi", "market data", "technical analysis"],
      path: "skills/candles-feed",
      installs: { total: 0, weekly: 0, by_agent: {} },
      first_seen: "2026-01-26T00:00:00Z",
      status: "active",
      creatorGithubHandle: "fengtality"
    },
    {
      id: "portfolio",
      name: "portfolio",
      description: "View portfolio balances, positions, and history across all connected exchanges",
      category: "data",
      triggers: ["show balance", "portfolio", "positions", "check balance"],
      path: "skills/portfolio",
      installs: { total: 0, weekly: 0, by_agent: {} },
      first_seen: "2026-01-26T00:00:00Z",
      status: "active",
      creatorGithubHandle: "fengtality"
    }
  ],
  categories: [
    { id: "infrastructure", name: "Infrastructure", icon: "server" },
    { id: "configuration", name: "Configuration", icon: "settings" },
    { id: "trading", name: "Trading", icon: "chart-line" },
    { id: "data", name: "Data", icon: "database" }
  ]
};

export async function getSkillsData(): Promise<SkillsData> {
  try {
    // Read from local skills.json file (one level up from app/)
    const skillsPath = path.join(process.cwd(), "..", "skills.json");
    const content = await fs.readFile(skillsPath, "utf-8");
    return JSON.parse(content);
  } catch {
    return fallbackData;
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
    const response = await fetch(
      `https://raw.githubusercontent.com/hummingbot/skills/main/${skillPath}/SKILL.md`,
      { next: { revalidate: 60 } }
    );

    if (!response.ok) {
      return "";
    }

    const content = await response.text();
    // Remove frontmatter (YAML between ---)
    const frontmatterRegex = /^---[\s\S]*?---\n*/;
    return content.replace(frontmatterRegex, "");
  } catch {
    return "";
  }
}
