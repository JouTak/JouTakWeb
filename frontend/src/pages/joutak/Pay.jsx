import "./pay.css";

import { Button, Loader } from "@gravity-ui/uikit";
import { useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  PageActions,
  PageNotice,
  PagePanel,
  PageShell,
} from "../../components/ui/PageShell.jsx";
import { useThemePreference } from "../../theme/themeContext.js";

const PAYMENT_FORM_URL = "https://forms.yandex.ru/u/6515e3dcd04688fca3cc271b";

export default function Pay() {
  const navigate = useNavigate();
  const { theme } = useThemePreference();
  const [loadedFrameUrl, setLoadedFrameUrl] = useState("");
  const isFirstFrameLoad = useRef(true);
  const iframeUrl = useMemo(
    () => `${PAYMENT_FORM_URL}?iframe=1&theme=${theme}`,
    [theme],
  );
  const frameReady = loadedFrameUrl === iframeUrl;

  function handleFrameLoad() {
    setLoadedFrameUrl(iframeUrl);
    if (isFirstFrameLoad.current) {
      isFirstFrameLoad.current = false;
      requestAnimationFrame(() =>
        window.scrollTo({ top: 0, behavior: "auto" }),
      );
    }
  }

  return (
    <PageShell
      eyebrow="JouTak SMP"
      title="Оплата доступа"
      description="JouTak существует на взносы игроков: деньги идут на хостинг и поддержку сервера, а не на игровые преимущества."
    >
      <PagePanel className="pay-intro">
        <div>
          <h2>Как устроен взнос</h2>
          <p>
            Можно выбрать любую сумму не ниже минимальной. Чем устойчивее общий
            ежемесячный сбор, тем надёжнее работает сервер. Дополнительная
            оплата не даёт привилегий и не влияет на игровой баланс.
          </p>
        </div>
        <PageActions>
          <Button view="outlined" size="l" onClick={() => navigate("/joutak")}>
            Вернуться к серверу
          </Button>
          <a
            className="pay-external-link"
            href={PAYMENT_FORM_URL}
            target="_blank"
            rel="noopener noreferrer"
          >
            Открыть форму отдельно ↗
          </a>
        </PageActions>
      </PagePanel>

      <PagePanel className="pay-form-panel">
        <div className="pay-form-heading">
          <div>
            <h2>Форма оплаты</h2>
            <p>
              Форма откроется ниже. Если браузер блокирует встроенный контент,
              используй ссылку «Открыть форму отдельно».
            </p>
          </div>
          <PageNotice tone="info">
            Платёж оформляется на защищённой странице Яндекс Форм.
          </PageNotice>
        </div>

        <div className="pay-frame-shell" aria-busy={!frameReady}>
          {!frameReady && (
            <div className="pay-frame-loading" aria-live="polite">
              <Loader size="l" />
              <span>Загружаем защищённую форму…</span>
            </div>
          )}
          <iframe
            className="pay"
            src={iframeUrl}
            name="ya-form-6515e3dcd04688fca3cc271b"
            title="Форма оплаты JouTak"
            loading="lazy"
            referrerPolicy="strict-origin-when-cross-origin"
            sandbox="allow-forms allow-popups allow-same-origin allow-scripts"
            onLoad={handleFrameLoad}
          />
        </div>
      </PagePanel>
    </PageShell>
  );
}
