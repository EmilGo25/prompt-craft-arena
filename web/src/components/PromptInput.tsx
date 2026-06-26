import { useState } from "react";

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
    return (
      <div className="prompt-locked">
        ✓ Prompt locked in — waiting for the other players…
      </div>
    );
  }

  return (
    <form className="prompt-form" onSubmit={submit}>
      <textarea
        className="prompt-box"
        placeholder="Describe the target image as precisely as you can…"
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
        <span className="prompt-hint">Pasting is disabled — type your prompt.</span>
        <button className="btn btn-primary" type="submit" disabled={disabled || !value.trim()}>
          Submit prompt
        </button>
      </div>
    </form>
  );
}
