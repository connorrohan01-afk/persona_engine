interface Config {
    MODE: "fake" | "real";
    IMG_API_BASE?: string;
    IMG_API_KEY?: string;
    NOTIFY_WEBHOOK?: string;
    HMAC_SECRET: string;
}
export declare const cfg: Config;
export default cfg;
//# sourceMappingURL=config.d.ts.map