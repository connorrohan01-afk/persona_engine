import { GenRequest } from './types';
import { getPersona } from './personas';
import { newJob, saveImage, writeManifest } from './vault';
import { getStyle } from './styles';
import { gen as fakeGen } from './fakeGen';
import { upscale as fakeUpscale, face as fakeFace } from './fakePolish';
import { genTxt2Img as realGen, upscale as realUpscale, face as realFace } from './realGen';
import { cfg } from './config';
import { logger } from './log';
import path from 'path';

interface GenerationResult {
  jobId: string;
  style: string;
  images: { url: string; seed: number }[];
  metrics: {
    duration: number;
    count: number;
    totalSize: number;
  };
}

/**
 * Run image generation orchestration flow
 */
export async function runGen(req: GenRequest): Promise<GenerationResult> {
  const startTime = Date.now();
  logger.info(`🚀 Starting generation for persona ${req.persona_id}, style ${req.style}, count ${req.count}`);
  
  try {
    // Step 1: Validate persona_id
    logger.info(`📋 Step 1: Validating persona ${req.persona_id}`);
    const persona = await getPersona(req.persona_id);
    if (!persona) {
      throw new Error(`Persona ${req.persona_id} not found`);
    }
    logger.info(`✅ Persona validated: ${persona.name}`);
    
    // Step 2: Create job via vault
    logger.info(`📁 Step 2: Creating job for style ${req.style}`);
    const { jobId, styleDir } = await newJob(req.persona_id, req.style);
    logger.info(`✅ Job created: ${jobId} in ${styleDir}`);
    
    // Step 3: Build style configuration and merge slots
    logger.info(`🎨 Step 3: Building style configuration`);
    const styleConfig = getStyle(req.style, req.tone, req.slots);
    logger.info(`✅ Style config: ${styleConfig.name} with ${styleConfig.negatives.length} negatives`);
    
    // Step 4: Generate and process images
    logger.info(`🖼️ Step 4: Generating ${req.count} images (mode: ${cfg.MODE})`);
    
    let generatedImages: { buffer: Buffer; seed: number }[];
    
    if (cfg.MODE === "real") {
      logger.info(`🔄 Using real image generation`);
      
      // Convert style config to real generation parameters
      const genParams = {
        prompt: styleConfig.basePrompt,
        negativePrompt: styleConfig.negatives.join(', '),
        count: req.count,
        seed: req.seed,
        sampler: styleConfig.sampler,
        cfg_scale: styleConfig.cfg,
        steps: styleConfig.steps
      };
      
      generatedImages = await realGen(genParams);
    } else {
      logger.info(`🔄 Using fake image generation`);
      generatedImages = await fakeGen(req.count, req.seed);
    }
    
    logger.info(`✅ Generated ${generatedImages.length} base images`);
    
    const processedImages: { url: string; seed: number; size: number }[] = [];
    
    for (let i = 0; i < generatedImages.length; i++) {
      const { buffer, seed } = generatedImages[i];
      logger.info(`🔄 Processing image ${i + 1}/${generatedImages.length} (seed: ${seed})`);
      
      // Process through polish pipeline
      const upscaledBuffer = cfg.MODE === "real" ? await realUpscale(buffer) : await fakeUpscale(buffer);
      const enhancedBuffer = cfg.MODE === "real" ? await realFace(upscaledBuffer) : await fakeFace(upscaledBuffer);
      
      // Save to vault
      const imagePath = await saveImage(styleDir, i + 1, enhancedBuffer);
      
      // Convert to file:// URL
      const imageUrl = `file://${path.resolve(imagePath)}`;
      
      processedImages.push({
        url: imageUrl,
        seed: seed,
        size: enhancedBuffer.length
      });
      
      logger.info(`✅ Saved image ${i + 1}: ${imagePath} (${enhancedBuffer.length} bytes)`);
    }
    
    // Step 5: Write manifest
    logger.info(`📄 Step 5: Writing manifest`);
    const manifestData = {
      persona_id: req.persona_id,
      job_id: jobId,
      style: req.style,
      count: req.count,
      seeds: processedImages.map(img => img.seed),
      tone: req.tone,
      slots: req.slots,
      styleConfig: {
        name: styleConfig.name,
        sampler: styleConfig.sampler,
        cfg: styleConfig.cfg,
        steps: styleConfig.steps
      },
      images: processedImages.map(img => ({
        url: img.url,
        seed: img.seed,
        size: img.size
      })),
      created_at: new Date().toISOString()
    };
    
    await writeManifest(styleDir, manifestData);
    logger.info(`✅ Manifest written`);
    
    // Step 6: Calculate metrics and return result
    const endTime = Date.now();
    const duration = endTime - startTime;
    const totalSize = processedImages.reduce((sum, img) => sum + img.size, 0);
    
    const result: GenerationResult = {
      jobId,
      style: req.style,
      images: processedImages.map(img => ({ url: img.url, seed: img.seed })),
      metrics: {
        duration,
        count: processedImages.length,
        totalSize
      }
    };
    
    logger.info(`🎉 Generation complete! Job ${jobId}: ${result.images.length} images in ${duration}ms (${totalSize} bytes total)`);
    return result;
    
  } catch (error) {
    const duration = Date.now() - startTime;
    logger.error(`❌ Generation failed after ${duration}ms:`, error);
    throw error;
  }
}