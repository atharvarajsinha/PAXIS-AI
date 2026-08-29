import { useRef, useState, useEffect } from 'react';
import html2pdf from 'html2pdf.js';
import {
  BookIcon,
  BriefcaseIcon,
  CalendarIcon,
  CheckIcon,
  CircleCheckIcon,
  DownloadIcon,
  GoalIcon,
  LoaderIcon,
  PinIcon,
  RoadmapIcon,
  SkillIcon,
  SparklesIcon,
  TrendingUpIcon,
  VideoIcon,
  WebsiteIcon,
} from './icons.jsx';

// Cycled per stage so a long roadmap still reads as distinct cards.
const STEP_ICONS = [BookIcon, TrendingUpIcon, SkillIcon, BriefcaseIcon, GoalIcon];
const STEP_TINTS = ['#f3e8ff', '#e0f2fe', '#dcfce7', '#fef3c7', '#ffe4e6'];

const safeStr = (val) => {
  if (val == null) return '';
  if (typeof val === 'string') return val;
  if (typeof val === 'number' || typeof val === 'boolean') return String(val);
  try { return JSON.stringify(val); } catch (e) { return ''; }
};

function ResourceLinks({ material }) {
  return (
    <div className="resourceLinks">
      {material?.website?.url && typeof material.website.url === 'string' && (
        <a href={material.website.url} target="_blank" rel="noopener noreferrer" aria-label={`Open ${safeStr(material.website.name)}`} title={safeStr(material.website.name)}>
          <WebsiteIcon className="resourceIcon websiteIcon" size={16} aria-hidden="true" />
          <span>Learn on {safeStr(material.website.name)}</span>
        </a>
      )}
      {material?.youtube?.url && typeof material.youtube.url === 'string' && (
        <a href={material.youtube.url} target="_blank" rel="noopener noreferrer" aria-label={`Watch ${safeStr(material.youtube.title)}`} title={safeStr(material.youtube.title)}>
          <VideoIcon className="resourceIcon youtubeIcon" size={16} aria-hidden="true" />
          <span>Watch on YouTube</span>
        </a>
      )}
    </div>
  );
}

export default function RoadmapPanel({ roadmap, loading, statusText, onTrack, saveState = 'idle' }) {
  const printRef = useRef(null);

  const handleDownloadPDF = () => {
    const element = printRef.current;
    if (!element) return;
    const opt = {
      margin: 10,
      filename: 'PAXIS_AI_Learning_Roadmap.pdf',
      image: { type: 'jpeg', quality: 0.98 },
      html2canvas: { scale: 2, useCORS: true },
      jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
    };
    html2pdf().set(opt).from(element).save();
  };

  const [activeStepIndex, setActiveStepIndex] = useState(0);

  useEffect(() => {
    if (!loading) {
      if (roadmap && Array.isArray(roadmap.steps)) {
        setActiveStepIndex(roadmap.steps.length - 1);
      } else {
        setActiveStepIndex(0);
      }
      return;
    }

    if (typeof statusText === 'string' && roadmap && Array.isArray(roadmap.steps)) {
      const matchIndex = roadmap.steps.findIndex(s => 
        Array.isArray(s.topics) && s.topics.some(t => typeof t === 'string' && statusText.includes(t))
      );
      if (matchIndex > activeStepIndex) {
        setActiveStepIndex(matchIndex);
      }
    }
  }, [statusText, loading, roadmap, activeStepIndex]);

  if (!roadmap) {
    return (
      <aside className="roadmapCard empty">
        {loading && statusText ? (
          <div className="statusOverlay">
            <div className="emptyIcon spin"><LoaderIcon size={34} /></div>
            <h2>Typing...</h2>
            <p>{statusText}</p>
          </div>
        ) : (
          <>
            <div className="emptyIcon"><RoadmapIcon size={34} /></div>
            <h2>Your Personalized Learning Path</h2>
            <p>Tell me your learning goal in the chat and I'll create your roadmap.</p>
            <div className="hint">PAXIS AI can make mistakes. Check important information.</div>
          </>
        )}
      </aside>
    );
  }

  const stepsToRender = (Array.isArray(roadmap.steps) ? roadmap.steps : []).slice(0, activeStepIndex + 1);

  return (
    <aside className="roadmapCard">
      <div className="roadmapHeader flex-between hide-on-print">
        <div className="roadmapHeaderLeft">
          <div className="heroIcon"><SparklesIcon size={20} /></div>
          <div>
            <h2>Your Personalized Learning Path</h2>
            <p>A step-by-step roadmap tailored for your goal</p>
          </div>
        </div>
        <div className="roadmapHeaderActions">
          {onTrack && Array.isArray(roadmap.steps) && roadmap.steps.length > 0 && (
            <button
              className={saveState === 'saved' ? 'ghostBtn trackedBtn' : 'primaryBtn small'}
              onClick={onTrack}
              disabled={loading || saveState !== 'idle'}
              title={
                saveState === 'saved'
                  ? 'This roadmap is already on your dashboard'
                  : 'Save this roadmap to your dashboard and tick off stages as you go'
              }
            >
              {saveState === 'saving' && (<><LoaderIcon size={16} className="spin" /> <span>Saving...</span></>)}
              {saveState === 'saved' && (<><CircleCheckIcon size={16} /> <span>Tracking on your dashboard</span></>)}
              {saveState === 'idle' && (<><PinIcon size={16} /> <span>Track this roadmap</span></>)}
            </button>
          )}
          <button className="ghostBtn" onClick={handleDownloadPDF}>
            <DownloadIcon size={16} /> <span>Download PDF</span>
          </button>
        </div>
      </div>

      <div ref={printRef} style={{ padding: '5px' }}>
        <div className="roadmapGoalCard">
          <div className="goalCardLeft">
            <div className="goalIcon"><GoalIcon size={20} /></div>
            <div>
              <p>Goal</p>
              <h3>{roadmap.goal ? safeStr(roadmap.goal) : 'Personalized Learning Goal'}</h3>
            </div>
          </div>
          <div className="goalCardStats">
            <div className="statItem">
              <span className="statIcon"><CalendarIcon size={16} /></span>
              <div>
                <p>Timeline</p>
                <strong>{roadmap.duration ? safeStr(roadmap.duration) : 'Flexible timeline'}</strong>
              </div>
            </div>
            <div className="statItem">
              <span className="statIcon"><TrendingUpIcon size={16} /></span>
              <div>
                <p>Level</p>
                <strong>{roadmap.starting_level ? safeStr(roadmap.starting_level) : 'Level not specified'}</strong>
              </div>
            </div>
          </div>
        </div>

        {loading && statusText && (
          <div className="miniSection hide-on-print" style={{ display: 'flex', alignItems: 'center', gap: '10px', backgroundColor: '#fef3c7', color: '#b45309', borderColor: '#fde68a' }}>
            <LoaderIcon size={16} className="spin" />
            <strong style={{ margin: 0 }}>{statusText}</strong>
          </div>
        )}

        <div className="timeline">
          {stepsToRender.map((step, index) => {
            const isSearchingStep = loading && index === activeStepIndex && statusText.includes('Searching');
            
            return (
              <div className="timelineItem" key={`${safeStr(step?.title) || 'step'}-${index}`}>
                <div className="stepBadge">{index + 1}</div>
                <div className="stepCard" style={isSearchingStep ? { border: '2px solid #7e57ff' } : {}}>
                  <div className="stepCardIcon" style={{ backgroundColor: STEP_TINTS[index % STEP_TINTS.length] }}>
                    {(() => {
                      const StepIcon = STEP_ICONS[index % STEP_ICONS.length];
                      return <StepIcon size={20} />;
                    })()}
                  </div>
                  <div className="stepCardContent">
                    <div className="stepHeader">
                      <h3>{safeStr(step?.title)}</h3>
                      <div className="stepDurationBadge">{step?.duration ? safeStr(step.duration) : `Stage ${index + 1}`}</div>
                    </div>
                    <p>{safeStr(step?.description)}</p>
                    
                    {isSearchingStep && (
                      <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', color: '#7e57ff', fontSize: '13px', fontWeight: 600, marginTop: '10px', background: 'rgba(126, 87, 255, 0.1)', padding: '4px 10px', borderRadius: '12px' }}>
                        <LoaderIcon size={14} className="spin" /> {statusText}
                      </div>
                    )}
                    
                    <ul>
                      {(Array.isArray(step?.topics) ? step.topics : []).map((topic, i) => <li key={i}>{typeof topic === 'string' ? topic : 'Invalid topic'}</li>)}
                    </ul>
                    {step.study_material && (
                      <div className="studyMaterial">
                        <strong>Study Material</strong>
                        <ResourceLinks material={step.study_material} />
                      </div>
                    )}
                    {(Array.isArray(step?.topic_materials) ? step.topic_materials : []).map((item, i) => (
                      <div className="studyMaterial" key={safeStr(item?.topic) || i}>
                        <strong>{safeStr(item?.topic)}</strong>
                        <ResourceLinks material={item?.study_material} />
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
        {!loading && Array.isArray(roadmap.projects) && roadmap.projects.length > 0 && (
          <div className="miniSection">
            <h3>Projects</h3>
            {roadmap.projects.map((p, i) => (
              <p key={i}><CheckIcon size={15} /> {typeof p === 'string' ? p : 'Invalid project'}</p>
            ))}
          </div>
        )}
        {!loading && roadmap.next_action && (
          <div className="nextAction"><strong>Next action:</strong> {safeStr(roadmap.next_action)}</div>
        )}
      </div>
    </aside>
  );
}
