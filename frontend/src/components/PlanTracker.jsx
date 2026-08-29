import { ProjectIcon, VideoIcon, WebsiteIcon } from './icons.jsx';

function ResourceLink({ material }) {
  if (!material) return null;
  return (
    <div className="resourceLinks">
      {material.website?.url && (
        <a href={material.website.url} target="_blank" rel="noopener noreferrer">
          <WebsiteIcon className="resourceIcon websiteIcon" size={15} aria-hidden="true" />
          <span>{material.website.name || 'Read'}</span>
        </a>
      )}
      {material.youtube?.url && (
        <a href={material.youtube.url} target="_blank" rel="noopener noreferrer">
          <VideoIcon className="resourceIcon youtubeIcon" size={15} aria-hidden="true" />
          <span>Watch on YouTube</span>
        </a>
      )}
    </div>
  );
}

/** Expanded view of one plan: tick stages off and see milestones move. */
export default function PlanTracker({ plan, busyIds, onToggle }) {
  const byTopic = (step) => step.study_material?.by_topic || {};

  return (
    <div className="planTracker">
      <ol className="trackerSteps">
        {plan.steps.map((step) => (
          <li key={step.id} className={step.is_completed ? 'done' : ''}>
            <label className="trackerCheck">
              <input
                type="checkbox"
                checked={step.is_completed}
                disabled={busyIds.includes(`step-${step.id}`)}
                onChange={(e) => onToggle('step', step.id, e.target.checked)}
              />
              <span className="checkMark" aria-hidden="true" />
              <span className="trackerBody">
                <strong>{step.title}</strong>
                {step.duration && <em>{step.duration}</em>}
                {step.description && <p>{step.description}</p>}
                {step.topics?.length > 0 && (
                  <span className="topicChips">
                    {step.topics.map((topic) => (
                      <span key={topic}>{topic}</span>
                    ))}
                  </span>
                )}
              </span>
            </label>

            <ResourceLink material={step.study_material?.default} />
            {Object.entries(byTopic(step)).map(([topic, material]) => (
              <div className="topicMaterial" key={topic}>
                <small>{topic}</small>
                <ResourceLink material={material} />
              </div>
            ))}
          </li>
        ))}
      </ol>

      {plan.milestones.length > 0 && (
        <div className="trackerMilestones">
          <h4>Milestones</h4>
          <ul>
            {plan.milestones.map((milestone) => (
              <li key={milestone.id}>
                <label className="trackerCheck compact">
                  <input
                    type="checkbox"
                    checked={milestone.is_completed}
                    disabled={busyIds.includes(`milestone-${milestone.id}`)}
                    onChange={(e) => onToggle('milestone', milestone.id, e.target.checked)}
                  />
                  <span className="checkMark" aria-hidden="true" />
                  <span>{milestone.title}</span>
                </label>
              </li>
            ))}
          </ul>
        </div>
      )}

      {plan.projects?.length > 0 && (
        <div className="trackerMilestones">
          <h4>Projects to build</h4>
          <ul className="plainList">
            {plan.projects.map((project) => (
              <li key={project}>
                <ProjectIcon size={15} /> {project}
              </li>
            ))}
          </ul>
        </div>
      )}

      {plan.next_action && (
        <div className="nextAction">
          <strong>Next action:</strong> {plan.next_action}
        </div>
      )}
    </div>
  );
}
