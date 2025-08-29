import {Avatar, Label} from '@gravity-ui/uikit';

export default function AccountHero({profile}) {
    const first = profile?.first_name || '';
    const last = profile?.last_name || '';
    const fullName = [first, last].filter(Boolean).join(' ').trim();
    const displayName = fullName || profile?.username || profile?.nickname || 'Anonymous';
    const avatarUrl = profile?.avatar_url || '';
    const email = profile?.email || '';
    const emailVerified = profile?.email_verified === true;

    return (
        <section style={{
            border: '1px solid rgba(255,255,255,0.12)',
            borderRadius: 12,
            padding: 16,
            display: 'grid',
            gridTemplateColumns: 'minmax(96px, 120px) 1fr',
            gap: 16,
            alignItems: 'center'
        }}>
            <div style={{justifySelf: 'center'}}>
                <Avatar
                    size="2xl"
                    imgUrl={avatarUrl || undefined}
                    text={displayName}
                    view="outlined"
                    title={displayName}
                />
            </div>
            <div style={{display: 'grid', gap: 6}}>
                <div style={{fontSize: 22, fontWeight: 700}}>{displayName}</div>
                {email && (
                    <div style={{opacity: 0.9, display: 'flex', gap: 8, alignItems: 'center'}}>
                        <span>Email: <b>{email}</b></span>
                        {emailVerified
                            ? <Label size="s" theme="success">Подтверждён</Label>
                            : <Label size="s" theme="danger">Не подтверждён</Label>}
                    </div>
                )}
            </div>
        </section>
    );
}
