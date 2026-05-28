import LandingPageBuilder from "../components/LandingPageBuilder/LandingPageBuilder";
import { joutakPageContent } from "./landingContent";

const JouTak = () => {
  return (<LandingPageBuilder sections={joutakPageContent.sections} />

  
);
};

export default function JouTak() {
  const bootstrapVariant = useStringFlagValue(
    "site_homepage_version",
    "legacy",
  );
  const [state, setState] = useState({
    payload: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;

    async function loadHomepage() {
      try {
        const params = pickFeatureOverrideParams(window.location.search);
        const payload = await getHomepagePayload(params);
        if (!cancelled) {
          setState({
            payload,
            loading: false,
            error: null,
          });
        }
      } catch (error) {
        if (!cancelled) {
          setState({
            payload: null,
            loading: false,
            error,
          });
        }
      }
    }

    loadHomepage();

    return () => {
      cancelled = true;
    };
  }, [bootstrapVariant]);

  if (state.loading && !state.payload) {
    return <div className="py-5 text-center text-secondary">Загрузка...</div>;
  }

  if (state.error && !state.payload) {
    if (bootstrapVariant === "v2") {
      return <HomepageV2 content={FALLBACK_HOMEPAGE_CONTENT} />;
    }
    return <LegacyHomepage content={FALLBACK_HOMEPAGE_CONTENT} />;
  }

  const variant = state.payload?.variant || bootstrapVariant || "legacy";
  const content = state.payload?.content || FALLBACK_HOMEPAGE_CONTENT;

  if (variant === "v2") {
    return <HomepageV2 content={content} />;
  }

  return <LegacyHomepage content={content} />;
}
