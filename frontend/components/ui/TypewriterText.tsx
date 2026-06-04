import { useState, useRef, useEffect } from 'react';

export const TypewriterText = ({ content, speed = 15, onTyping }: { content: string, speed?: number, onTyping?: () => void }) => {
  const [displayedContent, setDisplayedContent] = useState('');
  const onTypingRef = useRef(onTyping);

  useEffect(() => {
    onTypingRef.current = onTyping;
  }, [onTyping]);
  
  useEffect(() => {
    let i = 0;
    setDisplayedContent('');
    const interval = setInterval(() => {
      setDisplayedContent(content.substring(0, i));
      if (onTypingRef.current) onTypingRef.current();
      i++;
      if (i > content.length) {
        clearInterval(interval);
      }
    }, speed);
    
    return () => clearInterval(interval);
  }, [content, speed]);

  return <span>{displayedContent}</span>;
};
