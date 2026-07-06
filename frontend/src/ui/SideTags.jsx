import { memo } from 'react';

function SideTags({ children }) {
  return <div className="side-tags">{children}</div>;
}

export default memo(SideTags);
