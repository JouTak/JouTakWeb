import "./security.css";

import { Skeleton } from "@gravity-ui/uikit";

import { HubPage } from "../hub/HubShell";

export default function AccountSecuritySkeleton() {
  return (
    <HubPage
      title="Безопасность"
      intro="Управляйте входом в аккаунт и доступом с ваших устройств."
    >
      <div
        className="security-layout"
        aria-busy="true"
        aria-label="Загрузка настроек безопасности"
      >
        {[0, 1, 2].map((n) => (
          <div
            key={n}
            className={`security-card security-skeleton ${n === 2 ? "security-devices" : ""}`}
          >
            <Skeleton style={{ width: "60%", height: 24 }} />
            <Skeleton style={{ width: "100%", height: 70 }} />
            <Skeleton style={{ width: "80%", height: 20 }} />
          </div>
        ))}
      </div>
    </HubPage>
  );
}
