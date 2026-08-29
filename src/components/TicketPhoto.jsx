import React, { useState } from 'react';
import { mediaURL } from '../api/client';
import { categoryIcon } from './categoryIcon';

export default function TicketPhoto({ media, category, className, alt }) {
  const [imgFailed, setImgFailed] = useState(false);

  if (media && media.available && !imgFailed) {
    return (
      <img 
        src={mediaURL(media.id)} 
        alt={alt || "Evidence"} 
        loading="lazy" 
        className={`object-cover ${className}`}
        onError={() => setImgFailed(true)}
      />
    );
  } else if (media && (!media.available || imgFailed)) {
    return (
      <div 
        className={`bg-surface-container flex flex-col items-center justify-center shrink-0 overflow-hidden ${className}`}
        title={media.unavailable_reason}
      >
        <span className="material-symbols-outlined text-primary/50">{categoryIcon(category)}</span>
        {media.unavailable_reason && (
          <span className="text-outline text-[10px] leading-tight mt-1 truncate w-full text-center px-1">
            {media.unavailable_reason}
          </span>
        )}
      </div>
    );
  } else {
    return (
      <div className={`bg-surface-container flex items-center justify-center shrink-0 ${className}`}>
        <span className="material-symbols-outlined text-primary/50">{categoryIcon(category)}</span>
      </div>
    );
  }
}
