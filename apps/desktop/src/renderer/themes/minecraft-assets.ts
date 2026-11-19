// These files are deliberately gitignored: a public checkout must not include
// the owner's Minecraft assets. Vite bundles the locally prepared CSS/resources
// only when present. No download, filesystem access or remote CSS at runtime.
const assets = import.meta.glob('../assets/minecraft-local/minecraft-assets.css', { eager: true });
export const hasMinecraftAssets = Object.keys(assets).length > 0;
