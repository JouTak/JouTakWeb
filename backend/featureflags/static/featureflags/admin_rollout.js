(function () {
  "use strict";

  function toggleFields() {
    const audience = document.getElementById("id_audience");
    const ruleType = document.getElementById("id_rule_type");
    const scope = document.getElementById("id_scope_type");
    const page = document.getElementById("id_page");
    const selected = audience ? audience.value : ruleType ? ruleType.value : "";
    const visibility = {
      target_groups: selected === "group",
      target_users: selected === "users" || selected === "user_allowlist" || selected === "user_denylist",
      anonymous_ids: selected === "anonymous_allowlist" || selected === "anonymous_denylist",
      percentage: selected === "percentage",
      value: !["user_denylist", "anonymous_denylist"].includes(selected),
      confirm_dangerous: ["authenticated", "percentage", "everyone"].includes(selected),
      target_user: scope ? scope.value === "user" : false,
      anonymous_scope: scope ? scope.value === "anonymous" : false,
      confirm_global: scope ? scope.value === "global" : false,
      page: page ? page.options.length > 1 : false,
    };
    Object.entries(visibility).forEach(function ([name, visible]) {
      const row = document.querySelector(".field-" + name + ", [data-field='" + name + "']");
      if (row) row.hidden = !visible;
    });
  }

  function replaceOptions(select, choices, preferredValue) {
    if (!select || !choices) return;
    const preferred =
      preferredValue === undefined ? select.value : String(preferredValue);
    select.replaceChildren();
    choices.forEach(function (choice) {
      const option = document.createElement("option");
      option.value = choice[0];
      option.textContent = choice[1];
      option.selected = choice[0] === preferred;
      select.appendChild(option);
    });
    if (select.selectedIndex < 0 && select.options.length) {
      select.selectedIndex = 0;
    }
  }

  function setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value || "—";
  }

  function configureRegistryFields(event) {
    const feature = document.getElementById("id_feature");
    if (!feature || !feature.dataset.registryOptions) return;
    let registry;
    try {
      registry = JSON.parse(feature.dataset.registryOptions);
    } catch (_error) {
      return;
    }
    const selected = registry[feature.value];
    if (!selected) return;
    setText("rollout-feature-title", selected.title);
    setText("rollout-feature-key", selected.key);
    setText("rollout-feature-description", selected.description);
    setText("rollout-feature-impact", selected.visual_impact);
    setText(
      "rollout-feature-default",
      selected.default +
        (selected.sticky
          ? " (ранее назначенный вариант может быть закреплён)"
          : ""),
    );
    const featureChanged = event && event.type === "change";
    replaceOptions(
      document.getElementById("id_value"),
      selected.values,
      featureChanged ? selected.suggested_value : undefined,
    );
    replaceOptions(document.getElementById("id_page"), selected.pages);
    const audienceLabels = {
      group: "Группа тестировщиков",
      users: "Выбранные пользователи",
      staff: "Сотрудники",
      authenticated: "Все авторизованные",
      percentage: "Процент аудитории",
      everyone: "Все посетители",
    };
    replaceOptions(
      document.getElementById("id_audience"),
      selected.audiences.map(function (value) {
        return [value, audienceLabels[value] || value];
      })
    );
    replaceOptions(
      document.getElementById("id_rule_type"),
      selected.rule_types,
    );
    const groups = document.getElementById("id_target_groups");
    if (groups) {
      const required = String(selected.required_group_id || "");
      const previousRequired = groups.dataset.requiredGroupId || "";
      Array.from(groups.options).forEach(function (option) {
        if (required) {
          option.disabled = option.value !== required;
          option.selected = option.value === required;
        } else {
          option.disabled = false;
          if (previousRequired && option.value === previousRequired) {
            option.selected = false;
          }
        }
      });
      groups.dataset.requiredGroup = selected.required_group || "";
      groups.dataset.requiredGroupId = required;
      groups.setAttribute("aria-readonly", required ? "true" : "false");
    }
    toggleFields();
  }

  document.addEventListener("DOMContentLoaded", function () {
    ["id_audience", "id_rule_type", "id_scope_type"].forEach(function (id) {
      const input = document.getElementById(id);
      if (input) input.addEventListener("change", toggleFields);
    });
    const feature = document.getElementById("id_feature");
    if (feature) feature.addEventListener("change", configureRegistryFields);
    const groups = document.getElementById("id_target_groups");
    if (groups) {
      groups.addEventListener("change", function () {
        const required = groups.dataset.requiredGroupId;
        if (!required) return;
        Array.from(groups.options).forEach(function (option) {
          option.selected = option.value === required;
        });
      });
    }
    configureRegistryFields();
    toggleFields();
  });
})();
