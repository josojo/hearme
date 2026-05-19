// Pure validation for /ask. Kept in its own module so we can `import` it
// from non-server code (forms, tests) without falling under the
// "use server" rule that every export of a server-action module must be
// an async function.

export type CreateQuestionInput = {
  displayName: string;
  text: string;
  topic?: string | null;
  closesAt: Date;
};

const MAX_TEXT_LEN = 2000;
const MAX_TOPIC_LEN = 80;
const MAX_NAME_LEN = 80;

export function validateCreateQuestion(
  input: Partial<CreateQuestionInput>,
):
  | { ok: true; value: CreateQuestionInput }
  | { ok: false; errors: Record<string, string> } {
  const errors: Record<string, string> = {};

  const displayName = (input.displayName ?? "").trim();
  if (!displayName) {
    errors.displayName = "Display name is required.";
  } else if (displayName.length > MAX_NAME_LEN) {
    errors.displayName = `Display name must be ≤ ${MAX_NAME_LEN} characters.`;
  }

  const text = (input.text ?? "").trim();
  if (!text) {
    errors.text = "Question text is required.";
  } else if (text.length > MAX_TEXT_LEN) {
    errors.text = `Question must be ≤ ${MAX_TEXT_LEN} characters.`;
  }

  const topicRaw = (input.topic ?? "").toString().trim();
  const topic = topicRaw === "" ? null : topicRaw;
  if (topic && topic.length > MAX_TOPIC_LEN) {
    errors.topic = `Topic must be ≤ ${MAX_TOPIC_LEN} characters.`;
  }

  const closesAt = input.closesAt instanceof Date ? input.closesAt : null;
  if (!closesAt || Number.isNaN(closesAt.getTime())) {
    errors.closesAt = "A close time is required.";
  } else if (closesAt.getTime() <= Date.now()) {
    errors.closesAt = "Close time must be in the future.";
  }

  if (Object.keys(errors).length > 0) {
    return { ok: false, errors };
  }

  return {
    ok: true,
    value: {
      displayName,
      text,
      topic,
      closesAt: closesAt as Date,
    },
  };
}
