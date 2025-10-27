/**
 * JOBMATCH PRO - Main JavaScript
 * Modern utilities and interactions
 */

// ==========================================
// DOM Utilities
// ==========================================
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => document.querySelectorAll(selector);

// ==========================================
// Alert System
// ==========================================
const showAlert = (message, type = 'info', duration = 5000) => {
    const alertContainer = $('#alert-container') || createAlertContainer();

    const alert = document.createElement('div');
    alert.className = `alert alert-${type} animate-fadeIn`;
    alert.innerHTML = `
        <div class="flex items-center gap-3">
            <span class="alert-icon">${getAlertIcon(type)}</span>
            <span class="alert-message">${message}</span>
        </div>
        <button class="alert-close" onclick="this.parentElement.remove()">×</button>
    `;

    alertContainer.appendChild(alert);

    if (duration > 0) {
        setTimeout(() => alert.remove(), duration);
    }
};

const createAlertContainer = () => {
    const container = document.createElement('div');
    container.id = 'alert-container';
    container.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        max-width: 400px;
    `;
    document.body.appendChild(container);
    return container;
};

const getAlertIcon = (type) => {
    const icons = {
        success: '✓',
        error: '✕',
        warning: '⚠',
        info: 'ℹ'
    };
    return icons[type] || icons.info;
};

// ==========================================
// Form Validation
// ==========================================
const validateForm = (formElement) => {
    const inputs = formElement.querySelectorAll('[required]');
    let isValid = true;

    inputs.forEach(input => {
        if (!input.value.trim()) {
            input.classList.add('error');
            isValid = false;
        } else {
            input.classList.remove('error');
        }
    });

    return isValid;
};

// ==========================================
// Loading States
// ==========================================
const setLoading = (element, isLoading = true) => {
    if (isLoading) {
        element.disabled = true;
        element.dataset.originalText = element.innerHTML;
        element.innerHTML = `<span class="spinner"></span> Chargement...`;
    } else {
        element.disabled = false;
        element.innerHTML = element.dataset.originalText;
    }
};

// ==========================================
// Smooth Scroll
// ==========================================
const smoothScroll = (target) => {
    const element = typeof target === 'string' ? $(target) : target;
    if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
};

// ==========================================
// Debounce & Throttle
// ==========================================
const debounce = (func, wait) => {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
};

const throttle = (func, limit) => {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
};

// ==========================================
// API Helper
// ==========================================
const api = {
    async get(url) {
        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            showAlert('Erreur de connexion au serveur', 'error');
            throw error;
        }
    },

    async post(url, data) {
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            showAlert('Erreur de connexion au serveur', 'error');
            throw error;
        }
    },

    async upload(url, formData) {
        try {
            const response = await fetch(url, {
                method: 'POST',
                body: formData
            });
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error('Upload Error:', error);
            showAlert('Erreur lors de l\'upload', 'error');
            throw error;
        }
    }
};

// ==========================================
// Local Storage Helper
// ==========================================
const storage = {
    set(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (e) {
            console.error('Storage Error:', e);
        }
    },

    get(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (e) {
            console.error('Storage Error:', e);
            return defaultValue;
        }
    },

    remove(key) {
        localStorage.removeItem(key);
    },

    clear() {
        localStorage.clear();
    }
};

// ==========================================
// Tab System
// ==========================================
const initTabs = (containerSelector) => {
    const container = $(containerSelector);
    if (!container) return;

    const tabs = container.querySelectorAll('[data-tab]');
    const contents = container.querySelectorAll('[data-tab-content]');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const targetId = tab.dataset.tab;

            // Remove active class from all tabs
            tabs.forEach(t => t.classList.remove('active'));
            contents.forEach(c => c.classList.remove('active'));

            // Add active class to clicked tab and corresponding content
            tab.classList.add('active');
            const targetContent = container.querySelector(`[data-tab-content="${targetId}"]`);
            if (targetContent) {
                targetContent.classList.add('active');
            }
        });
    });
};

// ==========================================
// Modal System
// ==========================================
const modal = {
    open(modalId) {
        const modalElement = $(`#${modalId}`);
        if (modalElement) {
            modalElement.classList.add('active');
            document.body.style.overflow = 'hidden';
        }
    },

    close(modalId) {
        const modalElement = $(`#${modalId}`);
        if (modalElement) {
            modalElement.classList.remove('active');
            document.body.style.overflow = '';
        }
    },

    closeAll() {
        $$('.modal').forEach(m => m.classList.remove('active'));
        document.body.style.overflow = '';
    }
};

// ==========================================
// Dropdown System
// ==========================================
const initDropdowns = () => {
    $$('[data-dropdown-toggle]').forEach(toggle => {
        toggle.addEventListener('click', (e) => {
            e.stopPropagation();
            const targetId = toggle.dataset.dropdownToggle;
            const dropdown = $(`#${targetId}`);
            if (dropdown) {
                dropdown.classList.toggle('active');
            }
        });
    });

    // Close dropdowns when clicking outside
    document.addEventListener('click', () => {
        $$('[data-dropdown]').forEach(dropdown => {
            dropdown.classList.remove('active');
        });
    });
};

// ==========================================
// Copy to Clipboard
// ==========================================
const copyToClipboard = async (text) => {
    try {
        await navigator.clipboard.writeText(text);
        showAlert('Copié dans le presse-papier!', 'success', 2000);
    } catch (err) {
        console.error('Failed to copy:', err);
        showAlert('Erreur lors de la copie', 'error');
    }
};

// ==========================================
// Format Helpers
// ==========================================
const formatDate = (dateString) => {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('fr-FR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    }).format(date);
};

const formatNumber = (number) => {
    return new Intl.NumberFormat('fr-FR').format(number);
};

const formatCurrency = (amount, currency = 'EUR') => {
    return new Intl.NumberFormat('fr-FR', {
        style: 'currency',
        currency: currency
    }).format(amount);
};

// ==========================================
// Progress Bar
// ==========================================
const updateProgress = (elementId, percent) => {
    const progressBar = $(`#${elementId}`);
    if (progressBar) {
        progressBar.style.width = `${percent}%`;
        progressBar.setAttribute('aria-valuenow', percent);
        progressBar.textContent = `${percent}%`;
    }
};

// ==========================================
// Initialize on DOM Ready
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    // Initialize dropdowns
    initDropdowns();

    // Close modals on backdrop click
    $$('.modal-backdrop').forEach(backdrop => {
        backdrop.addEventListener('click', () => modal.closeAll());
    });

    // Close modals on ESC key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') modal.closeAll();
    });

    // Add smooth scroll to all anchor links
    $$('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', (e) => {
            e.preventDefault();
            const target = $(anchor.getAttribute('href'));
            if (target) smoothScroll(target);
        });
    });

    console.log('🚀 JobMatch Pro initialized');
});

// Export for global use
window.JobMatch = {
    $,
    $$,
    showAlert,
    validateForm,
    setLoading,
    smoothScroll,
    debounce,
    throttle,
    api,
    storage,
    initTabs,
    modal,
    copyToClipboard,
    formatDate,
    formatNumber,
    formatCurrency,
    updateProgress
};
