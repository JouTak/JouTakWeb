import { Navigate, useParams } from "react-router-dom";
export default function CityManage() {
  const { slug } = useParams();
  return (
    <Navigate
      to={`/cities/${encodeURIComponent(slug)}?edit=identity`}
      replace
    />
  );
}
