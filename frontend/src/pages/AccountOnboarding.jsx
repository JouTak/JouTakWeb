import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Label, Loader, TextInput, useToaster } from "@gravity-ui/uikit";
import { me, updateProfile } from "../services/api";
import { isPersonalizedProfile } from "../utils/profileState";
import {
  boolToSelect,
  selectToBool,
  PROFILE_FIELD_LABELS,
} from "../utils/profileForm";

const cardStyle = {
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 12,
  padding: 20,
  display: "grid",
  gap: 16,
  maxWidth: 880,
  margin: "0 auto",
};

export default function AccountOnboarding() {
  const navigate = useNavigate();
  const { add } = useToaster();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [registrationCompleted, setRegistrationCompleted] = useState(false);
  const [profileComplete, setProfileComplete] = useState(false);
  const [missingFields, setMissingFields] = useState([]);

  const [vkUsername, setVkUsername] = useState("");
  const [minecraftNick, setMinecraftNick] = useState("");
  const [minecraftHasLicense, setMinecraftHasLicense] = useState("");
  const [isItmoStudent, setIsItmoStudent] = useState("");
  const [itmoIsu, setItmoIsu] = useState("");

  const isuRequired = isItmoStudent === "true";

  const redirectToSessionExpired = useCallback(() => {
    const params = new URLSearchParams({
      reason: "SESSION_UNAUTHORIZED",
      next: "/account/complete-profile",
    });
    navigate(`/session-expired?${params.toString()}`, { replace: true });
  }, [navigate]);

  const progress = useMemo(() => {
    let total = 4;
    let done = 0;
    if (vkUsername.trim()) done += 1;
    if (minecraftNick.trim()) done += 1;
    if (minecraftHasLicense !== "") done += 1;
    if (isItmoStudent !== "") {
      if (isItmoStudent === "true") {
        total += 1;
        if ((itmoIsu || "").trim()) done += 1;
      }
      done += 1;
    }
    return { done, total };
  }, [
    vkUsername,
    minecraftNick,
    minecraftHasLicense,
    isItmoStudent,
    itmoIsu,
  ]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const profile = await me();
      setRegistrationCompleted(isPersonalizedProfile(profile));
      setProfileComplete(profile?.profile_complete === true);
      setMissingFields(
        Array.isArray(profile?.missing_fields) ? profile.missing_fields : [],
      );
      setVkUsername(profile?.vk_username || "");
      setMinecraftNick(profile?.minecraft_nick || "");
      setMinecraftHasLicense(boolToSelect(profile?.minecraft_has_license));
      setIsItmoStudent(boolToSelect(profile?.is_itmo_student));
      setItmoIsu(profile?.itmo_isu || "");
    } catch (error) {
      if (error?.response?.status === 401) {
        redirectToSessionExpired();
        return;
      }
      add({
        name: "onboarding-load-error",
        title: "Ошибка",
        content: "Не удалось загрузить данные аккаунта",
        theme: "danger",
      });
    } finally {
      setLoading(false);
    }
  }, [add, redirectToSessionExpired]);

  useEffect(() => {
    load();
  }, [load]);

  async function onSave(event) {
    event.preventDefault();
    const vk = (vkUsername || "").trim();
    const mc = (minecraftNick || "").trim();
    const isu = (itmoIsu || "").trim();

    if (!vk || !mc || minecraftHasLicense === "" || isItmoStudent === "") {
      add({
        name: "onboarding-required-fields",
        title: "Проверьте форму",
        content: "Заполните все обязательные поля перед сохранением.",
        theme: "warning",
      });
      return;
    }
    if (!/^[A-Za-z0-9_]{3,16}$/.test(mc)) {
      add({
        name: "onboarding-minecraft-invalid",
        title: "Некорректный ник Minecraft",
        content: "Допустимы 3-16 символов: латиница, цифры и _",
        theme: "warning",
      });
      return;
    }
    if (isItmoStudent === "true" && !/^\d{5,20}$/.test(isu)) {
      add({
        name: "onboarding-isu-invalid",
        title: "Некорректный ИСУ",
        content: "Номер ИСУ должен содержать только цифры (5-20).",
        theme: "warning",
      });
      return;
    }

    setSaving(true);
    try {
      const payload = {
        vk_username: vk,
        minecraft_nick: mc,
        ...(minecraftHasLicense !== ""
          ? { minecraft_has_license: selectToBool(minecraftHasLicense) }
          : {}),
        ...(isItmoStudent !== ""
          ? { is_itmo_student: selectToBool(isItmoStudent) }
          : {}),
        ...(isItmoStudent === "true" ? { itmo_isu: isu } : {}),
      };
      const data = await updateProfile(payload);
      add({
        name: "onboarding-save",
        title: "Профиль",
        content: data?.message || "Данные сохранены",
        theme: "success",
      });
      await load();
    } catch (err) {
      const msg =
        err?.response?.data?.fields?.vk_username ||
        err?.response?.data?.fields?.minecraft_nick ||
        err?.response?.data?.fields?.itmo_isu ||
        err?.response?.data?.detail ||
        "Не удалось сохранить профиль";
      add({
        name: "onboarding-save-error",
        title: "Ошибка",
        content: String(msg),
        theme: "danger",
      });
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <section style={cardStyle}>
        <Loader size="m" />
      </section>
    );
  }

  return (
    <section style={cardStyle}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <h2 style={{ margin: 0 }}>Обязательная персонализация профиля</h2>
          <p style={{ margin: "8px 0 0", opacity: 0.85 }}>
            Мы обновили требования к данным профиля. Эти поля нужны для
            корректной работы функций системы и отображения аккаунта в
            интерфейсах.
          </p>
        </div>
        {registrationCompleted ? (
          <Label size="m" theme="success">
            Профиль персонализирован
          </Label>
        ) : (
          <Label size="m" theme="danger">
            Базовый аккаунт
          </Label>
        )}
      </div>

      {!registrationCompleted && (
        <div
          style={{
            border: "1px solid rgba(255, 163, 0, 0.45)",
            borderRadius: 10,
            padding: 12,
            background: "rgba(255, 163, 0, 0.12)",
          }}
        >
          <b>Что будет, если не заполнить?</b>
          <div style={{ marginTop: 6, opacity: 0.9 }}>
            Аккаунт останется в базовом режиме: часть функций будет
            недоступна, пока персонализация не завершена.
          </div>
        </div>
      )}

      {!profileComplete && missingFields.length > 0 && (
        <div
          style={{
            border: "1px solid rgba(255,85,85,0.45)",
            borderRadius: 10,
            padding: 12,
            background: "rgba(255,85,85,0.1)",
          }}
        >
          <b>Осталось заполнить:</b>{" "}
          {missingFields
            .map((field) => PROFILE_FIELD_LABELS[field] || field)
            .join(", ")}
        </div>
      )}

      <div style={{ opacity: 0.85 }}>
        Прогресс персонализации профиля: <b>{progress.done}</b> из{" "}
        <b>{progress.total}</b>
      </div>

      <form onSubmit={onSave} style={{ display: "grid", gap: 12 }}>
        <TextInput
          size="l"
          label="Username VK"
          value={vkUsername}
          onUpdate={setVkUsername}
          placeholder="Например, id123456 или username"
          required
        />

        <TextInput
          size="l"
          label="Ник в Minecraft"
          value={minecraftNick}
          onUpdate={setMinecraftNick}
          placeholder="Только латиница, цифры и _"
          required
        />

        <label style={{ display: "grid", gap: 6 }}>
          <span>Есть лицензия Minecraft?</span>
          <select
            className="form-select"
            value={minecraftHasLicense}
            onChange={(e) => setMinecraftHasLicense(e.target.value)}
            required
          >
            <option value="" disabled>
              Выберите вариант
            </option>
            <option value="true">Да</option>
            <option value="false">Нет</option>
          </select>
        </label>

        <label style={{ display: "grid", gap: 6 }}>
          <span>Вы студент ИТМО?</span>
          <select
            className="form-select"
            value={isItmoStudent}
            onChange={(e) => setIsItmoStudent(e.target.value)}
            required
          >
            <option value="" disabled>
              Выберите вариант
            </option>
            <option value="true">Да</option>
            <option value="false">Нет</option>
          </select>
        </label>

        {isuRequired && (
          <TextInput
            size="l"
            label="Номер ИСУ"
            value={itmoIsu}
            onUpdate={setItmoIsu}
            placeholder="Только цифры"
            required
          />
        )}

        <div style={{ display: "flex", gap: 8, justifyContent: "space-between", flexWrap: "wrap" }}>
          <Button view="outlined" onClick={() => navigate("/account/security")} type="button">
            Аккаунт и безопасность
          </Button>
          <Button view="action" type="submit" loading={saving}>
            Сохранить изменения
          </Button>
        </div>
      </form>
    </section>
  );
}
