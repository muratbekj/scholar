import { QAMessage } from '@/lib/api';

/**
 * Active reflective gate: only when the **latest** message is a pending assistant turn.
 * (Older pending messages may remain in history after unlock; ignore them.)
 */
export function getPendingReflectionGate(messages: QAMessage[] | undefined): {
  pendingQuestionId: string;
  messageId: string;
} | null {
  if (!messages?.length) return null;
  const last = messages[messages.length - 1];
  if (last.type !== 'assistant') return null;
  if (last.metadata?.response_state !== 'pending_reflection') return null;
  const pendingQuestionId = last.metadata?.pending_question_id as string | undefined;
  if (!pendingQuestionId) return null;
  return { pendingQuestionId, messageId: last.id };
}
