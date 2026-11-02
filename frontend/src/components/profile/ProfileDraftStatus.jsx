import { Button } from "@gravity-ui/uikit";

function valueText(value) {
  if (Array.isArray(value))
    return (
      value.map((c) => `${c.type}: ${c.value} (${c.visibility})`).join("; ") ||
      "Нет контактов"
    );
  if (value === true) return "Да";
  if (value === false) return "Нет";
  return value || "Не указано";
}
export default function ProfileDraftStatus({ editor, labels }) {
  return (
    <>
      {editor.error && (
        <p role="alert" className="hub-error">
          {editor.error}
        </p>
      )}
      {editor.conflict && (
        <div className="profile-conflict">
          <p>
            Ваши изменения сохранены в форме. Сначала сверьте их с текущими
            значениями.
          </p>
          {!editor.latest ? (
            <Button loading={editor.busy} onClick={editor.compare}>
              Загрузить актуальные данные
            </Button>
          ) : (
            <>
              <dl>
                {Object.keys(editor.changed).map((key) => (
                  <div key={key}>
                    <dt>{labels[key] || key}</dt>
                    <dd>Сейчас сохранено: {valueText(editor.latest[key])}</dd>
                    <dd>Ваш вариант: {valueText(editor.draft[key])}</dd>
                  </div>
                ))}
              </dl>
              <div className="hub-actions">
                <Button onClick={() => editor.resolve(true)}>
                  Продолжить с моими изменениями
                </Button>
                <Button onClick={() => editor.resolve(false)}>
                  Оставить актуальные данные
                </Button>
              </div>
              <p className="hub-muted">
                Продолжение обновит форму. Для записи потребуется сохранить её.
              </p>
            </>
          )}
        </div>
      )}
      <p role="status">
        {editor.dirty ? "Есть несохранённые изменения." : editor.message}
      </p>
    </>
  );
}
