/* ===== BASE STYLES ===== */
:root {
    --bg-primary: #f8f9fa;
    --bg-secondary: #ffffff;
    --text-primary: #212529;
    --text-secondary: #495057;
    --border-color: #dee2e6;
    --shadow-color: rgba(0, 0, 0, 0.1);
    --card-bg: #ffffff;
    --navbar-bg: #ffffff;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    background-color: var(--bg-primary);
    color: var(--text-primary);
    transition: background-color 0.3s ease, color 0.3s ease;
    min-height: 100vh;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

/* ===== THEME TOGGLE ===== */
.theme-toggle-container {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 9999;
}

.theme-toggle-btn {
    background: var(--card-bg);
    border: 2px solid var(--border-color);
    border-radius: 50px;
    padding: 10px 18px;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 10px;
    box-shadow: 0 2px 10px var(--shadow-color);
    transition: all 0.3s ease;
    font-size: 14px;
}

.theme-toggle-btn:hover {
    transform: scale(1.05);
    box-shadow: 0 4px 20px var(--shadow-color);
}

.theme-toggle-btn i {
    font-size: 20px;
}

.theme-toggle-btn .toggle-label {
    font-weight: 600;
}

/* ===== CARDS ===== */
.card {
    background: var(--card-bg);
    border: none;
    border-radius: 15px;
    box-shadow: 0 4px 20px var(--shadow-color);
    transition: all 0.3s ease;
    margin-bottom: 20px;
}

.card:hover {
    box-shadow: 0 8px 30px var(--shadow-color);
}

.header-card {
    background: linear-gradient(135deg, #1a237e 0%, #0d47a1 100%);
    color: white;
    padding: 30px 20px;
    border-radius: 15px;
}

.header-card .card-body {
    padding: 20px;
}

/* ===== LOGO ===== */
.logo-container {
    margin-bottom: 20px;
}

.noun-logo {
    max-width: 200px;
    height: auto;
    filter: brightness(0) invert(1);
}

/* ===== TITLES ===== */
.main-title {
    font-size: 2.5rem;
    font-weight: 900;
    color: #ffffff;
    letter-spacing: 2px;
    margin-bottom: 5px;
    text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
}

.sub-title {
    font-size: 1.2rem;
    font-weight: 500;
    color: #e3f2fd;
    letter-spacing: 1px;
}

/* ===== NAVIGATION BUTTONS ===== */
.nav-card {
    background: var(--card-bg);
    padding: 20px;
}

.nav-btn {
    padding: 18px 10px;
    font-size: 0.9rem;
    font-weight: 600;
    border-radius: 12px;
    transition: all 0.3s ease;
    min-height: 90px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 5px;
    text-decoration: none;
    color: white;
}

.nav-btn:hover {
    transform: translateY(-3px);
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.2);
    color: white;
}

.nav-btn i {
    font-size: 2rem;
    margin-bottom: 5px;
}

/* ===== STATS ===== */
.stats-row .stat-box {
    background: var(--card-bg);
    padding: 15px;
    border-radius: 12px;
    box-shadow: 0 2px 10px var(--shadow-color);
}

.stats-row .stat-box h3 {
    font-size: 2rem;
    font-weight: 700;
    color: #0d47a1;
    margin-bottom: 0;
}

.stats-row .stat-box p {
    color: var(--text-secondary);
    margin-bottom: 0;
}

/* ===== DARK MODE ===== */
body.dark-mode {
    --bg-primary: #121212;
    --bg-secondary: #1e1e1e;
    --text-primary: #e0e0e0;
    --text-secondary: #b0b0b0;
    --border-color: #333333;
    --shadow-color: rgba(0, 0, 0, 0.5);
    --card-bg: #1e1e1e;
}

body.dark-mode .header-card {
    background: linear-gradient(135deg, #0d1b3e 0%, #1a237e 100%);
}

body.dark-mode .card {
    background: var(--card-bg);
    border: 1px solid #333;
}

body.dark-mode .nav-btn {
    color: white;
}

body.dark-mode .stats-row .stat-box {
    background: var(--card-bg);
}

body.dark-mode .stat-box h3 {
    color: #64b5f6;
}

body.dark-mode .table {
    color: var(--text-primary);
}

body.dark-mode .table-striped > tbody > tr:nth-of-type(odd) > * {
    background-color: rgba(255, 255, 255, 0.05);
}

/* ===== RESPONSIVE ===== */
@media (max-width: 768px) {
    .main-title {
        font-size: 1.8rem;
    }
    
    .sub-title {
        font-size: 1rem;
    }
    
    .noun-logo {
        max-width: 150px;
    }
    
    .nav-btn {
        min-height: 70px;
        font-size: 0.8rem;
    }
    
    .nav-btn i {
        font-size: 1.5rem;
    }
    
    .theme-toggle-container {
        top: 10px;
        right: 10px;
    }
    
    .theme-toggle-btn {
        padding: 6px 12px;
        font-size: 12px;
    }
    
    .theme-toggle-btn .toggle-label {
        display: none;
    }
}

@media (max-width: 576px) {
    .main-title {
        font-size: 1.4rem;
    }
    
    .header-card {
        padding: 15px 10px;
    }
    
    .col-6 {
        padding: 5px;
    }
}

/* ===== LOGIN CARDS ===== */
.login-card {
    border-radius: 15px;
    box-shadow: 0 8px 30px var(--shadow-color);
}

.login-card .card-header {
    background: linear-gradient(135deg, #1a237e 0%, #0d47a1 100%);
    color: white;
    border-radius: 15px 15px 0 0;
    padding: 20px;
}

.login-card .card-header h3 {
    margin: 0;
    font-weight: 700;
}

/* ===== ADMIN DASHBOARD ===== */
.stat-card {
    background: linear-gradient(135deg, #1a237e 0%, #0d47a1 100%);
    color: white;
    border-radius: 12px;
    padding: 10px;
}

.stat-card h3 {
    font-size: 2.5rem;
    font-weight: 700;
    margin-bottom: 0;
}

.stat-card p {
    margin-bottom: 0;
    opacity: 0.8;
}

/* ===== BUTTONS ===== */
.btn-primary {
    background: #0d47a1;
    border: none;
}

.btn-primary:hover {
    background: #1a237e;
}

.btn-success {
    background: #2e7d32;
    border: none;
}

.btn-success:hover {
    background: #1b5e20;
}

.btn-warning {
    background: #f57c00;
    border: none;
    color: white;
}

.btn-warning:hover {
    background: #e65100;
    color: white;
}

.btn-info {
    background: #00838f;
    border: none;
    color: white;
}

.btn-info:hover {
    background: #006064;
    color: white;
}

/* ===== TABLE ===== */
.table {
    margin-bottom: 0;
}

.table th {
    background: #f5f5f5;
    font-weight: 600;
}

body.dark-mode .table th {
    background: #2a2a2a;
}

/* ===== FORM ===== */
.form-control:focus {
    border-color: #0d47a1;
    box-shadow: 0 0 0 0.2rem rgba(13, 71, 161, 0.25);
}

/* ===== ALERTS ===== */
.alert {
    border-radius: 10px;
    border: none;
}
