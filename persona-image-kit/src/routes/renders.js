import { Router } from 'express';
import { Jimp } from 'jimp';
import { nanoid } from 'nanoid';
import { parse, MemeSchema } from '../lib/validators.js';
import { filePathFor, toDataUrl } from '../lib/fsio.js';

function hex(c){ return c.startsWith('#') ? c : `#${c}`; }

const r = Router();

// POST /renders/meme
r.post('/meme', async (req, res) => {
  const v = parse(MemeSchema, req.body || {});
  if (!v.ok) return res.status(400).json({ ok:false, error:v.error });

  const { topText = '', bottomText = '', width, height, bg, fg } = v.data;
  const id = nanoid();
  const img = new Jimp(width, height, hex(bg));

  const font = await Jimp.loadFont(Jimp.FONT_SANS_32_WHITE);
  const margin = Math.round(height * 0.05);
  const boxWidth = width - margin * 2;

  // Top
  if (topText) {
    const th = Jimp.measureTextHeight(font, topText, boxWidth);
    img.print(font, margin, margin, { text: topText, alignmentX: Jimp.HORIZONTAL_ALIGN_CENTER, alignmentY: Jimp.VERTICAL_ALIGN_TOP }, boxWidth, th);
  }
  // Bottom
  if (bottomText) {
    const bh = Jimp.measureTextHeight(font, bottomText, boxWidth);
    img.print(font, margin, height - bh - margin, { text: bottomText, alignmentX: Jimp.HORIZONTAL_ALIGN_CENTER, alignmentY: Jimp.VERTICAL_ALIGN_BOTTOM }, boxWidth, bh);
  }

  // Tint to fg
  img.color([{ apply:'mix', params:[hex(fg), 15] }]);

  await img.writeAsync(filePathFor(id));
  const buf = await img.getBufferAsync(Jimp.MIME_PNG);
  res.json({ ok:true, data:{ id, file:`/public/img/${id}.png`, base64: toDataUrl(buf) }});
});

export default r;