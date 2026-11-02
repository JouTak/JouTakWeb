export default function ProfileServerHistory({ history }) {
  const firstJoined =
    history &&
    new Intl.DateTimeFormat("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      timeZone: "UTC",
    }).format(new Date(`${history.first_joined_on}T00:00:00Z`));
  return (
    <section
      className="hub-panel profile-server-history"
      aria-label="На сервере"
    >
      <h2>{history ? `Игрок уже ${history.days_text}` : "Стаж на сервере"}</h2>
      {history ? (
        <>
          <p className="hub-muted">
            с <time dateTime={history.first_joined_on}>{firstJoined}</time>
          </p>
        </>
      ) : (
        <p className="hub-muted">Дата первого входа недоступна.</p>
      )}
    </section>
  );
}
