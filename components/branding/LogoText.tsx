import Image from "next/image";

interface LogoTextProps {
  /** Height in pixels - width scales proportionally */
  height?: number;
  /** Additional CSS classes */
  className?: string;
}

/**
 * LLMHive logo text as an image - matches the 3D metallic gold rendering exactly.
 * Use this instead of CSS-styled text for brand consistency.
 */
export default function LogoText({ height = 48, className = "" }: LogoTextProps) {
  // The original image aspect ratio (approximately 4:1 based on the provided image)
  const aspectRatio = 4;
  const width = height * aspectRatio;

  return (
    <Image
      src="/llmhive/logo-text.png"
      alt="LLMHive"
      width={width * 2}
      height={height * 2}
      className={`object-contain ${className}`}
      style={{ width: width, height: height }}
      quality={100}
      priority
      unoptimized
    />
  );
}

