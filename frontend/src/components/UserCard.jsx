/* ==========================================================================
   UserCard.jsx -- one person, shown as a card.
   Used on Browse and on Matches (where it also shows a match score).
   ========================================================================== */

import { Link } from 'react-router-dom';
import { Avatar, SkillPill, Stars } from './ui';

export default function UserCard({ person, match, onSwap }) {
  const offered = person.skills_offered || [];
  const wanted = person.skills_wanted || [];

  return (
    <div className="card card-hover col" style={{ gap: 14 }}>
      {/* ---- header ---- */}
      <div className="between" style={{ alignItems: 'flex-start' }}>
        <Link to={`/users/${person.id}`} className="row" style={{ color: 'inherit' }}>
          <Avatar name={person.name} url={person.avatar_url} />
          <div>
            <h3>{person.name}</h3>
            <p className="small muted">{person.location || 'Location not set'}</p>
          </div>
        </Link>

        {match && (
          <div style={{ textAlign: 'right' }}>
            <div className="match-score">{match.score}<span>/100</span></div>
            {match.is_mutual && <span className="badge badge-accepted">mutual</span>}
          </div>
        )}
      </div>

      {/* ---- why this person was suggested ---- */}
      {match?.reason && (
        <p className="small muted" style={{ borderLeft: '2px solid var(--accent)', paddingLeft: 10 }}>
          {match.reason}
        </p>
      )}

      {person.bio && !match && (
        <p className="small muted" style={{
          display: '-webkit-box', WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical', overflow: 'hidden',
        }}>
          {person.bio}
        </p>
      )}

      {/* ---- skills ---- */}
      {offered.length > 0 && (
        <div>
          <p className="small faint mb-1">Can teach</p>
          <div className="row-wrap">
            {offered.slice(0, 4).map((s) => <SkillPill key={s.id} skill={s} />)}
            {offered.length > 4 && <span className="small faint">+{offered.length - 4}</span>}
          </div>
        </div>
      )}

      {wanted.length > 0 && (
        <div>
          <p className="small faint mb-1">Wants to learn</p>
          <div className="row-wrap">
            {wanted.slice(0, 3).map((s) => <SkillPill key={s.id} skill={s} />)}
            {wanted.length > 3 && <span className="small faint">+{wanted.length - 3}</span>}
          </div>
        </div>
      )}

      {/* ---- footer ---- */}
      <div className="between mt-1">
        <Stars value={person.average_rating || 0} count={person.rating_count} />
        <div className="row">
          <Link to={`/users/${person.id}`} className="btn btn-ghost btn-sm">View</Link>
          <button className="btn btn-primary btn-sm" onClick={() => onSwap(person)}>
            Request Swap
          </button>
        </div>
      </div>
    </div>
  );
}
