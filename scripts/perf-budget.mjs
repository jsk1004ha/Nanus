import { spawnSync } from "node:child_process";
import { existsSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

const npm = process.platform === "win32" ? "npm.cmd" : "npm";
const budgets = {
  initialJsBytes: 190_000,
  initialCssBytes: 35_000,
};

function runScript(script) {
  const result = spawnSync(npm, ["run", script], { stdio: "inherit", shell: process.platform === "win32" });
  if (result.error) {
    console.error(result.error);
  }
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

function collectInitialAssets() {
  const indexPath = join("dist", "index.html");
  if (!existsSync(indexPath)) throw new Error("dist/index.html is missing. Run the production build first.");

  const html = readFileSync(indexPath, "utf8");
  const assets = [];
  const assetPattern = /(?:src|href)="\/?([^"]+\.(?:js|css))"/g;
  let match;

  while ((match = assetPattern.exec(html))) {
    const relativePath = match[1];
    const filePath = join("dist", relativePath);
    if (existsSync(filePath)) assets.push({ path: relativePath, bytes: statSync(filePath).size });
  }

  return assets;
}

function assertBudget() {
  const assets = collectInitialAssets();
  const initialJsBytes = assets.filter((asset) => asset.path.endsWith(".js")).reduce((sum, asset) => sum + asset.bytes, 0);
  const initialCssBytes = assets.filter((asset) => asset.path.endsWith(".css")).reduce((sum, asset) => sum + asset.bytes, 0);

  console.log(`Initial JS: ${initialJsBytes} bytes (budget ${budgets.initialJsBytes})`);
  console.log(`Initial CSS: ${initialCssBytes} bytes (budget ${budgets.initialCssBytes})`);

  if (initialJsBytes > budgets.initialJsBytes) {
    throw new Error(`Initial JS budget exceeded: ${initialJsBytes} > ${budgets.initialJsBytes}`);
  }
  if (initialCssBytes > budgets.initialCssBytes) {
    throw new Error(`Initial CSS budget exceeded: ${initialCssBytes} > ${budgets.initialCssBytes}`);
  }
}

runScript("typecheck");
runScript("build");
assertBudget();
runScript("test:e2e:run");
