import {
  Button,
  Dialog,
  TextInput,
  Tooltip,
  useToaster,
} from "@gravity-ui/uikit";
import { useState } from "react";
import { FiLink } from "react-icons/fi";

export default function ShareProfileButton({ username }) {
  const { add } = useToaster();
  const [fallback, setFallback] = useState(false);
  const url = `${window.location.origin}/u/${encodeURIComponent(username)}`;
  async function share() {
    try {
      await navigator.clipboard.writeText(url);
      add({
        name: "profile-link",
        title: "Ссылка скопирована",
        theme: "success",
        autoHiding: 2500,
      });
    } catch {
      setFallback(true);
    }
  }
  return (
    <>
      <Tooltip content="Скопировать ссылку на профиль">
        <Button
          view="flat-secondary"
          size="l"
          extraProps={{ "aria-label": "Поделиться профилем" }}
          onClick={share}
        >
          <FiLink size={20} aria-hidden="true" />
        </Button>
      </Tooltip>
      <Dialog
        open={fallback}
        onClose={() => setFallback(false)}
        aria-label="Ссылка на профиль"
      >
        <Dialog.Header caption="Ссылка на профиль" />
        <Dialog.Body>
          <p>
            Не удалось скопировать автоматически. Выделите адрес и скопируйте
            его.
          </p>
          <TextInput
            value={url}
            controlProps={{ readOnly: true, "aria-label": "Адрес профиля" }}
          />
        </Dialog.Body>
        <Dialog.Footer
          onClickButtonApply={() => setFallback(false)}
          textButtonApply="Готово"
        />
      </Dialog>
    </>
  );
}
