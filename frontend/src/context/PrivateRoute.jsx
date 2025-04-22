import React, { useContext } from "react";
import { AuthContext } from "./AuthContext";
import { Navigate } from "react-router-dom";

function PrivateRoute({ children }) {
  const { authState } = useContext(AuthContext);
  const { isAuthenticated } = authState;
  console.log("PrivateRoute:", { isAuthenticated });

  return isAuthenticated ? children : <Navigate to="/login" replace />;
}

export default PrivateRoute;