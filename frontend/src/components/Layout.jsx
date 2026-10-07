import PropTypes from "prop-types";
import { Suspense } from "react";

import { usePageDocument } from "../features/pageDocument/pageDocumentContext";
import FooterNew from "./Footer/Footer";
import HeaderNew from "./HeaderNew/HeaderNew";
import PageLoading from "./PageLoading";
import SimpleFooter from "./SimpleFooter/SimpleFooter";
import SimpleHeader from "./SimpleHeader/SimpleHeader";

const Layout = ({ children }) => {
  const { document } = usePageDocument();
  const headerVariant = document?.layout?.header_variant ?? "legacy";
  const footerVariant = document?.layout?.footer_variant ?? "legacy";

  return (
    <Suspense fallback={<PageLoading />}>
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
