import React from 'react'
import { motion, useMotionValue, useMotionTemplate } from 'framer-motion'
import { cn } from '../lib/utils'

interface HeroHighlightProps {
  children: React.ReactNode
  className?: string
  containerClassName?: string
  showGradient?: boolean
}

export const HeroHighlight: React.FC<HeroHighlightProps> = ({
  children,
  className,
  containerClassName,
  showGradient = true,
}) => {
  const mouseX = useMotionValue(0)
  const mouseY = useMotionValue(0)

  function handleMouseMove({
    currentTarget,
    clientX,
    clientY,
  }: React.MouseEvent<HTMLDivElement>) {
    if (!currentTarget) return
    const { left, top } = currentTarget.getBoundingClientRect()
    mouseX.set(clientX - left)
    mouseY.set(clientY - top)
  }

  const dotPattern = (color: string) => ({
    backgroundImage: `radial-gradient(circle, ${color} 1px, transparent 1px)`,
    backgroundSize: '16px 16px',
  })

  // Detect if the container is intended to be dark based on classes passed
  const isDark = containerClassName?.includes('bg-black') || containerClassName?.includes('bg-slate-900')

  return (
    <div
      className={cn(
        'relative flex items-center justify-center w-full group transition-colors duration-500',
        isDark ? 'bg-black' : 'bg-white',
        containerClassName,
      )}
      onMouseMove={handleMouseMove}
    >
      {/* base dot pattern */}
      <div
        className="absolute inset-0 pointer-events-none opacity-70"
        style={dotPattern(isDark ? 'rgb(38 38 38)' : 'rgb(212 212 212)')}
      />

      {/* hover highlight mask */}
      {showGradient && (
        <motion.div
          className="pointer-events-none absolute inset-0 opacity-0 transition duration-300 group-hover:opacity-100"
          style={{
            ...dotPattern('rgb(99 102 241)'), // indigo-500
            WebkitMaskImage: useMotionTemplate`
              radial-gradient(
                200px circle at ${mouseX}px ${mouseY}px,
                black 0%,
                transparent 100%
              )
            `,
            maskImage: useMotionTemplate`
              radial-gradient(
                200px circle at ${mouseX}px ${mouseY}px,
                black 0%,
                transparent 100%
              )
            `,
          }}
        />
      )}

      <div className={cn('relative z-20', className)}>{children}</div>
    </div>
  )
}

interface HighlightProps {
  children: React.ReactNode
  className?: string
}

export const Highlight: React.FC<HighlightProps> = ({ children, className }) => {
  return (
    <motion.span
      initial={{
        backgroundSize: '0% 100%',
      }}
      animate={{
        backgroundSize: '100% 100%',
      }}
      transition={{
        duration: 2,
        ease: 'linear',
        delay: 0.5,
      }}
      style={{
        backgroundRepeat: 'no-repeat',
        backgroundPosition: 'left center',
        display: 'inline',
      }}
      className={cn(
        'relative inline-block pb-1 px-1 rounded-lg bg-gradient-to-r from-indigo-300 to-purple-300 dark:from-indigo-500 dark:to-purple-500',
        className,
      )}
    >
      {children}
    </motion.span>
  )
}