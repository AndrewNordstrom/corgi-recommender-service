// Diagram zoom functionality for Corgi documentation
// Global diagram enhancement functionality for Corgi documentation
// This script handles:
// 1. Making diagrams zoomable with an overlay when clicked
// 2. Fixing text colors in yellow/amber elements in dark mode
// 3. Ensuring good contrast on all Mermaid diagrams sitewide

document.addEventListener('DOMContentLoaded', function() {
  // Create modal elements
  const modal = document.createElement('div');
  modal.id = 'diagram-modal';
  modal.className = 'diagram-modal';
  modal.innerHTML = `
    <div class="diagram-modal-content">
      <span class="diagram-close">&times;</span>
      <div class="diagram-container"></div>
    </div>
  `;
  document.body.appendChild(modal);

  // Enhance diagram colors for better contrast
  function enhanceDiagramContrast(svg) {
    // Check if we're in dark mode
    const isDarkMode = document.querySelector('body[data-md-color-scheme="slate"]') !== null;
    
    if (isDarkMode) {
      // Target all elements with yellow/amber fills or colors
      svg.querySelectorAll('[fill="#ffb300"], [fill="#FFB300"], [fill="#ffcc80"], [fill="#FFCC80"], [fill="#ffecb3"], [fill="#FFECB3"], [fill="#ffd54f"], [fill="#FFD54F"], [fill="#ffe082"], [fill="#FFE082"], [fill="#ffca28"], [fill="#FFCA28"], [fill="#ffc107"], [fill="#FFC107"]').forEach(el => {
        // Handle nested SVG elements
        const foreignObjects = el.querySelectorAll('foreignObject');
        if (foreignObjects.length > 0) {
          foreignObjects.forEach(foreign => {
            const divs = foreign.querySelectorAll('div');
            divs.forEach(div => {
              div.style.color = '#000000';
              div.style.fontWeight = 'bold';
            });
          });
        }
        
        // Handle text elements
        const texts = el.querySelectorAll('text');
        texts.forEach(text => {
          text.setAttribute('fill', '#000000');
          text.style.fontWeight = 'bold';
        });
        
        // If this element itself is a text with a yellow fill
        if (el.tagName.toLowerCase() === 'text') {
          el.setAttribute('fill', '#000000');
          el.style.fontWeight = 'bold';
        }
      });
      
      // Specifically handle subgraph cluster labels (they're a special case in Mermaid)
      svg.querySelectorAll('.cluster-label').forEach(label => {
        const textEls = label.querySelectorAll('text');
        textEls.forEach(text => {
          text.setAttribute('fill', '#000000');
          text.style.fontWeight = 'bold';
        });
        
        const foreignObjects = label.querySelectorAll('foreignObject');
        foreignObjects.forEach(foreign => {
          const divs = foreign.querySelectorAll('div');
          divs.forEach(div => {
            div.style.color = '#000000';
            div.style.fontWeight = 'bold';
          });
        });
      });
      
      // Handle elements with inline style using fill:#ffb300
      svg.querySelectorAll('*').forEach(el => {
        const style = el.getAttribute('style');
        if (style && style.includes('fill:#ffb300')) {
          // Find all text elements within this element
          const textEls = el.querySelectorAll('text');
          textEls.forEach(text => {
            text.setAttribute('fill', '#000000');
            text.style.fontWeight = 'bold';
          });
          
          // If the element is a text with fill:#ffb300
          if (el.tagName.toLowerCase() === 'text') {
            el.setAttribute('fill', '#000000');
            el.style.fontWeight = 'bold';
          }
          
          // Handle any foreignObject divs
          const divs = el.querySelectorAll('foreignObject div');
          divs.forEach(div => {
            div.style.color = '#000000';
            div.style.fontWeight = 'bold';
          });
        }
      });
      
      // Target any subgraphs that have the yellow background and ensure their titles have black text
      // This is specific to the diagram in the proxy.md file
      svg.querySelectorAll('.cluster').forEach(cluster => {
        const rect = cluster.querySelector('rect');
        if (rect && (rect.getAttribute('fill') === '#ffb300' || 
                    (rect.getAttribute('style') && 
                     rect.getAttribute('style').includes('fill:#ffb300')))) {
          const label = cluster.querySelector('.cluster-label');
          if (label) {
            const text = label.querySelector('text');
            if (text) {
              text.setAttribute('fill', '#000000');
              text.style.fontWeight = 'bold';
            }
            
            const divs = label.querySelectorAll('div');
            divs.forEach(div => {
              div.style.color = '#000000';
              div.style.fontWeight = 'bold'; 
            });
          }
        }
      });
    }
    
    return svg;
  }

  // Get all SVG diagrams (rendered from Mermaid)
  function initDiagrams() {
    // Wait for Mermaid to render SVGs
    setTimeout(() => {
      const diagrams = document.querySelectorAll('.mermaid svg');
      
      diagrams.forEach(svg => {
        // Skip already processed diagrams
        if (svg.parentElement.classList.contains('diagram-zoomable')) return;
        
        // Make container zoomable
        svg.parentElement.classList.add('diagram-zoomable');
        
        // Add cursor style to indicate it's clickable
        svg.style.cursor = 'zoom-in';
        
        // Apply contrast improvements
        enhanceDiagramContrast(svg);
        
        // Add click event
        svg.addEventListener('click', function(e) {
          e.preventDefault();
          openModal(this);
        });
      });
    }, 1000); // Wait for Mermaid rendering
  }

  // Function to open modal with diagram
  function openModal(svg) {
    const modal = document.getElementById('diagram-modal');
    const container = modal.querySelector('.diagram-container');
    
    // Clone the SVG and adjust it for the modal
    const clonedSvg = svg.cloneNode(true);
    
    // Enhance contrast in the modal view (again, to be sure)
    enhanceDiagramContrast(clonedSvg);
    
    // Clear previous content
    container.innerHTML = '';
    container.appendChild(clonedSvg);
    
    // Show modal
    modal.style.display = 'flex';
    
    // Add max dimensions to the SVG
    clonedSvg.style.width = '100%';
    clonedSvg.style.height = 'auto';
    clonedSvg.style.maxHeight = '90vh';
  }

  // Close modal when clicking the × button
  document.querySelector('.diagram-close').addEventListener('click', function() {
    document.getElementById('diagram-modal').style.display = 'none';
  });

  // Close modal when clicking outside the content
  window.addEventListener('click', function(event) {
    const modal = document.getElementById('diagram-modal');
    if (event.target === modal) {
      modal.style.display = 'none';
    }
  });

  // Handle dark mode changes
  function handleColorSchemeChange() {
    const diagrams = document.querySelectorAll('.mermaid svg');
    diagrams.forEach(svg => {
      enhanceDiagramContrast(svg);
    });
    
    // Check for any elements with amber/yellow fills regardless of case
    document.querySelectorAll('.mermaid rect[fill^="#ff"], .mermaid rect[fill^="#FF"], .mermaid polygon[fill^="#ff"], .mermaid polygon[fill^="#FF"]').forEach(el => {
      // Get all text elements that are siblings or children of this element
      const parentGroup = el.closest('g');
      if (parentGroup) {
        const textElements = parentGroup.querySelectorAll('text');
        textElements.forEach(text => {
          text.setAttribute('fill', '#000000');
          text.style.fontWeight = 'bold';
        });
      }
    });
    
    // Enhance any other SVG elements that might have yellow backgrounds
    document.querySelectorAll('svg g').forEach(g => {
      const fill = g.getAttribute('fill');
      if (fill && fill.startsWith('#ff')) {
        const textElements = g.querySelectorAll('text');
        textElements.forEach(text => {
          text.setAttribute('fill', '#000000');
          text.style.fontWeight = 'bold';
        });
      }
    });
  }

  // Watch for theme changes
  const observer = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
      if (mutation.type === 'attributes' && mutation.attributeName === 'data-md-color-scheme') {
        handleColorSchemeChange();
      }
      if (mutation.type === 'childList') {
        initDiagrams();
      }
    });
  });
  
  // Initialize on page load
  initDiagrams();
  
  // Observe the document body for content changes and theme changes
  observer.observe(document.body, { 
    childList: true, 
    subtree: true,
    attributes: true,
    attributeFilter: ['data-md-color-scheme']
  });

  // Add keyboard support for ESC to close modal
  document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape' && modal.style.display === 'flex') {
      modal.style.display = 'none';
    }
  });
});