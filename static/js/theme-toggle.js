// ===== THEME TOGGLE FUNCTIONALITY =====

document.addEventListener('DOMContentLoaded', function() {
    // Get the toggle button
    const toggleBtn = document.getElementById('theme-toggle');
    
    // Check for saved theme preference
    const savedTheme = localStorage.getItem('theme');
    
    // Apply saved theme
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-mode');
        updateToggleButton(true);
    }
    
    // Toggle theme on button click
    toggleBtn.addEventListener('click', function() {
        const isDark = document.body.classList.toggle('dark-mode');
        
        // Save preference
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
        
        // Update button appearance
        updateToggleButton(isDark);
    });
    
    // Function to update toggle button icon and text
    function updateToggleButton(isDark) {
        const icon = toggleBtn.querySelector('i');
        const label = toggleBtn.querySelector('.toggle-label');
        
        if (isDark) {
            icon.className = 'fas fa-sun';
            label.textContent = 'Light Mode';
        } else {
            icon.className = 'fas fa-moon';
            label.textContent = 'Dark Mode';
        }
    }
});