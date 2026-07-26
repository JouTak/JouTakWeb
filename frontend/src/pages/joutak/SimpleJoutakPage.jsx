import SimpleHomepage from "./SimpleHomepage";

const LEGACY_CONTENT = {
  hero: {
    title: "JouTak",
    description:
      "Джоутек — колыбель ITMOcraft: приватный мир без вайпов, сохранивший память сообщества.",
    server_ip: "mc.joutak.ru",
    primary_cta: {
      label: "Зарегистрироваться на приватном сервере",
      href: "https://forms.yandex.ru/u/6501f64f43f74f18a8da28de/",
    },
    secondary_cta: {
      label: "Оплатить проходку",
      to: "/joutak/pay",
    },
  },
  carousel: [
    {
      src: "https://cloud.joutak.ru/s/ZZg89sgcx6X9cxp/preview",
      alt: "Центральный район сервера",
    },
    {
      src: "https://cloud.joutak.ru/s/mFfm4HqBzYm5Wxc/preview",
      alt: "Большой гриб на нулевых координатах",
    },
  ],
};

export default function SimpleJoutakPage() {
  return <SimpleHomepage content={LEGACY_CONTENT} />;
}
