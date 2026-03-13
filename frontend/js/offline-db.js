// IndexedDB for offline patient submissions and cached health records
const DB_NAME = 'sehatsetu_offline';
const DB_VERSION = 2;
const STORE_NAME = 'patient_queue';
const CONSULTATIONS_STORE = 'consultations_cache';
const HISTORY_STORE = 'patient_history_cache';

function openDB() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(DB_NAME, DB_VERSION);

        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            if (!db.objectStoreNames.contains(STORE_NAME)) {
                db.createObjectStore(STORE_NAME, { keyPath: 'id', autoIncrement: true });
            }
            if (!db.objectStoreNames.contains(CONSULTATIONS_STORE)) {
                const consultationsStore = db.createObjectStore(CONSULTATIONS_STORE, { keyPath: 'id' });
                consultationsStore.createIndex('status', 'status', { unique: false });
                consultationsStore.createIndex('patient_id', 'patient_id', { unique: false });
                consultationsStore.createIndex('created_at', 'created_at', { unique: false });
            }
            if (!db.objectStoreNames.contains(HISTORY_STORE)) {
                const historyStore = db.createObjectStore(HISTORY_STORE, { keyPath: 'patient_id' });
                historyStore.createIndex('cached_at', 'cached_at', { unique: false });
            }
        };

        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

/** Save patient submission to offline queue */
async function saveToQueue(patientData) {
    const db = await openDB();
    return new Promise((resolve, reject) => {
        const tx = db.transaction(STORE_NAME, 'readwrite');
        const store = tx.objectStore(STORE_NAME);
        patientData.queued_at = new Date().toISOString();
        patientData.synced = false;
        const req = store.add(patientData);
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
        tx.oncomplete = () => db.close();
    });
}

/** Get all queued submissions */
async function getQueue() {
    const db = await openDB();
    return new Promise((resolve, reject) => {
        const tx = db.transaction(STORE_NAME, 'readonly');
        const store = tx.objectStore(STORE_NAME);
        const req = store.getAll();
        req.onsuccess = () => resolve(req.result.filter(item => !item.synced));
        req.onerror = () => reject(req.error);
        tx.oncomplete = () => db.close();
    });
}

/** Mark an item as synced */
async function markSynced(id) {
    const db = await openDB();
    return new Promise((resolve, reject) => {
        const tx = db.transaction(STORE_NAME, 'readwrite');
        const store = tx.objectStore(STORE_NAME);
        const getReq = store.get(id);
        getReq.onsuccess = () => {
            const item = getReq.result;
            if (item) {
                item.synced = true;
                store.put(item);
            }
            resolve();
        };
        getReq.onerror = () => reject(getReq.error);
        tx.oncomplete = () => db.close();
    });
}

/** Get count of pending items */
async function getQueueCount() {
    const queue = await getQueue();
    return queue.length;
}

/** Clear all synced items */
async function clearSynced() {
    const db = await openDB();
    return new Promise((resolve, reject) => {
        const tx = db.transaction(STORE_NAME, 'readwrite');
        const store = tx.objectStore(STORE_NAME);
        const req = store.getAll();
        req.onsuccess = () => {
            req.result.filter(item => item.synced).forEach(item => store.delete(item.id));
            resolve();
        };
        req.onerror = () => reject(req.error);
        tx.oncomplete = () => db.close();
    });
}

/** Cache consultations for offline doctor access */
async function cacheConsultations(consultations) {
    if (!Array.isArray(consultations) || consultations.length === 0) return;

    const db = await openDB();
    return new Promise((resolve, reject) => {
        const tx = db.transaction(CONSULTATIONS_STORE, 'readwrite');
        const store = tx.objectStore(CONSULTATIONS_STORE);

        consultations.forEach(item => {
            store.put({
                ...item,
                _cached_at: new Date().toISOString()
            });
        });

        tx.oncomplete = () => {
            db.close();
            resolve();
        };
        tx.onerror = () => reject(tx.error);
    });
}

/** Cache a single consultation update */
async function cacheConsultation(consultation) {
    if (!consultation || !consultation.id) return;
    await cacheConsultations([consultation]);
}

/** Read cached consultations and optionally filter by status */
async function getCachedConsultations(status) {
    const db = await openDB();
    return new Promise((resolve, reject) => {
        const tx = db.transaction(CONSULTATIONS_STORE, 'readonly');
        const store = tx.objectStore(CONSULTATIONS_STORE);
        const req = store.getAll();

        req.onsuccess = () => {
            const items = req.result || [];
            const filtered = status ? items.filter(item => item.status === status) : items;
            filtered.sort((a, b) => {
                const priorityOrder = { RED: 0, YELLOW: 1, GREEN: 2 };
                const priorityDiff = (priorityOrder[a.ai_priority] ?? 1) - (priorityOrder[b.ai_priority] ?? 1);
                if (priorityDiff !== 0) return priorityDiff;
                return new Date(b.created_at || 0) - new Date(a.created_at || 0);
            });
            resolve(filtered);
        };
        req.onerror = () => reject(req.error);
        tx.oncomplete = () => db.close();
    });
}

/** Cache full patient history for offline medical-record access */
async function cachePatientHistory(patientId, historyData) {
    if (!patientId || !historyData) return;

    const db = await openDB();
    return new Promise((resolve, reject) => {
        const tx = db.transaction(HISTORY_STORE, 'readwrite');
        const store = tx.objectStore(HISTORY_STORE);

        store.put({
            patient_id: patientId,
            patient: historyData.patient || null,
            consultations: historyData.consultations || [],
            cached_at: new Date().toISOString()
        });

        tx.oncomplete = () => {
            db.close();
            resolve();
        };
        tx.onerror = () => reject(tx.error);
    });
}

/** Read cached patient history */
async function getCachedPatientHistory(patientId) {
    if (!patientId) return null;

    const db = await openDB();
    return new Promise((resolve, reject) => {
        const tx = db.transaction(HISTORY_STORE, 'readonly');
        const store = tx.objectStore(HISTORY_STORE);
        const req = store.get(patientId);

        req.onsuccess = () => resolve(req.result || null);
        req.onerror = () => reject(req.error);
        tx.oncomplete = () => db.close();
    });
}
