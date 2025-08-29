import {useEffect, useState, useMemo} from 'react';
import {Button, Label, TextInput, useToaster, Loader} from '@gravity-ui/uikit';
import {getEmailStatus, changeEmail, resendEmailVerification} from '../../services/api';

const cardStyle = {
    border: '1px solid rgba(255,255,255,0.12)',
    borderRadius: 12,
    padding: 16,
    display: 'grid',
    gap: 12,
};
const headerStyle = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12
};

export default function EmailCard() {
    const [email, setEmail] = useState('');
    const [verified, setVerified] = useState(false);
    const [loading, setLoading] = useState(true);

    const [editMode, setEditMode] = useState(false);
    const [newEmail, setNewEmail] = useState('');
    const [busy, setBusy] = useState(false);

    const {add} = useToaster();

    async function load() {
        setLoading(true);
        try {
            const s = await getEmailStatus();
            setEmail(s.email || '');
            setVerified(!!s.verified);
            setNewEmail(s.email || '');
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        load();
    }, []);

    async function onResend() {
        setBusy(true);
        try {
            const {message} = await resendEmailVerification();
            add({
                name: 'email-resend',
                title: 'Подтверждение',
                content: message || 'Письмо отправлено',
                theme: 'success'
            });
        } catch (e) {
            add({
                name: 'email-resend-err',
                title: 'Ошибка',
                content: 'Не удалось отправить письмо',
                theme: 'danger'
            });
        } finally {
            setBusy(false);
        }
    }

    async function onSave(e) {
        e.preventDefault();
        if (!newEmail || newEmail === email) {
            setEditMode(false);
            return;
        }
        setBusy(true);
        try {
            const {message} = await changeEmail(newEmail);
            add({
                name: 'email-change',
                title: 'Email',
                content: message || 'Проверьте почту для подтверждения',
                theme: 'success'
            });
            setEmail(newEmail);
            setVerified(false);
            setEditMode(false);
        } catch (e) {
            const msg = e?.response?.data?.detail || 'Не удалось изменить email';
            add({name: 'email-change-err', title: 'Ошибка', content: String(msg), theme: 'danger'});
        } finally {
            setBusy(false);
        }
    }

    function onCancel() {
        setEditMode(false);
        setNewEmail(email || '');
    }

    const canSave = useMemo(
        () => !!newEmail && newEmail !== email,
        [newEmail, email]
    );

    return (
        <section style={cardStyle}>
            <div style={headerStyle}>
                <h3 style={{margin: 0, fontSize: 18}}>Email</h3>
                {email ? (verified ? <Label theme="success">Подтверждён</Label> :
                    <Label theme="danger">Не подтверждён</Label>) : null}
            </div>

            {loading ? (
                <Loader size="m"/>
            ) : (
                <>
                    {!editMode && (
                        <>
                            <div><b>{email || '—'}</b></div>
                            {!verified && email && (
                                <div style={{color: '#d9534f'}}>
                                    Ваш email не подтверждён. Пожалуйста, подтвердите его.
                                </div>
                            )}
                            <div style={{display: 'flex', gap: 8, flexWrap: 'wrap'}}>
                                <Button view="outlined" onClick={() => setEditMode(true)}>Изменить
                                    email</Button>
                                {!verified && email && (
                                    <Button view="normal" loading={busy} onClick={onResend}>
                                        Отправить письмо повторно
                                    </Button>
                                )}
                            </div>
                        </>
                    )}

                    {editMode && (
                        <form onSubmit={onSave} style={{display: 'grid', gap: 12}}>
                            <TextInput
                                size="l"
                                label="Новый email"
                                type="email"
                                value={newEmail}
                                onUpdate={setNewEmail}
                                name="email"
                                autoComplete="email"
                                required
                            />
                            <div style={{display: 'flex', gap: 8, justifyContent: 'flex-end'}}>
                                <Button view="flat" onClick={onCancel}
                                        disabled={busy}>Отмена</Button>
                                <Button view="action" type="submit" loading={busy}
                                        disabled={!canSave}>
                                    Сохранить
                                </Button>
                            </div>
                            <div style={{opacity: 0.75, fontSize: 12}}>
                                После изменения мы отправим письмо с подтверждением на новый адрес.
                            </div>
                        </form>
                    )}
                </>
            )}
        </section>
    );
}
