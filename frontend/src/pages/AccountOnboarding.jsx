import {
  Button,
  Label,
  Loader,
  TextInput,
  useToaster,
} from "@gravity-ui/uikit";
import PropTypes from "prop-types";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { me, updateProfile } from "../services/api";
import {
  boolToSelect,
  PROFILE_FIELD_LABELS,
  selectToBool,
} from "../utils/profileForm";
import { isLegacyPersonalization } from "../utils/profileState";

const shellStyle = {
  maxWidth: 960,
  margin: "0 auto",
  display: "grid",
  gap: 16,
};

const panelStyle = {
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 12,
  padding: 20,
  display: "grid",
  gap: 16,
  background: "rgba(255,255,255,0.02)",
};

const stepButtonStyle = {
  border: "1px solid rgba(255,255,255,0.14)",
  borderRadius: 8,
  padding: 12,
  display: "grid",
  gap: 4,
  textAlign: "left",
  background: "rgba(255,255,255,0.04)",
  color: "inherit",
};

function SelectField({ label, value, onChange, children }) {
  return (
    <label style={{ display: "grid", gap: 6 }}>
      <span>{label}</span>
      <select
        className="form-select"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        required
      >
        {children}
      </select>
    </label>
  );
}

SelectField.propTypes = {
  label: PropTypes.string.isRequired,
  value: PropTypes.string.isRequired,
  onChange: PropTypes.func.isRequired,
  children: PropTypes.node.isRequired,
};

function MissingFields({ fields }) {
  if (!fields.length) return null;
  return (
    <div
      style={{
        border: "1px solid rgba(255,85,85,0.45)",
        borderRadius: 10,
        padding: 12,
        background: "rgba(255,85,85,0.1)",
      }}
    >
      <b>Осталось заполнить:</b>{" "}
      {fields.map((field) => PROFILE_FIELD_LABELS[field] || field).join(", ")}
    </div>
  );
}

MissingFields.propTypes = {
  fields: PropTypes.arrayOf(PropTypes.string).isRequired,
};

export default function AccountOnboarding() {
  const navigate = useNavigate();
  const location = useLocation();
  const { add } = useToaster();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeStep, setActiveStep] = useState(1);

  const [profileComplete, setProfileComplete] = useState(false);
  const [missingFields, setMissingFields] = useState([]);
  const [profile, setProfile] = useState(null);

  const [vkUsername, setVkUsername] = useState("");
  const [minecraftNick, setMinecraftNick] = useState("");
  const [minecraftHasLicense, setMinecraftHasLicense] = useState("");
  const [isItmoStudent, setIsItmoStudent] = useState("");
  const [itmoIsu, setItmoIsu] = useState("");

  const isRegistrationCompletion = location.pathname.startsWith(
    "/account/complete-registration",
  );
  const isMigrationFlow = isLegacyPersonalization(profile);
  const isuRequired = isItmoStudent === "true";

  const stepStatus = useMemo(() => {
    const gameDone = minecraftNick.trim() && minecraftHasLicense !== "";
    const contactDone =
      vkUsername.trim() &&
      isItmoStudent !== "" &&
      (!isuRequired || itmoIsu.trim());
    return {
      gameDone: Boolean(gameDone),
      contactDone: Boolean(contactDone),
      done: Number(Boolean(gameDone)) + Number(Boolean(contactDone)),
      total: 2,
    };
  }, [
    minecraftNick,
    minecraftHasLicense,
    vkUsername,
    isItmoStudent,
    isuRequired,
    itmoIsu,
  ]);

  const redirectToSessionExpired = useCallback(() => {
    const params = new URLSearchParams({
      reason: "SESSION_UNAUTHORIZED",
      next: "/account/complete-profile",
    });
    navigate(`/session-expired?${params.toString()}`, { replace: true });
  }, [navigate]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const profileData = await me();
      setProfile(profileData);
      setProfileComplete(profileData?.profile_complete === true);
      setMissingFields(
        Array.isArray(profileData?.missing_fields)
          ? profileData.missing_fields
          : [],
      );
      const missing = Array.isArray(profileData?.missing_fields)
        ? profileData.missing_fields
        : [];
      if (
        !missing.includes("minecraft_nick") &&
        !missing.includes("minecraft_has_license") &&
        (missing.includes("vk_username") ||
          missing.includes("is_itmo_student") ||
          missing.includes("itmo_isu"))
      ) {
        setActiveStep(2);
      }
      setVkUsername(profileData?.vk_username || "");
      setMinecraftNick(profileData?.minecraft_nick || "");
      setMinecraftHasLicense(boolToSelect(profileData?.minecraft_has_license));
      setIsItmoStudent(boolToSelect(profileData?.is_itmo_student));
      setItmoIsu(profileData?.itmo_isu || "");
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

  async function saveStep(step) {
    const mc = minecraftNick.trim();
    const vk = vkUsername.trim();
    const isu = itmoIsu.trim();

    if (step === 1) {
      if (!mc || minecraftHasLicense === "") {
        add({
          name: "onboarding-game-required",
          title: "Проверьте игровой профиль",
          content: "Укажите ник Minecraft и наличие лицензии.",
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
    }

    if (step === 2) {
      if (!vk || isItmoStudent === "") {
        add({
          name: "onboarding-contact-required",
          title: "Проверьте связь и статус",
          content: "Укажите VK и статус студента ИТМО.",
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
    }

    const payload =
      step === 1
        ? {
            minecraft_nick: mc,
            minecraft_has_license: selectToBool(minecraftHasLicense),
          }
        : {
            vk_username: vk,
            is_itmo_student: selectToBool(isItmoStudent),
            itmo_isu: isItmoStudent === "true" ? isu : "",
          };

    setSaving(true);
    try {
      const result = await updateProfile(payload);
      add({
        name: `onboarding-save-step-${step}`,
        title: "Профиль",
        content:
          step === 1
            ? "Игровой профиль сохранён"
            : result?.message || "Профиль обновлён",
        theme: "success",
      });
      await load();
      if (step === 1) {
        setActiveStep(2);
      } else if (result?.profile_complete) {
        setActiveStep(2);
      } else if (
        Array.isArray(result?.missing_fields) &&
        (result.missing_fields.includes("minecraft_nick") ||
          result.missing_fields.includes("minecraft_has_license"))
      ) {
        setActiveStep(1);
      }
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

  function onSkip() {
    navigate("/joutak");
  }

  if (loading) {
    return (
      <section style={shellStyle}>
        <div style={panelStyle}>
          <Loader size="m" />
        </div>
      </section>
    );
  }

  if (profileComplete) {
    return (
      <section style={shellStyle}>
        <div style={panelStyle}>
          <Label size="m" theme="success">
            Профиль персонализирован
          </Label>
          <h2 style={{ margin: 0 }}>Регистрация завершена</h2>
          <p style={{ margin: 0, opacity: 0.85 }}>
            Теперь доступны профиль, привязки аккаунтов и персональные функции.
          </p>
          <div>
            <Button view="action" onClick={() => navigate("/account/security")}>
              Перейти в аккаунт
            </Button>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section style={shellStyle}>
      <div style={panelStyle}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: 12,
            flexWrap: "wrap",
          }}
        >
          <div style={{ display: "grid", gap: 8 }}>
            <Label size="m" theme={isMigrationFlow ? "warning" : "info"}>
              {isMigrationFlow ? "Требуется обновление" : "Аккаунт создан"}
            </Label>
            <h2 style={{ margin: 0 }}>
              {isRegistrationCompletion
                ? "Завершите регистрацию"
                : "Персонализируйте профиль"}
            </h2>
            <p style={{ margin: 0, opacity: 0.85 }}>
              {isMigrationFlow
                ? "Мы обновили требования к данным профиля. Заполните 2 коротких шага, чтобы открыть полный доступ к аккаунту."
                : "Чтобы открыть профиль и адаптировать сервисы под вас, заполните 2 коротких шага. Публичные разделы доступны и без этого."}
            </p>
          </div>
          <Label size="m" theme="danger">
            Базовый аккаунт
          </Label>
        </div>

        <div
          style={{
            border: "1px solid rgba(255, 163, 0, 0.45)",
            borderRadius: 10,
            padding: 12,
            background: "rgba(255, 163, 0, 0.12)",
          }}
        >
          <b>До завершения персонализации</b>
          <div style={{ marginTop: 6, opacity: 0.9 }}>
            Можно пользоваться публичными страницами. Профиль, привязки
            аккаунтов и персональные действия откроются после заполнения.
          </div>
        </div>

        <MissingFields fields={missingFields} />

        <div style={{ opacity: 0.85 }}>
          Прогресс: <b>{stepStatus.done}</b> из <b>{stepStatus.total}</b> шагов
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
            gap: 10,
          }}
        >
          <button
            type="button"
            style={{
              ...stepButtonStyle,
              borderColor:
                activeStep === 1
                  ? "rgba(255, 190, 92, 0.8)"
                  : "rgba(255,255,255,0.14)",
            }}
            onClick={() => setActiveStep(1)}
          >
            <b>1. Игровой профиль</b>
            <span style={{ opacity: 0.8 }}>
              {stepStatus.gameDone ? "Сохранено" : "Minecraft и лицензия"}
            </span>
          </button>
          <button
            type="button"
            style={{
              ...stepButtonStyle,
              borderColor:
                activeStep === 2
                  ? "rgba(255, 190, 92, 0.8)"
                  : "rgba(255,255,255,0.14)",
            }}
            onClick={() => setActiveStep(2)}
          >
            <b>2. Связь и статус</b>
            <span style={{ opacity: 0.8 }}>
              {stepStatus.contactDone ? "Сохранено" : "VK и ИТМО"}
            </span>
          </button>
        </div>
      </div>

      <form
        onSubmit={(event) => {
          event.preventDefault();
          saveStep(activeStep);
        }}
        style={panelStyle}
      >
        {activeStep === 1 ? (
          <>
            <div>
              <h3 style={{ margin: 0 }}>Игровой профиль</h3>
              <p style={{ margin: "6px 0 0", opacity: 0.8 }}>
                Эти данные нужны для серверных функций и корректного отображения
                игрового аккаунта.
              </p>
            </div>
            <TextInput
              size="l"
              label="Ник в Minecraft"
              value={minecraftNick}
              onUpdate={setMinecraftNick}
              placeholder="Только латиница, цифры и _"
              required
            />
            <SelectField
              label="Есть лицензия Minecraft?"
              value={minecraftHasLicense}
              onChange={setMinecraftHasLicense}
            >
              <option value="" disabled>
                Выберите вариант
              </option>
              <option value="true">Да</option>
              <option value="false">Нет</option>
            </SelectField>
          </>
        ) : (
          <>
            <div>
              <h3 style={{ margin: 0 }}>Связь и статус</h3>
              <p style={{ margin: "6px 0 0", opacity: 0.8 }}>
                Эти сведения помогают адаптировать коммуникацию и доступные
                сервисные сценарии.
              </p>
            </div>
            <TextInput
              size="l"
              label="Username VK"
              value={vkUsername}
              onUpdate={setVkUsername}
              placeholder="Например, id123456 или username"
              required
            />
            <SelectField
              label="Вы студент ИТМО?"
              value={isItmoStudent}
              onChange={setIsItmoStudent}
            >
              <option value="" disabled>
                Выберите вариант
              </option>
              <option value="true">Да</option>
              <option value="false">Нет</option>
            </SelectField>
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
          </>
        )}

        <div
          style={{
            display: "flex",
            gap: 8,
            justifyContent: "space-between",
            flexWrap: "wrap",
          }}
        >
          <Button view="outlined" onClick={onSkip} type="button">
            Перейти на сайт
          </Button>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {activeStep === 2 && (
              <Button
                view="flat"
                type="button"
                onClick={() => setActiveStep(1)}
                disabled={saving}
              >
                Назад
              </Button>
            )}
            <Button view="action" type="submit" loading={saving}>
              {activeStep === 1 ? "Сохранить и продолжить" : "Завершить"}
            </Button>
          </div>
        </div>
      </form>
    </section>
  );
}
