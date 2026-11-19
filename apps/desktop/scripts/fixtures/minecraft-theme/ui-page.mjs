import { existsSync } from 'node:fs';

const prepared = existsSync(new URL('../../../src/renderer/assets/minecraft-local/minecraft-assets.css', import.meta.url));
const minecraftStorage = { 'theme.familyId': 'minecraft' };

export default {
  name: 'minecraft-theme', entry: './fixture.tsx', viewport: { width: 1040, height: 720 },
  real: 'AppearanceSection, Button, ChromeIconButton, SettingsCard, Switch, Slider, original private game textures and fonts when prepared',
  notCovered: 'No production data, installation, account or model requests. Original game resources are local-only and absent from public CI.',
  cases: {
    default: { about: 'Existing Cindy light/dark appearance remains unchanged' },
    ...(prepared ? {
      'minecraft-controls': { about: 'Original Minecraft controls and font in either saved display mode', storage: minecraftStorage },
      'minecraft-appearance': { about: 'Real appearance picker and retained meme wallpaper thumbnails', storage: minecraftStorage, viewport: { width: 1200, height: 950 } },
    } : {}),
  },
  async check(page, ui) {
    const minecraft = ui.case.startsWith('minecraft');
    await page.evaluate(() => document.fonts.ready);
    if (ui.case === 'minecraft-appearance') {
      const picker = page.getByRole('combobox', { name: await ui.t('settings.appearance.themeAriaLabel') });
      await picker.click();
      await page.getByRole('option', { name: await ui.t('settings.appearance.minecraftTheme'), exact: false }).waitFor();
      await ui.capture('picker');
      await page.keyboard.press('Escape');
      // Switching through the real picker must remove all skin-specific geometry/font effects.
      await picker.click();
      await page.getByRole('option', { name: 'Classic', exact: true }).click();
      await page.waitForFunction(() => document.documentElement.dataset.theme?.startsWith('default-'));
      const font = await page.locator('body').evaluate(el => getComputedStyle(el).fontFamily);
      if (font.includes('Minecraft Game')) throw new Error('Private font leaked into Classic');
      await ui.capture('restored-classic');
      return;
    }
    const filled = page.locator('[data-check="filled"]');
    const bare = page.locator('[data-check="bare"]');
    const face = el => getComputedStyle(el, '::before').borderImageSource;
    const normal = await filled.evaluate(face);
    if (minecraft) {
      if (!normal.includes('button-')) throw new Error('Original button sprite missing');
      if (!await page.locator('body').evaluate(el => getComputedStyle(el).fontFamily.includes('Minecraft Game'))) throw new Error('Original font missing');
      if (await page.locator('[data-check="code-font"]').evaluate(el => getComputedStyle(el).fontFamily.includes('Minecraft Game'))) throw new Error('UI font overrode the code editor font');
      await bare.hover();
      const plain = await bare.evaluate(el => ({ image: getComputedStyle(el, '::before').borderImageSource, background: getComputedStyle(el, '::before').backgroundColor }));
      if (plain.image !== 'none' || plain.background !== 'rgba(0, 0, 0, 0)') throw new Error('Bare icon acquired a painted background');
      const fast = page.getByRole('button', { name: 'Fast Mode' });
      await fast.hover();
      if (await fast.evaluate(el => getComputedStyle(el).borderImageSource) !== 'none') throw new Error('Transparent Fast button acquired a raised frame');
      if (!await page.locator('.composer-send-face').first().evaluate(el => getComputedStyle(el).borderImageSource.includes('button-'))) throw new Error('Send face missing original sprite');
      if (!await page.locator('.composer-send[data-companion] > span.inset-0').first().evaluate(el => getComputedStyle(el).borderImageSource.includes('button-'))) throw new Error('Companion face missing original sprite');
      const checkbox = await page.locator('[data-check="native-checkbox"]').boundingBox();
      if (!checkbox || checkbox.width < 16 || checkbox.height < 16) throw new Error('Native checkbox lost its intrinsic hit target');
      await filled.hover();
      if (await filled.evaluate(face) === normal) throw new Error('Minecraft hover sprite did not change');
      const disabled = page.locator('[data-check="disabled"]');
      const before = await disabled.evaluate(face);
      await disabled.hover();
      if (await disabled.evaluate(face) !== before) throw new Error('Disabled control changed sprite on hover');
    } else if (normal !== 'none') throw new Error('Minecraft frame leaked into Cindy');
    await filled.focus();
    await page.keyboard.press('Enter');
    if (await page.locator('[data-check="count"]').textContent() !== '1') throw new Error('Keyboard activation regressed');
    await ui.capture('controls');
  },
};
