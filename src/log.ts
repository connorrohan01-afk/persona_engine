type LogLevel = 'info' | 'warn' | 'error';

const timestamp = () => new Date().toISOString();

const log = (level: LogLevel, message: string, ...args: any[]) => {
  const time = timestamp();
  const prefix = `[${time}] ${level.toUpperCase()}:`;
  console.log(prefix, message, ...args);
};

export const logger = {
  info: (message: string, ...args: any[]) => log('info', message, ...args),
  warn: (message: string, ...args: any[]) => log('warn', message, ...args),
  error: (message: string, ...args: any[]) => log('error', message, ...args)
};

export default logger;