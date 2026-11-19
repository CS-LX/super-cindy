import { Plus, Settings, X } from 'lucide-react';
import { useState } from 'react';
import { mountPage, subscription } from '../../ui-page/harness';
import { Button } from '../../../src/renderer/components/ui/button';
import { SettingsCard } from '../../../src/renderer/components/ui/settings-rows';
import { ChromeIconButton } from '../../../src/renderer/components/title-bar/ChromeIconButton';
import { Slider } from '../../../src/renderer/components/ui/slider';
import { Switch } from '../../../src/renderer/components/ui/switch';
import { AppearanceSection } from '../../../src/renderer/components/settings/AppearanceSection';
import { WallpaperSettingsProvider } from '../../../src/renderer/hooks/useWallpaperSettings';
import { DEFAULT_APPEARANCE_SETTINGS } from '../../../src/shared/appearanceSettings';
import { SendButton } from '../../../src/renderer/components/new-chat/SendButton';
import { FastModeToggle } from '../../../src/renderer/components/new-chat/FastModeToggle';

function Controls() {
  const [count, setCount] = useState(0);
  return <main className="mx-auto max-w-[900px] space-y-6 p-8 text-[var(--text-primary)]" data-theme-sample>
    <h1 className="text-24">我的世界 · Minecraft</h1>
    <SettingsCard className="space-y-6 p-6">
      <p className="text-16">游戏菜单 / Game menu</p>
      <div className="flex flex-wrap items-center gap-4">
        <Button data-check="filled" onClick={() => setCount(count + 1)}>继续游戏</Button>
        <Button variant="secondary">选项…</Button>
        <Button variant="cta">完成</Button>
        <Button disabled data-check="disabled">暂不可用</Button>
        <Button tone="danger-solid">删除</Button>
        <span data-check="count">{count}</span>
      </div>
      <div className="flex items-center gap-4">
        <ChromeIconButton aria-label="添加" data-check="bare"><Plus size={18} /></ChromeIconButton>
        <ChromeIconButton aria-label="设置"><Settings size={18} /></ChromeIconButton>
        <ChromeIconButton aria-label="关闭"><X size={18} /></ChromeIconButton>
        <Button tone="quiet">无底文字按钮</Button>
        <FastModeToggle enabled={false} onToggle={() => {}} />
        <SendButton disabled={false} onClick={() => {}} />
        <SendButton disabled={false} isStreaming onClick={() => {}} />
        <SendButton disabled={false} companionVoice action="voice" onClick={() => {}} />
      </div>
      <label className="flex items-center gap-4">世界名称 <input className="h-9 px-3" defaultValue="奶蛙的世界" /></label>
      <label className="flex items-center gap-3"><input type="checkbox" className="size-5" defaultChecked />保留奶龙奶蛙素材</label>
      <label><input type="checkbox" data-check="native-checkbox" />自动使用</label>
      <div className="flex items-center gap-6"><Switch aria-label="声音" defaultChecked /><Slider aria-label="音量" defaultValue={[65]} className="w-64" /></div>
      <p className="text-14">中文像素字体：你好，世界！ English 0123456789</p>
      <p className="text-13 text-[var(--text-secondary)]">文字阴影与原版控件；图标保持现有形状。</p>
      <textarea aria-label="代码字体预览" className="font-mono w-full" defaultValue="const world = 'Minecraft';" data-check="code-font" />
    </SettingsCard>
  </main>;
}

void mountPage({
  route: '/settings/appearance',
  host: {
    localThemes: { list: async () => ({ success: true, themes: [] }) },
    appearanceSettings: {
      getSync: () => DEFAULT_APPEARANCE_SETTINGS,
      get: async () => DEFAULT_APPEARANCE_SETTINGS,
      onChanged: subscription('appearance'),
    },
  },
  render: ({ case: scenario }) => scenario === 'minecraft-appearance'
    ? <WallpaperSettingsProvider desktopBackground={false}><main className="mx-auto max-w-[1080px] p-8"><AppearanceSection /></main></WallpaperSettingsProvider>
    : <Controls />,
});
