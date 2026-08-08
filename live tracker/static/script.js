/* =====================================================
   Nearby — live map front end
   Swap `mockFeed` for your real-time source (see the
   "CONNECT YOUR BACKEND" block near the bottom) — the
   render functions don't need to change either way.
===================================================== */

const AVATAR_COLORS = ["#5eaaa8", "#e8a33d", "#8aa9e0", "#c98bd6", "#7fc79e"];

const state = {
    members: new Map(),   // id -> { id, name, lat, lon, accuracy, battery, updatedAt, status }
    selectedId: null,
    markers: new Map(),   // id -> L.marker
};

/* ---------------------------------------------------
   Map setup
--------------------------------------------------- */
const map = L.map("map", { zoomControl: true }).setView([37.7749, -122.4194], 12);

L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_matter/{z}/{x}/{y}{r}.png", {
    attribution: '&copy; OpenStreetMap &copy; CARTO',
    subdomains: "abcd",
    maxZoom: 19,
}).addTo(map);

const socket = io();

function colorFor(id) {
    const key = String(id);
    let hash = 0;
    for (const ch of key) hash = (hash * 31 + ch.charCodeAt(0)) % AVATAR_COLORS.length;
    return AVATAR_COLORS[hash];
}

function initials(name) {
    return name.trim().split(/\s+/).slice(0, 2).map(w => w[0].toUpperCase()).join("");
}

function relativeTime(ts) {
    const seconds = Math.round((Date.now() - ts) / 1000);
    if (seconds < 60) return "just now";
    const minutes = Math.round(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.round(minutes / 60);
    return `${hours}h ago`;
}

function statusFor(ts) {
    const minutes = (Date.now() - ts) / 60000;
    if (minutes < 3) return "active";
    if (minutes < 30) return "idle";
    return "offline";
}

/* ---------------------------------------------------
   Marker rendering
--------------------------------------------------- */
function buildIcon(member) {
    const color = member.sos ? "#ef4444" : colorFor(member.id);
    const pingClass = member.sos ? "pin-ping--sos" : "";
    const pinClass = member.sos ? "pin--sos" : "";
    const label = member.sos ? "🚨" : initials(member.name);

    return L.divIcon({
        className: "",
        html: `
            <div style="position:relative; width:34px; height:34px;">
                <div class="pin-ping ${pingClass}" style="background:${color};"></div>
                <div class="pin ${pinClass}" style="background:${color};">${label}</div>
            </div>`,
        iconSize: [34, 34],
        iconAnchor: [17, 17],
    });
}

function upsertMarker(member) {
    const existing = state.markers.get(member.id);
    const icon = buildIcon(member);

    if (existing) {
        existing.setLatLng([member.lat, member.lon]);
        existing.setIcon(icon);
        return;
    }

    const marker = L.marker([member.lat, member.lon], { icon }).addTo(map);
    marker.on("click", () => selectMember(member.id));
    state.markers.set(member.id, marker);
}

function setMemberSOS(id, active) {
    const member = state.members.get(id);
    if (!member) return;
    member.sos = active;
    upsertMarker(member);
    renderMemberList();
}

/* ---------------------------------------------------
   Route trail rendering — one polyline per member, so
   each family member's path is drawn independently.
--------------------------------------------------- */
const routes = new Map(); // id -> { polyline: L.polyline, points: [[lat, lon], ...] }

function getRoute(id) {
    let entry = routes.get(id);

    if (!entry) {
        entry = {
            polyline: L.polyline([], {
                color: colorFor(id),
                weight: 5,
                opacity: 0.8
            }).addTo(map),
            points: []
        };
        routes.set(id, entry);
    }

    return entry;
}

function extendRoute(id, lat, lon) {
    const entry = getRoute(id);
    entry.points.push([lat, lon]);
    entry.polyline.setLatLngs(entry.points);
}

function clearRoute(id) {
    const entry = routes.get(id);
    if (!entry) return;
    entry.points = [];
    entry.polyline.setLatLngs(entry.points);
}

/* ---------------------------------------------------
   Geofence circles — one L.circle per safe place,
   drawn once and left on the map (Part 6).
--------------------------------------------------- */
async function loadGeofences() {
    try {
        const response = await fetch("/geofence");
        const fences = await response.json();

        fences.forEach(fence => {
            L.circle([fence.lat, fence.lon], {
                radius: fence.radius,
                color: "#5eaaa8",
                weight: 2,
                fillColor: "#5eaaa8",
                fillOpacity: 0.12
            })
            .addTo(map)
            .bindTooltip(`${fence.name} &middot; ${fence.radius}m`, { direction: "top" });
        });
    } catch (error) {
        console.error(error);
    }
}

/* ---------------------------------------------------
   Notifications — Part 5. Prepends geofence arrival/
   departure events to the sidebar list.
--------------------------------------------------- */
function addNotification({ user, place, event }) {
    const list = document.getElementById("notifications-list");
    const empty = document.getElementById("notifications-empty");
    if (empty) empty.remove();

    const icon = event === "arrived" ? "✅" : "⚠️";
    const verb = event === "arrived" ? "arrived at" : "left";

    const item = document.createElement("li");
    item.className = "notifications__item";
    item.innerHTML = `${icon} <strong>${user}</strong> ${verb} <strong>${place}</strong>`;

    list.prepend(item);

    // Keep the list from growing forever
    while (list.children.length > 20) {
        list.removeChild(list.lastChild);
    }
}

function addSOSNotification({ user_id, name, time }) {
    const list = document.getElementById("notifications-list");
    const empty = document.getElementById("notifications-empty");
    if (empty) empty.remove();

    const item = document.createElement("li");
    item.className = "notifications__item notifications__item--sos";
    item.innerHTML = `
        🚨 <strong>${name}</strong> sent SOS
        <span class="notifications__time">${time}</span>
        <button type="button" class="notifications__view">View Location</button>
    `;

    item.querySelector(".notifications__view").addEventListener("click", () => {
        const member = state.members.get(user_id);
        if (member) {
            map.setView([member.lat, member.lon], 17);
            selectMember(user_id);
        }
    });

    list.prepend(item);

    while (list.children.length > 20) {
        list.removeChild(list.lastChild);
    }
}

/* ---------------------------------------------------
   Sidebar rendering
--------------------------------------------------- */
function renderMemberList() {
    const list = document.getElementById("member-list");
    const empty = document.getElementById("member-list-empty");

    const members = Array.from(state.members.values());
    if (empty) empty.hidden = members.length > 0;

    list.querySelectorAll(".member-card").forEach(el => el.remove());

    members
        .sort((a, b) => b.updatedAt - a.updatedAt)
        .forEach(member => {
            const status = statusFor(member.updatedAt);
            const card = document.createElement("button");
            card.className = "member-card";
            card.dataset.status = status;
            card.dataset.sos = String(!!member.sos);
            card.setAttribute("aria-selected", String(member.id === state.selectedId));
            card.innerHTML = `
                <div class="member-card__avatar" style="background:${colorFor(member.id)}">
                    ${initials(member.name)}
                </div>
                <div class="member-card__body">
                    <p class="member-card__name">${member.sos ? "🚨 " : ""}${member.name}</p>
                    <p class="member-card__meta">${status === "offline" ? "Last seen" : "Updated"} ${relativeTime(member.updatedAt)}${member.battery != null ? ` &middot; ${member.battery}%` : ""}</p>
                </div>
            `;
            card.addEventListener("click", () => selectMember(member.id));
            list.appendChild(card);
        });
}

/* ---------------------------------------------------
   Selection + overlay panel
--------------------------------------------------- */
function selectMember(id) {
    state.selectedId = id;
    const member = state.members.get(id);
    if (!member) return;

    map.panTo([member.lat, member.lon]);

    document.getElementById("selected-panel").hidden = false;
    document.getElementById("selected-name").textContent = member.name;
    document.getElementById("selected-time").textContent = relativeTime(member.updatedAt);
    document.getElementById("selected-lat").textContent = member.lat.toFixed(5);
    document.getElementById("selected-lon").textContent = member.lon.toFixed(5);
    document.getElementById("selected-accuracy").textContent = member.accuracy ? `±${Math.round(member.accuracy)}m` : "—";
    document.getElementById("selected-battery").textContent = member.battery != null ? `${member.battery}%` : "—";

    renderMemberList();
}

document.getElementById("selected-close").addEventListener("click", () => {
    state.selectedId = null;
    document.getElementById("selected-panel").hidden = true;
    renderMemberList();
});

/* ---------------------------------------------------
   Connection status pill
--------------------------------------------------- */
function setConnState(stateName, label) {
    const pill = document.getElementById("conn-status");
    pill.dataset.state = stateName;
    document.getElementById("conn-label").textContent = label;
}

/* ---------------------------------------------------
   Ingest a location update from any source
--------------------------------------------------- */
function handleUpdate({ id, name, lat, lon, accuracy, battery }) {

    const existing = state.members.get(id);

    state.members.set(id, {
        id,
        name,
        lat,
        lon,
        accuracy,
        battery,
        updatedAt: Date.now(),
        sos: existing ? existing.sos : false,
    });

    upsertMarker(state.members.get(id));

    if (state.selectedId === null) {
        state.selectedId = id;
    }

    renderMemberList();

    if (id === state.selectedId) {
        selectMember(id);
    }

}
/* =====================================================
   CONNECT YOUR BACKEND
   On load, fetch every family member's last known
   position from GET /location. From then on, live
   updates arrive over the socket.io connection for
   the family's room. Everything above (map, list,
   overlay) only depends on handleUpdate() being
   called, so this block can be swapped for any other
   real-time source later without touching the render
   functions.
===================================================== */
socket.on("connect", () => {
    setConnState("live", "Live");
});

socket.on("disconnect", () => {
    setConnState("offline", "Offline");
});

socket.on("location_update", (data) => {

    handleUpdate({
        id: data.id,
        name: data.name,
        lat: data.lat,
        lon: data.lon,
        accuracy: 10,
        battery: data.battery
    });

    extendRoute(data.id, data.lat, data.lon);

});

socket.on("geofence_event", (data) => {
    addNotification(data);
});

/* ---------------------------------------------------
   SOS — Module 13
--------------------------------------------------- */
const sosButton = document.getElementById("sos-button");
const sosModal = document.getElementById("sos-modal");
const sosCancel = document.getElementById("sos-cancel");
const sosConfirm = document.getElementById("sos-confirm");

sosButton.addEventListener("click", () => {
    sosModal.hidden = false;
});

sosCancel.addEventListener("click", () => {
    sosModal.hidden = true;
});

sosConfirm.addEventListener("click", async () => {
    sosConfirm.disabled = true;
    sosConfirm.textContent = "Sending…";

    try {
        const position = await new Promise((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(resolve, reject, {
                enableHighAccuracy: true,
                timeout: 10000,
            });
        });

        await fetch("/sos", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                lat: position.coords.latitude,
                lon: position.coords.longitude,
                message: "Need Help",
            }),
        });

    } catch (error) {
        console.error(error);
        alert("Could not send SOS — " + (error.message || "your location is unavailable."));
    } finally {
        sosModal.hidden = true;
        sosConfirm.disabled = false;
        sosConfirm.textContent = "Send SOS";
    }
});

socket.on("sos_alert", (data) => {

    // Make sure we have a marker at the SOS location even if it's
    // newer than the sender's last regular check-in.
    handleUpdate({
        id: data.user_id,
        name: data.name,
        lat: data.lat,
        lon: data.lon,
        accuracy: 10,
        battery: state.members.get(data.user_id)?.battery,
    });

    setMemberSOS(data.user_id, true);
    addSOSNotification(data);

    // Auto-center + zoom onto the emergency
    map.setView([data.lat, data.lon], 17);
});

socket.on("sos_resolved", (data) => {
    setMemberSOS(data.user_id, false);
});

async function loadFamilyLocations() {
    try {
        const response = await fetch("/location");
        const members = await response.json();

        members.forEach(member => {
            handleUpdate({
                id: member.id,
                name: member.name,
                lat: member.lat,
                lon: member.lon,
                accuracy: 10,
                battery: member.battery
            });

            extendRoute(member.id, member.lat, member.lon);
        });
    } catch (error) {
        console.error(error);
    }
}

loadFamilyLocations();
loadGeofences();

/* =====================================================
   Notification Center — Module 15
===================================================== */
const NOTIFICATION_META = {
    sos:       { icon: "🔴🚨", label: "SOS",      color: "#ef4444" },
    arrival:   { icon: "🟢🏠", label: "Arrival",  color: "#22c55e" },
    departure: { icon: "🟡🏫", label: "Departure",color: "#eab308" },
    battery:   { icon: "🟠🔋", label: "Battery",  color: "#f97316" },
    system:    { icon: "⚪",   label: "System",   color: "#9ca3af" },
    message:   { icon: "🔵",   label: "Message",  color: "#3b82f6" },
};

const bellButton = document.getElementById("bell-button");
const bellBadge = document.getElementById("bell-badge");
const notificationCenter = document.getElementById("notification-center");
const notificationList = document.getElementById("notification-center-list");
const notificationFilters = document.getElementById("notification-filters");
const notificationClear = document.getElementById("notification-clear");
const toastContainer = document.getElementById("toast-container");

let unreadCount = 0;
let activeFilter = { type: "range", value: "" };

function setUnreadCount(count) {
    unreadCount = count;
    if (unreadCount > 0) {
        bellBadge.hidden = false;
        bellBadge.textContent = unreadCount > 99 ? "99+" : String(unreadCount);
    } else {
        bellBadge.hidden = true;
    }
}

function notificationTimeAgo(isoString) {
    const seconds = Math.round((Date.now() - new Date(isoString).getTime()) / 1000);
    if (seconds < 60) return "just now";
    const minutes = Math.round(seconds / 60);
    if (minutes < 60) return `${minutes} min ago`;
    const hours = Math.round(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.round(hours / 24)}d ago`;
}

function renderNotificationItem(n) {
    const meta = NOTIFICATION_META[n.type] || NOTIFICATION_META.message;

    const li = document.createElement("li");
    li.className = "notification-center__item";
    li.dataset.read = String(!!n.is_read);
    li.style.setProperty("--notif-color", meta.color);
    li.innerHTML = `
        <span class="notification-center__icon">${meta.icon}</span>
        <span class="notification-center__body">
            <span class="notification-center__message">${n.message}</span>
            <span class="notification-center__time">${notificationTimeAgo(n.created_at)}</span>
        </span>
    `;
    return li;
}

async function loadNotifications() {
    try {
        const params = new URLSearchParams();
        if (activeFilter.value) params.set(activeFilter.type, activeFilter.value);

        const response = await fetch(`/notifications?${params.toString()}`);
        const notifications = await response.json();

        notificationList.querySelectorAll(".notification-center__item").forEach(el => el.remove());
        const empty = document.getElementById("notification-center-empty");

        if (notifications.length === 0) {
            if (empty) empty.hidden = false;
        } else {
            if (empty) empty.hidden = true;
            notifications.forEach(n => notificationList.appendChild(renderNotificationItem(n)));
        }

        setUnreadCount(notifications.filter(n => !n.is_read).length);
    } catch (error) {
        console.error(error);
    }
}

async function markAllRead() {
    try {
        await fetch("/notification/read", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({}),
        });
        setUnreadCount(0);
        notificationList.querySelectorAll(".notification-center__item").forEach(el => {
            el.dataset.read = "true";
        });
    } catch (error) {
        console.error(error);
    }
}

bellButton.addEventListener("click", () => {
    const isHidden = notificationCenter.hidden;
    notificationCenter.hidden = !isHidden;
    bellButton.setAttribute("aria-expanded", String(isHidden));

    if (isHidden) {
        loadNotifications();
        // Step 5 — opening the panel resets the counter to 0
        markAllRead();
    }
});

notificationFilters.addEventListener("click", (event) => {
    const button = event.target.closest(".notification-filter");
    if (!button) return;

    notificationFilters.querySelectorAll(".notification-filter").forEach(b => {
        b.classList.remove("notification-filter--active");
    });
    button.classList.add("notification-filter--active");

    activeFilter = {
        type: button.dataset.filterType,
        value: button.dataset.filterValue,
    };

    loadNotifications();
});

notificationClear.addEventListener("click", async () => {
    if (!confirm("Clear all notification history for your family?")) return;

    try {
        await fetch("/notifications", { method: "DELETE" });
        loadNotifications();
    } catch (error) {
        console.error(error);
    }
});

/* ---------------------------------------------------
   Step 8 — Toast messages for live events
--------------------------------------------------- */
function showToast(n) {
    const meta = NOTIFICATION_META[n.type] || NOTIFICATION_META.message;

    const toast = document.createElement("div");
    toast.className = "toast";
    toast.style.setProperty("--notif-color", meta.color);
    toast.innerHTML = `
        <span class="toast__icon">${meta.icon}</span>
        <span class="toast__message">${n.message}</span>
        <span class="toast__time">Just now</span>
    `;

    toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.classList.add("toast--leaving");
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

/* ---------------------------------------------------
   Step 7 — live notifications over Socket.IO
--------------------------------------------------- */
socket.on("notification", (data) => {
    showToast(data);
    setUnreadCount(unreadCount + 1);

    // If the panel is open, prepend it live instead of waiting for a refetch
    if (!notificationCenter.hidden) {
        const empty = document.getElementById("notification-center-empty");
        if (empty) empty.hidden = true;
        notificationList.prepend(renderNotificationItem(data));
    }
});

loadNotifications();