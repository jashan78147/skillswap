/* ==========================================================================
   ui.jsx -- small building blocks used across every page.
   --------------------------------------------------------------------------
   Each one is a "component": a function that returns markup. Naming them
   with a Capital Letter is what tells React they are components, not
   ordinary HTML tags.
   ========================================================================== */

/* -------------------------------------------------------------- avatar -- */
/** Shows a photo if there is one, otherwise the person's initials. */
export function Avatar({ name = '?', url, size = '' }) {
  const initials = name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0])
    .join('')
    .toUpperCase();

  if (url) {
    return <img className={`avatar ${size}`} src={url} alt={name} />;
  }
  return <div className={`avatar ${size}`} aria-hidden="true">{initials || '?'}</div>;
}

/* --------------------------------------------------------------- stars -- */
/** Read-only star display, e.g. ★★★★☆ */
export function Stars({ value = 0, count }) {
  const filled = Math.round(value);
  return (
    <span className="row" style={{ gap: 6 }}>
      <span className="stars" aria-label={`${value} out of 5 stars`}>
        {[1, 2, 3, 4, 5].map((n) => (
          <span key={n} className={n <= filled ? '' : 'star-empty'}>★</span>
        ))}
      </span>
      {count !== undefined && (
        <span className="small muted">
          {value ? value.toFixed(1) : '—'} {count > 0 && `(${count})`}
        </span>
      )}
    </span>
  );
}

/** Clickable star picker used in the rating form. */
export function StarPicker({ value, onChange }) {
  return (
    <div className="row" style={{ gap: 0 }}>
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          className={`star-input ${n <= value ? 'on' : ''}`}
          onClick={() => onChange(n)}
          aria-label={`${n} star${n > 1 ? 's' : ''}`}
        >
          ★
        </button>
      ))}
    </div>
  );
}

/* --------------------------------------------------------------- pills -- */
export function SkillPill({ skill, onRemove }) {
  const cls = skill.kind === 'offered' ? 'pill pill-offer' : 'pill pill-want';
  return (
    <span className={cls} title={skill.description || skill.name}>
      {skill.name}
      {skill.level && skill.level !== 'intermediate' && (
        <span className="faint small">· {skill.level}</span>
      )}
      {onRemove && (
        <button className="pill-x" onClick={onRemove} aria-label={`Remove ${skill.name}`}>
          ×
        </button>
      )}
    </span>
  );
}

/* -------------------------------------------------------------- badges -- */
export function StatusBadge({ status }) {
  return <span className={`badge badge-${status}`}>{status}</span>;
}

/* ------------------------------------------------------- states/alerts -- */
export function Loading({ label = 'Loading…' }) {
  return (
    <div className="loading">
      <span className="spinner" /> {label}
    </div>
  );
}

export function Empty({ icon = '○', title, hint, action }) {
  return (
    <div className="empty">
      <div className="empty-icon">{icon}</div>
      <h3 className="mb-1">{title}</h3>
      {hint && <p className="small muted">{hint}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

export function Alert({ kind = 'error', children }) {
  if (!children) return null;
  return <div className={`alert alert-${kind}`}>{children}</div>;
}

/* --------------------------------------------------------------- toast -- */
export function Toast({ message, kind = 'success' }) {
  if (!message) return null;
  return <div className={`toast toast-${kind}`}>{message}</div>;
}
