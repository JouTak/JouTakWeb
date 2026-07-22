import { Button, Label, TextInput } from "@gravity-ui/uikit";
import PropTypes from "prop-types";

import { ConfirmDialog } from "../../ui/primitives";
import { blockStyle, formatTimestamp, rowBetweenStyle } from "./shared";

export default function PasskeysSection({
  webauthnAuthenticators,
  expanded,
  newPasskeyName,
  renamingId,
  renamingName,
  busyKey,
  deleteTarget,
  mfaBlocked,
  onExpand,
  onCollapse,
  onNewNameChange,
  onAdd,
  onStartRename,
  onRenamingNameChange,
  onConfirmRename,
  onCancelRename,
  onRequestDelete,
  onConfirmDelete,
  onCancelDelete,
}) {
  return (
    <>
      <div style={blockStyle}>
        <div style={rowBetweenStyle}>
          <h4 style={{ margin: 0, fontSize: 16 }}>Ключи безопасности</h4>
          {webauthnAuthenticators.length ? (
            <Label theme="success">{webauthnAuthenticators.length} шт.</Label>
          ) : null}
        </div>

        {expanded ? (
          <>
            <div style={{ opacity: 0.84 }}>
              Аппаратные ключи или биометрия устройства для быстрого и
              безопасного входа.
            </div>
            <div style={{ display: "grid", gap: 10, maxWidth: 420 }}>
              <TextInput
                size="l"
                label="Название нового ключа"
                value={newPasskeyName}
                onUpdate={onNewNameChange}
              />
              <Button
                view="action"
                loading={busyKey === "add-passkey"}
                onClick={onAdd}
                disabled={mfaBlocked}
              >
                Добавить ключ безопасности
              </Button>
            </div>
            {webauthnAuthenticators.length ? (
              <div style={{ display: "grid", gap: 10 }}>
                {webauthnAuthenticators.map((auth) => (
                  <div key={auth.id} style={blockStyle}>
                    <div style={rowBetweenStyle}>
                      <div style={{ display: "grid", gap: 6 }}>
                        <div
                          style={{
                            display: "flex",
                            gap: 8,
                            flexWrap: "wrap",
                          }}
                        >
                          <strong>{auth.name || `Ключ ${auth.id}`}</strong>
                          {auth.is_passwordless ? (
                            <Label theme="success">Passkey</Label>
                          ) : null}
                        </div>
                        <div style={{ opacity: 0.76, fontSize: 13 }}>
                          Последнее использование:{" "}
                          {formatTimestamp(auth.last_used_at)}
                        </div>
                      </div>
                      <div
                        style={{
                          display: "flex",
                          gap: 8,
                          flexWrap: "wrap",
                        }}
                      >
                        <Button
                          view="outlined"
                          onClick={() => onStartRename(auth)}
                          disabled={mfaBlocked}
                        >
                          Переименовать
                        </Button>
                        <Button
                          view="flat"
                          onClick={() => onRequestDelete(auth)}
                          disabled={mfaBlocked}
                        >
                          Удалить
                        </Button>
                      </div>
                    </div>
                    {renamingId === auth.id ? (
                      <div
                        style={{
                          display: "grid",
                          gap: 8,
                          maxWidth: 360,
                        }}
                      >
                        <TextInput
                          size="l"
                          value={renamingName}
                          onUpdate={onRenamingNameChange}
                        />
                        <div
                          style={{
                            display: "flex",
                            gap: 8,
                            flexWrap: "wrap",
                          }}
                        >
                          <Button
                            view="action"
                            loading={busyKey === `rename-passkey-${auth.id}`}
                            onClick={() => onConfirmRename(auth.id)}
                            disabled={mfaBlocked}
                          >
                            Сохранить
                          </Button>
                          <Button view="flat" onClick={onCancelRename}>
                            Отмена
                          </Button>
                        </div>
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
            ) : null}
            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <Button view="flat" onClick={onCollapse}>
                Свернуть
              </Button>
            </div>
          </>
        ) : (
          <div style={rowBetweenStyle}>
            <div style={{ opacity: 0.84 }}>
              Аппаратные ключи или биометрия для входа без ввода кода.
            </div>
            <Button view="outlined" onClick={onExpand}>
              Управление
            </Button>
          </div>
        )}
      </div>

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title="Удалить ключ безопасности?"
        confirmText="Удалить"
        cancelText="Отмена"
        loading={busyKey === `delete-passkey-${deleteTarget?.id}`}
        onConfirm={onConfirmDelete}
        onCancel={onCancelDelete}
      >
        {deleteTarget ? (
          <div>
            Ключ <strong>{deleteTarget.name || deleteTarget.id}</strong> больше
            нельзя будет использовать для подтверждения входа.
          </div>
        ) : (
          <div />
        )}
      </ConfirmDialog>
    </>
  );
}

PasskeysSection.propTypes = {
  webauthnAuthenticators: PropTypes.arrayOf(PropTypes.object).isRequired,
  expanded: PropTypes.bool.isRequired,
  newPasskeyName: PropTypes.string.isRequired,
  renamingId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  renamingName: PropTypes.string.isRequired,
  busyKey: PropTypes.string.isRequired,
  deleteTarget: PropTypes.object,
  mfaBlocked: PropTypes.bool.isRequired,
  onExpand: PropTypes.func.isRequired,
  onCollapse: PropTypes.func.isRequired,
  onNewNameChange: PropTypes.func.isRequired,
  onAdd: PropTypes.func.isRequired,
  onStartRename: PropTypes.func.isRequired,
  onRenamingNameChange: PropTypes.func.isRequired,
  onConfirmRename: PropTypes.func.isRequired,
  onCancelRename: PropTypes.func.isRequired,
  onRequestDelete: PropTypes.func.isRequired,
  onConfirmDelete: PropTypes.func.isRequired,
  onCancelDelete: PropTypes.func.isRequired,
};
