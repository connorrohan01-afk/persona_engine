import { Router } from 'express';
import { Jimp } from 'jimp';
import { nanoid } from 'nanoid';
import { parse, AvatarSchema, OverlaySchema, TransformSchema } from '../lib/validators.js';
import { filePathFor, toDataUrl } from '../lib/fsio.js';

function hex(c){ return c.startsWith('#') ? c : `#${c}`; }

const r = Router();

// POST /images/avatar
r.post('/avatar', async (req, res) => {
  const v = parse(AvatarSchema, req.body || {});
  if (!v.ok) return res.status(400).json({ ok:false, error:v.error });

  const { initials, size, bg, fg } = v.data;
  const id = nanoid();
  const img = new Jimp(size, size, hex(bg));
  const font = await Jimp.loadFont(Jimp.FONT_SANS_64_WHITE);

  const text = initials.toUpperCase();
  const scale = Math.max(32, Math.floor(size * 0.28));
  const customFont = await Jimp.loadFont(scale >= 128 ? Jimp.FONT_SANS_128_WHITE :
                                       scale >= 64  ? Jimp.FONT_SANS_64_WHITE  :
                                                       Jimp.FONT_SANS_32_WHITE);
  const textW = Jimp.measureText(customFont, text);
  const textH = Jimp.measureTextHeight(customFont, text, size);
  const x = (size - textW) / 2;
  const y = (size - textH) / 2;
  img.print(customFont, x, y, { text, alignmentX: Jimp.HORIZONTAL_ALIGN_CENTER, alignmentY: Jimp.VERTICAL_ALIGN_MIDDLE }, textW, textH);

  // tint to requested fg by drawing text color overlay
  // (Jimp fonts are white; apply color with composite colorize)
  img.color([{ apply:'mix', params:[hex(fg), 100] }]); // subtle tint

  await img.writeAsync(filePathFor(id));
  const buf = await img.getBufferAsync(Jimp.MIME_PNG);
  res.json({ ok:true, data:{ id, file:`/public/img/${id}.png`, base64: toDataUrl(buf) }});
});

// POST /images/overlay
r.post('/overlay', async (req, res) => {
  const v = parse(OverlaySchema, req.body || {});
  if (!v.ok) return res.status(400).json({ ok:false, error:v.error });
  const { text, width, height, bg, fg, fontSize } = v.data;

  const id = nanoid();
  const img = new Jimp(width, height, hex(bg));
  const font = await Jimp.loadFont(
    fontSize >= 128 ? Jimp.FONT_SANS_128_WHITE :
    fontSize >= 64  ? Jimp.FONT_SANS_64_WHITE  : Jimp.FONT_SANS_32_WHITE
  );
  const tw = Jimp.measureText(font, text);
  const th = Jimp.measureTextHeight(font, text, width);
  const x = (width - tw) / 2;
  const y = (height - th) / 2;

  img.print(font, x, y, { text, alignmentX: Jimp.HORIZONTAL_ALIGN_CENTER, alignmentY: Jimp.VERTICAL_ALIGN_MIDDLE }, tw, th);
  // recolor overlay text by mixing a layer; simple approach:
  img.color([{ apply:'mix', params:[hex(fg), 25] }]);

  await img.writeAsync(filePathFor(id));
  const buf = await img.getBufferAsync(Jimp.MIME_PNG);
  res.json({ ok:true, data:{ id, file:`/public/img/${id}.png`, base64: toDataUrl(buf) }});
});

// POST /images/transform
r.post('/transform', async (req, res) => {
  const v = parse(TransformSchema, req.body || {});
  if (!v.ok) return res.status(400).json({ ok:false, error:v.error });

  const { imageBase64, ops, output } = v.data;
  const raw = imageBase64.replace(/^data:image\/\w+;base64,/, '');
  const buf = Buffer.from(raw, 'base64');
  let img = await Jimp.read(buf);

  for (const op of ops) {
    if (op.type === 'resize') {
      img = img.resize(op.w || img.getWidth(), op.h || img.getHeight());
    } else if (op.type === 'crop') {
      const x = op.x ?? 0, y = op.y ?? 0, w = op.w ?? img.getWidth(), h = op.h ?? img.getHeight();
      img = img.crop(x, y, w, h);
    }
  }

  const id = nanoid();
  await img.writeAsync(filePathFor(id));
  if (output === 'base64') {
    const out = await img.getBufferAsync(Jimp.MIME_PNG);
    return res.json({ ok:true, data:{ id, base64: `data:image/png;base64,${out.toString('base64')}` }});
  }
  res.json({ ok:true, data:{ id, file:`/public/img/${id}.png` }});
});

export default r;