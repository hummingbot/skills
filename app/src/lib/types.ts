export interface Skill {
  id: string;
  name: string;
  description: string;
  path: string;
  author?: string;
  installs: number;
}

export interface SkillsData {
  repo: {
    owner: string;
    name: string;
    url: string;
  };
  skills: Skill[];
}
