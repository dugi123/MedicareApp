// Main JavaScript for Medicare Website

// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap components
    initBootstrapComponents();
    
    // Animate elements on scroll
    initScrollAnimations();
    
    // Initialize statistics counters
    initCounters();
    
    // Form validation
    initFormValidation();
    
    // Authentication form validation
    validateAuthForms();
});

// Initialize Bootstrap Tooltips, Popovers, etc.
function initBootstrapComponents() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Initialize hero carousel
    const heroCarousel = document.getElementById('heroCarousel');
    if (heroCarousel) {
        // Initialize carousel using Bootstrap's data attributes
        // The carousel will be initialized automatically by Bootstrap
        console.log('Hero carousel initialized');
    }
}

// Animate elements when they come into view
function initScrollAnimations() {
    // Get all elements with the animate-up class
    const animateElements = document.querySelectorAll('.animate-up');
    
    // Create an observer
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, { threshold: 0.1 });
    
    // Observe each element
    animateElements.forEach(element => {
        observer.observe(element);
    });
}

// Animate counters in statistics section
function initCounters() {
    // Check if the stats section exists
    const statsSection = document.querySelector('.stats-number');
    if (!statsSection) return;
    
    // Get all counter elements
    const counters = document.querySelectorAll('.stats-number');
    
    // Create an observer for the counters
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                // Get the target number
                const target = parseInt(entry.target.innerText);
                // Start from zero
                let count = 0;
                // Update the count every 30ms
                const updateCount = setInterval(() => {
                    // Calculate the increment (faster for bigger numbers)
                    const increment = target / 30;
                    count += increment;
                    // Update the display
                    entry.target.innerText = Math.ceil(count);
                    // Stop when we reach the target
                    if (count >= target) {
                        entry.target.innerText = target;
                        clearInterval(updateCount);
                    }
                }, 30);
                // Unobserve the element after animation
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.5 });
    
    // Observe each counter
    counters.forEach(counter => {
        // Start with zero
        counter.innerText = '0';
        // Observe the counter
        observer.observe(counter);
    });
}

// Form validation for appointment and contact forms
function initFormValidation() {
    // Get all forms that need validation
    const forms = document.querySelectorAll('.needs-validation');
    
    // Loop over them and prevent submission
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            } else {
                // If the form is valid, you can add AJAX submission here
                event.preventDefault();
                // Example AJAX submission (comment out if not using)
                // submitFormViaAjax(form);
                
                // For now, just show an alert
                alert('Form submitted successfully! We will contact you soon.');
                form.reset();
            }
            
            form.classList.add('was-validated');
        }, false);
    });
}

// Example function for AJAX form submission
function submitFormViaAjax(form) {
    const formData = new FormData(form);
    fetch(form.action, {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Form submitted successfully!');
            form.reset();
        } else {
            alert('Error submitting form. Please try again.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred. Please try again later.');
    });
}

// Helper function to get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (const cookieStr of cookies) {
            const cookie = cookieStr.trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Add smooth scrolling to all links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth'
            });
        }
    });
});

// Authentication form validation
function validateAuthForms() {
    // Sign up form validation
    const signupForm = document.querySelector('.signup-form');
    if (signupForm) {
        signupForm.addEventListener('submit', function(e) {
            const password = document.getElementById('password');
            const confirmPassword = document.getElementById('confirm-password');
            
            if (password.value !== confirmPassword.value) {
                e.preventDefault();
                alert('Passwords do not match. Please try again.');
            }
        });
    }
    
    // Login form support
    const loginForm = document.querySelector('.login-form');
    if (loginForm) {
        // Here you can add custom login form behavior if needed
        console.log('Login form initialized');
    }
}

// Add sticky header on scroll
window.addEventListener('scroll', function() {
    const header = document.querySelector('header');
    if (window.scrollY > 100) {
        header.classList.add('sticky-header');
    } else {
        header.classList.remove('sticky-header');
    }
});
