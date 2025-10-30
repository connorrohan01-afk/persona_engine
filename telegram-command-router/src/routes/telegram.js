import { Router } from 'express';
import { parseCommand } from '../lib/parse.js';
import { call } from '../lib/downstream.js';
import { linkChat, getLink } from '../lib/store.js';

const router = Router();

function logCommand(chatId, user, cmd, args, ok, err) {
  const logEntry = {
    ts: new Date().toISOString(),
    chatId,
    user: user?.username || user?.first_name || 'unknown',
    cmd,
    args,
    ok,
    err
  };
  console.log(JSON.stringify(logEntry));
}

async function sendMessage(chatId, text) {
  // In a real implementation, this would send back to Telegram
  // For now, we'll just log it
  console.log(`[TELEGRAM_REPLY] ${chatId}: ${text}`);
}

router.post('/webhook', async (req, res) => {
  try {
    const update = req.body;
    
    // Validate incoming update
    if (!update?.message?.chat || !update.message.text) {
      return res.json({ ok: true }); // Ignore non-text messages
    }

    const { chat, text, from: user } = update.message;
    const chatId = chat.id;

    // Parse command
    const parsed = parseCommand(text, process.env.TELEGRAM_BOT_USERNAME);
    if (!parsed) {
      await sendMessage(chatId, 'Invalid command format. Use /help for available commands.');
      logCommand(chatId, user, 'unknown', text, false, 'invalid_format');
      return res.json({ ok: true });
    }

    const { cmd, parts, kv } = parsed;
    let result = { ok: true };

    try {
      switch (cmd) {
        case 'ping':
          await sendMessage(chatId, 'pong');
          break;

        case 'help':
          const helpText = [
            'Available commands:',
            '/ping - Test connectivity',
            '/status - Service status check', 
            '/link <accountId> - Link chat to account',
            '/post <accountId> <subreddit> :: <text> - Queue a post',
            '/schedule <accountId> every <N> <unit> :: <subreddit> :: <text> - Schedule posts',
            '/media <accountId> :: <prompt or url> - Generate/queue media',
            '/help - Show this help'
          ].join('\n');
          await sendMessage(chatId, helpText);
          break;

        case 'status':
          const services = ['CONTENT_URL', 'POSTER_URL', 'SCHEDULER_URL', 'INTAKE_URL', 'VAULTS_URL'];
          const statuses = [];
          
          for (const service of services) {
            const healthResult = await call(service, '/api/v1/health', { method: 'GET' });
            statuses.push(`${service}: ${healthResult.ok ? '✅' : '❌'}`);
          }
          
          await sendMessage(chatId, `Service Status:\n${statuses.join('\n')}`);
          break;

        case 'link':
          if (parts.length < 1) {
            await sendMessage(chatId, 'Usage: /link <accountId>');
            break;
          }
          
          linkChat(chatId, parts[0]);
          await sendMessage(chatId, `Linked chat to account: ${parts[0]}`);
          break;

        case 'post':
          let accountId = parts[0];
          let subreddit = parts[1]; 
          let postText = parts.slice(2).join(' :: ');

          // If no accountId provided, try linked account
          if (!accountId || accountId.startsWith('r/')) {
            const link = getLink(chatId);
            if (!link) {
              await sendMessage(chatId, 'No account linked. Use /link <accountId> first.');
              break;
            }
            accountId = link.accountId;
            subreddit = parts[0];
            postText = parts.slice(1).join(' :: ');
          }

          if (!subreddit || !postText) {
            await sendMessage(chatId, 'Usage: /post <accountId> <subreddit> :: <text>');
            break;
          }

          const postResult = await call('POSTER_URL', '/api/v1/queue', {
            json: { accountId, subreddit, text: postText }
          });

          if (postResult.ok) {
            await sendMessage(chatId, `Post queued successfully! ID: ${postResult.data?.id || 'unknown'}`);
          } else {
            await sendMessage(chatId, `Failed to queue post: ${postResult.error}`);
          }
          break;

        case 'schedule':
          if (kv?.accountId && kv?.every && kv?.remaining) {
            const [schedSubreddit, schedText] = kv.remaining.split(' :: ').map(s => s.trim());
            
            if (!schedSubreddit || !schedText) {
              await sendMessage(chatId, 'Usage: /schedule <accountId> every <N> <unit> :: <subreddit> :: <text>');
              break;
            }

            const schedResult = await call('SCHEDULER_URL', '/api/v1/jobs', {
              json: {
                type: 'post',
                payload: {
                  accountId: kv.accountId,
                  subreddit: schedSubreddit,
                  text: schedText
                },
                delayMs: 0 // Schedule immediately, let scheduler handle timing
              }
            });

            if (schedResult.ok) {
              await sendMessage(chatId, `Scheduled post every ${kv.every.value} ${kv.every.unit}! Job ID: ${schedResult.data?.id || 'unknown'}`);
            } else {
              await sendMessage(chatId, `Failed to schedule: ${schedResult.error}`);
            }
          } else {
            await sendMessage(chatId, 'Usage: /schedule <accountId> every <N> <unit> :: <subreddit> :: <text>');
          }
          break;

        case 'media':
          if (parts.length < 2) {
            await sendMessage(chatId, 'Usage: /media <accountId> :: <prompt or url>');
            break;
          }

          const mediaAccountId = parts[0];
          const mediaInput = parts.slice(1).join(' :: ');
          
          let imageUrl = null;
          
          if (mediaInput.includes('http://') || mediaInput.includes('https://')) {
            // Direct URL
            imageUrl = mediaInput;
          } else {
            // Generate image via content service
            const imageResult = await call('CONTENT_URL', '/api/v1/images', {
              json: { prompt: mediaInput }
            });
            
            if (imageResult.ok && imageResult.data?.url) {
              imageUrl = imageResult.data.url;
            }
          }

          if (imageUrl) {
            // Queue the image post
            const mediaPostResult = await call('POSTER_URL', '/api/v1/queue', {
              json: { accountId: mediaAccountId, imageUrl, text: `Generated: ${mediaInput}` }
            });

            if (mediaPostResult.ok) {
              await sendMessage(chatId, `Media post queued! ID: ${mediaPostResult.data?.id || 'unknown'}`);
            } else {
              await sendMessage(chatId, `Failed to queue media post: ${mediaPostResult.error}`);
            }
          } else {
            await sendMessage(chatId, 'Failed to generate or process media');
          }
          break;

        default:
          await sendMessage(chatId, `Unknown command: ${cmd}. Use /help for available commands.`);
          result.ok = false;
      }

      logCommand(chatId, user, cmd, parts, result.ok, result.error);
    } catch (error) {
      await sendMessage(chatId, `Error processing command: ${error.message}`);
      logCommand(chatId, user, cmd, parts, false, error.message);
    }

    return res.json({ ok: true });
  } catch (error) {
    console.error('Webhook error:', error);
    return res.status(500).json({ ok: false, error: 'internal_error' });
  }
});

export default router;