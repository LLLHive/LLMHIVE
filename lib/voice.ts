/**
 * Voice Input Utility for LLMHive
 * 
 * Provides advanced speech recognition with:
 * - Real-time transcription
 * - Audio level visualization
 * - Language detection
 * - Continuous listening mode
 */

// Type declarations for Web Speech API
interface SpeechRecognitionEvent extends Event {
  resultIndex: number
  results: SpeechRecognitionResultList
}

interface SpeechRecognitionErrorEvent extends Event {
  error: string
}

interface SpeechRecognition extends EventTarget {
  continuous: boolean
  interimResults: boolean
  lang: string
  start(): void
  stop(): void
  onresult: ((event: SpeechRecognitionEvent) => void) | null
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null
  onstart: (() => void) | null
  onend: (() => void) | null
}

interface SpeechRecognitionConstructor {
  new (): SpeechRecognition
}

declare global {
  interface Window {
    SpeechRecognition: SpeechRecognitionConstructor
    webkitSpeechRecognition: SpeechRecognitionConstructor
  }
}

export interface VoiceRecognitionOptions {
  continuous?: boolean
  interimResults?: boolean
  language?: string
  onResult?: (transcript: string, isFinal: boolean) => void
  onError?: (error: string) => void
  onStart?: () => void
  onEnd?: () => void
  onAudioLevel?: (level: number) => void
}

export interface VoiceRecognitionState {
  isListening: boolean
  transcript: string
  interimTranscript: string
  audioLevel: number
  error: string | null
}

class VoiceRecognitionManager {
  private recognition: SpeechRecognition | null = null
  private audioContext: AudioContext | null = null
  private analyser: AnalyserNode | null = null
  private microphone: MediaStreamAudioSourceNode | null = null
  private mediaStream: MediaStream | null = null
  private animationFrame: number | null = null
  private isSupported: boolean = false

  constructor() {
    if (typeof window !== 'undefined') {
      const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition
      this.isSupported = !!SpeechRecognitionAPI
    }
  }

  public get supported(): boolean {
    return this.isSupported
  }

  public async start(options: VoiceRecognitionOptions = {}): Promise<void> {
    if (!this.isSupported) {
      options.onError?.('Speech recognition is not supported in this browser')
      return
    }

    try {
      // Request microphone access
      this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true })
      
      // Set up audio analysis for level monitoring
      this.audioContext = new AudioContext()
      this.analyser = this.audioContext.createAnalyser()
      this.analyser.fftSize = 256
      this.microphone = this.audioContext.createMediaStreamSource(this.mediaStream)
      this.microphone.connect(this.analyser)

      // Start audio level monitoring
      if (options.onAudioLevel) {
        this.startAudioLevelMonitoring(options.onAudioLevel)
      }

      // Initialize speech recognition
      const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition
      this.recognition = new SpeechRecognitionAPI()
      
      this.recognition.continuous = options.continuous ?? true
      this.recognition.interimResults = options.interimResults ?? true
      this.recognition.lang = options.language ?? 'en-US'

      this.recognition.onstart = () => {
        options.onStart?.()
      }

      this.recognition.onresult = (event: SpeechRecognitionEvent) => {
        let interimTranscript = ''
        let finalTranscript = ''

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const result = event.results[i]
          if (result.isFinal) {
            finalTranscript += result[0].transcript
          } else {
            interimTranscript += result[0].transcript
          }
        }

        if (finalTranscript) {
          options.onResult?.(finalTranscript, true)
        } else if (interimTranscript) {
          options.onResult?.(interimTranscript, false)
        }
      }

      this.recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
        let errorMessage = 'Speech recognition error'
        
        switch (event.error) {
          case 'not-allowed':
            errorMessage = 'Microphone access denied. Please enable microphone permissions.'
            break
          case 'no-speech':
            errorMessage = 'No speech detected. Please try again.'
            break
          case 'audio-capture':
            errorMessage = 'No microphone found. Please check your audio settings.'
            break
          case 'network':
            errorMessage = 'Network error. Please check your connection.'
            break
          case 'aborted':
            errorMessage = 'Speech recognition was aborted.'
            break
          default:
            errorMessage = `Speech recognition error: ${event.error}`
        }
        
        options.onError?.(errorMessage)
      }

      this.recognition.onend = () => {
        options.onEnd?.()
      }

      this.recognition.start()
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to start voice recognition'
      options.onError?.(errorMessage)
      this.stop()
    }
  }

  private startAudioLevelMonitoring(callback: (level: number) => void): void {
    if (!this.analyser) return

    const dataArray = new Uint8Array(this.analyser.frequencyBinCount)

    const updateLevel = () => {
      if (!this.analyser) return

      this.analyser.getByteFrequencyData(dataArray)
      
      // Calculate average volume level
      let sum = 0
      for (let i = 0; i < dataArray.length; i++) {
        sum += dataArray[i]
      }
      const average = sum / dataArray.length
      const normalizedLevel = Math.min(1, average / 128)
      
      callback(normalizedLevel)
      
      this.animationFrame = requestAnimationFrame(updateLevel)
    }

    updateLevel()
  }

  public stop(): void {
    // Stop animation frame
    if (this.animationFrame) {
      cancelAnimationFrame(this.animationFrame)
      this.animationFrame = null
    }

    // Stop speech recognition
    if (this.recognition) {
      try {
        this.recognition.stop()
      } catch {
        // Ignore errors when stopping
      }
      this.recognition = null
    }

    // Clean up audio context
    if (this.microphone) {
      this.microphone.disconnect()
      this.microphone = null
    }
    
    if (this.audioContext) {
      this.audioContext.close()
      this.audioContext = null
    }

    // Stop media stream
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach(track => track.stop())
      this.mediaStream = null
    }

    this.analyser = null
  }

  public get isActive(): boolean {
    return this.recognition !== null
  }
}

// Singleton instance
export const voiceRecognition = new VoiceRecognitionManager()

/**
 * Hook-friendly voice recognition utilities
 */
export function createVoiceSession(options: VoiceRecognitionOptions) {
  return {
    start: () => voiceRecognition.start(options),
    stop: () => voiceRecognition.stop(),
    isSupported: voiceRecognition.supported,
    isActive: () => voiceRecognition.isActive,
  }
}

