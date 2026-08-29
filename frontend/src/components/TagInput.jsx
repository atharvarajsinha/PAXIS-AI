import { useState } from 'react';
import { CloseIcon, PlusIcon } from './icons.jsx';

/**
 * Free-text list editor. Enter or comma commits an entry; Backspace on an empty
 * field removes the last one.
 */
export default function TagInput({ id, label, hint, placeholder, suggestions = [], values, onChange }) {
  const [draft, setDraft] = useState('');

  const add = (raw) => {
    const value = raw.trim();
    if (!value) return;
    if (values.some((existing) => existing.toLowerCase() === value.toLowerCase())) {
      setDraft('');
      return;
    }
    onChange([...values, value]);
    setDraft('');
  };

  const remove = (index) => onChange(values.filter((_, i) => i !== index));

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' || event.key === ',') {
      event.preventDefault();
      add(draft);
    } else if (event.key === 'Backspace' && !draft && values.length) {
      remove(values.length - 1);
    }
  };

  const unusedSuggestions = suggestions.filter(
    (suggestion) => !values.some((value) => value.toLowerCase() === suggestion.toLowerCase()),
  );

  return (
    <div className="tagField">
      <label htmlFor={id}>{label}</label>
      {hint && <p className="fieldHint">{hint}</p>}

      <div className="tagBox">
        {values.map((value, index) => (
          <span className="tag" key={`${value}-${index}`}>
            {value}
            <button
              type="button"
              onClick={() => remove(index)}
              aria-label={`Remove ${value}`}
              title={`Remove ${value}`}
            >
              <CloseIcon size={12} />
            </button>
          </span>
        ))}
        <input
          id={id}
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={() => add(draft)}
          placeholder={values.length ? '' : placeholder}
        />
      </div>

      {unusedSuggestions.length > 0 && (
        <div className="suggestions">
          <span>Quick add:</span>
          {unusedSuggestions.slice(0, 8).map((suggestion) => (
            <button type="button" key={suggestion} onClick={() => add(suggestion)}>
              <PlusIcon size={12} /> {suggestion}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
