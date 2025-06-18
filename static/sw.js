// Service Worker for 我的日記 PWA
const CACHE_NAME = 'diabetes-diary-v1.0.0';
const STATIC_CACHE_NAME = 'diabetes-diary-static-v1.0.0';
const DATA_CACHE_NAME = 'diabetes-diary-data-v1.0.0';

// Files to cache for offline functionality
const STATIC_FILES = [
  '/',
  '/manifest.json',
  '/generated-icon.png'
];

// Install event - cache essential files
self.addEventListener('install', (event) => {
  console.log('Service Worker installing...');
  event.waitUntil(
    Promise.all([
      caches.open(STATIC_CACHE_NAME).then((cache) => {
        console.log('Caching static files');
        return cache.addAll(STATIC_FILES);
      }),
      caches.open(DATA_CACHE_NAME).then((cache) => {
        console.log('Data cache initialized');
        return cache;
      })
    ])
  );
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('Service Worker activating...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== STATIC_CACHE_NAME && 
              cacheName !== DATA_CACHE_NAME && 
              cacheName !== CACHE_NAME) {
            console.log('Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Fetch event - serve from cache when offline
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Handle API requests with network-first strategy
  if (url.pathname.includes('api') || url.pathname.includes('streamlit')) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          // Clone the response before caching
          const responseClone = response.clone();
          
          // Cache successful responses
          if (response.status === 200) {
            caches.open(DATA_CACHE_NAME).then((cache) => {
              cache.put(request, responseClone);
            });
          }
          
          return response;
        })
        .catch(() => {
          // Serve from cache when network fails
          return caches.match(request).then((cachedResponse) => {
            if (cachedResponse) {
              return cachedResponse;
            }
            
            // Return offline page or fallback
            return new Response(JSON.stringify({
              error: 'Offline mode active',
              message: 'Using cached data'
            }), {
              headers: { 'Content-Type': 'application/json' }
            });
          });
        })
    );
    return;
  }

  // Handle static files with cache-first strategy
  event.respondWith(
    caches.match(request).then((cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse;
      }

      return fetch(request).then((response) => {
        // Cache the new resource
        if (response.status === 200) {
          const responseClone = response.clone();
          caches.open(STATIC_CACHE_NAME).then((cache) => {
            cache.put(request, responseClone);
          });
        }
        
        return response;
      }).catch(() => {
        // Return a fallback for offline mode
        if (request.destination === 'document') {
          return caches.match('/').then((cachedPage) => {
            return cachedPage || new Response('Offline - Please check your connection', {
              status: 503,
              statusText: 'Service Unavailable'
            });
          });
        }
      });
    })
  );
});

// Background sync for offline data persistence
self.addEventListener('sync', (event) => {
  console.log('Background sync triggered:', event.tag);
  
  if (event.tag === 'diabetes-data-sync') {
    event.waitUntil(syncDiabetesData());
  }
});

// Function to sync diabetes data when online
async function syncDiabetesData() {
  try {
    // Get pending data from IndexedDB or localStorage
    const pendingData = await getPendingData();
    
    if (pendingData && pendingData.length > 0) {
      // Attempt to sync with server
      for (const dataItem of pendingData) {
        try {
          await syncDataItem(dataItem);
          // Remove from pending queue on successful sync
          await removePendingData(dataItem.id);
        } catch (error) {
          console.error('Failed to sync data item:', error);
        }
      }
    }
  } catch (error) {
    console.error('Background sync failed:', error);
  }
}

// Helper functions for data synchronization
async function getPendingData() {
  // Implementation would retrieve pending data from IndexedDB
  return [];
}

async function syncDataItem(dataItem) {
  // Implementation would send data to server
  console.log('Syncing data item:', dataItem);
}

async function removePendingData(itemId) {
  // Implementation would remove synced data from pending queue
  console.log('Removed pending data:', itemId);
}

// Push notification handler for health alerts
self.addEventListener('push', (event) => {
  if (event.data) {
    const data = event.data.json();
    
    const options = {
      body: data.body || '请检查您的血糖记录',
      icon: '/generated-icon.png',
      badge: '/generated-icon.png',
      tag: 'diabetes-alert',
      requireInteraction: true,
      actions: [
        {
          action: 'view',
          title: '查看详情'
        },
        {
          action: 'dismiss',
          title: '忽略'
        }
      ]
    };

    event.waitUntil(
      self.registration.showNotification(data.title || '糖尿病提醒', options)
    );
  }
});

// Handle notification clicks
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  if (event.action === 'view') {
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});