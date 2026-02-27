#!/usr/bin/env node
/**
 * Fetches install counts from skills.sh for hummingbot skills
 * and updates src/data/installs.json
 *
 * Usage: node scripts/update-installs.js
 */

const fs = require('fs');
const path = require('path');
const https = require('https');

const SKILLS_SH_URL = 'https://skills.sh/?q=hummingbot';
const INSTALLS_FILE = path.join(__dirname, '../src/data/installs.json');

// Skills we track (from our skills/ folder)
const OUR_SKILLS = [
  'hummingbot-deploy',
  'lp-agent',
  'connectors-available',
  'slides-generator',
  'find-arbitrage-opps',
  'hummingbot'
];

async function fetchPage(url) {
  return new Promise((resolve, reject) => {
    https.get(url, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve(data));
      res.on('error', reject);
    }).on('error', reject);
  });
}

async function main() {
  console.log('Fetching install counts from skills.sh...');

  try {
    const html = await fetchPage(SKILLS_SH_URL);

    // Parse install counts from the page
    // The page contains data like: "installs":48
    // We need to match skill names with hummingbot/skills repo
    const installs = {};

    // Initialize all our skills with 0
    for (const skill of OUR_SKILLS) {
      installs[skill] = 0;
    }

    // Try to find install counts in the page data
    // Look for patterns like: "name":"hummingbot-deploy"..."installs":48
    const skillPattern = /"name":"([^"]+)"[^}]*"repo":"hummingbot\/skills"[^}]*"installs":(\d+)/g;
    const altPattern = /"installs":(\d+)[^}]*"name":"([^"]+)"[^}]*"repo":"hummingbot\/skills"/g;

    let match;
    while ((match = skillPattern.exec(html)) !== null) {
      const [, name, count] = match;
      if (OUR_SKILLS.includes(name)) {
        installs[name] = parseInt(count, 10);
        console.log(`  ${name}: ${count}`);
      }
    }

    // Try alternate pattern
    while ((match = altPattern.exec(html)) !== null) {
      const [, count, name] = match;
      if (OUR_SKILLS.includes(name) && installs[name] === 0) {
        installs[name] = parseInt(count, 10);
        console.log(`  ${name}: ${count}`);
      }
    }

    // Write to file
    fs.writeFileSync(INSTALLS_FILE, JSON.stringify(installs, null, 2) + '\n');
    console.log(`\nUpdated ${INSTALLS_FILE}`);
    console.log('Install counts:', installs);

  } catch (error) {
    console.error('Error fetching install counts:', error.message);
    console.log('\nTo manually update, edit src/data/installs.json with values from:');
    console.log('  https://skills.sh/?q=hummingbot');
    process.exit(1);
  }
}

main();
