import { Button } from "@gravity-ui/uikit";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  applyToGroup,
  joinGroup,
  leaveGroup,
  setGroupVisibility,
} from "../../services/api/groupsApi";
import { ConfirmDialog } from "../ui/primitives";
import { GroupSelect, GroupText } from "./GroupFields";
import GroupProcessActions from "./GroupProcessActions";
import {
  groupModes,
  groupRoles,
  memberVisibility,
  processLabels,
} from "./labels";
import useGroupAction from "./useGroupAction";

export default function GroupParticipation({ group, onChanged }) {
  const { viewer, capabilities } = group;
  const [visibility, setVisibility] = useState(
    viewer.membership?.visibility || "private",
  );
  const [answer, setAnswer] = useState("");
  const [leaving, setLeaving] = useState(false);
  const navigate = useNavigate();
  const action = useGroupAction(onChanged);
  const incoming =
    viewer.leadership?.status === "pending"
      ? viewer.leadership
      : viewer.invitation?.status === "pending"
        ? viewer.invitation
        : viewer.request?.status === "pending"
          ? viewer.request
          : null;
  return (
    <section
      className="hub-panel hub-form"
      aria-labelledby="group-participation-title"
    >
      <h2 id="group-participation-title">
        {viewer.membership?.status === "active"
          ? "Ваше участие"
          : "Как присоединиться"}
      </h2>
      {group.status === "archived" && (
        <p>Объединение в архиве. Новые участники не принимаются.</p>
      )}
      {group.status === "draft" && (
        <p>
          Черновик виден только руководству. Перед публикацией настройте
          страницу и условия участия.
        </p>
      )}
      {group.restricted && <p>Действия в объединении ограничены платформой.</p>}
      {viewer.state === "scope_required" && (
        <p>
          Для вступления нужно участие в{" "}
          {group.scope?.name || "серверном сообществе"}.{" "}
          <Link
            to={
              group.scope
                ? `/communities/${group.scope.slug}`
                : "/account/communities"
            }
          >
            Открыть сообщество
          </Link>
        </p>
      )}
      {viewer.state === "restricted" && (
        <p>Ваше участие ограничено. Повторное вступление сейчас недоступно.</p>
      )}
      {incoming && (
        <GroupProcessActions
          process={incoming}
          group={group}
          writeEnabled={capabilities.write_enabled}
          onChanged={onChanged}
        />
      )}
      {viewer.state === "member" && (
        <>
          <p>{groupRoles[viewer.membership.role]}</p>
          <GroupSelect
            label="Кто видит моё участие"
            value={visibility}
            options={memberVisibility}
            onChange={setVisibility}
            disabled={!capabilities.write_enabled}
          />
          <Button
            disabled={
              !capabilities.write_enabled ||
              visibility === viewer.membership.visibility
            }
            loading={action.busy}
            onClick={() =>
              action.run(
                () => setGroupVisibility(group.slug, { visibility }),
                "Видимость участия сохранена",
              )
            }
          >
            Сохранить видимость
          </Button>
        </>
      )}
      {!incoming && viewer.state !== "member" && (
        <>
          <p>
            {groupModes[group.join_mode]}
            {!group.accepting && group.status === "active"
              ? " · набор на паузе"
              : ""}
          </p>
          {viewer.request && viewer.request.status !== "pending" && (
            <p>
              {processLabels[viewer.request.status]}
              {viewer.request.reason ? `: ${viewer.request.reason}` : ""}
            </p>
          )}
          {capabilities.join || capabilities.apply ? (
            <form
              className="hub-form"
              onSubmit={(event) => {
                event.preventDefault();
                action.run(
                  () =>
                    capabilities.join
                      ? joinGroup(group.slug, { visibility })
                      : applyToGroup(group.slug, { answer, visibility }),
                  capabilities.join
                    ? `Вы присоединились к «${group.name}»`
                    : "Заявка отправлена. Решение появится в ваших сообществах.",
                );
              }}
            >
              {capabilities.apply && (
                <GroupText
                  label={
                    group.application_question ||
                    "Сообщение организаторам (необязательно)"
                  }
                  value={answer}
                  onChange={setAnswer}
                  multiline
                  rows={3}
                  maxLength={1000}
                  required={!!group.application_question}
                />
              )}
              <GroupSelect
                label="Кто увидит моё участие"
                value={visibility}
                options={memberVisibility}
                onChange={setVisibility}
              />
              <p className="hub-muted">
                Руководство сможет видеть и управлять вашим участием. Это не
                меняет ваши города и доступ к серверу.
              </p>
              <Button type="submit" view="action" loading={action.busy}>
                {capabilities.join ? "Вступить" : "Отправить заявку"}
              </Button>
            </form>
          ) : (
            viewer.state === "guest" &&
            group.accepting &&
            group.join_mode !== "invite_only" && (
              <Link
                to={`/login?next=${encodeURIComponent(`/groups/${group.slug}`)}`}
              >
                Войти, чтобы присоединиться
              </Link>
            )
          )}
        </>
      )}
      {!capabilities.write_enabled && viewer.state !== "guest" && (
        <p className="hub-muted">Изменения временно приостановлены.</p>
      )}
      {capabilities.leave && (
        <Button view="flat-secondary" onClick={() => setLeaving(true)}>
          Выйти из объединения
        </Button>
      )}
      {action.error && <p role="alert">{action.error}</p>}
      <ConfirmDialog
        open={leaving}
        title={`Выйти из «${group.name}»?`}
        confirmText="Выйти из объединения"
        cancelText="Остаться"
        onCancel={() => setLeaving(false)}
        onConfirm={() =>
          action.run(
            () => leaveGroup(group.slug),
            "Вы вышли из объединения",
            () => navigate("/account/communities"),
          )
        }
        loading={action.busy}
      >
        <p>
          Закрытые материалы и участие станут недоступны. Ваши города, серверное
          участие и друзья сохранятся.
        </p>
        {viewer.membership?.role === "manager" && (
          <p>
            Если вы последний руководитель, сначала передайте роль или отправьте
            объединение в архив.
          </p>
        )}
        {action.error && <p role="alert">{action.error}</p>}
      </ConfirmDialog>
    </section>
  );
}
