interface Config {
  MODE: "fake" | "real";
  IMG_API_BASE?: string;
  IMG_API_KEY?: string;
  NOTIFY_WEBHOOK?: string;
  HMAC_SECRET: string;
}

export const cfg: Config = {
  MODE: (process.env.MODE as "fake" | "real") || "fake",
  IMG_API_BASE: process.env.IMG_API_BASE,
  IMG_API_KEY: process.env.IMG_API_KEY,
  NOTIFY_WEBHOOK: process.env.NOTIFY_WEBHOOK,
  HMAC_SECRET: process.env.HMAC_SECRET || "fake-hmac-secret-placeholder-change-in-production"
};

export default cfg;