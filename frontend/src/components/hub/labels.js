export const cityRoles = {
  resident: "Житель",
  representative: "Представитель",
  manager: "Управляющий",
};
export const communityRoles = {
  member: "Участник",
  moderator: "Модератор сообщества",
  admin: "Администратор сообщества",
};
export const recruitmentLabels = {
  open: "Открыт для жителей",
  limited: "Ограниченный набор",
  closed: "Набор закрыт",
};
export const cityStatuses = {
  active: "Опубликован",
  draft: "Черновик",
  archived: "В архиве",
};
export const visibilityLabels = {
  public: "Все посетители",
  community: "Участники общих серверов",
  private: "Только я",
};
export const memberStatuses = {
  active: "Активное участие",
  pending: "Ожидает",
  left: "Участие завершено",
  removed: "Исключён",
  suspended: "Приостановлено",
};
export const formatDate = (value) =>
  value ? new Date(value).toLocaleDateString("ru-RU") : "Не указано";

export const formatDateTime = (value) =>
  value
    ? new Date(value).toLocaleString("ru-RU", {
        dateStyle: "short",
        timeStyle: "short",
      })
    : "Не указано";
