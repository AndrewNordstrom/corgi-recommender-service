// A simplified React component for Elk that focuses on the profile elements
import React from 'react';
import './PostComponentSimple.css'; // You'd need to create this CSS file separately

const PostComponentSimple = ({ status }) => {
  return (
    <div className="status">
      {/* User profile section */}
      <div className="status__profile">
        {/* Avatar with link to profile */}
        <a 
          href={status.account.url} 
          target="_blank" 
          rel="noopener noreferrer"
          className="status__avatar-link"
        >
          <img 
            src={status.account.avatar} 
            alt={status.account.display_name} 
            className="status__avatar" 
          />
        </a>
        
        {/* User info section */}
        <div className="status__user-info">
          {/* Display name with link to profile */}
          <a 
            href={status.account.url} 
            target="_blank" 
            rel="noopener noreferrer"
            className="status__display-name"
          >
            <span className="status__name">{status.account.display_name}</span>
          </a>
          
          {/* Username with link to profile */}
          <a 
            href={status.account.url} 
            target="_blank" 
            rel="noopener noreferrer"
            className="status__username"
          >
            @{status.account.username}
          </a>
        </div>
      </div>
      
      {/* Status content (keep your existing content rendering) */}
      <div 
        className="status__content" 
        dangerouslySetInnerHTML={{ __html: status.content }}
      ></div>
      
      {/* Your existing status interactions would go here */}
    </div>
  );
};

export default PostComponentSimple;