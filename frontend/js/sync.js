// Sync offline queue to backend when online
async function syncQueue() {
    if (!navigator.onLine) return { synced: 0, failed: 0 };

    const queue = await getQueue();
    let synced = 0, failed = 0;

    for (const item of queue) {
        try {
            const response = await fetch(`${API_BASE}/api/triage`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: item.name,
                    phone: item.phone,
                    village: item.village,
                    age: item.age,
                    gender: item.gender,
                    symptoms: item.symptoms,
                    source: 'app'
                })
            });

            if (response.ok) {
                await markSynced(item.id);
                synced++;
            } else {
                failed++;
            }
        } catch (e) {
            failed++;
        }
    }

    if (synced > 0) await clearSynced();
    return { synced, failed };
}

// Auto-sync when coming back online
window.addEventListener('online', async () => {
    const result = await syncQueue();
    if (result.synced > 0) {
        showToast(`✅ Synced ${result.synced} patient(s) to server`);
    }
    updateOnlineStatus();
    // Notify page-specific UIs to refresh
    window.dispatchEvent(new CustomEvent('queue-synced', { detail: result }));
});

window.addEventListener('offline', () => {
    updateOnlineStatus();
});

function updateOnlineStatus() {
    const indicators = document.querySelectorAll('.online-indicator');
    indicators.forEach(el => {
        if (navigator.onLine) {
            el.innerHTML = '<span class="status-dot online"></span> Online';
            el.className = 'online-indicator';
        } else {
            el.innerHTML = '<span class="status-dot offline"></span> Offline';
            el.className = 'online-indicator';
        }
    });

    const banner = document.getElementById('offline-banner');
    if (banner) {
        banner.classList.toggle('hidden', navigator.onLine);
    }
}

// Init on page load
document.addEventListener('DOMContentLoaded', updateOnlineStatus);
