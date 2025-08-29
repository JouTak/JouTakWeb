import { useEffect, useMemo, useState } from 'react';
import { Button, Loader, TextInput, useToaster } from '@gravity-ui/uikit';
import { me, updateProfile } from '../../services/api';

const cardStyle = {
  border: '1px solid rgba(255,255,255,0.12)',
  borderRadius: 12,
  padding: 16,
  display: 'grid',
  gap: 12,
};
const headerStyle = { display:'flex', alignItems:'center', justifyContent:'space-between', gap:12 };

export default function NameCard() {
  const [firstName, setFirstName] = useState('');
  const [lastName,  setLastName]  = useState('');
  const [loading,   setLoading]   = useState(true);

  const [open,      setOpen]      = useState(false);
  const [busy,      setBusy]      = useState(false);
  const [fDraft,    setFDraft]    = useState('');
  const [lDraft,    setLDraft]    = useState('');

  const { add } = useToaster();

  async function load() {
    setLoading(true);
    try {
      const data = await me();
      setFirstName(data.first_name || '');
      setLastName(data.last_name || '');
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { load(); }, []);

  function openForm() {
    setFDraft(firstName);
    setLDraft(lastName);
    setOpen(true);
  }

  const dirty = useMemo(
    () => fDraft !== firstName || lDraft !== lastName,
    [fDraft, lDraft, firstName, lastName]
  );
  const valid = useMemo(() => {
    const f = (fDraft || '').trim();
    const l = (lDraft || '').trim();
    return (f.length > 0 || l.length > 0) && f.length <= 100 && l.length <= 100;
  }, [fDraft, lDraft]);

  async function onSave(e) {
    e.preventDefault();
    if (!dirty || !valid) return;
    setBusy(true);
    try {
      const payload = { first_name: (fDraft || '').trim(), last_name: (lDraft || '').trim() };
      const { message } = await updateProfile(payload);
      setFirstName(payload.first_name);
      setLastName(payload.last_name);
      add({ name:'name-save', title:'Профиль', content: message || 'Сохранено', theme:'success' });
      setOpen(false);
    } catch (e) {
      const msg = e?.response?.data?.detail || 'Не удалось сохранить';
      add({ name:'name-save-err', title:'Ошибка', content: String(msg), theme:'danger' });
    } finally {
      setBusy(false);
    }
  }

  function onCancel() {
    setOpen(false);
  }

  return (
    <section style={cardStyle}>
      <div style={headerStyle}>
        <h3 style={{margin:0, fontSize:18}}>Имя и фамилия</h3>
        {!open && (
          <Button view="outlined" size="m" onClick={openForm} disabled={loading}>
            Изменить
          </Button>
        )}
      </div>

      {loading ? (
        <Loader size="m" />
      ) : (
        <>
          <div><b>{firstName || '—'}</b> {lastName || ''}</div>

          {/* Инлайн-форма с плавным раскрытием */}
          <div className={`collapse-y ${open ? 'open' : ''}`}>
            <div>
              {open && (
                <form onSubmit={onSave} className="inline-edit" style={{display:'grid', gap:12}}>
                  <TextInput
                    size="l"
                    label="Имя"
                    name="given-name"
                    autoComplete="given-name"
                    value={fDraft}
                    onUpdate={setFDraft}
                  />
                  <TextInput
                    size="l"
                    label="Фамилия"
                    name="family-name"
                    autoComplete="family-name"
                    value={lDraft}
                    onUpdate={setLDraft}
                  />
                  <div style={{display:'flex', gap:8, justifyContent:'flex-end', marginTop:4}}>
                    <Button view="flat" type="button" onClick={onCancel} disabled={busy}>
                      Отмена
                    </Button>
                    <Button view="action" type="submit" loading={busy} disabled={!dirty || !valid}>
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
