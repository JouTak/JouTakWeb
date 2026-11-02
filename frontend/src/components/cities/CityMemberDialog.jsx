import { Button } from "@gravity-ui/uikit";
import { useState } from "react";

import {
  removeCityMember,
  updateCityMember,
} from "../../services/api/citiesApi";
import { extractErrorMessage } from "../../services/errors";
import { getPlayerName } from "../../utils/playerIdentity";
import EditDialog from "../hub/EditDialog";
import { cityRoles } from "../hub/labels";
import { ConfirmDialog } from "../ui/primitives";
import { TextField } from "./CityEditorFields";
export default function CityMemberDialog({ member, city, onClose, onSaved }) {
  const [role, setRole] = useState(member.role);
  const [position, setPosition] = useState(member.position);
  const [action, setAction] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const dirty = role !== member.role || position !== member.position;
  const disabled =
    member.role === "manager" && !city.capabilities.assign_manager;
  async function confirm() {
    setBusy(true);
    setError("");
    try {
      if (action === "remove") await removeCityMember(city.slug, member.id);
      else await updateCityMember(city.slug, member.id, { role, position });
      onSaved();
      onClose();
    } catch (e) {
      setError(extractErrorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <EditDialog title={getPlayerName(member)} onClose={onClose} dirty={dirty}>
      <div className="hub-form">
        {disabled ? (
          <p>Назначение и снятие управляющих доступно модератору платформы.</p>
        ) : (
          <>
            <label>
              Права в городе
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                disabled={busy}
              >
                {Object.entries(cityRoles)
                  .filter(
                    ([v]) =>
                      v !== "manager" || city.capabilities.assign_manager,
                  )
                  .map(([v, label]) => (
                    <option key={v} value={v}>
                      {label}
                    </option>
                  ))}
              </select>
            </label>
            <p className="hub-muted">
              {role === "representative"
                ? "Может изменять описание, оформление и контакты города."
                : role === "manager"
                  ? "Может редактировать город, приглашать жителей и назначать представителей."
                  : "Участие в городе без доступа к редактированию."}
            </p>
            <TextField
              label="Должность · необязательно"
              value={position}
              onChange={setPosition}
              maxLength={100}
              placeholder="Например, архитектор"
            />
            <div className="hub-actions">
              <Button
                view="action"
                disabled={!dirty || busy}
                onClick={() => setAction("change")}
              >
                Сохранить
              </Button>
              <Button
                view="outlined-danger"
                disabled={busy}
                onClick={() => setAction("remove")}
              >
                Исключить из города
              </Button>
            </div>
          </>
        )}
        <ConfirmDialog
          open={!!action}
          title={
            action === "remove"
              ? `Исключить ${getPlayerName(member)}?`
              : `Изменить права ${getPlayerName(member)}?`
          }
          onCancel={() => setAction(null)}
          onConfirm={confirm}
          loading={busy}
        >
          <p>
            {action === "remove"
              ? "Участие и права в городе будут прекращены. Вернуться можно будет по новому приглашению."
              : `Пользователь получит роль «${cityRoles[role]}». Предыдущие права будут заменены.`}
          </p>
          {error && <p role="alert">{error}</p>}
        </ConfirmDialog>
      </div>
    </EditDialog>
  );
}
