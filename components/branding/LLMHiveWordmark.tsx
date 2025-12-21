// components/branding/LLMHiveWordmark.tsx
import Image from 'next/image';
import clsx from 'clsx';

type Variant = 'hero' | 'title' | 'nav';

const files = {
  hero: { src: '/brand/llmhive-wordmark-hero.png', width: 3000, height: 700, priority: true },
  title:{ src: '/brand/llmhive-wordmark-title.png', width: 1600, height: 350, priority: false },
  nav:  { src: '/brand/llmhive-wordmark-nav.png', width: 700,  height: 150, priority: false },
};

export default function LLMHiveWordmark({ variant, className = '' }: { variant: Variant; className?: string }) {
  const { src, width, height, priority } = files[variant];
  return (
    <Image
      src={src}
      alt="LLMHive"
      width={width}
      height={height}
      priority={priority}
      className={clsx('select-none', className)}
    />
  );
}
