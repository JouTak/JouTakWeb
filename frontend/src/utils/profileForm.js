export const PROFILE_FIELD_LABELS = Object.freeze({
  vk_username: "Username VK",
  minecraft_nick: "Ник Minecraft",
  minecraft_has_license: "Наличие лицензии Minecraft",
  is_itmo_student: "Статус студента ИТМО",
  itmo_isu: "Номер ИСУ",
});

export function boolToSelect(value) {
  if (value === true) return "true";
  if (value === false) return "false";
  return "";
}

export function selectToBool(value) {
  if (value === "true") return true;
  if (value === "false") return false;
  return null;
}
