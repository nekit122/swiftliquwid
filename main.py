<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover, user-scalable=no">
    <title>💠 NVTULKA — Жидкое стекло + неон</title>
    <link rel="stylesheet" href="/static/style.css">
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>💠</text></svg>">
    <style>
        /* ====== НИЖНЯЯ ПАНЕЛЬ — СТЕКЛЯННАЯ ПИЛЮЛЯ С ПЕРЕТАСКИВАЕМОЙ КАПЛЕЙ ====== */
        :root {
            --nav-pill-height: 62px;
            --nav-pill-bottom: 12px;
        }

        body {
            padding-bottom: calc(var(--nav-pill-height) + var(--nav-pill-bottom) + 16px);
        }

        .tg-bottom-nav {
            position: fixed;
            bottom: var(--nav-pill-bottom);
            left: 50%;
            transform: translateX(-50%);
            width: calc(100% - 24px);
            max-width: 440px;
            height: var(--nav-pill-height);
            background: rgba(20, 20, 30, 0.55);
            backdrop-filter: blur(25px);
            -webkit-backdrop-filter: blur(25px);
            border: 0.5px solid rgba(255, 255, 255, 0.12);
            border-radius: 31px;
            z-index: 1000;
            display: flex;
            align-items: center;
            padding: 0 6px;
            touch-action: none;
            user-select: none;
            -webkit-user-select: none;
            -webkit-tap-highlight-color: transparent;
            box-shadow:
                0 8px 32px rgba(0, 0, 0, 0.5),
                0 0 0 1px rgba(255, 255, 255, 0.03) inset,
                0 1px 0 rgba(255, 255, 255, 0.06) inset;
        }

        .tg-nav-track {
            position: relative;
            display: flex;
            align-items: center;
            justify-content: space-between;
            width: 100%;
            height: 100%;
        }

        .tg-nav-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 1px;
            color: rgba(255, 255, 255, 0.45);
            text-decoration: none;
            font-size: 1.25rem;
            padding: 4px 0;
            border-radius: 14px;
            transition: color 0.2s ease;
            position: relative;
            z-index: 2;
            flex: 1;
            text-align: center;
            cursor: pointer;
            min-width: 0;
        }

        .tg-nav-item span {
            font-size: 8px;
            font-weight: 500;
            letter-spacing: 0.1px;
            opacity: 0;
            transform: translateY(3px);
            transition: all 0.3s cubic-bezier(0.25, 0.1, 0.25, 1);
            white-space: nowrap;
        }

        .tg-nav-item.active {
            color: #ffffff;
        }

        .tg-nav-item.active span {
            opacity: 1;
            transform: translateY(0);
        }

        /* Капля-индикатор */
        .tg-nav-droplet {
            position: absolute;
            bottom: 8px;
            height: 28px;
            width: 44px;
            background: var(--accent-primary);
            border-radius: 16px;
            z-index: 1;
            box-shadow:
                0 0 16px var(--accent-primary-glow),
                0 0 36px rgba(179, 71, 234, 0.35),
                inset 0 1px 0 rgba(255, 255, 255, 0.3);
            pointer-events: none;
            will-change: left, width, border-radius, height;
        }

        .tg-nav-droplet::after {
            content: '';
            position: absolute;
            top: 5px;
            left: 8px;
            right: 8px;
            height: 6px;
            background: rgba(255, 255, 255, 0.4);
            border-radius: 50%;
            filter: blur(2px);
        }

        /* При удержании — расширяется */
        .tg-nav-droplet.dragging {
            width: 58px;
            height: 32px;
            border-radius: 20px;
            box-shadow:
                0 0 24px var(--accent-primary-glow),
                0 0 50px rgba(179, 71, 234, 0.55),
                inset 0 1px 0 rgba(255, 255, 255, 0.35);
            transition: width 0.2s cubic-bezier(0.34, 1.56, 0.64, 1),
                        height 0.2s cubic-bezier(0.34, 1.56, 0.64, 1),
                        border-radius 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
        }

        /* Бейдж */
        .tg-nav-badge {
            position: absolute;
            top: -2px;
            right: calc(50% - 22px);
            width: 14px;
            height: 14px;
            background: var(--danger);
            border-radius: 50%;
            font-size: 8px;
            font-weight: 700;
            color: #fff;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 0 10px var(--danger-glow);
            z-index: 3;
            animation: badge-pulse 2s ease-in-out infinite;
        }

        @keyframes badge-pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.2); }
        }

        @media (max-width: 380px) {
            .tg-bottom-nav {
                width: calc(100% - 16px);
                height: 54px;
                border-radius: 27px;
            }
            .tg-nav-item { font-size: 1.1rem; }
            .tg-nav-item span { font-size: 7px; }
            .tg-nav-droplet { width: 36px; height: 24px; bottom: 6px; }
            .tg-nav-droplet.dragging { width: 48px; height: 28px; }
        }
    </style>
</head>
<body class="{{ user.theme if user else 'dark' }} {% if is_new_year %}new-year{% endif %}">

    {% if is_new_year %}
    <div class="snow-container" id="snowContainer"></div>
    {% endif %}

    <header class="header">
        <a href="/" class="header-logo" id="adminLogo" title="NVTULKA — зажать 7 сек для админки">
            <span class="logo-icon">💠</span> NVTULKA
        </a>
        <div class="header-actions">
            <a href="/search" title="Поиск">🔍</a>
            <a href="/notifications" title="Уведомления" style="position:relative;">
                🔔
                {% if unread_notifs and unread_notifs > 0 %}
                <span class="notif-badge">{{ unread_notifs if unread_notifs < 10 else '9+' }}</span>
                {% endif %}
            </a>
            {% if user %}
            <a href="/profile/{{ user.username }}" title="Профиль">
                {% if user.avatar %}
                <img src="{{ user.avatar }}" class="avatar avatar-sm" alt="{{ user.username }}">
                {% else %}
                <span class="avatar avatar-sm">{{ user.username[0]|upper }}</span>
                {% endif %}
            </a>
            {% endif %}
        </div>
    </header>

    <main class="container" style="margin-top:8px;margin-bottom:8px;">
        {% block content %}{% endblock %}
    </main>

    <!-- Нижняя панель — стеклянная пилюля -->
    <nav class="tg-bottom-nav" id="tgBottomNav">
        <div class="tg-nav-track" id="tgNavTrack">
            <div class="tg-nav-droplet" id="tgDroplet"></div>

            <a href="/chats" class="tg-nav-item" data-page="chats" data-url="/chats">💬<span>Чаты</span></a>
            <a href="/" class="tg-nav-item" data-page="feed" data-url="/">🏠<span>Лента</span></a>
            <a href="/swift" class="tg-nav-item" data-page="swift" data-url="/swift">🌀<span>Swift</span></a>
            <a href="/recommendations" class="tg-nav-item" data-page="recommendations" data-url="/recommendations">💠<span>Рек</span></a>
            <a href="/stories" class="tg-nav-item" data-page="stories" data-url="/stories">✨<span>Сторис</span></a>
            <a href="/notifications" class="tg-nav-item" data-page="notifications" data-url="/notifications">
                🔔<span>Увед.</span>
                {% if unread_notifs and unread_notifs > 0 %}
                <span class="tg-nav-badge">{{ unread_notifs if unread_notifs < 10 else '9+' }}</span>
                {% endif %}
            </a>
            <a href="/profile/{{ user.username if user else '' }}" class="tg-nav-item" data-page="profile" data-url="/profile/{{ user.username if user else '' }}">👤<span>Профиль</span></a>
        </div>
    </nav>

    <script>
        // ====== ПЕРЕТАСКИВАЕМАЯ СТЕКЛЯННАЯ КАПЛЯ ======
        (function() {
            const nav = document.getElementById('tgBottomNav');
            const track = document.getElementById('tgNavTrack');
            const droplet = document.getElementById('tgDroplet');
            const items = [...track.querySelectorAll('.tg-nav-item')];

            if (!nav || !track || !droplet || items.length === 0) return;

            let activeIndex = 1;
            let isDragging = false;
            let startX = 0;
            let dropletStartX = 0;

            const pages = items.map(item => item.dataset.url);
            const pageNames = items.map(item => item.dataset.page);

            // Определяем активную страницу
            const currentPath = window.location.pathname;
            pageNames.forEach((name, i) => {
                if (name === 'chats' && currentPath.startsWith('/chat')) activeIndex = 0;
                else if (name === 'feed' && (currentPath === '/' || currentPath === '/bookmarks' || currentPath === '/search')) activeIndex = 1;
                else if (name === 'swift' && currentPath === '/swift') activeIndex = 2;
                else if (name === 'recommendations' && currentPath === '/recommendations') activeIndex = 3;
                else if (name === 'stories' && currentPath.startsWith('/stor')) activeIndex = 4;
                else if (name === 'notifications' && currentPath === '/notifications') activeIndex = 5;
                else if (name === 'profile' && (currentPath.startsWith('/profile') || currentPath.startsWith('/followers'))) activeIndex = 6;
            });

            function getItemCenter(index) {
                const item = items[index];
                if (!item) return 0;
                const itemRect = item.getBoundingClientRect();
                const trackRect = track.getBoundingClientRect();
                return itemRect.left - trackRect.left + itemRect.width / 2 - droplet.offsetWidth / 2;
            }

            function positionDroplet(index, animate) {
                const targetX = getItemCenter(index);
                droplet.style.transition = animate
                    ? 'left 0.35s cubic-bezier(0.34, 1.56, 0.64, 1)'
                    : 'left 0.06s linear';
                droplet.style.left = targetX + 'px';
            }

            function setActive(index, animate) {
                items.forEach((item, i) => item.classList.toggle('active', i === index));
                activeIndex = index;
                positionDroplet(index, animate !== false);
            }

            function navigateTo(index) {
                if (index >= 0 && index < pages.length) {
                    window.location.href = pages[index];
                }
            }

            // Инициализация
            setActive(activeIndex, false);
            setTimeout(() => positionDroplet(activeIndex, false), 50);

            // Тач
            track.addEventListener('touchstart', function(e) {
                isDragging = true;
                startX = e.touches[0].clientX;
                dropletStartX = parseFloat(droplet.style.left) || getItemCenter(activeIndex);
                droplet.classList.add('dragging');
                e.preventDefault();
            }, { passive: false });

            track.addEventListener('touchmove', function(e) {
                if (!isDragging) return;
                e.preventDefault();
                const deltaX = e.touches[0].clientX - startX;
                let newX = dropletStartX + deltaX;
                const minX = getItemCenter(0);
                const maxX = getItemCenter(items.length - 1);
                newX = Math.max(minX - 15, Math.min(maxX + 15, newX));
                droplet.style.left = newX + 'px';

                let closest = activeIndex;
                let closestDist = Infinity;
                items.forEach((item, i) => {
                    const dist = Math.abs(newX - getItemCenter(i));
                    if (dist < closestDist) { closestDist = dist; closest = i; }
                });
                if (closest !== activeIndex) {
                    items.forEach((item, i) => item.classList.toggle('active', i === closest));
                    activeIndex = closest;
                }
            }, { passive: false });

            track.addEventListener('touchend', function() {
                if (!isDragging) return;
                isDragging = false;
                droplet.classList.remove('dragging');
                const startPageIndex = pageNames.indexOf(pageNames.find(name => {
                    const p = window.location.pathname;
                    if (name === 'chats') return p.startsWith('/chat');
                    if (name === 'feed') return p === '/';
                    if (name === 'swift') return p === '/swift';
                    if (name === 'recommendations') return p === '/recommendations';
                    if (name === 'stories') return p.startsWith('/stor');
                    if (name === 'notifications') return p === '/notifications';
                    if (name === 'profile') return p.startsWith('/profile');
                    return false;
                }));
                setActive(activeIndex, true);
                if (activeIndex !== startPageIndex) navigateTo(activeIndex);
            });

            // Мышь
            track.addEventListener('mousedown', function(e) {
                if (e.target.closest('a')) return;
                isDragging = true;
                startX = e.clientX;
                dropletStartX = parseFloat(droplet.style.left) || getItemCenter(activeIndex);
                droplet.classList.add('dragging');
                e.preventDefault();
            });

            document.addEventListener('mousemove', function(e) {
                if (!isDragging) return;
                const deltaX = e.clientX - startX;
                let newX = dropletStartX + deltaX;
                const minX = getItemCenter(0);
                const maxX = getItemCenter(items.length - 1);
                newX = Math.max(minX - 15, Math.min(maxX + 15, newX));
                droplet.style.left = newX + 'px';

                let closest = activeIndex;
                let closestDist = Infinity;
                items.forEach((item, i) => {
                    const dist = Math.abs(newX - getItemCenter(i));
                    if (dist < closestDist) { closestDist = dist; closest = i; }
                });
                if (closest !== activeIndex) {
                    items.forEach((item, i) => item.classList.toggle('active', i === closest));
                    activeIndex = closest;
                }
            });

            document.addEventListener('mouseup', function() {
                if (!isDragging) return;
                isDragging = false;
                droplet.classList.remove('dragging');
                const startPageIndex = pageNames.indexOf(pageNames.find(name => {
                    const p = window.location.pathname;
                    if (name === 'chats') return p.startsWith('/chat');
                    if (name === 'feed') return p === '/';
                    if (name === 'swift') return p === '/swift';
                    if (name === 'recommendations') return p === '/recommendations';
                    if (name === 'stories') return p.startsWith('/stor');
                    if (name === 'notifications') return p === '/notifications';
                    if (name === 'profile') return p.startsWith('/profile');
                    return false;
                }));
                setActive(activeIndex, true);
                if (activeIndex !== startPageIndex) navigateTo(activeIndex);
            });

            items.forEach((item, i) => {
                item.addEventListener('click', function(e) {
                    if (isDragging) { e.preventDefault(); return; }
                    setActive(i, true);
                });
            });

            window.addEventListener('resize', () => positionDroplet(activeIndex, false));
        })();
    </script>

    <script src="/static/script.js"></script>
</body>
</html>
