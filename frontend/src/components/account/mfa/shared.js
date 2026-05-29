/**
 * Shared styles and utilities for MFA sub-components.
 */

export const rowBetweenStyle = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: 12,
  flexWrap: "wrap",
};

export const blockStyle = {
  border: "1px solid rgba(255,255,255,0.08)",
  borderRadius: 8,
  padding: 14,
  display: "grid",
  gap: 12,
};

export const warningBoxStyle = {
  border: "1px solid rgba(255, 163, 0, 0.45)",
  borderRadius: 8,
  padding: 12,
  background: "rgba(255, 163, 0, 0.12)",
  display: "grid",
  gap: 8,
};

export function formatTimestamp(value) {
  if (!value) return "Никогда";
  const date = new Date(Number(value) * 1000);
  if (Number.isNaN(date.getTime())) return "Никогда";
  return date.toLocaleString("ru-RU");
}
