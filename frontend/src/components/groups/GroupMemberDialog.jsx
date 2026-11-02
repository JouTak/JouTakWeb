import { useState } from "react";

import {
  changeGroupRole,
  offerGroupLeadership,
  removeGroupMember,
  restrictGroupMember,
} from "../../services/api/groupsApi";
import { getPlayerName } from "../../utils/playerIdentity";
import { ConfirmDialog } from "../ui/primitives";
import { GroupText } from "./GroupFields";
import useGroupAction from "./useGroupAction";

const operations = {
  moderator: [
    "Назначить модератором",
    "Участник сможет редактировать страницу, разбирать заявки и приглашать людей. Управление руководителями ему недоступно.",
  ],
  member: [
    "Снять полномочия",
    "Участник потеряет права управления. Его участие в объединении сохранится.",
  ],
  remove: [
    "Завершить участие",
    "Человек перестанет быть участником, но сможет вступить снова по действующим условиям.",
  ],
  restrict: [
    "Ограничить участие",
    "Участие завершится. Новые вступления, заявки и принятия приглашений будут недоступны до снятия ограничения.",
  ],
  restore: [
    "Снять ограничение",
    "Человек сможет вступить заново. Прежняя роль не восстановится автоматически.",
  ],
  offer: [
    "Предложить руководство",
    "Полномочия появятся только после согласия получателя. Вы сохраните свою роль.",
  ],
  transfer: [
    "Передать руководство",
    "После согласия получателя он станет руководителем, а вы — обычным участником. До этого ваши права сохраняются.",
  ],
};

export default function GroupMemberDialog({
  group,
  member,
  operation,
  onClose,
  onChanged,
}) {
  const [reason, setReason] = useState("");
  const [until, setUntil] = useState("");
  const action = useGroupAction(onChanged);
  const [title, explanation] = operations[operation];
  const needsReason =
    ["restrict", "restore"].includes(operation) ||
    (member.role === "manager" &&
      ["member", "moderator", "remove"].includes(operation));
  function submit() {
    const work = () => {
      if (["member", "moderator"].includes(operation))
        return changeGroupRole(group.slug, member.id, {
          role: operation,
          reason,
        });
      if (operation === "remove")
        return removeGroupMember(group.slug, member.id, { reason });
      if (["restrict", "restore"].includes(operation))
        return restrictGroupMember(group.slug, member.id, {
          active: operation === "restrict",
          reason,
          until: until ? new Date(until).toISOString() : null,
        });
      return offerGroupLeadership(group.slug, {
        membership_id: member.id,
        transfer: operation === "transfer",
      });
    };
    action.run(
      work,
      ["offer", "transfer"].includes(operation)
        ? "Предложение отправлено в личный кабинет"
        : "Участие обновлено",
      onClose,
    );
  }
  return (
    <ConfirmDialog
      open
      title={`${title}: ${getPlayerName(member)}?`}
      confirmText={title}
      onCancel={onClose}
      onConfirm={submit}
      loading={action.busy}
      disabled={needsReason && reason.trim().length < 3}
    >
      <p>{explanation}</p>
      {!["offer", "transfer"].includes(operation) && (
        <GroupText
          label={
            needsReason
              ? "Основание (обязательно)"
              : "Пояснение (необязательно)"
          }
          value={reason}
          onChange={setReason}
          multiline
          maxLength={500}
        />
      )}
      {operation === "restrict" && (
        <GroupText
          label="До (необязательно, иначе бессрочно)"
          type="datetime-local"
          value={until}
          onChange={setUntil}
        />
      )}
      {action.error && <p role="alert">{action.error}</p>}
    </ConfirmDialog>
  );
}
