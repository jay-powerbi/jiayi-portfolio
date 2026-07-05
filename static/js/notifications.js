(function () {
    var btn = document.getElementById('enable-notifications-btn');
    if (!btn) return;

    var block = document.querySelector('.notification-permission-block');
    var statusEl = block && block.querySelector('[data-role="status"]');
    var permissionUrl = '/settings/notifications/permission';

    function syncPermission(status) {
        if (block) block.setAttribute('data-permission', status);
        if (status === 'granted') {
            btn.disabled = true;
        }
        fetch(permissionUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: 'status=' + encodeURIComponent(status),
        }).catch(function () {});
    }

    btn.addEventListener('click', function () {
        if (!('Notification' in window)) {
            if (statusEl) statusEl.textContent = 'Browser notifications are not supported on this device.';
            return;
        }

        Notification.requestPermission().then(function (result) {
            syncPermission(result);
            if (statusEl) {
                if (result === 'granted') {
                    statusEl.textContent = 'Notifications enabled — you\'ll receive alerts when we launch delivery.';
                } else if (result === 'denied') {
                    statusEl.textContent = 'Notifications blocked. Enable them in your browser settings to receive alerts.';
                } else {
                    statusEl.textContent = 'Notification permission not granted yet.';
                }
            }
        });
    });
})();
