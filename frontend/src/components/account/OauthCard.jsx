import {useEffect, useState} from 'react';
import {Button, DropdownMenu, Loader} from '@gravity-ui/uikit';
import {getOAuthProviders, getOAuthLink} from '../../services/api';

const cardStyle = {
    border: '1px solid rgba(255,255,255,0.12)',
    borderRadius: 12,
    padding: 16,
    display: 'grid',
    gap: 12,
};

const row = {display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12};

export default function OauthCard() {
    const [providers, setProviders] = useState([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        let cancelled = false;
        (async () => {
            setLoading(true);
            try {
                const list = await getOAuthProviders();
                if (!cancelled) setProviders(list);
            } finally {
                if (!cancelled) setLoading(false);
            }
        })();
        return () => {
            cancelled = true;
        };
    }, []);

    function submitPost(url, fields = {}) {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = url;
        Object.entries(fields || {}).forEach(([k, v]) => {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = k;
            input.value = v == null ? '' : String(v);
            form.appendChild(input);
        });
        document.body.appendChild(form);
        form.submit();
    }

    async function connectProvider(providerId) {
        try {
            const {url, method} = await getOAuthLink(providerId, '/account/security#linked');
            if (method === 'GET') {
                window.location.href = url;
                return;
            }
            const u = new URL(url, window.location.origin);
            const params = Object.fromEntries(u.searchParams.entries());
            submitPost(u.pathname, params);
        } catch {
            alert('Не удалось получить ссылку провайдера');
        }
    }

    return (
        <section style={cardStyle}>
            <h3 style={{margin: 0, fontSize: 18}}>Связанные аккаунты</h3>
            {loading ? (
                <Loader size="m"/>
            ) : providers?.length ? (
                <div style={{display: 'grid', gap: 8}}>
                    {providers.map((p) => (
                        <div key={p.id} style={row}>
                            <div style={{textTransform: 'capitalize'}}>{p.name}</div>
                            <DropdownMenu
                                size="m"
                                renderSwitcher={(props) => <Button {...props}
                                                                   view="outlined">Действия</Button>}
                                items={[
                                    {text: 'Связать', action: () => connectProvider(p.id)},
                                ]}
                            />
                        </div>
                    ))}
                </div>
            ) : (
                <div style={{opacity: 0.8}}>Доступных провайдеров нет.</div>
            )}
        </section>
    );
}
