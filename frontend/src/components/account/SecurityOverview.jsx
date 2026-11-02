import "./security.css";

import { Button, Label } from "@gravity-ui/uikit";
import { useState } from "react";
import { FiKey, FiMonitor, FiShield } from "react-icons/fi";

import { HubPage } from "../hub/HubShell";
import DeleteAccountCard from "./DeleteAccountCard";
import EmailCard from "./EmailCard";
import MfaCard from "./MfaCard";
import OauthCard from "./OauthCard";
import PasswordCard from "./PasswordCard";
import SecurityAction from "./SecurityAction";
import SessionsCard from "./SessionsCard";

export default function SecurityOverview({
  profile,
  emailStatus,
  sessionsPayload,
  onRetry,
}) {
  const [email, setEmail] = useState(emailStatus);
  const [mfa, setMfa] = useState(profile.has_2fa);
  return (
    <HubPage
      title="Безопасность"
      intro="Управляйте входом в аккаунт и доступом с ваших устройств."
    >
      <div className="security-layout">
        <section className="security-card" aria-labelledby="security-login">
          <div className="security-card-heading">
            <FiKey aria-hidden="true" />
            <h2 id="security-login">Вход в аккаунт</h2>
          </div>
          {email ? (
            <SecurityAction
              id="email"
              title="Электронная почта"
              description={
                <>
                  <span>{email.email || "Адрес не указан"}</span>
                  {email.pending_email && (
                    <p>Ожидает подтверждения: {email.pending_email}</p>
                  )}
                </>
              }
              status={
                <Label theme={email.verified ? "success" : "warning"}>
                  {email.verified ? "Подтверждена" : "Нужно подтвердить"}
                </Label>
              }
              action="Настроить почту"
              collapse="Свернуть почту"
            >
              <EmailCard
                embedded
                initialStatus={email}
                onStatusChange={setEmail}
              />
            </SecurityAction>
          ) : (
            <div role="alert" className="security-action">
              <p>Не удалось загрузить данные почты.</p>
              <Button onClick={onRetry}>Повторить загрузку почты</Button>
            </div>
          )}
          <SecurityAction
            id="password"
            title="Пароль"
            description="Изменение пароля завершит вход на других устройствах."
            action="Изменить пароль"
            collapse="Свернуть пароль"
          >
            <PasswordCard
              embedded
              defaultOpen
              autoCloseOnSuccess={false}
              identityHint={profile.email || profile.username}
            />
          </SecurityAction>
          <SecurityAction
            id="linked"
            title="Связанные аккаунты"
            description="Вход через другие сервисы. Эти привязки видны только вам."
            action="Настроить привязки"
            collapse="Свернуть привязки"
          >
            <OauthCard embedded linkedProviders={profile.oauth_providers} />
          </SecurityAction>
        </section>
        <section
          className="security-card"
          aria-labelledby="security-protection"
        >
          <div className="security-card-heading">
            <FiShield aria-hidden="true" />
            <h2 id="security-protection">Защита при входе</h2>
          </div>
          <div className="security-protection-intro">
            <Label theme={mfa === true ? "success" : "normal"}>
              {mfa === true
                ? "Включена"
                : mfa === false
                  ? "Не подключена"
                  : "Статус недоступен"}
            </Label>
            <p>
              Подтверждайте вход кодом из приложения или ключом безопасности.
            </p>
            <ul className="security-methods">
              <li>Приложение-аутентификатор</li>
              <li>Ключи доступа и биометрия</li>
              <li>Резервные коды для восстановления</li>
            </ul>
          </div>
          <SecurityAction
            id="mfa"
            title="Дополнительная защита"
            action="Настроить защиту"
            collapse="Свернуть настройки защиты"
          >
            <MfaCard
              embedded
              profile={{
                ...profile,
                email_verified: email?.verified ?? profile.email_verified,
              }}
              onStatusChange={setMfa}
            />
          </SecurityAction>
        </section>
        <section
          className="security-card security-devices"
          aria-labelledby="security-devices"
        >
          <div className="security-card-heading">
            <FiMonitor aria-hidden="true" />
            <div>
              <h2 id="security-devices">Устройства и сеансы</h2>
              <p className="security-muted">
                Проверьте, где выполнен вход. Незнакомое устройство можно
                отключить.
              </p>
            </div>
          </div>
          {sessionsPayload ? (
            <SessionsCard embedded initialSessions={sessionsPayload} />
          ) : (
            <div role="alert" className="security-action">
              <p>Не удалось получить список устройств.</p>
              <Button onClick={onRetry}>Повторить загрузку устройств</Button>
            </div>
          )}
        </section>
        <section className="security-danger" aria-label="Удаление аккаунта">
          <SecurityAction
            id="delete"
            title="Удаление аккаунта"
            description="Профиль и доступ к аккаунту будут удалены. Это действие нельзя отменить."
            action="Перейти к удалению"
            collapse="Свернуть удаление"
          >
            <DeleteAccountCard embedded defaultOpen />
          </SecurityAction>
        </section>
      </div>
    </HubPage>
  );
}
