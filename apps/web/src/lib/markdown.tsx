import DOMPurify from 'dompurify'
import ReactMarkdown from 'react-markdown'

import { cn } from '@/lib/utils'

/**
 * Render untrusted / AI-authored Markdown safely (§7.7).
 *
 * react-markdown never injects raw HTML (no rehype-raw, no dangerouslySetInnerHTML);
 * as defense-in-depth we DOMPurify the source first to strip any embedded HTML/script,
 * leaving pure Markdown text for react-markdown to render.
 */
export function Markdown({ content, className }: { content: string; className?: string }) {
  const clean = DOMPurify.sanitize(content, { ALLOWED_TAGS: [], ALLOWED_ATTR: [] })
  return (
    <div
      className={cn(
        'text-sm leading-relaxed text-text-primary break-words',
        '[&_p]:my-1.5 [&_ul]:my-1.5 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:my-1.5 [&_ol]:list-decimal [&_ol]:pl-5',
        '[&_a]:text-brand-primary [&_a]:underline',
        '[&_code]:rounded [&_code]:bg-surface-secondary [&_code]:px-1 [&_code]:py-0.5 [&_code]:text-xs',
        '[&_h1]:mt-2 [&_h1]:mb-1 [&_h1]:text-base [&_h1]:font-semibold',
        '[&_h2]:mt-2 [&_h2]:mb-1 [&_h2]:text-sm [&_h2]:font-semibold',
        '[&_blockquote]:border-l-2 [&_blockquote]:border-border-default [&_blockquote]:pl-3 [&_blockquote]:text-text-secondary',
        className,
      )}
    >
      <ReactMarkdown>{clean}</ReactMarkdown>
    </div>
  )
}
