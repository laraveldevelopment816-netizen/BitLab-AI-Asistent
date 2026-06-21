export const C = {
  bg:        '#0b0d10',
  panel:     '#101317',
  panelHi:   '#14181d',
  panelLo:   '#0d1014',
  border:    '#1f242b',
  borderHi:  '#2a3038',
  text:      '#e4e7ec',
  textDim:   '#8a929c',
  textMute:  '#5a626c',
  accent:    '#7dd3fc',     // cyan, sekundarni
  accentDim: '#0c4a6e',
  bitlab:    '#fb6d3b',     // BitLab orange — primarni brand accent
  ok:        '#4ade80',
  warn:      '#fbbf24',
  err:       '#f87171',
  rate:      '#c084fc',
}

// Per-channel boje
export const CHANNEL: Record<string, string> = {
  chat:    '#7dd3fc',  // cyan
  voice:   '#c084fc',  // purple
  email:   '#4ade80',  // green
  compare: '#fbbf24',  // amber
}

// Per-model boje
export const MODEL: Record<string, string> = {
  haiku:  '#fb6d3b',  // orange (BitLab brand)
  sonnet: '#d97757',  // warm orange
  opus:   '#a855f7',  // violet
}

/** Adapter id je "<channel>:<model>" — vrati boju modela kao primarnu. */
export function adapterColor(adapter: string): string {
  const [, model] = adapter.split(':')
  if (model && MODEL[model]) return MODEL[model]
  if (adapter && CHANNEL[adapter]) return CHANNEL[adapter]
  return C.textMute
}

/** Boja za channel pill. */
export function channelColor(channel: string): string {
  return CHANNEL[channel] ?? C.textMute
}

/** Boja za model pill. */
export function modelColor(model: string): string {
  return MODEL[model] ?? C.textMute
}

// Backward-compat alias za postojeće komponente koje su zvale providerColor
export const providerColor = adapterColor
