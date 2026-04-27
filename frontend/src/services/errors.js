export function extractErrorMessage(
  error,
  fallback = "Произошла ошибка. Попробуйте ещё раз.",
) {
  const data = error?.response?.data;
  if (!data) {
    return error?.message || fallback;
  }

  const fieldMessage = firstMessage(Object.values(data.fields || {}));
  if (fieldMessage) {
    return fieldMessage;
  }

  const structuredError = firstMessage(
    Array.isArray(data.errors)
      ? data.errors
      : Object.values(data.errors || {}).flat(),
  );
  if (structuredError) {
    return structuredError;
  }

  const detail = normalizeMessage(data.detail);
  if (detail && detail !== "validation_error") {
    return detail;
  }

  const message = normalizeMessage(data.message);
  if (message) {
    return message;
  }

  return fallback;
}

function firstMessage(values) {
  for (const value of values) {
    const message = normalizeMessage(value);
    if (message) {
      return message;
    }
  }
  return "";
}

function normalizeMessage(value) {
  if (typeof value === "string" && value.trim()) {
    return value;
  }
  if (Array.isArray(value)) {
    return firstMessage(value);
  }
  if (value && typeof value === "object") {
    return normalizeMessage(value.message);
  }
  return "";
}
