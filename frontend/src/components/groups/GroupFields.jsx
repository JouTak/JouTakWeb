import { TextArea, TextInput } from "@gravity-ui/uikit";
import { useId } from "react";

export function GroupText({ label, value, onChange, multiline, ...props }) {
  const id = useId();
  const Input = multiline ? TextArea : TextInput;
  return (
    <label htmlFor={id}>
      {label}
      <Input id={id} value={value ?? ""} onUpdate={onChange} {...props} />
    </label>
  );
}
export function GroupSelect({ label, value, options, onChange, ...props }) {
  return (
    <label>
      {label}
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        {...props}
      >
        {Object.entries(options).map(([key, title]) => (
          <option value={key} key={key}>
            {title}
          </option>
        ))}
      </select>
    </label>
  );
}
