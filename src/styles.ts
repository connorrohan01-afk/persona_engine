interface StyleConfig {
  name: string;
  basePrompt: string;
  negatives: string[];
  sampler: string;
  cfg: number;
  steps: number;
}

interface StyleSlots {
  outfit?: string;
  mood?: string;
  setting?: string;
}

const BASE_STYLES: Record<string, StyleConfig> = {
  studio: {
    name: "Studio Portrait",
    basePrompt: "Professional studio portrait of a person in {outfit}, {mood} expression, {setting} background, professional lighting, high quality, detailed, sharp focus",
    negatives: ["blurry", "low quality", "amateur", "poor lighting", "overexposed", "underexposed"],
    sampler: "DPM++ 2M Karras",
    cfg: 7,
    steps: 25
  },
  
  street: {
    name: "Street Style",
    basePrompt: "Street style photography of a person in {outfit}, {mood} vibe, {setting} urban environment, natural lighting, candid moment, trendy, fashionable",
    negatives: ["posed", "artificial", "studio lighting", "overprocessed", "fake", "low quality"],
    sampler: "Euler a",
    cfg: 6,
    steps: 20
  },
  
  editorial: {
    name: "Editorial Fashion",
    basePrompt: "High fashion editorial portrait of a person in {outfit}, {mood} aesthetic, {setting} backdrop, dramatic lighting, magazine quality, artistic composition, elegant",
    negatives: ["casual", "amateur", "snapshots", "poor composition", "bad lighting", "low quality"],
    sampler: "DPM++ SDE Karras", 
    cfg: 8,
    steps: 30
  },
  
  boudoir_soft: {
    name: "Soft Boudoir",
    basePrompt: "Elegant soft portrait of a person in {outfit}, {mood} expression, {setting} intimate setting, soft diffused lighting, tasteful, artistic, beautiful, classy",
    negatives: ["explicit", "vulgar", "inappropriate", "harsh lighting", "amateur", "low quality", "crude"],
    sampler: "DPM++ 2M Karras",
    cfg: 6,
    steps: 25
  }
};

const EXPLICIT_TONE_MODIFIERS: Record<string, { basePrompt: string; additionalNegatives: string[] }> = {
  studio: {
    basePrompt: "Alluring professional studio portrait of a person in {outfit}, seductive {mood} expression, {setting} background, glamorous lighting, captivating, sophisticated, alluring",
    additionalNegatives: ["explicit content", "inappropriate", "vulgar", "crude", "overly revealing"]
  },
  
  street: {
    basePrompt: "Captivating street style photography of a person in {outfit}, sultry {mood} vibe, {setting} urban environment, natural lighting, alluring moment, trendy, seductive appeal",
    additionalNegatives: ["explicit content", "inappropriate", "vulgar", "crude", "overly revealing"]
  },
  
  editorial: {
    basePrompt: "Seductive high fashion editorial portrait of a person in {outfit}, sultry {mood} aesthetic, {setting} backdrop, dramatic lighting, magazine quality, captivating composition, alluring elegance",
    additionalNegatives: ["explicit content", "inappropriate", "vulgar", "crude", "overly revealing"]
  },
  
  boudoir_soft: {
    basePrompt: "Sensual soft portrait of a person in {outfit}, alluring {mood} expression, {setting} intimate setting, soft romantic lighting, tasteful sensuality, artistic beauty, sophisticated allure",
    additionalNegatives: ["explicit content", "inappropriate", "vulgar", "crude", "overly revealing", "graphic"]
  }
};

/**
 * Get style configuration with optional tone modification and slot replacement
 */
export function getStyle(style: string, tone?: string, slots?: StyleSlots): StyleConfig {
  const baseStyle = BASE_STYLES[style];
  
  if (!baseStyle) {
    throw new Error(`Unknown style: ${style}. Available styles: ${Object.keys(BASE_STYLES).join(', ')}`);
  }
  
  let config = { ...baseStyle };
  
  // Apply explicit tone modifications
  if (tone === "explicit") {
    const modifier = EXPLICIT_TONE_MODIFIERS[style];
    if (modifier) {
      config.basePrompt = modifier.basePrompt;
      config.negatives = [...config.negatives, ...modifier.additionalNegatives];
    }
  }
  
  // Replace slots in the prompt
  if (slots) {
    config.basePrompt = replacePlaceholders(config.basePrompt, {
      outfit: slots.outfit || "elegant attire",
      mood: slots.mood || "confident", 
      setting: slots.setting || "neutral"
    });
  } else {
    // Use default slot values
    config.basePrompt = replacePlaceholders(config.basePrompt, {
      outfit: "elegant attire",
      mood: "confident",
      setting: "neutral"
    });
  }
  
  return config;
}

/**
 * Replace {slot} placeholders in the prompt string
 */
function replacePlaceholders(prompt: string, slots: Record<string, string>): string {
  let result = prompt;
  for (const [key, value] of Object.entries(slots)) {
    result = result.replace(new RegExp(`\\{${key}\\}`, 'g'), value);
  }
  return result;
}

/**
 * Get list of available styles
 */
export function getAvailableStyles(): string[] {
  return Object.keys(BASE_STYLES);
}

/**
 * Get style info without processing
 */
export function getStyleInfo(style: string): StyleConfig | null {
  return BASE_STYLES[style] || null;
}