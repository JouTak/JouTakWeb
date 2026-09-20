import PropTypes from "prop-types";
import { Suspense } from "react";

import { usePageDocument } from "../features/pageDocument/pageDocumentContext";
import FooterNew from "./Footer/Footer";
import HeaderNew from "./HeaderNew/HeaderNew";
import SimpleFooter from "./SimpleFooter/SimpleFooter";
import SimpleHeader from "./SimpleHeader/SimpleHeader";
import { LoadingPage } from "./ui/PageShell.jsx";

function LoadingFallback() {
  return <LoadingPage description="Загружаем оформление сайта" />;
}

const Layout = ({ children }) => {
  const { document } = usePageDocument();
  const headerVariant = document?.layout?.header_variant ?? "legacy";
  const footerVariant = document?.layout?.footer_variant ?? "legacy";

  return (
    <Suspense fallback={<LoadingFallback />}>
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
