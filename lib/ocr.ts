/**
 * OCR Utility for LLMHive
 * 
 * This module provides image text extraction capabilities.
 * It uses a multi-strategy approach:
 * 1. Client-side image preprocessing for better AI analysis
 * 2. Sends the image to the AI with OCR instructions
 * 
 * For production, consider integrating with:
 * - Google Cloud Vision API
 * - AWS Textract
 * - Azure Computer Vision
 * - Tesseract.js (client-side, but heavy)
 */

export interface OCRResult {
  text: string
  confidence: number
  language?: string
  regions?: OCRRegion[]
  processingTime: number
}

export interface OCRRegion {
  text: string
  boundingBox: {
    x: number
    y: number
    width: number
    height: number
  }
}

export interface ImageAnalysis {
  dataUrl: string
  width: number
  height: number
  aspectRatio: number
  isDocument: boolean
  hasText: boolean
  dominantColors: string[]
  brightness: number
  contrast: number
}

/**
 * Preprocess image for better OCR results
 * Applies contrast enhancement and noise reduction
 */
export async function preprocessImage(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('2d')
    
    if (!ctx) {
      reject(new Error('Canvas context not available'))
      return
    }

    img.onload = () => {
      // Set canvas size (limit max size for performance)
      const maxDimension = 2048
      let width = img.width
      let height = img.height
      
      if (width > maxDimension || height > maxDimension) {
        if (width > height) {
          height = (height / width) * maxDimension
          width = maxDimension
        } else {
          width = (width / height) * maxDimension
          height = maxDimension
        }
      }
      
      canvas.width = width
      canvas.height = height
      
      // Draw original image
      ctx.drawImage(img, 0, 0, width, height)
      
      // Get image data for processing
      const imageData = ctx.getImageData(0, 0, width, height)
      const data = imageData.data
      
      // Enhance contrast for text visibility
      const factor = 1.3 // Contrast factor
      const intercept = 128 * (1 - factor)
      
      for (let i = 0; i < data.length; i += 4) {
        // Convert to grayscale for text detection
        const gray = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2]
        
        // Apply contrast enhancement
        const enhanced = Math.min(255, Math.max(0, factor * gray + intercept))
        
        // Keep as color but with enhanced contrast
        data[i] = Math.min(255, Math.max(0, factor * data[i] + intercept))
        data[i + 1] = Math.min(255, Math.max(0, factor * data[i + 1] + intercept))
        data[i + 2] = Math.min(255, Math.max(0, factor * data[i + 2] + intercept))
      }
      
      ctx.putImageData(imageData, 0, 0)
      
      // Convert to data URL with high quality
      resolve(canvas.toDataURL('image/jpeg', 0.95))
    }
    
    img.onerror = () => reject(new Error('Failed to load image'))
    
    // Load image from file
    const reader = new FileReader()
    reader.onload = () => {
      img.src = reader.result as string
    }
    reader.onerror = () => reject(new Error('Failed to read file'))
    reader.readAsDataURL(file)
  })
}

/**
 * Analyze image properties for better OCR prompting
 */
export async function analyzeImage(file: File): Promise<ImageAnalysis> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('2d')
    
    if (!ctx) {
      reject(new Error('Canvas context not available'))
      return
    }
    
    const reader = new FileReader()
    reader.onload = () => {
      const dataUrl = reader.result as string
      img.src = dataUrl
      
      img.onload = () => {
        const width = img.width
        const height = img.height
        const aspectRatio = width / height
        
        // Sample a smaller version for analysis
        const sampleSize = 100
        canvas.width = sampleSize
        canvas.height = sampleSize
        ctx.drawImage(img, 0, 0, sampleSize, sampleSize)
        
        const imageData = ctx.getImageData(0, 0, sampleSize, sampleSize)
        const data = imageData.data
        
        // Calculate brightness and contrast
        let totalBrightness = 0
        let minBrightness = 255
        let maxBrightness = 0
        const colorCounts: Record<string, number> = {}
        
        for (let i = 0; i < data.length; i += 4) {
          const brightness = (data[i] + data[i + 1] + data[i + 2]) / 3
          totalBrightness += brightness
          minBrightness = Math.min(minBrightness, brightness)
          maxBrightness = Math.max(maxBrightness, brightness)
          
          // Track dominant colors (simplified)
          const colorKey = `${Math.round(data[i] / 32) * 32},${Math.round(data[i + 1] / 32) * 32},${Math.round(data[i + 2] / 32) * 32}`
          colorCounts[colorKey] = (colorCounts[colorKey] || 0) + 1
        }
        
        const pixelCount = data.length / 4
        const avgBrightness = totalBrightness / pixelCount
        const contrast = maxBrightness - minBrightness
        
        // Get dominant colors
        const sortedColors = Object.entries(colorCounts)
          .sort((a, b) => b[1] - a[1])
          .slice(0, 3)
          .map(([color]) => `rgb(${color})`)
        
        // Heuristics for document detection
        const isDocument = aspectRatio > 0.6 && aspectRatio < 1.5 && contrast > 100
        const hasText = contrast > 80 && avgBrightness > 100
        
        resolve({
          dataUrl,
          width,
          height,
          aspectRatio,
          isDocument,
          hasText,
          dominantColors: sortedColors,
          brightness: avgBrightness / 255,
          contrast: contrast / 255,
        })
      }
      
      img.onerror = () => reject(new Error('Failed to load image for analysis'))
    }
    
    reader.onerror = () => reject(new Error('Failed to read file'))
    reader.readAsDataURL(file)
  })
}

/**
 * Generate an optimized prompt for OCR based on image analysis
 */
export function generateOCRPrompt(analysis: ImageAnalysis): string {
  let prompt = "Please analyze this image and extract all visible text. "
  
  if (analysis.isDocument) {
    prompt += "This appears to be a document. "
    prompt += "Please preserve the formatting and structure of the text as much as possible. "
    prompt += "Include headings, paragraphs, lists, and any other structural elements. "
  }
  
  if (analysis.hasText) {
    prompt += "Focus on accurately transcribing all text content. "
    prompt += "If there are any unclear or partially visible words, indicate them with [unclear]. "
  }
  
  prompt += "If the image contains tables or structured data, please format them clearly. "
  prompt += "If there are any handwritten notes, do your best to transcribe them. "
  
  return prompt
}

/**
 * Main OCR function that preprocesses and prepares the image for AI analysis
 */
export async function processImageForOCR(file: File): Promise<{
  processedDataUrl: string
  analysis: ImageAnalysis
  suggestedPrompt: string
}> {
  const startTime = performance.now()
  
  // Analyze the image first
  const analysis = await analyzeImage(file)
  
  // Preprocess for better results
  const processedDataUrl = await preprocessImage(file)
  
  // Generate optimized prompt
  const suggestedPrompt = generateOCRPrompt(analysis)
  
  const processingTime = performance.now() - startTime
  console.log(`[OCR] Image preprocessing completed in ${processingTime.toFixed(0)}ms`)
  
  return {
    processedDataUrl,
    analysis,
    suggestedPrompt,
  }
}

