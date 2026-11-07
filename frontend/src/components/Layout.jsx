import PropTypes from "prop-types";
import { Suspense, useLayoutEffect } from "react";

import { usePageDocument } from "../features/pageDocument/pageDocumentContext";
import { useThemePreference } from "../theme/themeContext";
import FooterNew from "./Footer/Footer";
import HeaderNew from "./HeaderNew/HeaderNew";
import SimpleFooter from "./SimpleFooter/SimpleFooter";
import SimpleHeader from "./SimpleHeader/SimpleHeader";
import { LoadingPage } from "./ui/PageShell.jsx";

const Layout = ({ children }) => {
  const { theme } = useThemePreference();
  const { document } = usePageDocument();
  const headerVariant = document?.layout?.header_variant ?? "legacy";
  const documentRoot = window.document.documentElement;
  const footerVariant = document?.layout?.footer_variant ?? "legacy";

  useLayoutEffect(() => {
    documentRoot.dataset.siteDesign = headerVariant;
    if (headerVariant === "v2") documentRoot.dataset.bsTheme = theme;
    else delete documentRoot.dataset.bsTheme;
    return () => {
      delete documentRoot.dataset.siteDesign;
      delete documentRoot.dataset.bsTheme;
    };
  }, [documentRoot, headerVariant, theme]);

  return (
    <Suspense
      fallback={<LoadingPage description="Загружаем оформление сайта" />}
    >
      {headerVariant === "v2" ? <HeaderNew /> : <SimpleHeader />}
      <main className="w-100">{children}</main>
      {footerVariant === "v2" ? <FooterNew /> : <SimpleFooter />}
    </Suspense>
  );
};

Layout.propTypes = {
  children: PropTypes.node.isRequired,
};

export default Layout;
