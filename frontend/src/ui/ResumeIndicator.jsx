import { memo } from 'react';

function ResumeIndicator({ myStats, onResume }) {
  if (!myStats?.path_queue?.length) return null;
  return (
    <div className="side-tag side-tag--resume" onClick={onResume} title="Resume path">
      <span style={{ fontSize: 16 }}>▶</span>
    </div>
  );
}

export default memo(ResumeIndicator);
