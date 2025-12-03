"use client";

import { animate } from "framer-motion";
import { useEffect, useState } from "react";

/**
 * Hook for animating text display with streaming support
 * @param text - The text to animate
 * @param delimiter - Split delimiter: "" for char-by-char, " " for word-by-word
 * @returns Animated portion of text
 */
export function useAnimatedText(text: string, delimiter: string = "") {
  const [cursor, setCursor] = useState(0);
  const [startingCursor, setStartingCursor] = useState(0);
  const [prevText, setPrevText] = useState(text);

  // Smart continuation: if new text starts with previous text, continue from current position
  if (prevText !== text) {
    setPrevText(text);
    setStartingCursor(text.startsWith(prevText) ? cursor : 0);
  }

  useEffect(() => {
    const parts = text.split(delimiter);
    const newParts = parts.length - startingCursor;
    
    // Calculate duration based on new content only
    const duration =
      delimiter === ""
        ? Math.min(newParts * 0.015, 2) // char: ~15ms per char, max 2s
        : delimiter === " "
          ? Math.min(newParts * 0.05, 1.5) // word: ~50ms per word, max 1.5s
          : Math.min(newParts * 0.1, 1); // chunk: ~100ms per chunk, max 1s

    const controls = animate(startingCursor, parts.length, {
      duration: Math.max(duration, 0.1), // minimum 100ms
      ease: "linear", // linear for consistent typing feel
      onUpdate(latest) {
        setCursor(Math.floor(latest));
      },
    });

    return () => controls.stop();
  }, [startingCursor, text, delimiter]);

  return text.split(delimiter).slice(0, cursor).join(delimiter);
}

/**
 * Animated text component with typewriter effect
 */
interface AnimatedTextProps {
  text: string;
  delimiter?: string;
  className?: string;
}

export function AnimatedText({
  text,
  delimiter = "",
  className,
}: AnimatedTextProps) {
  const animatedText = useAnimatedText(text, delimiter);
  return <span className={className}>{animatedText}</span>;
}

/**
 * Animated text with blinking cursor
 */
export function AnimatedTextWithCursor({
  text,
  delimiter = " ",
  className,
  isStreaming = false,
}: AnimatedTextProps & { isStreaming?: boolean }) {
  const animatedText = useAnimatedText(text, delimiter);
  const showCursor = isStreaming || animatedText.length < text.length;
  
  return (
    <span className={className}>
      {animatedText}
      {showCursor && (
        <span className="inline-block w-[2px] h-[1em] bg-neutral-400 ml-0.5 animate-pulse align-middle" />
      )}
    </span>
  );
}
