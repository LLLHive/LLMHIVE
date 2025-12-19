"use client"

import { useEffect, useState } from "react"

/**
 * ForestBackground - Immersive forest scene with warm amber lighting
 * 
 * Features:
 * - Multi-layer gradient forest effect
 * - Animated fog/mist
 * - Light rays through trees
 * - Responsive and performant
 */
export function ForestBackground() {
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) return null

  return (
    <div className="forest-bg" aria-hidden="true">
      {/* Tree silhouettes layer */}
      <svg
        className="absolute inset-0 w-full h-full opacity-30"
        preserveAspectRatio="xMidYMax slice"
        viewBox="0 0 1920 1080"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Background trees - distant */}
        <path
          d="M0 1080V600C100 580 150 400 200 350C250 300 300 450 350 500C400 400 450 300 500 280C550 260 600 400 650 450C700 350 750 250 800 230C850 210 900 350 950 400C1000 300 1050 200 1100 180C1150 160 1200 300 1250 350C1300 250 1350 150 1400 130C1450 110 1500 250 1550 300C1600 200 1650 100 1700 80C1750 60 1800 200 1850 250C1900 150 1920 100 1920 100V1080H0Z"
          fill="url(#treesGradient)"
          opacity="0.4"
        />
        
        {/* Midground trees */}
        <path
          d="M0 1080V700C80 680 120 500 180 450C240 400 300 550 360 600C420 500 480 380 540 350C600 320 660 480 720 530C780 420 840 300 900 270C960 240 1020 400 1080 450C1140 340 1200 220 1260 190C1320 160 1380 320 1440 370C1500 260 1560 140 1620 110C1680 80 1740 240 1800 290C1860 180 1920 120 1920 120V1080H0Z"
          fill="url(#treesGradient)"
          opacity="0.6"
        />
        
        {/* Foreground trees - closest */}
        <path
          d="M0 1080V800C60 780 100 600 160 550C220 500 280 650 340 700C400 600 460 450 520 400C580 350 640 520 700 580C760 470 820 340 880 290C940 240 1000 420 1060 480C1120 360 1180 230 1240 180C1300 130 1360 310 1420 380C1480 260 1540 120 1600 70C1660 20 1720 200 1780 270C1840 150 1900 80 1920 60V1080H0Z"
          fill="url(#treesGradient)"
          opacity="0.8"
        />
        
        <defs>
          <linearGradient id="treesGradient" x1="960" y1="0" x2="960" y2="1080" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#0a1a0a" stopOpacity="0.9" />
            <stop offset="50%" stopColor="#0d1f0d" stopOpacity="0.95" />
            <stop offset="100%" stopColor="#050a05" stopOpacity="1" />
          </linearGradient>
        </defs>
      </svg>
      
      {/* Tall tree trunks */}
      <div className="absolute inset-0 pointer-events-none opacity-20">
        {[...Array(8)].map((_, i) => (
          <div
            key={i}
            className="absolute bottom-0 bg-gradient-to-t from-black/80 to-transparent"
            style={{
              left: `${10 + i * 12}%`,
              width: `${1.5 + Math.random()}%`,
              height: `${60 + Math.random() * 30}%`,
              transform: `translateX(-50%) skewX(${-2 + Math.random() * 4}deg)`,
            }}
          />
        ))}
      </div>
      
      {/* Ambient particles */}
      <div className="absolute inset-0 pointer-events-none">
        {[...Array(12)].map((_, i) => (
          <div
            key={i}
            className="absolute w-1 h-1 rounded-full bg-amber-400/30"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animation: `float-particle ${6 + Math.random() * 4}s ease-in-out infinite`,
              animationDelay: `${Math.random() * 5}s`,
            }}
          />
        ))}
      </div>
      
      <style jsx>{`
        @keyframes float-particle {
          0%, 100% { 
            transform: translate(0, 0) scale(1);
            opacity: 0.3;
          }
          50% { 
            transform: translate(${Math.random() > 0.5 ? '' : '-'}10px, -20px) scale(1.5);
            opacity: 0.6;
          }
        }
      `}</style>
    </div>
  )
}

/**
 * ForestBackgroundSimple - Lighter version for better performance
 */
export function ForestBackgroundSimple() {
  return (
    <div className="forest-bg" aria-hidden="true" />
  )
}

