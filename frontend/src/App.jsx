import { lazy, Suspense } from "react";
import { Route, Routes, useLocation, useNavigate } from "react-router-dom";

import AuthModal from "./components/AuthModal.jsx";
import { HubGate } from "./components/hub/HubShell";
import Layout from "./components/Layout";
import RequireAuth from "./components/RequireAuth.jsx";
import ScrollToTop from "./components/ScrollToTop.jsx";
import { safeInternalPath } from "./services/urlSafety";
const Legacy = lazy(() => import("./pages/Legacy.jsx"));
const Contact = lazy(() => import("./pages/Contact/Contact.jsx"));
const NotFound = lazy(() => import("./pages/NotFound.jsx"));
const AccountSecurity = lazy(() => import("./pages/AccountSecurity.jsx"));
const AccountOnboarding = lazy(() => import("./pages/AccountOnboarding.jsx"));
const SessionExpired = lazy(() => import("./pages/SessionExpired.jsx"));
const ConfirmEmail = lazy(() => import("./pages/ConfirmEmail.jsx"));
const ResetPassword = lazy(() => import("./pages/ResetPassword.jsx"));
const Pay = lazy(() => import("./pages/joutak/Pay.jsx"));
const ItmoCraftRoute = lazy(
  () => import("./pages/itmocraft/ItmoCraftRoute.jsx"),
);
const JouTakRoute = lazy(() => import("./pages/joutak/JouTakRoute.jsx"));
const MinigamesRoute = lazy(
  () => import("./pages/minigames/MinigamesRoute.jsx"),
);

const AccountDashboard = lazy(
  () => import("./pages/account/AccountDashboard.jsx"),
);
const AccountProfile = lazy(() => import("./pages/account/AccountProfile.jsx"));
const AccountCommunities = lazy(
  () => import("./pages/account/AccountCommunities.jsx"),
);
const Players = lazy(() => import("./pages/profile/Players.jsx"));
const PublicProfile = lazy(() => import("./pages/profile/PublicProfile.jsx"));
const ProfilePreview = lazy(() => import("./pages/profile/ProfilePreview.jsx"));
const OwnFollowing = lazy(() => import("./pages/profile/OwnFollowing.jsx"));
const Communities = lazy(() => import("./pages/communities/Communities.jsx"));
const CommunityDetail = lazy(
  () => import("./pages/communities/CommunityDetail.jsx"),
);
const GroupDetail = lazy(() => import("./pages/groups/GroupDetail.jsx"));
const GroupCreate = lazy(() => import("./pages/groups/GroupCreate.jsx"));
const GroupManage = lazy(() => import("./pages/groups/GroupManage.jsx"));
const GroupsModeration = lazy(
  () => import("./pages/moderation/GroupsModeration.jsx"),
);
const CityCatalog = lazy(() => import("./pages/cities/CityCatalog.jsx"));
const CityDetail = lazy(() => import("./pages/cities/CityDetail.jsx"));
const CityManage = lazy(() => import("./pages/cities/CityManage.jsx"));
const CitiesModeration = lazy(
  () => import("./pages/moderation/CitiesModeration.jsx"),
);

function RouteFallback() {
  return <div className="py-5 text-center text-secondary">Загрузка...</div>;
}

function LoginModalRoute() {
  const navigate = useNavigate();
  const location = useLocation();
  const params = new URLSearchParams(location.search);
  const nextFromQuery = params.get("next");
  const nextFromState = location.state?.next;
  const successRedirectTo = safeInternalPath(
    nextFromQuery || nextFromState || "/joutak",
  );

  return (
    <AuthModal
      open
      onClose={() =>
        location.state?.background
          ? navigate(-1)
          : navigate("/joutak", { replace: true })
      }
      successRedirectTo={successRedirectTo}
    />
  );
}

function AppRoutes() {
  const location = useLocation();
  const background = location.state && location.state.background;

  return (
    <Suspense fallback={<RouteFallback />}>
      <Routes location={background || location}>
        <Route path="/" element={<ItmoCraftRoute />} />
        <Route
          path="/account"
          element={
            <RequireAuth>
              <HubGate flag="community_profiles_ui">
                <AccountDashboard />
              </HubGate>
            </RequireAuth>
          }
        />
        <Route
          path="/account/profile/preview"
          element={
            <RequireAuth>
              <HubGate flag="community_profiles_ui">
                <ProfilePreview />
              </HubGate>
            </RequireAuth>
          }
        />
        <Route
          path="/account/profile/following"
          element={
            <RequireAuth>
              <HubGate flag="community_profiles_ui">
                <OwnFollowing />
              </HubGate>
            </RequireAuth>
          }
        />
        <Route
          path="/account/profile"
          element={
            <RequireAuth>
              <HubGate flag="community_profiles_ui">
                <AccountProfile />
              </HubGate>
            </RequireAuth>
          }
        />
        <Route
          path="/account/communities"
          element={
            <RequireAuth>
              <HubGate flag="communities_ui">
                <AccountCommunities />
              </HubGate>
            </RequireAuth>
          }
        />
        <Route
          path="/players"
          element={
            <HubGate flag="community_profiles_ui">
              <Players />
            </HubGate>
          }
        />
        <Route
          path="/u/:username"
          element={
            <HubGate flag="community_profiles_ui">
              <PublicProfile />
            </HubGate>
          }
        />
        <Route
          path="/communities"
          element={
            <HubGate flag="communities_ui">
              <Communities />
            </HubGate>
          }
        />
        <Route
          path="/communities/:slug"
          element={
            <HubGate flag="communities_ui">
              <CommunityDetail />
            </HubGate>
          }
        />
        <Route
          path="/cities"
          element={
            <HubGate flag="cities_ui">
              <CityCatalog />
            </HubGate>
          }
        />
        <Route
          path="/groups/new"
          element={
            <RequireAuth>
              <HubGate flag="player_groups_ui">
                <GroupCreate />
              </HubGate>
            </RequireAuth>
          }
        />
        <Route
          path="/groups/:slug"
          element={
            <HubGate flag="player_groups_ui">
              <GroupDetail />
            </HubGate>
          }
        />
        <Route
          path="/groups/:slug/manage"
          element={
            <RequireAuth>
              <HubGate flag="player_groups_ui">
                <GroupManage />
              </HubGate>
            </RequireAuth>
          }
        />
        <Route
          path="/moderation/groups"
          element={
            <RequireAuth>
              <HubGate flag="player_groups_ui">
                <GroupsModeration />
              </HubGate>
            </RequireAuth>
          }
        />
        <Route
          path="/cities/:slug"
          element={
            <HubGate flag="cities_ui">
              <CityDetail />
            </HubGate>
          }
        />
        <Route
          path="/cities/:slug/manage"
          element={
            <RequireAuth>
              <HubGate flag="cities_management_ui">
                <CityManage />
              </HubGate>
            </RequireAuth>
          }
        />
        <Route
          path="/moderation/cities"
          element={
            <RequireAuth>
              <HubGate flag="cities_moderation_ui">
                <CitiesModeration />
              </HubGate>
            </RequireAuth>
          }
        />

        <Route path="/joutak" element={<JouTakRoute />} />
        <Route path="/legacy" element={<Legacy />} />
        <Route path="/minigames" element={<MinigamesRoute />} />
        <Route path="/itmocraft" element={<ItmoCraftRoute legacyAlias />} />
        <Route path="/contact" element={<Contact />} />
        <Route
          path="/account/security"
          element={
            <RequireAuth>
              <AccountSecurity />
            </RequireAuth>
          }
        />
        <Route
          path="/account/onboarding"
          element={
            <RequireAuth>
              <AccountOnboarding />
            </RequireAuth>
          }
        />
        <Route
          path="/account/complete-registration"
          element={
            <RequireAuth>
              <AccountOnboarding />
            </RequireAuth>
          }
        />
        <Route
          path="/account/complete-profile"
          element={
            <RequireAuth>
              <AccountOnboarding />
            </RequireAuth>
          }
        />
        <Route path="/joutak/pay" element={<Pay />} />
        <Route path="/session-expired" element={<SessionExpired />} />
        <Route path="/confirm-email" element={<ConfirmEmail />} />
        <Route path="/reset-password" element={<ResetPassword />} />

        <Route path="/login" element={<LoginModalRoute />} />
        <Route path="*" element={<NotFound />} />
      </Routes>

      {background && (
        <Routes>
          <Route path="/login" element={<LoginModalRoute />} />
        </Routes>
      )}
    </Suspense>
  );
}

export default function App() {
  return (
    <>
      <ScrollToTop />
      <Layout>
        <AppRoutes />
      </Layout>
    </>
  );
}
