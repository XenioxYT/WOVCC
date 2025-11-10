/**
 * HTML Sanitizer Module
 * Provides secure HTML sanitization to prevent XSS attacks
 */
(function() {
    'use strict';

    /**
     * Escape HTML special characters to prevent XSS
     * @param {string} str - The string to escape
     * @returns {string} - The escaped string
     */
    function escapeHtml(str) {
        if (typeof str !== 'string') {
            return '';
        }
        
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    /**
     * Sanitize HTML by removing dangerous tags and attributes
     * Only allows safe formatting tags
     * @param {string} html - The HTML string to sanitize
     * @returns {string} - The sanitized HTML
     */
    function sanitizeHtml(html) {
        if (typeof html !== 'string') {
            return '';
        }

        // Create a temporary div to parse the HTML
        const temp = document.createElement('div');
        temp.innerHTML = html;

        // Allowed tags (whitelist approach)
        const allowedTags = ['b', 'i', 'u', 'strong', 'em', 'p', 'br', 'span', 'div'];
        
        // Recursively clean the DOM
       function cleanNode(node) {  
            // 1. Recurse on children first (post-order traversal).  
            //    We use a copy of the childNodes array because the list can be mutated.  
            const children = Array.from(node.childNodes);  
            children.forEach(child => cleanNode(child));  

            // 2. Process the node itself now that its children are sanitized.  

            // Remove script and style tags completely  
            if (node.nodeType === Node.ELEMENT_NODE && (node.tagName === 'SCRIPT' || node.tagName === 'STYLE')) {  
                node.remove();  
                return;  
            }  

            // Remove event handlers and javascript: links from allowed tags  
            if (node.nodeType === Node.ELEMENT_NODE) {  
                Array.from(node.attributes).forEach(attr => {  
                    if (attr.name.startsWith('on') || attr.value.toLowerCase().includes('javascript:')) {  
                        node.removeAttribute(attr.name);  
                    }  
                });  

                // If the tag is not allowed, replace it with its (already sanitized) children.  
                if (!allowedTags.includes(node.tagName.toLowerCase())) {  
                    const parent = node.parentNode;  
                    if (parent) {  
                        while (node.firstChild) {  
                            parent.insertBefore(node.firstChild, node);  
                        }  
                        node.remove();  
                    }  
                }  
            }  
        }  

        Array.from(temp.childNodes).forEach(child => cleanNode(child));
        return temp.innerHTML;
    }

    /**
     * Create a text node safely (always safe, no HTML parsing)
     * @param {string} text - The text to display
     * @returns {Text} - A text node
     */
    function createTextNode(text) {
        return document.createTextNode(String(text || ''));
    }

    /**
     * Safely set text content of an element (no HTML interpretation)
     * @param {HTMLElement} element - The element to update
     * @param {string} text - The text to set
     */
    function setTextContent(element, text) {
        if (element && element.nodeType === Node.ELEMENT_NODE) {
            element.textContent = String(text || '');
        }
    }

    /**
     * Safely set innerHTML after sanitization
     * @param {HTMLElement} element - The element to update
     * @param {string} html - The HTML to set
     */
    function setSafeHtml(element, html) {
        if (element && element.nodeType === Node.ELEMENT_NODE) {
            element.innerHTML = sanitizeHtml(html);
        }
    }

    // Export functions to global scope
    window.HTMLSanitizer = {
        escapeHtml,
        sanitizeHtml,
        createTextNode,
        setTextContent,
        setSafeHtml
    };
})();
