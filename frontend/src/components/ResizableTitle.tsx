import React, { useEffect } from 'react';
import { Resizable, ResizeCallbackData } from 'react-resizable';
import 'react-resizable/css/styles.css';
import './ResizableTitle.css';

interface ResizableTitleProps {
  onResize?: (e: React.SyntheticEvent, data: ResizeCallbackData) => void;
  width?: number;
  [key: string]: any;
}

const ResizableTitle: React.FC<ResizableTitleProps> = (props) => {
  const { onResize, width, ...restProps } = props;
  const [isResizing, setIsResizing] = React.useState(false);

  useEffect(() => {
    if (isResizing) {
      document.body.classList.add('resizing-column');
    } else {
      document.body.classList.remove('resizing-column');
    }
    return () => {
      document.body.classList.remove('resizing-column');
    };
  }, [isResizing]);

  if (!width) {
    return <th {...restProps} />;
  }

  const handleResizeStart = (e: React.SyntheticEvent) => {
    setIsResizing(true);
    e.stopPropagation();
  };

  const handleResizeStop = () => {
    setIsResizing(false);
  };

  return (
    <Resizable
      width={width}
      height={0}
      handle={
        <span
          className="react-resizable-handle"
          onClick={(e) => {
            e.stopPropagation();
          }}
          onMouseDown={handleResizeStart}
          onMouseUp={handleResizeStop}
        />
      }
      onResize={onResize || (() => {})}
      onResizeStop={handleResizeStop}
      draggableOpts={{ enableUserSelectHack: false }}
    >
      <th {...restProps} />
    </Resizable>
  );
};

export default ResizableTitle;
