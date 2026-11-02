import { useToaster } from "@gravity-ui/uikit";
import { useState } from "react";

import { extractErrorMessage } from "../../services/errors";

export default function useGroupAction(onChanged) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const { add } = useToaster();
  async function run(work, title, done) {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      const result = await work();
      if (title)
        add({
          name: "group-action",
          title,
          theme: "success",
          autoHiding: 4000,
        });
      done?.(result);
      onChanged?.(result);
      return true;
    } catch (failure) {
      setError(extractErrorMessage(failure));
      return false;
    } finally {
      setBusy(false);
    }
  }
  return { busy, error, run };
}
