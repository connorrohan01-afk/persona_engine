"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.logger = void 0;
const timestamp = () => new Date().toISOString();
const log = (level, message, ...args) => {
    const time = timestamp();
    const prefix = `[${time}] ${level.toUpperCase()}:`;
    console.log(prefix, message, ...args);
};
exports.logger = {
    info: (message, ...args) => log('info', message, ...args),
    warn: (message, ...args) => log('warn', message, ...args),
    error: (message, ...args) => log('error', message, ...args)
};
exports.default = exports.logger;
//# sourceMappingURL=log.js.map