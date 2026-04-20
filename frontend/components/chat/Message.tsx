"use client";

import React, { useState } from 'react';
import { User, Bot, Clock, Lock, BookOpen, Link2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { QAMessage, AnswerSegment, EvidenceRef, GapStep, AuditSummary, SourceLink } from '@/lib/api';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';

interface MessageProps {
  message: QAMessage;
  isUser: boolean;
}

function segmentStyle(level: string): string {
  switch (level) {
    case 'grounded':
      return 'border-b-2 border-emerald-600/50 bg-emerald-500/10 decoration-emerald-700/80 dark:decoration-emerald-400';
    case 'inferred':
      return 'border-b-2 border-amber-500/50 bg-amber-500/10 decoration-amber-700/80 dark:decoration-amber-400';
    default:
      return 'border-b-2 border-red-500/45 bg-red-500/10 decoration-red-700/80 dark:decoration-red-400';
  }
}

function SegmentSpan({
  segment,
  idx,
  isActive,
  onGroundedClick,
}: {
  segment: AnswerSegment;
  idx: number;
  isActive: boolean;
  onGroundedClick: (idx: number) => void;
}) {
  const pct =
    segment.source_match_percent != null ? `${segment.source_match_percent}% match` : 'Match n/a';
  const label = segment.support_label_ui || segment.support_tier || segment.support_level;
  const excerpt = segment.evidence_refs?.[0]?.excerpt;
  const grounded = segment.support_level === 'grounded';

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          role={grounded ? 'button' : undefined}
          tabIndex={grounded ? 0 : undefined}
          onClick={() => grounded && onGroundedClick(idx)}
          onKeyDown={(e) => {
            if (grounded && (e.key === 'Enter' || e.key === ' ')) {
              e.preventDefault();
              onGroundedClick(idx);
            }
          }}
          className={`rounded-sm px-0.5 underline decoration-dotted decoration-2 underline-offset-4 ${segmentStyle(segment.support_level)} ${
            grounded ? 'cursor-pointer hover:opacity-90' : 'cursor-help'
          } ${isActive && grounded ? 'ring-2 ring-emerald-600/70 ring-offset-1 ring-offset-background' : ''}`}
        >
          {segment.text}{' '}
        </span>
      </TooltipTrigger>
      <TooltipContent side="top" className="space-y-1 text-left max-w-xs">
        <p className="font-medium">{label}</p>
        <p className="text-xs text-muted-foreground">{pct} (heuristic)</p>
        {segment.support_level === 'weak_support' ? (
          <p className="text-xs text-foreground/90 border-t border-border pt-1 mt-1">
            This claim was not found in your document. The AI is relying on general training data.
          </p>
        ) : null}
        {segment.support_level === 'inferred' ? (
          <p className="text-xs text-muted-foreground border-t border-border pt-1 mt-1">
            This part goes beyond a direct quote; check that the inference still matches your source.
          </p>
        ) : null}
        {grounded ? (
          <p className="text-xs text-muted-foreground">Click to verify against source excerpt below.</p>
        ) : null}
        {excerpt ? (
          <p className="text-xs opacity-90 line-clamp-4 border-t border-border pt-1 mt-1">
            {excerpt}
          </p>
        ) : null}
      </TooltipContent>
    </Tooltip>
  );
}

function VerificationPanel({
  sourceLinks,
  activeSegmentIndex,
}: {
  sourceLinks: SourceLink[];
  activeSegmentIndex: number | null;
}) {
  if (!sourceLinks.length) return null;
  return (
    <div className="rounded-md border border-emerald-600/35 bg-emerald-500/5 p-3 space-y-2">
      <p className="text-xs font-semibold text-emerald-900 dark:text-emerald-200 flex items-center gap-1">
        <Link2 className="h-3 w-3" />
        Verification — source links (grounded segments)
      </p>
      <p className="text-[10px] text-muted-foreground">
        Open your PDF to the page shown and compare the excerpt. In-app PDF highlight is not wired yet.
      </p>
      <ul className="space-y-2 text-xs">
        {sourceLinks.map((link, i) => {
          const active = activeSegmentIndex != null && link.segment_index === activeSegmentIndex;
          return (
            <li
              key={`${link.chunk_id ?? i}-${i}`}
              className={`border-l-2 pl-2 py-1 rounded-r ${
                active ? 'border-emerald-600 bg-emerald-500/15' : 'border-border'
              }`}
            >
              {link.page_number != null ? (
                <span className="font-medium text-foreground">Page {link.page_number}</span>
              ) : (
                <span className="text-muted-foreground">Page n/a</span>
              )}
              {link.chunk_id ? (
                <span className="text-muted-foreground ml-2">chunk {link.chunk_id}</span>
              ) : null}
              <p className="text-muted-foreground mt-1 whitespace-pre-wrap">{link.excerpt}</p>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function AuditedAssistantBody({
  segments,
  auditSummary,
  gapSteps,
  intuitionText,
}: {
  segments: AnswerSegment[];
  auditSummary?: AuditSummary | null;
  gapSteps?: GapStep[];
  intuitionText?: string | null;
}) {
  const [activeSegmentIndex, setActiveSegmentIndex] = useState<number | null>(null);
  const sourceLinks = auditSummary?.source_links ?? [];

  return (
    <div className="space-y-3">
      {intuitionText ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
          <div className="rounded-md border border-border bg-muted/40 p-3 space-y-1">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              Your intuition
            </p>
            <p className="text-foreground/90 whitespace-pre-wrap leading-relaxed">{intuitionText}</p>
          </div>
          <div className="rounded-md border border-border bg-card p-3 space-y-1">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              Model answer (audited)
            </p>
            <p className="text-[11px] text-muted-foreground leading-snug">
              Compare your hypothesis to the highlighted spans. Green is closest to the cited source.
            </p>
          </div>
        </div>
      ) : null}

      <div className="text-sm leading-relaxed">
        {segments.map((seg, i) => (
          <SegmentSpan
            key={i}
            segment={seg}
            idx={i}
            isActive={activeSegmentIndex === i}
            onGroundedClick={setActiveSegmentIndex}
          />
        ))}
      </div>

      <VerificationPanel sourceLinks={sourceLinks} activeSegmentIndex={activeSegmentIndex} />

      {auditSummary?.summary ? (
        <p className="text-xs text-muted-foreground border border-border/60 rounded-md px-2 py-1.5 bg-muted/30">
          <span className="font-medium text-foreground/80">Audit: </span>
          {auditSummary.summary}
        </p>
      ) : null}
      {gapSteps && gapSteps.length > 0 ? (
        <div className="text-xs space-y-1 border-t border-border pt-2">
          <p className="font-medium flex items-center gap-1">
            <BookOpen className="h-3 w-3" /> Reasoning steps
          </p>
          <ol className="list-decimal list-inside space-y-1 text-muted-foreground">
            {gapSteps.map((s) => (
              <li key={s.order}>{s.prompt}</li>
            ))}
          </ol>
        </div>
      ) : null}
    </div>
  );
}

function PendingReflectionBody({ message }: { message: QAMessage }) {
  const cue = message.metadata?.visible_cue as string | undefined;
  const hidden = message.metadata?.hidden_evidence_count as number | undefined;
  const refs = message.metadata?.visible_evidence_refs as EvidenceRef[] | undefined;

  return (
    <div className="space-y-3 rounded-md border border-amber-500/40 bg-amber-500/5 p-3">
      <div className="flex items-center gap-2 text-amber-800 dark:text-amber-200 text-sm font-medium">
        <Lock className="h-4 w-4 shrink-0" />
        Reflective gate — answer withheld until you prove engagement
      </div>
      {cue ? (
        <div className="text-sm">
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
            Cue from source
          </span>
          <p className="mt-1 italic text-foreground/90">{cue}</p>
        </div>
      ) : null}
      {refs && refs.length > 0 ? (
        <div className="text-xs text-muted-foreground">
          {refs[0]?.excerpt ? (
            <p className="line-clamp-3 border-l-2 border-border pl-2">{refs[0].excerpt}</p>
          ) : null}
        </div>
      ) : null}
      {hidden != null && hidden > 0 ? (
        <p className="text-xs text-muted-foreground">
          +{hidden} more evidence chunk{hidden === 1 ? '' : 's'} unlocked after your reflection
        </p>
      ) : null}
      <div className="text-sm prose prose-sm max-w-none dark:prose-invert pt-1 border-t border-border/50">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content || ''}</ReactMarkdown>
      </div>
    </div>
  );
}

export const Message: React.FC<MessageProps> = ({ message, isUser }) => {
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const isReflectionUser = message.metadata?.role === 'reflection';
  const assistantState = message.metadata?.response_state as string | undefined;
  const rawSegments = message.metadata?.answer_segments as AnswerSegment[] | undefined;
  const auditSummary = message.metadata?.audit_summary as AuditSummary | undefined;
  const gapSteps = message.metadata?.gap_steps as GapStep[] | undefined;
  const intuitionText = message.metadata?.intuition_text as string | undefined;

  const showPending = !isUser && assistantState === 'pending_reflection';
  const showAudited =
    !isUser &&
    assistantState === 'answered' &&
    Array.isArray(rawSegments) &&
    rawSegments.length > 0;

  const wideAudited = showAudited && !!intuitionText;

  return (
    <div className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 bg-accent rounded-full flex items-center justify-center">
          <Bot className="h-4 w-4 text-accent-foreground" />
        </div>
      )}

      <div
        className={`${wideAudited ? 'max-w-[min(96%,52rem)]' : 'max-w-[70%]'} p-4 rounded-lg ${
          isUser
            ? isReflectionUser
              ? 'bg-secondary text-secondary-foreground border border-border'
              : 'bg-accent text-accent-foreground'
            : 'bg-card text-card-foreground border border-border'
        }`}
      >
        <div className="space-y-2">
          {isReflectionUser ? (
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Your intuition
            </p>
          ) : null}

          {showPending ? (
            <PendingReflectionBody message={message} />
          ) : showAudited ? (
            <AuditedAssistantBody
              segments={rawSegments}
              auditSummary={auditSummary}
              gapSteps={gapSteps}
              intuitionText={intuitionText}
            />
          ) : (
            <div className="text-sm leading-relaxed prose prose-sm max-w-none dark:prose-invert">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  h1: ({ children }) => <h1 className="text-lg font-bold mb-2">{children}</h1>,
                  h2: ({ children }) => <h2 className="text-base font-semibold mb-2">{children}</h2>,
                  h3: ({ children }) => <h3 className="text-sm font-semibold mb-1">{children}</h3>,
                  ul: ({ children }) => (
                    <ul className="list-disc list-inside space-y-1 mb-2">{children}</ul>
                  ),
                  ol: ({ children }) => (
                    <ol className="list-decimal list-inside space-y-1 mb-2">{children}</ol>
                  ),
                  p: ({ children }) => <p className="mb-2">{children}</p>,
                  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                  em: ({ children }) => <em className="italic">{children}</em>,
                  code: ({ children, className }) => {
                    const isInline = !className;
                    if (isInline) {
                      return (
                        <code className="bg-muted px-1 py-0.5 rounded text-xs font-mono">
                          {children}
                        </code>
                      );
                    }
                    return (
                      <code className="block bg-muted p-2 rounded text-xs font-mono overflow-x-auto">
                        {children}
                      </code>
                    );
                  },
                  blockquote: ({ children }) => (
                    <blockquote className="border-l-4 border-border pl-4 italic text-muted-foreground">
                      {children}
                    </blockquote>
                  ),
                }}
              >
                {message.content || ''}
              </ReactMarkdown>
            </div>
          )}

          {!isUser && message.metadata?.rag_context && !showAudited && (
            <div className="mt-3 pt-3 border-t border-border/50">
              <p className="text-xs text-muted-foreground mb-1">Sources:</p>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">
                  • {(message.metadata.rag_context as { chunk_count?: number }).chunk_count ?? 0}{' '}
                  relevant sections found
                </p>
              </div>
            </div>
          )}

          <div className="flex items-center gap-1 text-xs opacity-60">
            <Clock className="h-3 w-3" />
            <span>{formatTime(message.timestamp)}</span>
          </div>
        </div>
      </div>

      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 bg-muted rounded-full flex items-center justify-center">
          <User className="h-4 w-4 text-muted-foreground" />
        </div>
      )}
    </div>
  );
};
