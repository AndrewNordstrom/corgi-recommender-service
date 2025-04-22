// PostComponent.jsx - A React component for displaying Mastodon posts in Elk

import React from 'react';
import './PostComponent.css'; // You'd need to create this CSS file based on the styles below

const formatDate = (dateString) => {
  const date = new Date(dateString);
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date);
};

const PostComponent = ({ post }) => {
  return (
    <div className={`post ${post.is_recommendation ? 'post--recommendation' : ''}`}>
      {/* Post header with user info */}
      <div className="post__header">
        {/* Avatar (clickable) */}
        <a 
          href={post.account.url} 
          target="_blank"
          rel="noopener noreferrer" 
          className="post__avatar-link"
        >
          <img 
            src={post.account.avatar} 
            alt={post.account.display_name} 
            className="post__avatar" 
          />
        </a>
        
        <div className="post__user-info">
          {/* Display name (clickable) */}
          <a 
            href={post.account.url} 
            target="_blank"
            rel="noopener noreferrer" 
            className="post__display-name"
          >
            {post.account.display_name}
          </a>
          
          {/* Username (clickable) */}
          <a 
            href={post.account.url} 
            target="_blank"
            rel="noopener noreferrer" 
            className="post__username"
          >
            @{post.account.username}
          </a>
          
          {/* Timestamp */}
          <span className="post__timestamp">
            {formatDate(post.created_at)}
          </span>
        </div>
      </div>
      
      {/* Post content */}
      <div 
        className="post__content" 
        dangerouslySetInnerHTML={{ __html: post.content }}
      ></div>
      
      {/* Post media attachments (if any) */}
      {post.media_attachments && post.media_attachments.length > 0 && (
        <div className="post__media">
          {post.media_attachments.map((media, index) => (
            <div key={index} className="post__media-item">
              {media.type === 'image' ? (
                <img 
                  src={media.url}
                  alt={media.description || ''}
                  className="post__media-image"
                />
              ) : media.type === 'video' ? (
                <video 
                  src={media.url}
                  controls
                  className="post__media-video"
                ></video>
              ) : null}
            </div>
          ))}
        </div>
      )}
      
      {/* Post tags */}
      {post.tags && post.tags.length > 0 && (
        <div className="post__tags">
          {post.tags.map((tag) => (
            <span 
              key={tag}
              className="post__tag"
            >
              #{tag}
            </span>
          ))}
        </div>
      )}
      
      {/* Post actions */}
      <div className="post__actions">
        <button className="post__action post__action--like">
          <span className="post__action-icon">❤️</span>
          <span className="post__action-count">{post.favourites_count}</span>
        </button>
        
        <button className="post__action post__action--boost">
          <span className="post__action-icon">🔄</span>
          <span className="post__action-count">{post.reblogs_count}</span>
        </button>
        
        <button className="post__action post__action--reply">
          <span className="post__action-icon">💬</span>
          <span className="post__action-count">{post.replies_count}</span>
        </button>
      </div>
    </div>
  );
};

export default PostComponent;