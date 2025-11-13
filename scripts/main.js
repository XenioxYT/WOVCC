document.addEventListener("DOMContentLoaded", function () {
    // Mark page as loaded to prevent flash
    document.body.classList.add('page-loaded');
    
    const navToggle = document.querySelector(".nav-toggle");
    const navMenu = document.querySelector(".nav-menu");
    if (navToggle && navMenu) {
        navToggle.addEventListener("click", function () {
            const isActive = navMenu.classList.contains("active");
            navMenu.classList.toggle("active");
            navToggle.setAttribute("aria-expanded", !isActive);
            
            // Lock/unlock body scroll
            if (!isActive) {
                document.body.style.overflow = 'hidden';
            } else {
                document.body.style.overflow = '';
            }
        });
        document.addEventListener("click", function (event) {
            if (!navToggle.contains(event.target) && !navMenu.contains(event.target)) {
                navMenu.classList.remove("active");
                navToggle.setAttribute("aria-expanded", "false");
                document.body.style.overflow = '';
            }
        });
        const navLinks = navMenu.querySelectorAll(".nav-link");
        navLinks.forEach((link) => {
            link.addEventListener("click", function () {
                navMenu.classList.remove("active");
                navToggle.setAttribute("aria-expanded", "false");
                document.body.style.overflow = '';
            });
        });
        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape" && navMenu.classList.contains("active")) {
                navMenu.classList.remove("active");
                navToggle.setAttribute("aria-expanded", "false");
                navToggle.focus();
                document.body.style.overflow = '';
            }
        });
    }
    highlightActivePage();
    setupNewsletterForm();
});

// Re-initialize on page transitions
document.addEventListener('pageTransitionComplete', function() {
    highlightActivePage();
    setupNewsletterForm();
    document.body.classList.add('page-loaded');
});

function highlightActivePage() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll(".nav-link");
    navLinks.forEach((link) => {
        const href = link.getAttribute("href");
        if (href === currentPath || (currentPath === "/" && href === "/")) {
            link.classList.add("active");
        } else {
            link.classList.remove("active");
        }
    });
}
function setupNewsletterForm() {
    const forms = document.querySelectorAll(".newsletter-form,.newsletter-form-main");
    forms.forEach((form) => {
        if (form) {
            form.addEventListener("submit", async function (e) {
                e.preventDefault();
                const emailInput = form.querySelector('input[type="email"]');
                const email = emailInput.value.trim();
                
                if (!email) {
                    showNotification("Please enter a valid email address.", "error");
                    return;
                }
                
                // Get the button for loading state
                const submitButton = form.querySelector('button[type="submit"]');
                const originalButtonText = submitButton ? submitButton.textContent : '';
                
                try {
                    // Show loading state
                    if (submitButton) {
                        submitButton.disabled = true;
                        submitButton.textContent = 'Subscribing...';
                    }
                    
                    // Call the newsletter subscription API
                    const response = await fetch('/api/newsletter/subscribe', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ email: email })
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        if (result.already_subscribed) {
                            showNotification("You're already subscribed to our newsletter!", "info");
                        } else {
                            showNotification("Thank you for subscribing to our newsletter!", "success");
                        }
                        emailInput.value = "";
                    } else {
                        showNotification(result.error || "Failed to subscribe. Please try again.", "error");
                    }
                } catch (error) {
                    console.error('Newsletter subscription error:', error);
                    showNotification("An error occurred. Please try again later.", "error");
                } finally {
                    // Restore button state
                    if (submitButton) {
                        submitButton.disabled = false;
                        submitButton.textContent = originalButtonText;
                    }
                }
            });
        }
    });
}
function showNotification(message, type = "info") {
    const existing = document.querySelector(".notification-toast");
    if (existing) {
        existing.remove();
    }
    const icons = {
        success:
            '<svg width="20" height="20" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>',
        error: '<svg width="20" height="20" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/></svg>',
        info: '<svg width="20" height="20" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/></svg>',
        warning:
            '<svg width="20" height="20" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>',
    };
    const colors = {
        success: { bg: "#10b981", text: "#ffffff" },
        error: { bg: "#ef4444", text: "#ffffff" },
        info: { bg: "#3b82f6", text: "#ffffff" },
        warning: { bg: "#f59e0b", text: "#ffffff" },
    };
    const color = colors[type] || colors.info;
    const icon = icons[type] || icons.info;
    const notification = document.createElement("div");
    notification.className = "notification-toast";
    notification.style.cssText = ` position:fixed;top:90px;right:20px;background-color:${color.bg};color:${color.text};padding:10px 14px;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.15);z-index:10000;max-width:360px;display:flex;align-items:center;gap:10px;animation:toastSlideIn 0.3s cubic-bezier(0.21,1.02,0.73,1);font-family:var(--font-family);font-size:0.875rem;font-weight:500;line-height:1.3;min-height:auto;`;
    notification.innerHTML = `<div style="flex-shrink:0;display:flex;align-items:center;line-height:1;">${icon}</div><div style="flex:1;line-height:1.3;">${message}</div><button class="notification-close-btn" style="background:none;border:none;color:${color.text};cursor:pointer;padding:0;margin:0;width:16px;height:16px;display:flex;align-items:center;justify-content:center;opacity:0.8;flex-shrink:0;line-height:1;"><svg width="14" height="14" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/></svg></button>`;
    
    // Add event listener to close button (no inline onclick)
    const closeBtn = notification.querySelector('.notification-close-btn');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => notification.remove());
    }
    
    document.body.appendChild(notification);
    setTimeout(() => {
        notification.style.animation = "toastSlideOut 0.3s cubic-bezier(0.21,1.02,0.73,1)";
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}
const style = document.createElement("style");
style.textContent = ` @keyframes toastSlideIn{from{transform:translateX(400px);opacity:0;}to{transform:translateX(0);opacity:1;}}@keyframes toastSlideOut{from{transform:translateX(0);opacity:1;}to{transform:translateX(400px);opacity:0;}}.notification-toast button:hover{opacity:1!important;}`;
document.head.appendChild(style);
document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener("click", function (e) {
        const href = this.getAttribute("href");
        if (href !== "#") {
            e.preventDefault();
            const target = document.querySelector(href);
            if (target) {
                target.scrollIntoView({ behavior: "smooth", block: "start" });
            }
        }
    });
});
