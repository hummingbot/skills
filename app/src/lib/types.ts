export interface Skill {
  id: string;
  name: string;
  description: string;
  category: string;
  triggers: string[];
  path: string;
  installs: {
    total: number;
    weekly: number;
    by_agent: Record<string, number>;
  };
  first_seen: string;
  status: "active" | "planned";
  creatorGithubHandle?: string;
}

export interface Category {
  id: string;
  name: string;
  icon: string;
}

export interface SkillsData {
  repo: {
    owner: string;
    name: string;
    url: string;
  };
  skills: Skill[];
  categories: Category[];
}
