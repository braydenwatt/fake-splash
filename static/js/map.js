// Store markers for updating later
const markers = {
    me: null,
    tracked: {}
};

// Custom icon generator (text marker)
function createTextIcon(text, bg = "#333", color = "#fff") {
    return L.divIcon({
        className: "custom-marker",
        html: `<div class="marker-text" style="background-color:${bg}; color:${color};">${text}</div>`,
        iconSize: [32, 32],
        iconAnchor: [16, 16]
    });
}

// Format popup content
function formatPopup(user) {
    let content = `
    <div class="location-popup">
        <div class="user-name">${user.label}</div>
    `;
    
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

// Update the map with data
function updateMap(data) {
    // Update "Me" marker
    const me = data.find(user => user.type === 'me');
    if (me) {
        if (!markers.me) {
            markers.me = L.marker(me.coords, {
                icon: createTextIcon("Me", "red", "white")   // ✅ Fix: use me.coords, not coords
            }).addTo(map).bindPopup(formatPopup(me));
        } else {
            markers.me.setLatLng(me.coords);
            markers.me.getPopup().setContent(formatPopup(me));
        }
    }
    
    // Update tracked users
    const tracked = data.filter(user => user.type === 'tracked');
    tracked.forEach(user => {
        if (!markers.tracked[user.label]) {
            markers.tracked[user.label] = L.marker(user.coords, {
                icon: createTextIcon(user.icon, "#444", "#fff")  // ✅ Use initials instead of color dot
            }).addTo(map);
            markers.tracked[user.label].bindPopup(formatPopup(user));
        } else {
            markers.tracked[user.label].setLatLng(user.coords);
            markers.tracked[user.label].getPopup().setContent(formatPopup(user));
        }
    });
    
    // Center map if first load
    if (me && !window.mapInitialized) {
        map.setView(me.coords, 14);
        window.mapInitialized = true;
    }
    
    // Update status
    document.getElementById('status').textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
}
