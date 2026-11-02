import { useState } from "react";

import { saveMembershipVisibility } from "../../services/api/citiesApi";
import { extractErrorMessage } from "../../services/errors";
import { visibilityLabels } from "../hub/labels";

export default function MembershipVisibility({ membership }) {
  const [visibility, setVisibility] = useState(membership.visibility);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function update(value) {
    setBusy(true);
    setError("");
    try {
      await saveMembershipVisibility(membership.slug, value);
      setVisibility(value);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="hub-form">
      <label>
        Кто видит моё членство
        <select
          disabled={busy}
          value={visibility}
          onChange={(e) => update(e.target.value)}
        >
          {Object.entries(visibilityLabels).map(([v, label]) => (
            <option key={v} value={v}>
              {label}
            </option>
          ))}
        </select>
      </label>
      {error && <p role="alert">{error}</p>}
    </div>
  );
}
