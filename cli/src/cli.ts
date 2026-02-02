#!/usr/bin/env node

import { writeFileSync, readFileSync, existsSync, mkdirSync, readdirSync } from 'fs';
import { join, dirname } from 'path';
import { homedir } from 'os';
import { fileURLToPath } from 'url';
import { execSync, spawnSync } from 'child_process';

const __dirname = dirname(fileURLToPath(import.meta.url));

function getVersion(): string {
  try {
    const pkgPath = join(__dirname, '..', 'package.json');
    const pkg = JSON.parse(readFileSync(pkgPath, 'utf-8'));
    return pkg.version;
  } catch {
    return '1.0.0';
  }
}

const VERSION = getVersion();
const REPO = 'hummingbot/skills';
const SKILLS_API_URL = 'https://skills.hummingbot.org/api/skills';

// ANSI colors
const RESET = '\x1b[0m';
const BOLD = '\x1b[1m';
const DIM = '\x1b[38;5;102m';
const TEXT = '\x1b[38;5;145m';
const GREEN = '\x1b[32m';
const YELLOW = '\x1b[33m';

const LOGO_LINES = [
  ' _                               _             _   ',
  '| |__  _   _ _ __ ___  _ __ ___ (_)_ __   __ _| |__   ___  ___ ',
  "| '_ \\| | | | '_ ` _ \\| '_ ` _ \\| | '_ \\ / _` | '_ \\ / _ \\/ __|",
  '| | | | |_| | | | | | | | | | | | | | | | (_| | |_) | (_) \\__ \\',
  '|_| |_|\\__,_|_| |_| |_|_| |_| |_|_|_| |_|\\__, |_.__/ \\___/|___/',
  '                                         |___/                 ',
];

const GRAYS = [
  '\x1b[38;5;250m',
  '\x1b[38;5;248m',
  '\x1b[38;5;245m',
  '\x1b[38;5;243m',
  '\x1b[38;5;240m',
  '\x1b[38;5;238m',
];

interface Skill {
  id: string;
  name: string;
  description: string;
  path: string;
  author?: string;
}

interface SkillsResponse {
  skills: Skill[];
}

function showLogo(): void {
  console.log();
  LOGO_LINES.forEach((line, i) => {
    console.log(`${GRAYS[i % GRAYS.length]}${line}${RESET}`);
  });
}

function showBanner(): void {
  showLogo();
  console.log();
  console.log(`${DIM}AI agent skills for algorithmic trading${RESET}`);
  console.log();
  console.log(
    `  ${DIM}$${RESET} ${TEXT}npx hummingbot-skills add${RESET}      ${DIM}Install all skills${RESET}`
  );
  console.log(
    `  ${DIM}$${RESET} ${TEXT}npx hummingbot-skills list${RESET}     ${DIM}List available skills${RESET}`
  );
  console.log(
    `  ${DIM}$${RESET} ${TEXT}npx hummingbot-skills find${RESET}     ${DIM}Search for skills${RESET}`
  );
  console.log();
  console.log(`Discover more at ${TEXT}https://skills.hummingbot.org${RESET}`);
  console.log();
}

function showHelp(): void {
  console.log(`
${BOLD}Usage:${RESET} hummingbot-skills <command> [options]

${BOLD}Commands:${RESET}
  add [skills...]   Install skills (default: all skills)
  list, ls          List available skills
  find [query]      Search for skills

${BOLD}Add Options:${RESET}
  -g, --global      Install globally instead of project-level
  -a, --agent       Specify agents (claude-code, cursor, etc.)
  -y, --yes         Skip confirmation prompts

${BOLD}Examples:${RESET}
  ${DIM}$${RESET} hummingbot-skills add
  ${DIM}$${RESET} hummingbot-skills add portfolio candles-feed
  ${DIM}$${RESET} hummingbot-skills add -g
  ${DIM}$${RESET} hummingbot-skills list
  ${DIM}$${RESET} hummingbot-skills find trading

${BOLD}Options:${RESET}
  --help, -h        Show this help message
  --version, -v     Show version number

Discover more at ${TEXT}https://skills.hummingbot.org${RESET}
`);
}

async function fetchSkills(): Promise<Skill[]> {
  try {
    const response = await fetch(SKILLS_API_URL);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = (await response.json()) as SkillsResponse;
    return data.skills;
  } catch (error) {
    console.log(`${DIM}Could not fetch skills from API, using fallback...${RESET}`);
    // Fallback: fetch from GitHub
    try {
      const ghResponse = await fetch(
        `https://api.github.com/repos/${REPO}/contents/skills`
      );
      if (!ghResponse.ok) throw new Error('GitHub API error');
      const dirs = (await ghResponse.json()) as Array<{ name: string; type: string }>;
      return dirs
        .filter((d) => d.type === 'dir')
        .map((d) => ({
          id: d.name,
          name: d.name,
          description: '',
          path: `skills/${d.name}`,
        }));
    } catch {
      return [];
    }
  }
}

async function runList(): Promise<void> {
  console.log(`${TEXT}Available Hummingbot Skills:${RESET}`);
  console.log();

  const skills = await fetchSkills();

  if (skills.length === 0) {
    console.log(`${DIM}No skills found.${RESET}`);
    return;
  }

  const maxNameLen = Math.max(...skills.map((s) => s.name.length));

  for (const skill of skills) {
    const name = skill.name.padEnd(maxNameLen + 2);
    const author = skill.author ? `${DIM}by ${skill.author}${RESET}` : '';
    console.log(`  ${GREEN}•${RESET} ${TEXT}${name}${RESET}${skill.description ? ` ${DIM}${skill.description}${RESET}` : ''}`);
    if (author) {
      console.log(`    ${author}`);
    }
  }

  console.log();
  console.log(`${DIM}Install with:${RESET} npx hummingbot-skills add`);
  console.log();
}

async function runFind(args: string[]): Promise<void> {
  const query = args.join(' ').toLowerCase();
  const skills = await fetchSkills();

  if (!query) {
    console.log(`${TEXT}All Hummingbot Skills:${RESET}`);
    console.log();
    for (const skill of skills) {
      console.log(`  ${GREEN}•${RESET} ${TEXT}${skill.name}${RESET}`);
      if (skill.description) {
        console.log(`    ${DIM}${skill.description}${RESET}`);
      }
    }
    console.log();
    return;
  }

  const filtered = skills.filter(
    (s) =>
      s.name.toLowerCase().includes(query) ||
      s.description.toLowerCase().includes(query) ||
      s.id.toLowerCase().includes(query)
  );

  if (filtered.length === 0) {
    console.log(`${DIM}No skills found matching "${query}"${RESET}`);
    console.log();
    console.log(`${DIM}Available skills:${RESET}`);
    for (const skill of skills) {
      console.log(`  ${TEXT}${skill.name}${RESET}`);
    }
    return;
  }

  console.log(`${TEXT}Skills matching "${query}":${RESET}`);
  console.log();
  for (const skill of filtered) {
    console.log(`  ${GREEN}•${RESET} ${TEXT}${skill.name}${RESET}`);
    if (skill.description) {
      console.log(`    ${DIM}${skill.description}${RESET}`);
    }
  }
  console.log();
  console.log(
    `${DIM}Install with:${RESET} npx hummingbot-skills add ${filtered.map((s) => s.id).join(' ')}`
  );
  console.log();
}

interface AddOptions {
  global: boolean;
  agents: string[];
  skills: string[];
  yes: boolean;
}

function parseAddOptions(args: string[]): AddOptions {
  const options: AddOptions = {
    global: false,
    agents: [],
    skills: [],
    yes: false,
  };

  let i = 0;
  while (i < args.length) {
    const arg = args[i];
    if (arg === '-g' || arg === '--global') {
      options.global = true;
    } else if (arg === '-y' || arg === '--yes') {
      options.yes = true;
    } else if (arg === '-a' || arg === '--agent') {
      i++;
      while (i < args.length && !args[i].startsWith('-')) {
        options.agents.push(args[i]);
        i++;
      }
      continue;
    } else if (!arg.startsWith('-')) {
      options.skills.push(arg);
    }
    i++;
  }

  return options;
}

async function runAdd(options: AddOptions): Promise<void> {
  const allSkills = await fetchSkills();

  if (allSkills.length === 0) {
    console.log(`${DIM}No skills available to install.${RESET}`);
    return;
  }

  // Filter skills if specific ones requested
  let skillsToInstall = allSkills;
  if (options.skills.length > 0) {
    skillsToInstall = allSkills.filter((s) =>
      options.skills.some(
        (name) => s.id.toLowerCase() === name.toLowerCase() || s.name.toLowerCase() === name.toLowerCase()
      )
    );

    if (skillsToInstall.length === 0) {
      console.log(`${DIM}No matching skills found.${RESET}`);
      console.log();
      console.log(`${TEXT}Available skills:${RESET}`);
      for (const skill of allSkills) {
        console.log(`  ${skill.id}`);
      }
      return;
    }
  }

  console.log(`${TEXT}Installing ${skillsToInstall.length} skill(s):${RESET}`);
  for (const skill of skillsToInstall) {
    console.log(`  ${GREEN}•${RESET} ${skill.name}`);
  }
  console.log();

  // Use the skills CLI to install from hummingbot/skills
  const installArgs = ['skills', 'add', REPO];

  if (options.global) {
    installArgs.push('-g');
  }

  if (options.skills.length > 0) {
    installArgs.push('--skill', ...options.skills);
  } else {
    installArgs.push('--skill', '*');
  }

  if (options.agents.length > 0) {
    installArgs.push('--agent', ...options.agents);
  } else {
    installArgs.push('--agent', '*');
  }

  installArgs.push('-y');

  console.log(`${DIM}Running: npx ${installArgs.join(' ')}${RESET}`);
  console.log();

  const result = spawnSync('npx', ['-y', ...installArgs], {
    stdio: 'inherit',
  });

  if (result.status === 0) {
    console.log();
    console.log(`${GREEN}✓${RESET} ${TEXT}Skills installed successfully${RESET}`);
  } else {
    console.log();
    console.log(`${YELLOW}!${RESET} ${TEXT}Installation may have encountered issues${RESET}`);
  }

  console.log();
}

async function main(): Promise<void> {
  const args = process.argv.slice(2);

  if (args.length === 0) {
    showBanner();
    return;
  }

  const command = args[0];
  const restArgs = args.slice(1);

  switch (command) {
    case 'add':
    case 'install':
    case 'i':
    case 'a':
      showLogo();
      console.log();
      await runAdd(parseAddOptions(restArgs));
      break;

    case 'list':
    case 'ls':
    case 'l':
      showLogo();
      console.log();
      await runList();
      break;

    case 'find':
    case 'search':
    case 'f':
    case 's':
      showLogo();
      console.log();
      await runFind(restArgs);
      break;

    case '--help':
    case '-h':
    case 'help':
      showHelp();
      break;

    case '--version':
    case '-v':
    case 'version':
      console.log(VERSION);
      break;

    default:
      console.log(`Unknown command: ${command}`);
      console.log(`Run ${BOLD}hummingbot-skills --help${RESET} for usage.`);
      process.exit(1);
  }
}

main();
