// Collapsible sections functionality
document.addEventListener('DOMContentLoaded', function() {
    // Initialize all collapsible sections
    initializeCollapsibleSections();
});

function initializeCollapsibleSections() {
    const collapsibleHeaders = document.querySelectorAll('.collapsible-header');
    
    collapsibleHeaders.forEach(header => {
        // Add click event listener
        header.addEventListener('click', function() {
            toggleCollapsibleSection(this);
        });
        
        // Add keyboard support
        header.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                toggleCollapsibleSection(this);
            }
        });
        
        // Make header focusable for accessibility
        header.setAttribute('tabindex', '0');
        header.setAttribute('role', 'button');
        header.setAttribute('aria-expanded', 'false');
    });
}

function toggleCollapsibleSection(header) {
    const content = header.nextElementSibling;
    const toggle = header.querySelector('.collapsible-toggle');
    const isExpanded = content.classList.contains('expanded');
    
    if (isExpanded) {
        // Collapse the section
        content.classList.remove('expanded');
        toggle.classList.remove('expanded');
        header.setAttribute('aria-expanded', 'false');
    } else {
        // Expand the section
        content.classList.add('expanded');
        toggle.classList.add('expanded');
        header.setAttribute('aria-expanded', 'true');
    }
}

// Function to expand all sections (useful for form validation)
function expandAllSections() {
    const collapsibleHeaders = document.querySelectorAll('.collapsible-header');
    collapsibleHeaders.forEach(header => {
        const content = header.nextElementSibling;
        if (!content.classList.contains('expanded')) {
            toggleCollapsibleSection(header);
        }
    });
}

// Function to collapse all sections
function collapseAllSections() {
    const collapsibleHeaders = document.querySelectorAll('.collapsible-header');
    collapsibleHeaders.forEach(header => {
        const content = header.nextElementSibling;
        if (content.classList.contains('expanded')) {
            toggleCollapsibleSection(header);
        }
    });
}

// Function to expand a specific section by ID
function expandSection(sectionId) {
    const header = document.querySelector(`#${sectionId} .collapsible-header`);
    if (header) {
        const content = header.nextElementSibling;
        if (!content.classList.contains('expanded')) {
            toggleCollapsibleSection(header);
        }
    }
}

// Function to collapse a specific section by ID
function collapseSection(sectionId) {
    const header = document.querySelector(`#${sectionId} .collapsible-header`);
    if (header) {
        const content = header.nextElementSibling;
        if (content.classList.contains('expanded')) {
            toggleCollapsibleSection(header);
        }
    }
}

// Export functions for global use
window.expandAllSections = expandAllSections;
window.collapseAllSections = collapseAllSections;
window.expandSection = expandSection;
window.collapseSection = collapseSection;
