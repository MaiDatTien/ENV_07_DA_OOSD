const files = import.meta.glob("./images/*.{jpg,jpeg,png,webp}", { eager: true, query: "?url", import: "default" });

export const DEFAULT_BACKGROUND = "background.jpg";
export const DEFAULT_DIM = 45;
export const BG_DEFAULTS = {
  login: { name: "dang-nhap.jpg", dim: 35 },
  app: { name: DEFAULT_BACKGROUND, dim: DEFAULT_DIM },
};

export const backgrounds = Object.entries(files)
  .map(([path, url]) => ({ name: path.split("/").pop(), url }))
  .sort((a, b) => a.name.localeCompare(b.name));

export function applyBackground({ name, dim }) {
  const img = backgrounds.find((b) => b.name === name) || backgrounds.find((b) => b.name === DEFAULT_BACKGROUND);
  const root = document.documentElement.style;
  root.setProperty("--bg-image", img ? `url("${img.url}")` : "none");
  root.setProperty("--bg-dim", String((dim ?? DEFAULT_DIM) / 100));
}
