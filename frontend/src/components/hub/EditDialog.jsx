import { Button, Dialog } from "@gravity-ui/uikit";
import { useState } from "react";

import { ConfirmDialog } from "../ui/primitives";

export default function EditDialog({
  title,
  children,
  dirty = false,
  busy = false,
  onClose,
}) {
  const [confirm, setConfirm] = useState(false);
  const close = () => {
    if (!busy) {
      if (dirty) setConfirm(true);
      else onClose();
    }
  };
  return (
    <>
      <Dialog open onClose={close} aria-label={title}>
        <Dialog.Header caption={title} />
        <Dialog.Body>
          <div className="hub-dialog">{children}</div>
        </Dialog.Body>
        <div className="hub-dialog-footer">
          <Button disabled={busy} onClick={close}>
            Закрыть
          </Button>
        </div>
      </Dialog>
      <ConfirmDialog
        open={confirm}
        title="Закрыть без сохранения?"
        confirmText="Закрыть без сохранения"
        onCancel={() => setConfirm(false)}
        onConfirm={onClose}
      >
        <p>Введённые изменения будут потеряны.</p>
      </ConfirmDialog>
    </>
  );
}
