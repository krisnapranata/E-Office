// Cari patchright (fork Playwright) yang sudah terpasang lewat ekstensi CodeGPT — sama dengan casemix,
// sehingga uji browser tidak butuh `npm install`. Ganti dengan E2E_PATCHRIGHT=/path/ke/patchright bila perlu.
const fs = require("fs"), path = require("path");
module.exports = function cariPatchright() {
  if (process.env.E2E_PATCHRIGHT) return require(process.env.E2E_PATCHRIGHT);
  const ROOTS = [".vscode-server/extensions", ".vscode/extensions"].map(r => path.join(process.env.HOME || "", r));
  for (const root of ROOTS) {
    if (!fs.existsSync(root)) continue;
    const ext = fs.readdirSync(root).filter(d => d.startsWith("danielsanmedium.dscodegpt-")).sort().pop();
    const kand = ext && path.join(root, ext, "standalone/node_modules/patchright");
    if (kand && fs.existsSync(kand)) return require(kand);
  }
  return null;
};
