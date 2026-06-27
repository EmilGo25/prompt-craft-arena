import { useState } from "react";
import { useTranslation } from "../i18n";

/**
 * Prompt entry with paste disabled (anti-cheat deterrent). Blocks paste, drop,
 * and drag-in. This is a soft deterrent for a casual game, not a security
 * boundary — a determined user can still bypass it via devtools.
 */
export function PromptInput({
  disabled,
  submitted,
  onSubmit,
}: {
  disabled: boolean;
  submitted: boolean;
  onSubmit: (prompt: string) => void;
}) {
  const { t } = useTranslation();
  const [value, setValue] = useState("");

  const block = (e: React.SyntheticEvent) => {
    e.preventDefault();
  };

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const v = value.trim();
    if (v && !disabled && !submitted) onSubmit(v);
  };

  if (submitted) {
    return <div className="prompt-locked">{t("prompting.locked")}</div>;
  }

  return (
    <form className="prompt-form" onSubmit={submit}>
      <textarea
        className="prompt-box"
        placeholder={t("prompting.placeholder")}
        value={value}
        maxLength={1000}
        disabled={disabled}
        onChange={(e) => setValue(e.target.value)}
        onPaste={block}
        onDrop={block}
        onDragOver={block}
        autoFocus
      />
      <div className="prompt-row">
        <span className="prompt-hint">{t("prompting.pasteDisabled")}</span>
        <button className="btn btn-primary" type="submit" disabled={disabled || !value.trim()}>
          {t("prompting.submitBtn")}
        </button>
      </div>
    </form>
  );
}
