import { useMemo, useState, useCallback } from "react";
import PropTypes from "prop-types";
import { Button, TextInput } from "@gravity-ui/uikit";
import { toaster } from "@gravity-ui/uikit/toaster-singleton";
import { changePassword } from "../../services/api";

const cardStyle = {
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 12,
  padding: 16,
  display: "grid",
  gap: 12,
};

const COMMON_PASSWORDS = new Set([
  "123456",
  "123456789",
  "qwerty",
  "password",
  "111111",
  "12345678",
  "abc123",
  "1234567",
  "123123",
  "000000",
  "iloveyou",
  "1234",
  "1q2w3e4r",
  "qwertyuiop",
  "admin",
  "monkey",
  "letmein",
  "dragon",
  "sunshine",
  "princess",
]);

function computeStrength(pwd, { minLength, username }) {
  if (!pwd) return { score: 0, label: "Пусто" };
  const lenOK = pwd.length >= minLength;
  const hasLower = /[a-zа-я]/.test(pwd);
  const hasUpper = /[A-ZА-Я]/.test(pwd);
  const hasDigit = /\d/.test(pwd);
  const hasSpec = /[^A-Za-zА-Яа-я0-9\s]/.test(pwd);
  const notOnlyDigits = !/^\d+$/.test(pwd);
  const notCommon = !COMMON_PASSWORDS.has(pwd.toLowerCase());
  const uname = (username || "").toLowerCase();
  const unameLocal = uname.includes("@") ? uname.split("@")[0] : uname;
  const notSimilar = !(uname && pwd.toLowerCase().includes(unameLocal));
  let score = 0;
  if (lenOK) score++;
  if (hasLower) score++;
  if (hasUpper) score++;
  if (hasDigit) score++;
  if (hasSpec) score++;
  if (notOnlyDigits) score++;
  if (notCommon) score++;
  if (notSimilar) score++;
  let label = "Очень слабый";
  if (score >= 7) label = "Сильный";
  else if (score >= 5) label = "Хороший";
  else if (score >= 3) label = "Слабый";
  return {
    score,
    label,
    flags: {
      lenOK,
      hasLower,
      hasUpper,
      hasDigit,
      hasSpec,
      notOnlyDigits,
      notCommon,
      notSimilar,
    },
  };
}

function StrengthBar({ score, label }) {
  const total = 8;
  const percent = Math.round((score / total) * 100);
  const bg = percent >= 63 ? "#1a8f3a" : percent >= 26 ? "#c47f1b" : "#b3261e";
  return (
    <div style={{ display: "grid", gap: 6 }}>
      <div
        aria-hidden="true"
        style={{
          height: 8,
          background: "rgba(255,255,255,0.08)",
          borderRadius: 6,
        }}
      >
        <div
          style={{
            width: `${percent}%`,
            height: "100%",
            background: bg,
            borderRadius: 6,
            transition: "width 200ms ease",
          }}
        />
      </div>
      <div style={{ opacity: 0.8, fontSize: 12 }}>{label}</div>
    </div>
  );
}

StrengthBar.propTypes = {
  score: PropTypes.number.isRequired,
  label: PropTypes.string.isRequired,
};

export default function PasswordCard({
  username,
  minLength = 8,
  defaultOpen = false,
  autoCloseOnSuccess = true,
}) {
  const [editing, setEditing] = useState(!!defaultOpen);
  const [busy, setBusy] = useState(false);

  const [curPwd, setCurPwd] = useState("");
  const [new1, setNew1] = useState("");
  const [new2, setNew2] = useState("");

  const [touched, setTouched] = useState({ cur: false, n1: false, n2: false });
  const [capsCur, setCapsCur] = useState(false);
  const [capsNew, setCapsNew] = useState(false);
  const [backendErr, setBackendErr] = useState({ cur: "", n1: "" });

  const strength = useMemo(
    () =>
      editing
        ? computeStrength(new1, { minLength, username })
        : { score: 0, label: "Пусто" },
    [editing, new1, minLength, username],
  );

  const { curErr, n1Err, n2Err, hasErrors } = useMemo(() => {
    let curErr = "";
    let n1Err = "";
    let n2Err = "";
    if (touched.cur && !curPwd) curErr = "Введите текущий пароль.";
    if (touched.n1) {
      if (!new1) n1Err = "Введите новый пароль.";
      else if (new1.length < minLength)
        n1Err = `Минимум ${minLength} символов.`;
      else if (/^\d+$/.test(new1))
        n1Err = "Пароль не должен состоять только из цифр.";
      else if (username) {
        const uname = username.toLowerCase();
        const unameLocal = uname.includes("@") ? uname.split("@")[0] : uname;
        if (unameLocal && new1.toLowerCase().includes(unameLocal))
          n1Err = "Пароль слишком похож на логин/почту.";
      }
      if (!n1Err && COMMON_PASSWORDS.has(new1.toLowerCase()))
        n1Err = "Слишком распространённый пароль.";
    }
    if (touched.n2) {
      if (!new2) n2Err = "Повторите новый пароль.";
      else if (new1 && new2 && new1 !== new2) n2Err = "Пароли не совпадают.";
    }
    if (!curErr && backendErr.cur) curErr = backendErr.cur;
    if (!n1Err && backendErr.n1) n1Err = backendErr.n1;
    return { curErr, n1Err, n2Err, hasErrors: !!(curErr || n1Err || n2Err) };
  }, [curPwd, new1, new2, touched, backendErr, minLength, username]);

  const touchAll = () => setTouched({ cur: true, n1: true, n2: true });

  const resetForm = useCallback(() => {
    setCurPwd("");
    setNew1("");
    setNew2("");
    setTouched({ cur: false, n1: false, n2: false });
    setBackendErr({ cur: "", n1: "" });
    setCapsCur(false);
    setCapsNew(false);
  }, []);

  const onCancel = useCallback(() => {
    resetForm();
    setEditing(false);
  }, [resetForm]);

  function mapBackendErrors(data) {
    let cur = "";
    let n1 = "";
    const fieldMsgs = (k) =>
      Array.isArray(data?.[k])
        ? data[k].join("\n")
        : typeof data?.[k] === "string"
          ? data[k]
          : "";
    n1 = fieldMsgs("new_password") || fieldMsgs("password") || "";
    cur = fieldMsgs("current_password") || "";
    if (/too short/i.test(n1))
      n1 = `Слишком короткий пароль (минимум ${minLength} символов).`;
    if (/too common/i.test(n1)) n1 = "Слишком распространённый пароль.";
    if (/entirely numeric/i.test(n1))
      n1 = "Пароль не должен состоять только из цифр.";
    if (/too similar/i.test(n1)) n1 = "Пароль слишком похож на логин/почту.";
    setBackendErr({ cur, n1 });
    if (cur || n1) touchAll();
  }

  async function onSubmit(e) {
    e.preventDefault();
    touchAll();
    setBackendErr({ cur: "", n1: "" });
    if (hasErrors) return;

    setBusy(true);
    try {
      await changePassword({ current_password: curPwd, new_password: new1 });

      toaster.add({
        name: "pwd-ok",
        title: "Пароль обновлён",
        content: "Новый пароль уже доступен для авторизации.",
        type: "success",
      });

      try {
        if (
          username &&
          "credentials" in navigator &&
          "PasswordCredential" in window
        ) {
          const cred = new window.PasswordCredential({
            id: String(username),
            password: new1,
          });
          navigator.credentials.store(cred).catch(() => {});
        }
      } catch (err) {
        void err;
      }

      if (autoCloseOnSuccess) {
        onCancel();
      } else {
        resetForm();
      }
    } catch (ex) {
      const data = ex?.response?.data;
      const detail =
        (typeof data?.detail === "string" && data.detail) ||
        (Array.isArray(data?.non_field_errors) &&
          data.non_field_errors.join("\n")) ||
        null;
      toaster.add({
        name: "pwd-err",
        title: "Ошибка",
        content: detail || "Не удалось изменить пароль.",
        type: "error",
      });
      if (data && typeof data === "object") mapBackendErrors(data);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section style={cardStyle}>
      <h3 style={{ margin: 0, fontSize: 18 }}>Пароль</h3>

      {!editing ? (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 12,
            flexWrap: "wrap",
          }}
        >
          <div style={{ opacity: 0.8 }}>
            Для безопасности поля скрыты. Нажмите, чтобы изменить пароль.
          </div>
          <Button size="l" view="outlined" onClick={() => setEditing(true)}>
            Сменить пароль
          </Button>
        </div>
      ) : (
        <form
          id="password-change-form"
          onSubmit={onSubmit}
          style={{ display: "grid", gap: 12 }}
          autoComplete="off"
          onKeyDown={(e) => {
            if (e.key === "Escape" && !busy) onCancel();
          }}
        >
          {username ? (
            <input
              type="text"
              name="username"
              autoComplete="username"
              value={username}
              readOnly
              hidden
            />
          ) : null}

          <TextInput
            size="l"
            type="password"
            label="Текущий пароль"
            value={curPwd}
            onUpdate={(v) => {
              setCurPwd(v);
              if (!touched.cur) setTouched((t) => ({ ...t, cur: true }));
            }}
            onBlur={() => setTouched((t) => ({ ...t, cur: true }))}
            onKeyUp={(e) =>
              setCapsCur(e.getModifierState && e.getModifierState("CapsLock"))
            }
            name="joutak__password"
            autoComplete="current-password"
            validationState={curErr ? "invalid" : undefined}
            errorMessage={curErr || undefined}
          />
          {capsCur && (
            <div style={{ color: "#c47f1b", fontSize: 12 }}>
              Внимание: включён Caps Lock.
            </div>
          )}

          <TextInput
            size="l"
            type="password"
            label={`Новый пароль (мин. ${minLength})`}
            value={new1}
            onUpdate={(v) => {
              setNew1(v);
              if (!touched.n1) setTouched((t) => ({ ...t, n1: true }));
            }}
            onBlur={() => setTouched((t) => ({ ...t, n1: true }))}
            onKeyUp={(e) =>
              setCapsNew(e.getModifierState && e.getModifierState("CapsLock"))
            }
            name="joutak__password"
            autoComplete="new-password"
            inputProps={{ passwordRules: `minlength: ${minLength};` }}
            validationState={n1Err ? "invalid" : undefined}
            errorMessage={n1Err || undefined}
          />
          {capsNew && (
            <div style={{ color: "#c47f1b", fontSize: 12 }}>
              Внимание: включён Caps Lock.
            </div>
          )}

          <TextInput
            size="l"
            type="password"
            label="Повторите новый пароль"
            value={new2}
            onUpdate={(v) => {
              setNew2(v);
              if (!touched.n2) setTouched((t) => ({ ...t, n2: true }));
            }}
            onBlur={() => setTouched((t) => ({ ...t, n2: true }))}
            name="joutak__password"
            autoComplete="new-password"
            validationState={n2Err ? "invalid" : undefined}
            errorMessage={n2Err || undefined}
          />

          <StrengthBar score={strength.score} label={strength.label} />

          <div style={{ opacity: 0.8, fontSize: 12, display: "grid", gap: 4 }}>
            <div>
              Требования: минимум {minLength} символов, пароль не должен быть
              полностью из цифр и не должен совпадать с логином/почтой.
            </div>
          </div>

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Button
              size="l"
              view="action"
              type="submit"
              loading={busy}
              disabled={busy}
            >
              Обновить пароль
            </Button>
            <Button
              size="l"
              view="normal"
              type="button"
              disabled={busy}
              onClick={onCancel}
            >
              Отмена
            </Button>
          </div>
        </form>
      )}
    </section>
  );
}

PasswordCard.propTypes = {
  username: PropTypes.string,
  minLength: PropTypes.number,
  defaultOpen: PropTypes.bool,
  autoCloseOnSuccess: PropTypes.bool,
};
