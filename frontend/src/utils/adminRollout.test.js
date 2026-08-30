import { describe, expect, it } from "vitest";

describe("guided rollout admin behavior", () => {
  it("keeps reviewed groups, toggles targets, and suggests non-default values", async () => {
    document.body.innerHTML = `
      <select id="id_feature">
        <option value="ordinary" selected>Ordinary</option>
        <option value="design">Design</option>
      </select>
      <select id="id_value"><option value="false" selected>Off</option></select>
      <select id="id_page"><option value="account">Account</option></select>
      <select id="id_audience"><option value="group" selected>Group</option></select>
      <div data-field="target_groups">
        <select id="id_target_groups" multiple>
          <option value="1" selected>QA</option>
          <option value="2">Design testers</option>
        </select>
      </div>
      <div data-field="target_users"></div>
      <div data-field="percentage"></div>
      <div data-field="confirm_dangerous"></div>
      <div data-field="page"></div>
    `;
    const feature = document.getElementById("id_feature");
    feature.dataset.registryOptions = JSON.stringify({
      ordinary: {
        title: "Ordinary",
        key: "ordinary",
        default: "On",
        suggested_value: "false",
        values: [
          ["true", "On"],
          ["false", "Off"],
        ],
        pages: [["account", "Account"]],
        audiences: ["group", "percentage"],
        rule_types: [],
        required_group: null,
        required_group_id: null,
      },
      design: {
        title: "Design",
        key: "design",
        default: "Legacy",
        suggested_value: "v2",
        values: [
          ["legacy", "Legacy"],
          ["v2", "New design"],
        ],
        pages: [["", "All pages"]],
        audiences: ["group"],
        rule_types: [["group", "Group"]],
        required_group: "website-design-testers",
        required_group_id: 2,
      },
    });

    await import(
      "../../../backend/featureflags/static/featureflags/admin_rollout.js"
    );
    document.dispatchEvent(new Event("DOMContentLoaded"));

    const groups = document.getElementById("id_target_groups");
    expect(groups.options[0].selected).toBe(true);
    expect(document.querySelector('[data-field="target_groups"]').hidden).toBe(
      false,
    );

    const audience = document.getElementById("id_audience");
    audience.value = "percentage";
    audience.dispatchEvent(new Event("change"));
    expect(document.querySelector('[data-field="target_groups"]').hidden).toBe(
      true,
    );
    expect(document.querySelector('[data-field="percentage"]').hidden).toBe(
      false,
    );
    expect(
      document.querySelector('[data-field="confirm_dangerous"]').hidden,
    ).toBe(false);

    feature.value = "design";
    feature.dispatchEvent(new Event("change"));
    expect(document.getElementById("id_value").value).toBe("v2");
    expect(groups.value).toBe("2");
    expect(groups.options[0].disabled).toBe(true);
    groups.options[1].selected = false;
    groups.dispatchEvent(new Event("change"));
    expect(groups.options[1].selected).toBe(true);

    feature.value = "ordinary";
    feature.dispatchEvent(new Event("change"));
    expect(document.getElementById("id_value").value).toBe("false");
  });
});
