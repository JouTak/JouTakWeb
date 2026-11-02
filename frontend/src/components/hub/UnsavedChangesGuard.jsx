import { useCallback } from "react";
import { useBeforeUnload, useBlocker } from "react-router-dom";

import { ConfirmDialog } from "../ui/primitives";

export default function UnsavedChangesGuard({ dirty }) {
  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      dirty &&
      (currentLocation.pathname !== nextLocation.pathname ||
        currentLocation.search !== nextLocation.search),
  );
  useBeforeUnload(
    useCallback(
      (event) => {
        if (dirty) {
          event.preventDefault();
          event.returnValue = "";
        }
      },
      [dirty],
    ),
  );
  return (
    <ConfirmDialog
      open={blocker.state === "blocked"}
      title="Покинуть страницу без сохранения?"
      confirmText="Уйти без сохранения"
      cancelText="Остаться"
      onCancel={() => blocker.reset?.()}
      onConfirm={() => blocker.proceed?.()}
    >
      <p>
        Несохранённые изменения будут потеряны. Останьтесь, чтобы сохранить их.
      </p>
    </ConfirmDialog>
  );
}
