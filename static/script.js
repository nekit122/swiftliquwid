// ==========================================
// 💠 NVTULKA — Исправленный JavaScript
// Все функции в глобальной области видимости
// ==========================================

// ============ УТИЛИТЫ ============
function $(sel, ctx) { return (ctx || document).querySelector(sel); }
function $$(sel, ctx) { return [...(ctx || document).querySelectorAll(sel)]; }

function debounce(fn, delay) {
    let timer;
    return function(...args) { clearTimeout(timer); timer = setTimeout(() => fn.apply(this, args), delay); };
}

function formatTime(isoString) {
    if (!isoString) return '';
    const d = new Date(isoString);
    const now = new Date();
    const diff = now - d;
    if (diff < 60000) return 'только что';
    if (diff < 3600000) return Math.floor(diff / 60000) + ' мин. назад';
    if (diff < 86400000) return d.toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' });
    return d.toLocaleDateString('ru', { day: '2-digit', month: '2-digit', year: '2-digit' }) + ' ' + d.toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' });
}

function escapeHTML(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function linkify(text) {
    if (!text) return '';
    return escapeHTML(text)
        .replace(/#(\w+)/g, '<a href="/search?q=$1" class="hashtag">#$1</a>')
        .replace(/@(\w+)/g, '<a href="/profile/$1" class="mention">@$1</a>');
}

// ============ ТОСТ ============
function showToast(message, duration) {
    duration = duration || 2000;
    let toast = document.getElementById('nvtulkaToast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'nvtulkaToast';
        toast.style.cssText = 'position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:var(--bg-card);backdrop-filter:blur(20px);border:1px solid var(--border-medium);border-radius:20px;padding:10px 22px;color:var(--text-primary);font-size:0.85rem;z-index:9999;box-shadow:0 8px 40px rgba(0,0,0,0.5),0 0 20px rgba(179,71,234,0.4);animation:pop-in 0.3s ease-out;white-space:nowrap;pointer-events:none;';
        document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.style.opacity = '1';
    toast.style.display = 'block';
    clearTimeout(toast._t);
    toast._t = setTimeout(() => { toast.style.opacity = '0'; toast.style.transition = 'opacity 0.3s'; setTimeout(() => toast.style.display = 'none', 300); }, duration);
}

// ============ РЕАКЦИИ (ЛАЙКИ) ============
function toggleReactionPicker(event, postId) {
    event.stopPropagation();
    event.preventDefault();
    const picker = document.getElementById('reactionPicker' + postId);
    if (!picker) return;
    const isOpen = picker.classList.contains('show');
    // Закрываем все
    $$('.reaction-picker.show').forEach(p => p.classList.remove('show'));
    if (!isOpen) picker.classList.add('show');
}

function react(postId, emoji, event) {
    if (event) { event.stopPropagation(); event.preventDefault(); }
    const container = document.querySelector('.reactions-container[data-post-id="' + postId + '"]');
    if (!container) return;

    fetch('/post/' + postId + '/react', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ emoji: emoji })
    })
    .then(r => {
        if (r.status === 401) { window.location.href = '/login'; return null; }
        return r.json();
    })
    .then(data => {
        if (!data) return;
        const btn = container.querySelector('.reaction-btn');
        const countEl = container.querySelector('.reaction-count');
        let total = 0;
        if (data.reactions) {
            total = Object.values(data.reactions).reduce((a, b) => a + b, 0);
        }
        if (data.user_reaction) {
            btn.innerHTML = data.user_reaction + ' <span class="reaction-count">' + (total || '') + '</span>';
            btn.classList.add('active');
        } else {
            btn.innerHTML = '❤️ <span class="reaction-count">' + (total || '') + '</span>';
            btn.classList.remove('active');
        }
        // Закрываем пикер
        $$('.reaction-picker.show').forEach(p => p.classList.remove('show'));
    })
    .catch(err => console.error('Reaction error:', err));
}

// Закрытие пикера по клику вне
document.addEventListener('click', function(e) {
    if (!e.target.closest('.reactions-container')) {
        $$('.reaction-picker.show').forEach(p => p.classList.remove('show'));
    }
});

// ============ ЗАКЛАДКИ ============
function toggleBookmark(postId, btn) {
    fetch('/bookmark/' + postId, { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'added') {
                btn.innerHTML = '🔖';
                showToast('Добавлено в закладки');
            } else {
                btn.innerHTML = '📑';
                showToast('Удалено из закладок');
            }
        })
        .catch(err => console.error('Bookmark error:', err));
}

// ============ КОПИРОВАТЬ ССЫЛКУ ============
function copyPostLink(postId) {
    const url = window.location.origin + '/post/' + postId;
    if (navigator.clipboard) {
        navigator.clipboard.writeText(url).then(() => showToast('📋 Ссылка скопирована!'));
    } else {
        const ta = document.createElement('textarea');
        ta.value = url;
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        ta.remove();
        showToast('📋 Ссылка скопирована!');
    }
}

// ============ ПОДПИСКА ============
function toggleFollow(username, btn) {
    fetch('/follow/' + username, { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'followed') {
                btn.textContent = 'Отписаться';
                btn.classList.remove('btn-primary');
                btn.classList.add('btn-secondary');
                showToast('✅ Вы подписались');
            } else {
                btn.textContent = 'Подписаться';
                btn.classList.remove('btn-secondary');
                btn.classList.add('btn-primary');
                showToast('Вы отписались');
            }
        });
}

// ============ РЕДАКТИРОВАНИЕ ПОСТА ============
function editPost(postId) {
    const card = document.querySelector('.post-card[data-post-id="' + postId + '"]');
    if (!card) return;
    const contentDiv = card.querySelector('.post-content');
    if (!contentDiv) return;
    const originalText = contentDiv.textContent.trim();

    const textarea = document.createElement('textarea');
    textarea.value = originalText;
    textarea.style.cssText = 'width:100%;min-height:80px;margin-bottom:8px;background:var(--bg-input);border:1px solid var(--border-medium);border-radius:12px;padding:10px;color:var(--text-primary);resize:vertical;font-family:inherit;font-size:0.9rem;';

    const actions = document.createElement('div');
    actions.style.cssText = 'display:flex;gap:8px;';
    actions.innerHTML = '<button class="btn btn-sm btn-primary" id="saveEdit' + postId + '">Сохранить</button><button class="btn btn-sm btn-secondary" id="cancelEdit' + postId + '">Отмена</button>';

    contentDiv.replaceWith(textarea);
    textarea.after(actions);
    textarea.focus();

    document.getElementById('saveEdit' + postId).onclick = function() {
        const newContent = textarea.value.trim();
        fetch('/post/' + postId + '/edit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: 'content=' + encodeURIComponent(newContent)
        }).then(() => location.reload());
    };

    document.getElementById('cancelEdit' + postId).onclick = function() {
        textarea.replaceWith(contentDiv);
        actions.remove();
    };
}

// ============ ОПРОСЫ ============
function votePoll(pollId, optionIndex, el) {
    fetch('/poll/' + pollId + '/vote', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ option: optionIndex })
    })
    .then(r => r.json())
    .then(data => {
        if (data.error) { showToast(data.error); return; }
        const pollContainer = el.closest('.poll-container');
        if (!pollContainer) return;
        const options = pollContainer.querySelectorAll('.poll-option');
        let total = 0;
        Object.values(data.votes).forEach(v => total += v.length);
        options.forEach((opt, i) => {
            const votes = (data.votes[i] || []).length;
            const percent = total > 0 ? Math.round(votes / total * 100) : 0;
            const bar = opt.querySelector('.poll-option-bar');
            const pct = opt.querySelector('.poll-option-percent');
            if (bar) bar.style.width = percent + '%';
            if (pct) pct.textContent = percent + '%';
            opt.classList.toggle('selected', data.user_vote === i);
        });
        const totalEl = pollContainer.querySelector('.poll-total');
        if (totalEl) totalEl.textContent = total + ' голосов';
    });
}

// ============ ПРОФИЛЬ: ТАБЫ ============
function switchTab(tabName) {
    $$('.tab-content').forEach(el => el.style.display = 'none');
    const tab = document.getElementById('tab-' + tabName);
    if (tab) tab.style.display = 'block';
    $$('.profile-tab').forEach(el => el.classList.remove('active'));
    if (event && event.target) event.target.classList.add('active');
}

// ============ ГОЛОСОВЫЕ ============
function toggleVoice(el) {
    const src = el.dataset.src;
    if (!src) return;
    $$('.voice-message.playing').forEach(v => {
        if (v !== el) { v.classList.remove('playing'); const a = v.querySelector('audio'); if (a) { a.pause(); a.remove(); } }
    });
    if (el.classList.contains('playing')) {
        el.classList.remove('playing');
        const a = el.querySelector('audio');
        if (a) { a.pause(); a.remove(); }
        return;
    }
    el.classList.add('playing');
    const audio = document.createElement('audio');
    audio.src = src;
    audio.autoplay = true;
    audio.style.display = 'none';
    audio.onended = () => el.classList.remove('playing');
    audio.onerror = () => { el.classList.remove('playing'); showToast('Ошибка воспроизведения'); };
    el.appendChild(audio);
}

// ============ НАСТРОЙКИ ПРОФИЛЯ (шестерёнка) ============
function toggleSettings() {
    const panel = document.getElementById('settingsPanel');
    const gear = document.getElementById('settingsGear');
    if (!panel || !gear) return;

    if (panel.classList.contains('open')) {
        panel.classList.remove('open');
        gear.classList.remove('spinning');
    } else {
        panel.classList.add('open');
        gear.classList.add('spinning');
    }
}

// ============ УВЕДОМЛЕНИЯ ============
function markAllRead() {
    fetch('/notifications/read', { method: 'POST' }).then(() => location.reload());
}

// ============ АДМИН ============
(function() {
    const logo = document.getElementById('adminLogo');
    if (!logo) return;
    let timer, bar;
    function start(e) {
        e.preventDefault();
        bar = document.createElement('div');
        bar.style.cssText = 'position:fixed;top:0;left:0;height:3px;background:linear-gradient(90deg,var(--accent-primary),var(--accent-secondary));z-index:99999;width:0%;transition:width 7s linear;box-shadow:0 0 15px var(--accent-primary-glow);';
        document.body.appendChild(bar);
        requestAnimationFrame(() => bar.style.width = '100%');
        timer = setTimeout(() => window.location.href = '/admin', 7000);
    }
    function cancel() { clearTimeout(timer); if (bar) bar.remove(); bar = null; }
    logo.addEventListener('mousedown', start);
    logo.addEventListener('mouseup', cancel);
    logo.addEventListener('mouseleave', cancel);
    logo.addEventListener('touchstart', start, { passive: false });
    logo.addEventListener('touchend', cancel);
    logo.addEventListener('touchcancel', cancel);
})();

// ============ ИНИЦИАЛИЗАЦИЯ ============
document.addEventListener('DOMContentLoaded', function() {
    // Снегопад
    const snowContainer = document.getElementById('snowContainer');
    if (snowContainer) {
        const flakes = ['❄', '❅', '❆', '✦', '•'];
        for (let i = 0; i < 60; i++) {
            const flake = document.createElement('span');
            flake.className = 'snowflake';
            flake.textContent = flakes[Math.floor(Math.random() * flakes.length)];
            flake.style.cssText = 'left:' + Math.random() * 100 + '%;font-size:' + (8 + Math.random() * 20) + 'px;animation-duration:' + (4 + Math.random() * 12) + 's;animation-delay:' + Math.random() * 8 + 's;opacity:' + (0.3 + Math.random() * 0.7) + ';';
            snowContainer.appendChild(flake);
        }
    }

    // Счётчик файлов
    const fileInput = document.getElementById('fileInput');
    const fileCount = document.getElementById('fileCount');
    if (fileInput && fileCount) {
        fileInput.addEventListener('change', function() {
            const c = this.files.length;
            fileCount.textContent = c === 0 ? '' : c === 1 ? this.files[0].name : 'Выбрано: ' + c + ' файлов';
        });
    }

    // Настройки в профиле
    const gear = document.getElementById('settingsGear');
    if (gear) {
        gear.addEventListener('click', toggleSettings);
    }

    console.log('💠 NVTULKA ready');
});