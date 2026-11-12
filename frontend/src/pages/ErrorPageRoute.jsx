import { lazy, Suspense } from "react";
import { Navigate } from "react-router-dom";

import Layout from "../components/Layout.jsx";
import { LoadingPage } from "../components/ui/PageShell.jsx";
import { useBootstrapFeatures } from "../hooks/useBootstrapFeatures.js";

const LegacyNotFound = lazy(() => import("./NotFound.jsx"));
const Forbidden = lazy(() => import("./Forbidden.jsx"));
const Restricted = lazy(() => import("./Restricted.jsx"));
const NotFoundV2 = lazy(() => import("./NotFoundV2.jsx"));

export function ErrorPageRoute({ type }) {
  const { features, loading } = useBootstrapFeatures();

  if (loading) {
    return (
      <Layout>
        <LoadingPage />
      </Layout>
    );
  }

  if (type === "403" || type === "restricted") {
    const is403Enabled = features.site_403_page_ui === true;
    if (!is403Enabled) {
      return <Navigate to="/" replace />;
    }
    const Component = type === "restricted" ? Restricted : Forbidden;
    return (
      <Suspense fallback={<LoadingPage />}>
        <Component />
      </Suspense>
    );
  }

  const is404Enabled = features.site_404_page_ui === true;
  if (is404Enabled) {
    return (
      <Suspense fallback={<LoadingPage />}>
        <NotFoundV2 />
      </Suspense>
    );
  }

  return (
    <Layout>
      <Suspense fallback={<LoadingPage />}>
        <LegacyNotFound />
      </Suspense>
    </Layout>
  );
}
