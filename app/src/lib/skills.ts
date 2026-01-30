import { SkillsData } from "./types";

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
      description: "Deploy Hummingbot infrastructure (Docker, API server, Gateway)",
      category: "infrastructure",
      triggers: ["install hummingbot", "setup trading", "deploy api", "docker setup"],
      path: "skills/hummingbot-api-setup",
      installs: { total: 0, weekly: 0, by_agent: {} },
      first_seen: "2026-01-26T00:00:00Z",
      status: "active"
    },
    {
      id: "keys-manager",
      name: "keys-manager",
      description: "Manage exchange API credentials with progressive disclosure",
      category: "configuration",
      triggers: ["add api key", "configure exchange", "setup binance", "add credentials"],
      path: "skills/keys-manager",
      installs: { total: 0, weekly: 0, by_agent: {} },
      first_seen: "2026-01-26T00:00:00Z",
      status: "active"
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
      status: "active"
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
      status: "active"
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
    const response = await fetch(
      "https://raw.githubusercontent.com/hummingbot/skills/main/skills.json",
      { next: { revalidate: 60 } }
    );

    if (!response.ok) {
      return fallbackData;
    }

    return response.json();
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
