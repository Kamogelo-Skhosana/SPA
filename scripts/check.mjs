import { existsSync, readFileSync } from 'node:fs';

const required = ['README.md', 'docs/contracts.md', 'docs/design.md', 'apps/web/README.md', 'services/api/README.md', 'services/agent/README.md', 'services/xrpl/README.md'];
for (const file of required) {
  if (!existsSync(file)) throw new Error(`Missing ${file}`);
}
const packageJson = JSON.parse(readFileSync('package.json', 'utf8'));
if (packageJson.name !== 'spa') throw new Error('Unexpected package name');
console.log('SPA repository structure is valid');
