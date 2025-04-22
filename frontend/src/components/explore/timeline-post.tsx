"use client"

import Image from 'next/image'
import { formatDate } from '@/lib/utils'
import { Heart, RefreshCw, MessageCircle, Star } from 'lucide-react'
import { motion } from 'framer-motion'

type PostProps = {
  post: {
    id: string;
    account: {
      id: string;
      username: string;
      display_name: string;
      avatar: string;
      url: string;
    };
    content: string;
    created_at: string;
    media_attachments: any[];
    favourites_count: number;
    reblogs_count: number;
    replies_count: number;
    tags: string[];
    is_recommendation?: boolean;
  }
}

export default function TimelinePost({ post }: PostProps) {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`border rounded-lg p-4 ${
        post.is_recommendation 
          ? 'border-primary bg-primary/5 dark:bg-primary/10 relative overflow-hidden' 
          : 'border-neutral-200 dark:border-neutral-700'
      }`}
    >
      {post.is_recommendation && (
        <div className="absolute top-0 right-0">
          <div className="bg-primary text-neutral-900 text-xs font-bold py-1 px-2 rounded-bl-md">
            Recommended
          </div>
        </div>
      )}
      
      <div className="flex">
        <div className="flex-shrink-0 mr-3">
          <a 
            href={post.account.url} 
            target="_blank" 
            rel="noopener noreferrer"
            className="block transition-opacity hover:opacity-80"
          >
            <Image 
              src={post.account.avatar} 
              alt={post.account.display_name}
              width={48}
              height={48}
              className="rounded-full"
            />
          </a>
        </div>
        
        <div className="flex-1">
          <div className="flex items-baseline">
            <a 
              href={post.account.url} 
              target="_blank" 
              rel="noopener noreferrer"
              className="hover:underline"
            >
              <h3 className="font-bold text-neutral-900 dark:text-neutral-100">
                {post.account.display_name}
              </h3>
            </a>
            <a 
              href={post.account.url} 
              target="_blank" 
              rel="noopener noreferrer"
              className="ml-2 text-sm text-neutral-500 hover:underline"
            >
              @{post.account.username}
            </a>
            <span className="ml-auto text-xs text-neutral-500">
              {formatDate(new Date(post.created_at))}
            </span>
          </div>
          
          <div 
            className="mt-2 text-neutral-800 dark:text-neutral-200"
            dangerouslySetInnerHTML={{ __html: post.content }}
          />
          
          {post.tags.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-2">
              {post.tags.map(tag => (
                <span 
                  key={tag} 
                  className="bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300 text-xs px-2 py-1 rounded"
                >
                  #{tag}
                </span>
              ))}
            </div>
          )}
          
          <div className="mt-3 flex items-center text-neutral-500 gap-4">
            <div className="flex items-center">
              <Heart className="h-4 w-4 mr-1" />
              <span className="text-xs">{post.favourites_count}</span>
            </div>
            
            <div className="flex items-center">
              <RefreshCw className="h-4 w-4 mr-1" />
              <span className="text-xs">{post.reblogs_count}</span>
            </div>
            
            <div className="flex items-center">
              <MessageCircle className="h-4 w-4 mr-1" />
              <span className="text-xs">{post.replies_count}</span>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  )
}