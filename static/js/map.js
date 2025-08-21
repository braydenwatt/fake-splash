// --- Marker storage ---
const markers = {
    me: null,
    tracked: {}
};

// --- Custom icon generator ---
function createTextIcon(text, bg = "#333", color = "#fff") {
    return L.divIcon({
        className: "custom-marker",
        html: `<div class="marker-text" style="background-color:${bg}; color:${color};">${text}</div>`,
        iconSize: [32, 32],
        iconAnchor: [16, 16]
    });
}

// --- Format popup content ---
function formatPopup(user) {
    let content = `<div class="location-popup"><div class="user-name">${user.label}</div>`;
    if (user.type === 'tracked') {
        content += `
        <div class="info-row"><span class="info-icon">📍</span><span class="info-value">${user.city}, ${user.region}</span></div>
        <div class="info-row"><span class="info-icon">🚶</span><span class="info-value">${user.activity}</span></div>
        <div class="info-row"><span class="info-icon">🚗</span><span class="info-value">${user.in_car === 'true' ? 'Yes' : 'No'}</span></div>
        <div class="info-row"><span class="info-icon">⚡</span><span class="info-value speed-value">${user.speed}</span></div>
        <div class="info-row"><span class="info-icon">⏱</span><span class="info-value">${user.updated}</span></div>
        `;
    } else {
        content += `
        <div class="info-row"><span class="info-icon">📱</span><span class="info-value">Your Device</span></div>
        `;
    }
    content += '</div>';
    return content;
}

// --- Initialize map ---
const map = L.map('map').setView([33.8864, -84.4111], 13);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: 'Map data © OpenStreetMap contributors'
}).addTo(map);

// --- Update map with data ---
function updateMap(data) {
    // "Me" marker
    const me = data.find(user => user.type === 'me');
    if (me) {
        if (!markers.me) {
            markers.me = L.marker(me.coords, {
                icon: createTextIcon("Me", "red", "white")
            }).addTo(map).bindPopup(formatPopup(me));
        } else {
            markers.me.setLatLng(me.coords);
            markers.me.getPopup().setContent(formatPopup(me));
        }
    }

    // Tracked users
    const tracked = data.filter(user => user.type === 'tracked');
    tracked.forEach(user => {
        if (!markers.tracked[user.label]) {
            markers.tracked[user.label] = L.marker(user.coords, {
                icon: createTextIcon(user.icon, "#444", "#fff")
            }).addTo(map);
            markers.tracked[user.label].bindPopup(formatPopup(user));
        } else {
            markers.tracked[user.label].setLatLng(user.coords);
            markers.tracked[user.label].getPopup().setContent(formatPopup(user));
        }
    });

    // Remove markers for users no longer present
    const trackedLabels = new Set(tracked.map(u => u.label));
    for (const label in markers.tracked) {
        if (!trackedLabels.has(label)) {
            map.removeLayer(markers.tracked[label]);
            delete markers.tracked[label];
        }
    }

    // Center map if first load
    if (me && !window.mapInitialized) {
        map.setView(me.coords, 14);
        window.mapInitialized = true;
    }

    // Update status
    document.getElementById('status').textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
}

// --- Fetch data and update map ---
function refreshMap() {
    fetch('/get_map_data')
        .then(res => res.json())
        .then(data => updateMap(data));
}

// --- Initial and periodic refresh ---
refreshMap();
setInterval(refreshMap, 10000);

// --- Button: manual refresh ---
document.getElementById("refreshBtn").addEventListener("click", refreshMap);

// --- Button: use my location ---
document.getElementById("locateBtn").addEventListener("click", () => {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(pos => {
            fetch('/update_my_location', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ lat: pos.coords.latitude, lng: pos.coords.longitude })
            }).then(() => refreshMap());
        });
    }
});
