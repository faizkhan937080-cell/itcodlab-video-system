/**
 * Replica of reel DfMQ7zqkuxO (neuraltech.ai). Every number here is MEASURED from the reference frame sheets
 * (creators/neuraltech.ai/reel-DfMQ7zqkuxO/collage_ref_01..09.jpg, 240x427 tiles of 1080x1920 frames, x4.5).
 * Fonts are Google fonts (official @remotion/google-fonts) via ext/fonts; the brand kit shown IN the reel says
 * "Font: Inter Tight", "Colours: charcoal, grey, white".
 */
import {FONTS} from '../../ext/fonts';

export const REF = 'DfMQ7zqkuxO';
export const K = {
  page: '#E9E5DC', // page median RGB (233,229,220) at 13.4 / 37.5 / 87.4 s
  pageLight: '#EFEBE3', // centre of the page is lighter (237,233,224 at 29.1 s)
  card: '#F7F6F2',
  cardLine: '#DAD7CF',
  ink: '#1D1B19', // charcoal
  grey: '#8F8C86',
  greyLight: '#B9B6AF',
  blue: '#3A8DDE', // Finder selection / folder blue (31.0-32.8 s)
  blueSel: '#1F6FE5',
  green: '#2E9B5B', // Approved pill (76.3 s)
  red: '#D9533F', // Rejected pill
  dark: '#141210',
  split: 0.5, // top panel ends at 49.9 % of the height (12.5, 13.4, 37.5 s)
  headerY: 0.04, // "Step N Title" centre at 4.0 % height
  capSplitY: 0.529, // caption centre in split layout (226/427)
  capPunchY: 0.557, // caption centre on the punch-in (238/427)
};

export const F = {
  sans: FONTS['InterTight'] ?? 'Inter Tight, sans-serif',
  ui: FONTS['Inter'] ?? 'Inter, sans-serif',
  mono: FONTS['JetBrainsMono'] ?? 'monospace',
  type: FONTS['SpecialElite'] ?? 'monospace',
};

/** 1 unit = 1 px of a 1080-wide frame. */
export const unit = (w: number) => w / 1080;
