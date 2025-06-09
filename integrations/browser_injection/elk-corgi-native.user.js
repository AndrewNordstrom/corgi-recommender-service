// ==UserScript==
// @name         ELK Native AI Recommendations
// @namespace    http://tampermonkey.net/
// @version      3.0
// @description  Native AI-powered recommendations for ELK (Powered by Corgi)
// @author       ELK Community
// @match        http://localhost:3004/*
// @match        https://elk.zone/*
// @grant        none
// @run-at       document-end
// ==/UserScript==

(function() {
    'use strict';
    
    console.log('🤖 ELK AI Recommendations initializing...');
    
    const CORGI_API_URL = 'http://localhost:9999';
    
    // Ultra-native ELK integration - uses their exact design system
    const ELK_NATIVE = {
        // Matches ELK's StatusCard component exactly
        post: 'relative border-b border-border bg-base hover:bg-active/5 transition-all duration-200',
        content: 'px-4 py-3 relative',
        
        // Matches ELK's user display components
        header: 'flex items-center space-x-3 mb-2',
        avatar: 'w-12 h-12 rounded-full flex-shrink-0 bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center',
        userInfo: 'flex-1 min-w-0',
        displayName: 'font-semibold text-base leading-5 text-primary break-all',
        handle: 'text-sm text-secondary break-all',
        timestamp: 'text-sm text-secondary whitespace-nowrap',
        
        // Matches ELK's content styling
        postContent: 'mt-2 text-base leading-6 text-base break-words',
        
        // Native ELK action buttons
        actions: 'flex items-center justify-between mt-3 pt-2 max-w-md',
        actionBtn: 'flex items-center space-x-1 py-2 px-3 rounded-full transition-all duration-200 text-sm font-medium text-secondary',
        
        // AI-specific but native-feeling
        aiIndicator: 'inline-flex items-center space-x-1 px-2 py-1 rounded-full text-xs font-medium bg-primary/8 text-primary border border-primary/15',
        aiInsight: 'mt-3 p-3 rounded-lg bg-muted/25 border border-border/30'
    };
    
    class NativeAIEngine {
        constructor() {
            this.container = null;
            this.initialized = false;
        }
        
        async init() {
            if (this.initialized) return;
            
            await this.waitForELK();
            this.injectNativeStyles();
            this.findTimelineContainer();
            await this.loadAIContent();
            this.setupAutoRefresh();
            this.setupNavigation();
            
            this.initialized = true;
            console.log('✅ ELK AI integrated natively');
        }
        
        async waitForELK() {
            return new Promise(resolve => {
                const check = () => {
                    const main = document.querySelector('main');
                    if (main && main.offsetHeight > 100) {
                        resolve();
                    } else {
                        setTimeout(check, 300);
                    }
                };
                check();
            });
        }
        
        injectNativeStyles() {
            const style = document.createElement('style');
            style.textContent = `
                /* Ultra-native ELK AI styles */
                .elk-ai-post {
                    animation: elk-natural-fade 0.4s ease-out;
                }
                
                .elk-ai-post::before {
                    content: '';
                    position: absolute;
                    left: 0;
                    top: 0;
                    bottom: 0;
                    width: 1px;
                    background: var(--c-primary);
                    opacity: 0.3;
                }
                
                .elk-ai-enhanced {
                    background: linear-gradient(135deg, 
                        var(--c-bg-base) 0%, 
                        var(--c-primary-fade) 0.3%, 
                        var(--c-bg-base) 100%);
                }
                
                @keyframes elk-natural-fade {
                    from { opacity: 0; transform: translateY(4px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                
                .elk-ai-btn:hover {
                    transform: scale(1.02);
                }
                
                .elk-ai-btn:active {
                    transform: scale(0.98);
                }
                
                .elk-ai-indicator {
                    background: linear-gradient(45deg, var(--c-primary-fade), var(--c-primary-light));
                    backdrop-filter: blur(8px);
                }
            `;
            document.head.appendChild(style);
        }
        
        findTimelineContainer() {
            const main = document.querySelector('main');
            
            // Try ELK's common timeline selectors
            const candidates = [
                main.querySelector('[role="feed"]'),
                main.querySelector('.timeline'),
                main.querySelector('main > div:first-child'),
                main.querySelector('main > div > div:first-child')
            ].filter(Boolean);
            
            this.container = candidates.find(c => c.offsetHeight > 200) || candidates[0];
            
            if (!this.container) {
                // Create native-style container
                this.container = document.createElement('div');
                this.container.setAttribute('role', 'feed');
                this.container.className = 'elk-ai-timeline';
                (main.querySelector('div') || main).appendChild(this.container);
            }
        }
        
        async loadAIContent() {
            try {
                const response = await fetch(`${CORGI_API_URL}/api/v1/timelines/home`);
                const posts = await response.json();
                
                // Clear previous AI posts
                this.container.querySelectorAll('.elk-ai-post').forEach(p => p.remove());
                
                // Render with ultra-native styling
                posts.forEach(post => {
                    const element = this.createNativePost(post);
                    this.container.appendChild(element);
                });
                
                console.log(`🤖 Rendered ${posts.length} AI posts natively`);
                
            } catch (error) {
                console.warn('AI temporarily unavailable');
            }
        }
        
        createNativePost(post) {
            const article = document.createElement('article');
            const isAI = post.is_recommendation;
            
            // Ultra-native class composition
            article.className = [
                'elk-ai-post',
                ELK_NATIVE.post,
                isAI ? 'elk-ai-enhanced' : ''
            ].filter(Boolean).join(' ');
            
            // Native accessibility
            article.setAttribute('role', 'article');
            article.setAttribute('tabindex', '0');
            article.setAttribute('aria-label', isAI ? 'AI-recommended post' : 'Timeline post');
            
            const emoji = isAI ? '🤖' : '📰';
            const name = isAI ? 'AI Curator' : 'Timeline';
            const handle = isAI ? '@ai.elk' : '@feed';
            
            article.innerHTML = `
                <div class="${ELK_NATIVE.content}">
                    <div class="${ELK_NATIVE.header}">
                        <div class="${ELK_NATIVE.avatar}">
                            <span class="text-lg">${emoji}</span>
                        </div>
                        
                        <div class="${ELK_NATIVE.userInfo}">
                            <div class="flex items-center space-x-2 flex-wrap">
                                <span class="${ELK_NATIVE.displayName}">${name}</span>
                                <span class="${ELK_NATIVE.handle}">${handle}</span>
                                <span class="${ELK_NATIVE.timestamp}">
                                    ${this.formatTime(post.created_at)}
                                </span>
                                ${isAI ? `
                                    <span class="${ELK_NATIVE.aiIndicator} elk-ai-indicator">
                                        <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
                                        </svg>
                                        <span>AI</span>
                                    </span>
                                ` : ''}
                            </div>
                        </div>
                    </div>
                    
                    <div class="${ELK_NATIVE.postContent}">
                        ${this.enhanceContent(post.content || post.text || 'AI-curated content')}
                    </div>
                    
                    ${isAI && post.recommendation_reason ? `
                        <div class="${ELK_NATIVE.aiInsight}">
                            <div class="flex items-start space-x-2">
                                <svg class="w-4 h-4 text-primary mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/>
                                </svg>
                                <p class="text-sm text-secondary leading-relaxed">
                                    ${post.recommendation_reason}
                                </p>
                            </div>
                        </div>
                    ` : ''}
                    
                    <div class="${ELK_NATIVE.actions}">
                        ${this.createNativeAction('reply', 'Reply', 'hover:bg-blue-500/10 hover:text-blue-600')}
                        ${this.createNativeAction('boost', 'Boost', 'hover:bg-green-500/10 hover:text-green-600')}
                        ${this.createNativeAction('like', 'Like', 'hover:bg-red-500/10 hover:text-red-600')}
                        ${this.createNativeAction('share', 'Share', 'hover:bg-muted/50')}
                    </div>
                </div>
            `;
            
            this.attachNativeHandlers(article);
            return article;
        }
        
        createNativeAction(type, label, hoverClass) {
            const icons = {
                reply: 'M2.25 12.76c0 1.6 1.123 2.994 2.707 3.227 1.068.157 2.148.279 3.238.364.466.037.893.281 1.153.671L12 19.764l2.652-2.742c.26-.39.687-.634 1.153-.671 1.09-.085 2.17-.207 3.238-.364 1.584-.233 2.707-1.627 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z',
                boost: 'M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15',
                like: 'M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z',
                share: 'M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.367 2.684 3 3 0 00-5.367-2.684z'
            };
            
            return `
                <button class="${ELK_NATIVE.actionBtn} ${hoverClass} elk-ai-btn" 
                        data-action="${type}" 
                        aria-label="${label}">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="${icons[type]}"/>
                    </svg>
                    <span class="hidden sm:inline">${label}</span>
                </button>
            `;
        }
        
        attachNativeHandlers(article) {
            article.addEventListener('click', (e) => {
                const btn = e.target.closest('button[data-action]');
                if (!btn) return;
                
                // Native ELK-style feedback
                btn.style.transform = 'scale(0.95)';
                setTimeout(() => btn.style.transform = '', 150);
                
                const action = btn.dataset.action;
                this.handleNativeAction(action, btn);
            });
        }
        
        handleNativeAction(action, button) {
            switch(action) {
                case 'boost':
                    button.classList.toggle('text-green-600');
                    break;
                case 'like':
                    button.classList.toggle('text-red-600');
                    break;
                case 'reply':
                    console.log('💬 AI post reply');
                    break;
                case 'share':
                    console.log('📤 AI post share');
                    break;
            }
        }
        
        enhanceContent(content) {
            // Process like native ELK
            return content
                .replace(/(@\w+)/g, '<span class="text-primary font-medium">$1</span>')
                .replace(/(#\w+)/g, '<span class="text-primary font-medium">$1</span>')
                .replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" class="text-primary hover:underline" target="_blank" rel="noopener">$1</a>');
        }
        
        formatTime(timestamp) {
            if (!timestamp) return 'now';
            
            const date = new Date(timestamp);
            const now = new Date();
            const diff = Math.floor((now - date) / 60000);
            
            if (diff < 1) return 'now';
            if (diff < 60) return `${diff}m`;
            if (diff < 1440) return `${Math.floor(diff / 60)}h`;
            return date.toLocaleDateString();
        }
        
        setupAutoRefresh() {
            setInterval(() => {
                this.loadAIContent();
            }, 300000); // 5 minutes
        }
        
        setupNavigation() {
            let lastUrl = location.href;
            new MutationObserver(() => {
                if (location.href !== lastUrl) {
                    lastUrl = location.href;
                    if (location.href.includes('/home')) {
                        setTimeout(() => this.init(), 500);
                    }
                }
            }).observe(document, { subtree: true, childList: true });
        }
    }
    
    // Initialize the native AI engine
    const aiEngine = new NativeAIEngine();
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => aiEngine.init());
    } else {
        aiEngine.init();
    }
    
    // Expose for debugging
    window.ELKNativeAI = aiEngine;
    
})(); 