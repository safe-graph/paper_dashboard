// Inline built JS and CSS into dist/index.html to avoid external asset loads.
// Run after `npm run build` in frontend/.
const fs = require("fs");
const path = require("path");

const distDir = path.resolve(__dirname, "..", "frontend", "dist");
const indexPath = path.join(distDir, "index.html");

function findAsset(ext) {
  const files = fs.readdirSync(path.join(distDir, "assets"));
  const match = files.find((f) => f.endsWith(ext));
  if (!match) {
    throw new Error(`No ${ext} asset found in dist/assets`);
  }
  return path.join("assets", match);
}

function inline() {
  let html = fs.readFileSync(indexPath, "utf8");
  const jsPath = findAsset(".js");
  const cssPath = findAsset(".css");

  const jsContent = fs.readFileSync(path.join(distDir, jsPath), "utf8");
  const cssContent = fs.readFileSync(path.join(distDir, cssPath), "utf8");

  html = html
    .replace(
      /<link rel="stylesheet"[^>]*href="\.\/assets\/[^"]+">\s*/i,
      `<style>\n${cssContent}\n</style>\n`
    )
    .replace(
      /<script type="module"[^>]*src="\.\/assets\/[^"]+"><\/script>/i,
      `<script type="module">\n${jsContent}\n</script>`
    );

  fs.writeFileSync(indexPath, html, "utf8");
  console.log("Inlined JS and CSS into dist/index.html");
}

inline();
