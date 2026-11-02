import { Button } from "@gravity-ui/uikit";
import { useState } from "react";

import {
  moderateGroup,
  recoverGroupLeadership,
} from "../../services/api/groupsApi";
import { ConfirmDialog } from "../ui/primitives";
import { GroupText } from "./GroupFields";
import useGroupAction from "./useGroupAction";

export default function GroupModeration({ group, onChanged }) {
  const [reason, setReason] = useState("");
  const [username, setUsername] = useState("");
  const [confirm, setConfirm] = useState(null);
  const action = useGroupAction(onChanged);
  return (
    <section className="hub-panel hub-form">
      <h2>Модерация платформы</h2>
      <p>
        Действия записываются в историю с основанием. Городские и серверные роли
        не изменяются.
      </p>
      <GroupText
        label="Основание"
        value={reason}
        onChange={setReason}
        multiline
        maxLength={500}
      />
      <Button
        disabled={!group.capabilities.write_enabled || reason.trim().length < 3}
        onClick={() => setConfirm("restriction")}
      >
        {group.restricted
          ? "Снять ограничение объединения"
          : "Ограничить объединение"}
      </Button>
      {group.restricted && (
        <>
          <h3>Восстановление руководства</h3>
          <p>
            Выберите участника или игрока, соответствующего условиям
            объединения. Он получит предложение в личном кабинете и должен
            принять его сам.
          </p>
          <GroupText
            label="Логин игрока"
            value={username}
            onChange={setUsername}
            maxLength={150}
          />
          <Button
            disabled={
              !group.capabilities.write_enabled ||
              reason.trim().length < 3 ||
              !username.trim()
            }
            onClick={() => setConfirm("recovery")}
          >
            Предложить восстановление
          </Button>
        </>
      )}
      <ConfirmDialog
        open={!!confirm}
        title={
          confirm === "recovery"
            ? "Отправить предложение руководства?"
            : group.restricted
              ? "Снять ограничение?"
              : "Ограничить объединение?"
        }
        onCancel={() => setConfirm(null)}
        loading={action.busy}
        onConfirm={() =>
          action.run(
            () =>
              confirm === "recovery"
                ? recoverGroupLeadership(group.slug, { username, reason })
                : moderateGroup(group.slug, {
                    restricted: !group.restricted,
                    reason,
                  }),
            "Решение сохранено",
            () => setConfirm(null),
          )
        }
      >
        <p>
          {confirm === "recovery"
            ? "После согласия получателя управление восстановится. Набор останется на паузе."
            : group.restricted
              ? "Для снятия ограничения нужен действующий руководитель. Приём участников останется на паузе."
              : "Объединение исчезнет из каталога. Вступления и обычное управление будут приостановлены, старые предложения утратят силу."}
        </p>
        <p>{reason}</p>
        {action.error && <p role="alert">{action.error}</p>}
      </ConfirmDialog>
    </section>
  );
}
