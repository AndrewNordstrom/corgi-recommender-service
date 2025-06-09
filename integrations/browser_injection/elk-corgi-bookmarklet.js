// ELK-Corgi One-Click Bookmarklet
// Drag this to your bookmarks bar or save as bookmark
// Bookmark URL: javascript:(function(){var script=document.createElement('script');script.src='data:text/javascript;base64,'+btoa(`

// Compressed version of the auto-integration script
(function() {
    'use strict';
    
    console.log('🐕 ELK-Corgi One-Click Integration');
    
    // Check if already injected
    if (document.querySelector('.corgi-post')) {
        console.log('✅ Corgi already integrated, refreshing...');
        document.querySelectorAll('.corgi-post').forEach(p => p.remove());
    }
    
    const CORGI_API_URL = 'http://localhost:9999';
    
    async function quickInject() {
        try {
            // Find container
            const main = document.querySelector('main');
            let container = main.querySelector('.corgi-timeline');
            
            if (!container) {
                container = document.createElement('div');
                container.className = 'corgi-timeline space-y-0';
                const target = main.querySelector('div') || main;
                target.appendChild(container);
            }
            
            // Fetch and inject
            const response = await fetch(CORGI_API_URL + '/api/v1/timelines/home');
            const posts = await response.json();
            
            posts.forEach(post => {
                const article = document.createElement('article');
                article.className = 'corgi-post border-b border-border bg-base p-4 hover:bg-muted/25 transition-colors';
                
                if (post.is_recommendation) {
                    article.style.borderLeft = '2px solid #eab308';
                    article.style.background = 'linear-gradient(90deg, rgba(254,249,195,0.1) 0%, transparent 100%)';
                }
                
                article.innerHTML = \`
                    <div class="flex gap-3">
                        <div class="w-12 h-12 rounded-full bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center">
                            <span class="text-lg">\${post.is_recommendation ? '✨' : '🐕'}</span>
                        </div>
                        <div class="flex-1 min-w-0">
                            <div class="flex items-center gap-2 flex-wrap">
                                <span class="font-semibold text-primary">Corgi \${post.is_recommendation ? 'Recommendations' : 'Feed'}</span>
                                <span class="text-sm text-muted-foreground">@corgi</span>
                                <span class="text-sm text-muted-foreground">\${new Date().toLocaleTimeString()}</span>
                                \${post.is_recommendation ? '<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-500/10 text-yellow-600 border border-yellow-500/20">✨ Recommended</span>' : ''}
                            </div>
                            <div class="mt-2 text-base leading-relaxed text-foreground">
                                \${post.content || post.text || 'Content'}
                            </div>
                            \${post.recommendation_reason ? \`
                                <div class="mt-3 p-3 rounded-lg bg-muted/30 border border-border/50">
                                    <div class="flex items-start gap-2">
                                        <span class="text-yellow-500 mt-0.5">💡</span>
                                        <span class="text-sm text-muted-foreground">\${post.recommendation_reason}</span>
                                    </div>
                                </div>
                            \` : ''}
                        </div>
                    </div>
                \`;
                
                container.appendChild(article);
            });
            
            console.log(\`🎉 Injected \${posts.length} posts via bookmarklet!\`);
            
        } catch (error) {
            console.error('❌ Bookmarklet error:', error);
            alert('Corgi integration failed. Make sure the API is running on localhost:9999');
        }
    }
    
    quickInject();
})();

`);document.head.appendChild(script);})();

// Human-readable bookmarklet URL (copy this entire line as bookmark URL):
// javascript:(function(){var s=document.createElement('script');s.textContent='(function(){console.log("🐕 ELK-Corgi One-Click");if(document.querySelector(".corgi-post")){console.log("✅ Refreshing...");document.querySelectorAll(".corgi-post").forEach(p=>p.remove());}async function inject(){try{const main=document.querySelector("main");let container=main.querySelector(".corgi-timeline");if(!container){container=document.createElement("div");container.className="corgi-timeline space-y-0";(main.querySelector("div")||main).appendChild(container);}const response=await fetch("http://localhost:9999/api/v1/timelines/home");const posts=await response.json();posts.forEach(post=>{const article=document.createElement("article");article.className="corgi-post border-b border-border bg-base p-4 hover:bg-muted/25 transition-colors";if(post.is_recommendation){article.style.borderLeft="2px solid #eab308";article.style.background="linear-gradient(90deg, rgba(254,249,195,0.1) 0%, transparent 100%)";}article.innerHTML=`<div class="flex gap-3"><div class="w-12 h-12 rounded-full bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center"><span class="text-lg">${post.is_recommendation?"✨":"🐕"}</span></div><div class="flex-1 min-w-0"><div class="flex items-center gap-2 flex-wrap"><span class="font-semibold text-primary">Corgi ${post.is_recommendation?"Recommendations":"Feed"}</span><span class="text-sm text-muted-foreground">@corgi</span><span class="text-sm text-muted-foreground">${new Date().toLocaleTimeString()}</span>${post.is_recommendation?`<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-500/10 text-yellow-600 border border-yellow-500/20">✨ Recommended</span>`:""}</div><div class="mt-2 text-base leading-relaxed text-foreground">${post.content||post.text||"Content"}</div>${post.recommendation_reason?`<div class="mt-3 p-3 rounded-lg bg-muted/30 border border-border/50"><div class="flex items-start gap-2"><span class="text-yellow-500 mt-0.5">💡</span><span class="text-sm text-muted-foreground">${post.recommendation_reason}</span></div></div>`:""}</div></div>`;container.appendChild(article);});console.log(`🎉 Injected ${posts.length} posts!`);}catch(error){console.error("❌ Error:",error);alert("Corgi integration failed. API running on localhost:9999?");}}inject();})();';document.head.appendChild(s);})(); 