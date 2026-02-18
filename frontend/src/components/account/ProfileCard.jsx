import { useEffect, useMemo, useState, useCallback } from "react";
import PropTypes from "prop-types";
import { Button, Loader, TextInput, useToaster } from "@gravity-ui/uikit";
import { me, updateProfile } from "../../services/api";
import { boolToSelect, selectToBool } from "../../utils/profileForm";

const cardStyle = {
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 12,
  padding: 16,
  display: "grid",
  gap: 12,
};
const headerStyle = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: 12,
};

function boolIcon(value) {
  if (value === true) return "✅";
  if (value === false) return "❌";
  return "❔";
}

export default function ProfileCard({ onUpdated }) {
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [vkUsername, setVkUsername] = useState("");
  const [minecraftNick, setMinecraftNick] = useState("");
  const [minecraftHasLicense, setMinecraftHasLicense] = useState(null);
  const [isItmoStudent, setIsItmoStudent] = useState(null);
  const [itmoIsu, setItmoIsu] = useState("");
  const [loading, setLoading] = useState(true);

  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [fDraft, setFDraft] = useState("");
  const [lDraft, setLDraft] = useState("");
  const [vkDraft, setVkDraft] = useState("");
  const [mcDraft, setMcDraft] = useState("");
  const [licenseDraft, setLicenseDraft] = useState("");
  const [itmoDraft, setItmoDraft] = useState("");
  const [isuDraft, setIsuDraft] = useState("");

  const { add } = useToaster();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await me();
      setFirstName(data.first_name || "");
      setLastName(data.last_name || "");
      setVkUsername(data.vk_username || "");
      setMinecraftNick(data.minecraft_nick || "");
      setMinecraftHasLicense(data.minecraft_has_license ?? null);
      setIsItmoStudent(data.is_itmo_student ?? null);
      setItmoIsu(data.itmo_isu || "");
    } catch {
      add({
        name: "profile-load-error",
        title: "Ошибка",
        content: "Не удалось загрузить данные профиля",
        theme: "danger",
      });
    } finally {
      setLoading(false);
    }
  }, [add]);

  useEffect(() => {
    load();
  }, [load]);

  function openForm() {
    setFDraft(firstName);
    setLDraft(lastName);
    setVkDraft(vkUsername);
    setMcDraft(minecraftNick);
    setLicenseDraft(boolToSelect(minecraftHasLicense));
    setItmoDraft(boolToSelect(isItmoStudent));
    setIsuDraft(itmoIsu);
    setOpen(true);
  }

  const isuRequired = itmoDraft === "true";
  const dirty = useMemo(
    () =>
      fDraft !== firstName ||
      lDraft !== lastName ||
      vkDraft !== vkUsername ||
      mcDraft !== minecraftNick ||
      licenseDraft !== boolToSelect(minecraftHasLicense) ||
      itmoDraft !== boolToSelect(isItmoStudent) ||
      isuDraft !== itmoIsu,
    [
      fDraft,
      lDraft,
      vkDraft,
      mcDraft,
      licenseDraft,
      itmoDraft,
      isuDraft,
      firstName,
      lastName,
      vkUsername,
      minecraftNick,
      minecraftHasLicense,
      isItmoStudent,
      itmoIsu,
    ],
  );
  const valid = useMemo(() => {
    const f = (fDraft || "").trim();
    const l = (lDraft || "").trim();
    const vk = (vkDraft || "").trim();
    const mc = (mcDraft || "").trim();
    const isu = (isuDraft || "").trim();
    const mcOk = /^[A-Za-z0-9_]{3,16}$/.test(mc);
    const isuOk = !isuRequired || /^\d{5,20}$/.test(isu);

    return (
      f.length <= 100 &&
      l.length <= 100 &&
      vk.length > 0 &&
      mc.length > 0 &&
      mcOk &&
      licenseDraft !== "" &&
      itmoDraft !== "" &&
      (!isuRequired || isu.length > 0) &&
      isuOk
    );
  }, [fDraft, lDraft, vkDraft, mcDraft, licenseDraft, itmoDraft, isuDraft, isuRequired]);

  async function onSave(e) {
    e.preventDefault();
    if (!dirty || !valid) return;
    setBusy(true);
    try {
      const payload = {
        first_name: (fDraft || "").trim(),
        last_name: (lDraft || "").trim(),
        vk_username: (vkDraft || "").trim(),
        minecraft_nick: (mcDraft || "").trim(),
        minecraft_has_license: selectToBool(licenseDraft),
        is_itmo_student: selectToBool(itmoDraft),
        ...(isuRequired ? { itmo_isu: (isuDraft || "").trim() } : { itmo_isu: "" }),
      };
      const { message } = await updateProfile(payload);
      setFirstName(payload.first_name);
      setLastName(payload.last_name);
      setVkUsername(payload.vk_username);
      setMinecraftNick(payload.minecraft_nick);
      setMinecraftHasLicense(payload.minecraft_has_license);
      setIsItmoStudent(payload.is_itmo_student);
      setItmoIsu(payload.itmo_isu || "");
      onUpdated?.();
      add({
        name: "name-save",
        title: "Профиль",
        content: message || "Сохранено",
        theme: "success",
      });
      setOpen(false);
    } catch (e) {
      const msg =
        e?.response?.data?.fields?.vk_username ||
        e?.response?.data?.fields?.minecraft_nick ||
        e?.response?.data?.fields?.itmo_isu ||
        e?.response?.data?.detail ||
        "Не удалось сохранить";
      add({
        name: "name-save-err",
        title: "Ошибка",
        content: String(msg),
        theme: "danger",
      });
    } finally {
      setBusy(false);
    }
  }

  function onCancel() {
    setOpen(false);
  }

  const fullName = [firstName, lastName].filter(Boolean).join(" ").trim();
  const vkProfileUrl = vkUsername ? `https://vk.com/${vkUsername}` : "";
  const vkLabel = fullName || (vkUsername ? `@${vkUsername}` : "");

  return (
    <section style={cardStyle}>
      <div style={headerStyle}>
        <h3 style={{ margin: 0, fontSize: 18 }}>Профиль</h3>
        {!open && (
          <Button
            view="outlined"
            size="m"
            onClick={openForm}
            disabled={loading}
          >
            Изменить
          </Button>
        )}
      </div>

      {loading ? (
        <Loader size="m" />
      ) : (
        <>
          <div style={{ display: "grid", gap: 8 }}>
            {fullName ? <div><b>{fullName}</b></div> : null}

            {vkUsername ? (
              <a
                href={vkProfileUrl}
                target="_blank"
                rel="noreferrer"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 8,
                  width: "fit-content",
                  border: "1px solid rgba(255,255,255,0.18)",
                  borderRadius: 999,
                  padding: "6px 12px",
                  textDecoration: "none",
                  color: "inherit",
                }}
                title="Открыть профиль VK"
              >
                <span style={{ opacity: 0.75 }}>VK</span>
                <b>{vkLabel}</b>
              </a>
            ) : (
              <div>
                <span style={{ opacity: 0.75 }}>VK: </span>
                <b>Не указан</b>
              </div>
            )}

            <div>
              <span style={{ opacity: 0.75 }}>Minecraft: </span>
              <b>{minecraftNick || "—"}</b>
            </div>

            <div
              style={{
                display: "grid",
                gap: 6,
                marginTop: 2,
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: 8,
                }}
              >
                <span>Лицензия Minecraft</span>
                <b>{boolIcon(minecraftHasLicense)}</b>
              </div>
              {isItmoStudent === true && (
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: 8,
                  }}
                >
                  <span>Номер ИСУ</span>
                  <b>{itmoIsu || "—"}</b>
                </div>
              )}
            </div>
          </div>

          <div className={`collapse-y ${open ? "open" : ""}`}>
            <div>
              {open && (
                <form
                  onSubmit={onSave}
                  className="inline-edit"
                  style={{ display: "grid", gap: 12 }}
                  >
                  <TextInput
                    size="l"
                    label="Имя"
                    name="joutak__given-name"
                    autoComplete="given-name"
                    value={fDraft}
                    onUpdate={setFDraft}
                  />
                  <TextInput
                    size="l"
                    label="Фамилия"
                    name="joutak__family-name"
                    autoComplete="family-name"
                    value={lDraft}
                    onUpdate={setLDraft}
                  />
                  <TextInput
                    size="l"
                    label="Username VK"
                    value={vkDraft}
                    onUpdate={setVkDraft}
                    placeholder="Например, id123456 или username"
                    required
                  />
                  <TextInput
                    size="l"
                    label="Ник в Minecraft"
                    value={mcDraft}
                    onUpdate={setMcDraft}
                    placeholder="Только латиница, цифры и _"
                    required
                  />
                  <label style={{ display: "grid", gap: 6 }}>
                    <span>Есть лицензия Minecraft?</span>
                    <select
                      className="form-select"
                      value={licenseDraft}
                      onChange={(event) => setLicenseDraft(event.target.value)}
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
                      value={itmoDraft}
                      onChange={(event) => setItmoDraft(event.target.value)}
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
                      value={isuDraft}
                      onUpdate={setIsuDraft}
                      placeholder="Только цифры"
                      required
                    />
                  )}
                  <div
                    style={{
                      display: "flex",
                      gap: 8,
                      justifyContent: "flex-end",
                      marginTop: 4,
                    }}
                  >
                    <Button
                      view="flat"
                      type="button"
                      onClick={onCancel}
                      disabled={busy}
                    >
                      Отмена
                    </Button>
                    <Button
                      view="action"
                      type="submit"
                      loading={busy}
                      disabled={!dirty || !valid}
                    >
                      Сохранить
                    </Button>
                  </div>
                </form>
              )}
            </div>
          </div>
        </>
      )}
    </section>
  );
}

ProfileCard.propTypes = {
  onUpdated: PropTypes.func,
};
