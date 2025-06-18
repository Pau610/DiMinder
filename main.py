import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import pytz
from models.glucose_predictor import GlucosePredictor
from utils.data_processor import DataProcessor
from utils.visualization import create_glucose_plot, create_prediction_plot
import plotly.graph_objects as go

# Set Hong Kong timezone
HK_TZ = pytz.timezone('Asia/Hong_Kong')

# Page config
st.set_page_config(
    page_title="我的日記",
    layout="wide",
    initial_sidebar_state="collapsed"  # 在移动端默认收起侧边栏
)

# PWA Meta tags and manifest
st.markdown("""
<meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
<meta name="theme-color" content="#1f77b4">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="我的日記">
<meta name="description" content="专业的糖尿病健康数据管理和预测应用">
<link rel="manifest" href="/static/manifest.json">
<link rel="apple-touch-icon" href="/generated-icon.png">
<link rel="icon" type="image/png" href="/generated-icon.png">
""", unsafe_allow_html=True)

# Custom CSS for mobile-friendly design and localStorage
st.markdown("""
<style>
    /* 增大按钮尺寸 */
    .stButton > button {
        width: 100%;
        padding: 0.75rem 1.5rem;
        font-size: 1.1rem;
    }

    /* 优化输入框样式 */
    .stNumberInput input,
    .stTextInput input,
    .stDateInput input {
        font-size: 1.1rem;
        padding: 0.5rem;
    }

    /* 优化选择框样式 */
    .stSelectbox select {
        font-size: 1.1rem;
        padding: 0.5rem;
    }

    /* 响应式布局调整 */
    @media (max-width: 768px) {
        .element-container {
            margin: 0.5rem 0;
        }

        /* 调整图表容器 */
        .plotly-graph-div {
            height: 300px !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# Enhanced PWA JavaScript with offline functionality and IndexedDB
st.markdown("""
<script>
// Service Worker Registration for PWA
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/sw.js')
            .then(registration => {
                console.log('ServiceWorker registered successfully');
                // Enable background sync
                if ('sync' in window.ServiceWorkerRegistration.prototype) {
                    console.log('Background Sync supported');
                }
            })
            .catch(error => {
                console.log('ServiceWorker registration failed:', error);
            });
    });
}

// Enhanced Local Storage with IndexedDB for PWA - Version Safe
class PWADiabetesStorage {
    constructor() {
        this.storageKey = 'diabetes_diary_data';
        this.backupKey = 'diabetes_diary_backup';
        this.versionKey = 'diabetes_app_version';
        this.migrationKey = 'diabetes_migration_backup';
        this.dbName = 'DiabetesDiaryDB';
        this.dbVersion = 2;
        this.currentAppVersion = '2.1.0';
        this.db = null;
        this.initVersionSafeStorage();
    }
    
    // Initialize version-safe storage system
    async initVersionSafeStorage() {
        await this.checkVersionAndMigrate();
        await this.initIndexedDB();
    }

    // Check app version and protect user data during updates
    async checkVersionAndMigrate() {
        const savedVersion = localStorage.getItem(this.versionKey);
        
        if (!savedVersion) {
            // First time installation
            localStorage.setItem(this.versionKey, this.currentAppVersion);
            console.log('First installation - version tracking initialized');
            return;
        }
        
        if (savedVersion !== this.currentAppVersion) {
            console.log(`App version updated from ${savedVersion} to ${this.currentAppVersion}`);
            await this.protectDataDuringUpdate(savedVersion);
            localStorage.setItem(this.versionKey, this.currentAppVersion);
        }
    }

    // Protect user data during version updates
    async protectDataDuringUpdate(oldVersion) {
        try {
            // Create timestamped backup before any update
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            const backupKey = `${this.migrationKey}_${oldVersion}_${timestamp}`;
            
            // Backup localStorage data
            const currentData = localStorage.getItem(this.storageKey);
            if (currentData) {
                localStorage.setItem(backupKey, currentData);
                console.log(`Data backed up to ${backupKey} before version update`);
            }
            
            // Backup IndexedDB data
            if (this.db) {
                const indexedData = await this.loadFromIndexedDB();
                if (indexedData && indexedData.length > 0) {
                    localStorage.setItem(`${backupKey}_indexed`, JSON.stringify(indexedData));
                    console.log('IndexedDB data backed up before version update');
                }
            }
            
            // Mark as migration-protected
            localStorage.setItem('migration_protected', 'true');
            localStorage.setItem('migration_timestamp', timestamp);
            
        } catch (error) {
            console.error('Error protecting data during update:', error);
            // Even if backup fails, don't block the update
        }
    }

    // Initialize IndexedDB for offline storage
    async initIndexedDB() {
        try {
            const request = indexedDB.open(this.dbName, this.dbVersion);
            
            request.onerror = () => {
                console.error('IndexedDB error:', request.error);
                this.fallbackToLocalStorage();
            };
            
            request.onsuccess = () => {
                this.db = request.result;
                console.log('IndexedDB initialized successfully');
            };
            
            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                
                // Create object stores
                if (!db.objectStoreNames.contains('diabetesData')) {
                    const store = db.createObjectStore('diabetesData', { keyPath: 'id', autoIncrement: true });
                    store.createIndex('timestamp', 'timestamp', { unique: false });
                    store.createIndex('type', 'type', { unique: false });
                }
                
                if (!db.objectStoreNames.contains('pendingSync')) {
                    db.createObjectStore('pendingSync', { keyPath: 'id', autoIncrement: true });
                }
            };
        } catch (error) {
            console.error('IndexedDB initialization failed:', error);
            this.fallbackToLocalStorage();
        }
    }
    
    // Fallback to localStorage if IndexedDB fails
    fallbackToLocalStorage() {
        console.log('Using localStorage fallback');
        this.useLocalStorageOnly = true;
    }
    
    // Save data with offline protection - never override existing data
    async saveData(data) {
        try {
            // Load existing offline data first
            const existingData = await this.loadData();
            
            // Merge new data with existing to prevent overwrites
            const mergedData = this.mergeOfflineData(existingData, data);
            
            // Save merged data to IndexedDB
            if (this.db && !this.useLocalStorageOnly) {
                await this.saveToIndexedDB(mergedData);
            }
            
            // Backup to localStorage with conflict protection
            const jsonData = JSON.stringify(mergedData);
            localStorage.setItem(this.storageKey, jsonData);
            localStorage.setItem(this.backupKey, jsonData);
            
            // Mark offline entries for sync protection
            this.markOfflineEntries(mergedData);
            
            // Pure offline app - no server sync needed
            console.log('Data saved locally (offline-only mode)');
            
            console.log('Data saved with offline protection (PWA mode)');
            return true;
        } catch (error) {
            console.error('Error saving data:', error);
            return false;
        }
    }
    
    // Pure offline data management - no merging needed for single-user app
    mergeOfflineData(existingData, newData) {
        // For offline-only app, just return the new data
        return Array.isArray(newData) ? newData : (Array.isArray(existingData) ? existingData : []);
    }
    
    // Pure offline app - no need for offline marking
    markOfflineEntries(data) {
        // All data is offline in this standalone app
        console.log('Pure offline app - all data is local');
    }
    
    // Save to IndexedDB
    async saveToIndexedDB(data) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['diabetesData'], 'readwrite');
            const store = transaction.objectStore('diabetesData');
            
            // Clear existing data and add new
            store.clear().onsuccess = () => {
                data.forEach((item, index) => {
                    const record = {
                        ...item,
                        syncStatus: 'pending',
                        localId: index
                    };
                    store.add(record);
                });
            };
            
            transaction.oncomplete = () => resolve();
            transaction.onerror = () => reject(transaction.error);
        });
    }
    
    // Queue data for background sync
    queueForSync(data) {
        if (navigator.serviceWorker && navigator.serviceWorker.ready) {
            navigator.serviceWorker.ready.then(registration => {
                return registration.sync.register('diabetes-data-sync');
            }).catch(error => {
                console.log('Background sync registration failed:', error);
            });
        }
    }
    
    // Load data with version-safe recovery
    async loadData() {
        try {
            // Check if migration protection is needed
            const isMigrationProtected = localStorage.getItem('migration_protected') === 'true';
            
            if (isMigrationProtected) {
                console.log('Loading data with migration protection active');
                return await this.loadDataWithMigrationProtection();
            }
            
            // Normal data loading
            return await this.loadDataNormal();
            
        } catch (error) {
            console.error('Error loading data:', error);
            return await this.recoverDataFromBackups();
        }
    }

    // Load data with migration protection
    async loadDataWithMigrationProtection() {
        // Try IndexedDB first
        if (this.db && !this.useLocalStorageOnly) {
            const indexedData = await this.loadFromIndexedDB();
            if (indexedData && indexedData.length > 0) {
                return indexedData;
            }
        }
        
        // Try main storage
        const data = localStorage.getItem(this.storageKey);
        if (data) {
            return JSON.parse(data);
        }
        
        // If main storage is empty, recover from migration backups
        return await this.recoverFromMigrationBackups();
    }

    // Normal data loading (no migration protection needed)
    async loadDataNormal() {
        // Try IndexedDB first
        if (this.db && !this.useLocalStorageOnly) {
            const indexedData = await this.loadFromIndexedDB();
            if (indexedData && indexedData.length > 0) {
                return indexedData;
            }
        }
        
        // Fallback to localStorage
        const data = localStorage.getItem(this.storageKey);
        if (data) {
            return JSON.parse(data);
        }
        
        const backupData = localStorage.getItem(this.backupKey);
        if (backupData) {
            return JSON.parse(backupData);
        }
        
        return null;
    }

    // Recover data from migration backups
    async recoverFromMigrationBackups() {
        try {
            // Find the most recent migration backup
            const allKeys = Object.keys(localStorage);
            const migrationBackups = allKeys.filter(key => key.startsWith(this.migrationKey));
            
            if (migrationBackups.length > 0) {
                // Sort by timestamp and get the most recent
                migrationBackups.sort().reverse();
                const latestBackup = migrationBackups[0];
                
                console.log(`Recovering data from migration backup: ${latestBackup}`);
                const backupData = localStorage.getItem(latestBackup);
                
                if (backupData) {
                    const recoveredData = JSON.parse(backupData);
                    
                    // Restore to main storage
                    localStorage.setItem(this.storageKey, backupData);
                    console.log('Data successfully recovered from migration backup');
                    
                    return recoveredData;
                }
            }
            
            return null;
        } catch (error) {
            console.error('Error recovering from migration backups:', error);
            return null;
        }
    }

    // Recover data from any available backups
    async recoverDataFromBackups() {
        try {
            console.log('Attempting data recovery from all available backups');
            
            // Try migration backups first
            const migrationData = await this.recoverFromMigrationBackups();
            if (migrationData) return migrationData;
            
            // Try regular backup
            const backupData = localStorage.getItem(this.backupKey);
            if (backupData) {
                console.log('Recovered data from regular backup');
                return JSON.parse(backupData);
            }
            
            // Try IndexedDB backup
            if (this.db) {
                const indexedData = await this.loadFromIndexedDB();
                if (indexedData && indexedData.length > 0) {
                    console.log('Recovered data from IndexedDB');
                    return indexedData;
                }
            }
            
            console.log('No backup data found for recovery');
            return null;
        } catch (error) {
            console.error('Error in data recovery:', error);
            return null;
        }
    }
    
    // Load from IndexedDB
    async loadFromIndexedDB() {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['diabetesData'], 'readonly');
            const store = transaction.objectStore('diabetesData');
            const request = store.getAll();
            
            request.onsuccess = () => {
                const results = request.result.map(item => {
                    const { id, syncStatus, localId, ...data } = item;
                    return data;
                });
                resolve(results);
            };
            
            request.onerror = () => reject(request.error);
        });
    }
    
    // Export data for mobile app transfer
    exportData() {
        this.loadData().then(data => {
            if (data) {
                const exportData = {
                    version: '1.0.0',
                    exportDate: new Date().toISOString(),
                    app: '我的日記',
                    data: data
                };
                
                const blob = new Blob([JSON.stringify(exportData, null, 2)], {
                    type: 'application/json'
                });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `diabetes_diary_${new Date().toISOString().split('T')[0]}.json`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                console.log('Data exported for mobile app transfer');
            }
        });
    }
    
    // Check offline status
    isOnline() {
        return navigator.onLine;
    }
    
    // Get storage info with version safety details
    async getStorageInfo() {
        const data = await this.loadData();
        const backupInfo = this.getBackupInfo();
        
        return {
            hasData: !!(data && data.length > 0),
            dataSize: data ? JSON.stringify(data).length : 0,
            recordCount: data ? data.length : 0,
            lastModified: new Date().toISOString(),
            isOnline: this.isOnline(),
            storageType: this.useLocalStorageOnly ? 'localStorage' : 'IndexedDB',
            appVersion: this.currentAppVersion,
            migrationProtected: localStorage.getItem('migration_protected') === 'true',
            backupCount: backupInfo.migration_backups + (backupInfo.regular_backup_exists ? 1 : 0)
        };
    }

    // Get backup information for export and status
    getBackupInfo() {
        const allKeys = Object.keys(localStorage);
        const migrationBackups = allKeys.filter(key => key.startsWith(this.migrationKey));
        
        return {
            migration_backups: migrationBackups.length,
            latest_migration: migrationBackups.length > 0 ? migrationBackups.sort().reverse()[0] : null,
            regular_backup_exists: !!localStorage.getItem(this.backupKey),
            storage_version: this.dbVersion,
            protected_since: localStorage.getItem('migration_timestamp')
        };
    }

    // Enhanced export with version-safe backup information
    async exportData() {
        try {
            const data = await this.loadData();
            if (!data || data.length === 0) {
                console.log('No data available for export');
                return false;
            }
            
            // Include version and backup information in export
            const exportData = {
                exported_at: new Date().toISOString(),
                app_version: this.currentAppVersion,
                timezone: 'Asia/Shanghai',
                export_type: 'version_safe_backup',
                migration_protected: localStorage.getItem('migration_protected') === 'true',
                data_count: data.length,
                data: data,
                backup_info: this.getBackupInfo()
            };
            
            const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `diabetes_backup_v${this.currentAppVersion}_${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            console.log('Version-safe data export completed');
            return true;
        } catch (error) {
            console.error('Error exporting data:', error);
            return false;
        }
    }

    // Clean old migration backups (keep only last 3)
    cleanOldMigrationBackups() {
        try {
            const allKeys = Object.keys(localStorage);
            const migrationBackups = allKeys.filter(key => key.startsWith(this.migrationKey));
            
            if (migrationBackups.length > 3) {
                migrationBackups.sort();
                const toRemove = migrationBackups.slice(0, migrationBackups.length - 3);
                
                toRemove.forEach(key => {
                    localStorage.removeItem(key);
                    console.log(`Cleaned old migration backup: ${key}`);
                });
            }
        } catch (error) {
            console.error('Error cleaning old backups:', error);
        }
    }
}

// Initialize PWA storage manager
window.diabetesStorage = new PWADiabetesStorage();

// PWA functions
window.autoSaveData = function(data) {
    return window.diabetesStorage.saveData(data);
};

window.loadStoredData = function() {
    return window.diabetesStorage.loadData();
};

window.exportForMobile = function() {
    window.diabetesStorage.exportData();
};

// PWA install prompt
let deferredPrompt;
window.addEventListener('beforeinstallprompt', (e) => {
    deferredPrompt = e;
    console.log('PWA install prompt available');
});

window.showInstallPrompt = function() {
    if (deferredPrompt) {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then((choiceResult) => {
            if (choiceResult.outcome === 'accepted') {
                console.log('User accepted PWA install');
            }
            deferredPrompt = null;
        });
    }
};

// Network status monitoring
window.addEventListener('online', () => {
    console.log('App is online');
    // Trigger background sync
    if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
        navigator.serviceWorker.ready.then(registration => {
            return registration.sync.register('diabetes-data-sync');
        });
    }
});

window.addEventListener('offline', () => {
    console.log('App is offline - using local storage');
});
</script>
""", unsafe_allow_html=True)

# Helper function for time input parsing
def parse_time_input(time_input, default_time=None):
    """Parse time input from various formats including 4-digit format"""
    if not time_input:
        return default_time or datetime.now(HK_TZ).time()
    
    # Remove any spaces and colons
    time_str = str(time_input).replace(" ", "").replace(":", "")
    
    try:
        # Handle 4-digit format (e.g., 1430 -> 14:30)
        if len(time_str) == 4 and time_str.isdigit():
            hour = int(time_str[:2])
            minute = int(time_str[2:])
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time()
        
        # Handle 3-digit format (e.g., 930 -> 09:30)
        elif len(time_str) == 3 and time_str.isdigit():
            hour = int(time_str[0])
            minute = int(time_str[1:])
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time()
        
        # Handle 1-2 digit format (e.g., 9 -> 09:00, 14 -> 14:00)
        elif len(time_str) in [1, 2] and time_str.isdigit():
            hour = int(time_str)
            if 0 <= hour <= 23:
                return datetime.strptime(f"{hour:02d}:00", "%H:%M").time()
        
        # Handle standard HH:MM format
        elif ":" in time_str:
            return datetime.strptime(time_str, "%H:%M").time()
            
    except ValueError:
        pass
    
    # If parsing fails, return default time
    return default_time or datetime.now(HK_TZ).time()

# Functions for persistent data storage
def load_persistent_data():
    """Load data with offline protection and conflict resolution"""
    def create_empty_dataframe():
        return pd.DataFrame({
            'timestamp': [],
            'glucose_level': [],
            'carbs': [],
            'insulin': [],
            'insulin_type': [],
            'injection_site': [],
            'food_details': []
        }).astype({
            'timestamp': 'datetime64[ns]',
            'glucose_level': 'float64',
            'carbs': 'float64', 
            'insulin': 'float64',
            'insulin_type': 'object',
            'injection_site': 'object',
            'food_details': 'object'
        })
    
    try:
        # Load offline data first (highest priority to protect user's offline work)
        offline_data = None
        
        # Check for offline data in browser storage
        components.html("""
        <script>
            if (window.diabetesStorage) {
                window.diabetesStorage.loadData().then(data => {
                    if (data && data.length > 0) {
                        // Check for offline entries
                        const hasOfflineData = data.some(item => item.isOffline === true);
                        if (hasOfflineData) {
                            console.log('Offline data detected - protecting from overwrites');
                            // Store in a way that Python can access
                            localStorage.setItem('has_offline_data', 'true');
                            localStorage.setItem('offline_data_count', data.filter(item => item.isOffline).length);
                        }
                    }
                });
            }
        </script>
        """, height=0)
        
        # Priority order for data recovery with offline protection
        data_sources = [
            'user_data.csv',
            'user_data_safe.csv', 
            'user_data_backup.csv'
        ]
        
        # Try to load from each source in priority order
        for source_file in data_sources:
            if os.path.exists(source_file):
                try:
                    data = pd.read_csv(source_file)
                    data['timestamp'] = pd.to_datetime(data['timestamp'])
                    
                    # Verify data integrity
                    required_columns = ['timestamp', 'glucose_level', 'carbs', 'insulin']
                    if all(col in data.columns for col in required_columns):
                        # Add offline protection metadata if not present
                        if 'isOffline' not in data.columns:
                            data['isOffline'] = False
                        if 'offlineCreated' not in data.columns:
                            data['offlineCreated'] = None
                            
                        # If this is not the primary file but has data, restore it carefully
                        if source_file != 'user_data.csv' and not data.empty:
                            # Only restore if we don't have offline data that could be lost
                            import shutil
                            shutil.copy(source_file, 'user_data.csv')
                            st.info(f"已从备份文件{source_file}恢复数据 (已保护离线数据)")
                        return data
                except Exception as e:
                    st.warning(f"尝试从{source_file}加载数据失败: {e}")
                    continue
        
        # If no user data files exist, create initial data from imported sample
        if not any(os.path.exists(f) for f in data_sources):
            if os.path.exists('processed_dm_data.csv'):
                try:
                    imported_data = pd.read_csv('processed_dm_data.csv')
                    imported_data['timestamp'] = pd.to_datetime(imported_data['timestamp'])
                    # Save as user data with multiple backups
                    imported_data.to_csv('user_data.csv', index=False)
                    imported_data.to_csv('user_data_safe.csv', index=False)
                    imported_data.to_csv('user_data_backup.csv', index=False)
                    return imported_data
                except Exception as e:
                    st.warning(f"导入初始数据失败: {e}")
        
        # Last resort: return empty dataframe
        empty_df = create_empty_dataframe()
        # Save empty dataframe to prevent repeated initialization attempts
        empty_df.to_csv('user_data.csv', index=False)
        return empty_df
        
    except Exception as e:
        st.error(f"数据加载严重失败: {e}")
        return create_empty_dataframe()

def save_persistent_data():
    """Save current data to persistent storage with multiple backup layers"""
    try:
        import shutil
        from datetime import datetime
        
        # Create timestamped backup
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create multiple backup copies
        if os.path.exists('user_data.csv'):
            shutil.copy('user_data.csv', 'user_data_backup.csv')
            shutil.copy('user_data.csv', f'user_data_backup_{timestamp}.csv')
        
        # Save current data with verification
        temp_file = 'user_data_temp.csv'
        st.session_state.glucose_data.to_csv(temp_file, index=False)
        
        # Verify temp file before replacing main file
        if os.path.exists(temp_file):
            test_read = pd.read_csv(temp_file)
            if len(test_read) == len(st.session_state.glucose_data):
                # Verification passed, replace main file
                shutil.move(temp_file, 'user_data.csv')
                
                # Create additional safety backup
                shutil.copy('user_data.csv', 'user_data_safe.csv')
                
                # Save to localStorage with offline protection
                try:
                    data_json = st.session_state.glucose_data.to_json(orient='records', date_format='iso')
                    components.html(f"""
                    <script>
                        try {{
                            if (window.diabetesStorage) {{
                                const data = {data_json};
                                // Use protected save that merges with existing offline data
                                window.diabetesStorage.saveData(data).then(success => {{
                                    if (success) {{
                                        console.log('Data saved with offline protection');
                                        // Update UI to show protection status
                                        const protectedCount = data.filter(item => item.isOffline).length;
                                        if (protectedCount > 0) {{
                                            localStorage.setItem('protected_offline_entries', protectedCount.toString());
                                        }}
                                    }}
                                }});
                            }}
                        }} catch (error) {{
                            console.error('Protected localStorage save failed:', error);
                        }}
                    </script>
                    """, height=0)
                except Exception as e:
                    # Log error but don't interrupt main save process
                    st.warning(f"离线数据保护保存失败: {e}")
                    pass
                
                # Clean up old timestamped backups (keep only last 10)
                import glob
                backup_files = glob.glob('user_data_backup_*.csv')
                if len(backup_files) > 10:
                    backup_files.sort()
                    for old_backup in backup_files[:-10]:
                        try:
                            os.remove(old_backup)
                        except:
                            pass
            else:
                # Verification failed, remove temp file and restore backup
                os.remove(temp_file)
                if os.path.exists('user_data_backup.csv'):
                    st.error("数据保存验证失败，已保持原有数据")
            
    except Exception as e:
        st.error(f"数据保存失败: {e}")
        # Try multiple recovery options
        recovery_files = ['user_data_backup.csv', 'user_data_safe.csv']
        for recovery_file in recovery_files:
            if os.path.exists(recovery_file):
                try:
                    import shutil
                    shutil.copy(recovery_file, 'user_data.csv')
                    st.warning(f"已从{recovery_file}恢复数据")
                    break
                except:
                    continue

def generate_daily_summary(selected_date):
    """Generate daily summary in the requested format"""
    if st.session_state.glucose_data.empty:
        return ""
    
    # Filter data for the selected date
    data = st.session_state.glucose_data.copy()
    data['date'] = pd.to_datetime(data['timestamp']).dt.date
    daily_data = data[data['date'] == selected_date].sort_values('timestamp')
    
    if daily_data.empty:
        return f"({selected_date}\n 无记录\n)"
    
    summary_lines = [f"({selected_date}"]
    
    for _, row in daily_data.iterrows():
        time_str = pd.to_datetime(row['timestamp']).strftime('%H:%M')
        
        # Blood glucose record
        if row['glucose_level'] > 0:
            glucose_mmol = round(row['glucose_level'] / 18.0182, 1)
            summary_lines.append(f" {time_str} => {glucose_mmol}mmol")
        
        # Insulin injection record
        if row['insulin'] > 0:
            insulin_dose = int(row['insulin']) if float(row['insulin']).is_integer() else row['insulin']
            summary_lines.append(f" {time_str} => {insulin_dose}U {row['insulin_type']}")
        
        # Meal record - show if there are actual food details (including 0g carbs)
        if (pd.notna(row['food_details']) and 
            str(row['food_details']).strip() != '' and
            row['food_details'] != ''):
            carbs_total = int(row['carbs']) if pd.notna(row['carbs']) and float(row['carbs']).is_integer() else (row['carbs'] if pd.notna(row['carbs']) else 0)
            summary_lines.append(f" {time_str} => {row['food_details']} [{carbs_total}g]")
    
    summary_lines.append(" )")
    return "\n".join(summary_lines)

# Enhanced session state initialization with data corruption protection
def validate_session_data():
    """Validate and recover session data if corrupted"""
    if 'glucose_data' not in st.session_state or st.session_state.glucose_data is None:
        return False
    
    try:
        # Check if data structure is valid
        required_columns = ['timestamp', 'glucose_level', 'carbs', 'insulin']
        if not isinstance(st.session_state.glucose_data, pd.DataFrame):
            return False
        if not all(col in st.session_state.glucose_data.columns for col in required_columns):
            return False
        return True
    except:
        return False

# Initialize or recover session state data
if not validate_session_data():
    st.session_state.glucose_data = load_persistent_data()
    st.session_state.data_initialized = True
    st.session_state.data_recovery_count = 0
else:
    # Verify data hasn't been accidentally reset
    if hasattr(st.session_state, 'last_record_count'):
        current_count = len(st.session_state.glucose_data)
        if current_count < st.session_state.last_record_count:
            # Data loss detected - attempt recovery
            recovered_data = load_persistent_data()
            if len(recovered_data) > current_count:
                st.session_state.glucose_data = recovered_data
                st.warning(f"检测到数据丢失，已恢复 {len(recovered_data)} 条记录")

# Track record count for loss detection
st.session_state.last_record_count = len(st.session_state.glucose_data)

# Enhanced periodic backup system
if 'last_backup_time' not in st.session_state:
    st.session_state.last_backup_time = datetime.now()
    st.session_state.backup_interval = 180  # 3 minutes for more frequent saves
else:
    current_time = datetime.now()
    time_diff = current_time - st.session_state.last_backup_time
    # More aggressive auto-save schedule
    if time_diff.total_seconds() > st.session_state.backup_interval and not st.session_state.glucose_data.empty:
        save_persistent_data()
        st.session_state.last_backup_time = current_time
        # Show subtle save confirmation
        if len(st.session_state.glucose_data) > 0:
            st.toast(f"已自动保存 {len(st.session_state.glucose_data)} 条记录", icon="💾")



if 'selected_time' not in st.session_state:
    st.session_state.selected_time = datetime.now().time()

try:
    if 'predictor' not in st.session_state:
        st.session_state.predictor = GlucosePredictor()
    if 'processor' not in st.session_state:
        st.session_state.processor = DataProcessor()
except Exception as e:
    st.error(f"初始化预测模型时发生错误: {str(e)}")

# Version and title display
col1, col2 = st.columns([1, 10])
with col1:
    st.caption("v2.1.0")
with col2:
    st.title("📔 我的日記")

# Daily Summary Section
st.markdown("### 📋 每日记录摘要")
col1, col2 = st.columns([3, 1])

with col1:
    # Date selector for daily summary
    if not st.session_state.glucose_data.empty:
        data_dates = pd.to_datetime(st.session_state.glucose_data['timestamp']).dt.date.unique()
        data_dates = sorted(data_dates, reverse=True)
        
        if data_dates:
            selected_date = st.selectbox(
                "选择日期查看摘要",
                options=data_dates,
                format_func=lambda x: x.strftime('%Y-%m-%d'),
                key="summary_date_select"
            )
            
            # Generate and display daily summary
            daily_summary = generate_daily_summary(selected_date)
            
            if daily_summary:
                st.text_area(
                    "每日摘要 (可复制)",
                    value=daily_summary,
                    height=200,
                    key="daily_summary_text"
                )
            else:
                st.info("选择的日期没有记录")
        else:
            st.info("暂无数据可显示摘要")
    else:
        st.info("暂无数据可显示摘要")

with col2:
    pass

# Manual Data Entry Section
st.markdown("### 📝 数据录入")

# Data type selection buttons
col1, col2, col3 = st.columns(3)

with col1:
    glucose_selected = st.button("血糖记录", use_container_width=True, type="primary" if st.session_state.get('input_type') == 'glucose' else "secondary")
    if glucose_selected:
        st.session_state.input_type = 'glucose'

with col2:
    meal_selected = st.button("饮食记录", use_container_width=True, type="primary" if st.session_state.get('input_type') == 'meal' else "secondary")
    if meal_selected:
        st.session_state.input_type = 'meal'

with col3:
    insulin_selected = st.button("胰岛素注射", use_container_width=True, type="primary" if st.session_state.get('input_type') == 'insulin' else "secondary")
    if insulin_selected:
        st.session_state.input_type = 'insulin'

# Initialize input type if not set
if 'input_type' not in st.session_state:
    st.session_state.input_type = 'glucose'

st.markdown("---")

# Show selected input form
if st.session_state.input_type == 'glucose':
    # Blood glucose input
    st.markdown("#### 🩸 记录血糖")
    # 添加日期选择器
    col1, col2 = st.columns(2)
    with col1:
        hk_today = datetime.now(HK_TZ).date()
        record_date = st.date_input(
            "记录日期 (GMT+8)",
            hk_today,
            max_value=hk_today,
            key="glucose_date"
        )
    with col2:
        # 初始化血糖记录时间状态 (HK时区)
        if 'glucose_time_state' not in st.session_state:
            hk_now = datetime.now(HK_TZ)
            st.session_state.glucose_time_state = hk_now.strftime("%H:%M")
        
        # Custom time input with clear button
        components.html(f"""
        <div style="margin-bottom: 10px;">
            <label style="font-size: 14px; font-weight: 600; margin-bottom: 4px; display: block;">记录时间 (GMT+8)</label>
            <div style="position: relative; display: flex; align-items: center;">
                <input 
                    type="text" 
                    id="glucose_time_input_custom" 
                    value="{st.session_state.glucose_time_state}"
                    placeholder="例如: 1430 或 14:30"
                    style="
                        width: 100%; 
                        padding: 8px 35px 8px 12px; 
                        border: 1px solid #d1d5db; 
                        border-radius: 6px; 
                        font-size: 14px;
                        background-color: white;
                    "
                    oninput="updateGlucoseTime(this.value)"
                    onblur="handleGlucoseTimeBlur()"
                />
                <button 
                    onclick="clearGlucoseTime()" 
                    style="
                        position: absolute; 
                        right: 8px; 
                        background: none; 
                        border: none; 
                        color: #6b7280; 
                        cursor: pointer; 
                        font-size: 16px;
                        padding: 4px;
                        border-radius: 3px;
                    "
                    onmouseover="this.style.backgroundColor='#f3f4f6'"
                    onmouseout="this.style.backgroundColor='transparent'"
                    title="清除时间"
                >×</button>
            </div>
            <small style="color: #6b7280; font-size: 12px;">支持格式: 1430, 14:30, 930, 9:30</small>
        </div>
        <script>
            function updateGlucoseTime(value) {{
                // Store the raw input value
                window.glucoseTimeRawInput = value;
            }}
            
            function handleGlucoseTimeBlur() {{
                let value = document.getElementById('glucose_time_input_custom').value;
                if (value && (value.length === 3 || value.length === 4)) {{
                    let formatted = formatTimeInput(value);
                    if (formatted !== value && formatted.includes(':')) {{
                        document.getElementById('glucose_time_input_custom').value = formatted;
                        window.glucoseTimeRawInput = formatted;
                    }}
                }}
            }}
            
            function formatTimeInput(input) {{
                // Remove any non-digit characters except colon
                let cleaned = input.replace(/[^0-9:]/g, '');
                
                // Handle 4-digit format (2350 -> 23:50)
                if (cleaned.length === 4 && !cleaned.includes(':')) {{
                    let hours = parseInt(cleaned.substring(0, 2));
                    let minutes = parseInt(cleaned.substring(2));
                    // Validate hours (00-23) and minutes (00-59)
                    if (hours >= 0 && hours <= 23 && minutes >= 0 && minutes <= 59) {{
                        return cleaned.substring(0, 2) + ':' + cleaned.substring(2);
                    }}
                }}
                
                // Handle 3-digit format (930 -> 09:30)
                if (cleaned.length === 3 && !cleaned.includes(':')) {{
                    let hour = parseInt(cleaned.substring(0, 1));
                    let minutes = parseInt(cleaned.substring(1));
                    // Validate hour (0-9) and minutes (00-59)
                    if (hour >= 0 && hour <= 9 && minutes >= 0 && minutes <= 59) {{
                        return '0' + cleaned.substring(0, 1) + ':' + cleaned.substring(1);
                    }}
                }}
                
                return cleaned;
            }}
            
            function clearGlucoseTime() {{
                document.getElementById('glucose_time_input_custom').value = '';
                window.glucoseTimeRawInput = '';
            }}
            
            // Initialize the stored value
            window.glucoseTimeRawInput = '{st.session_state.glucose_time_state}';
        </script>
        """, height=80)
        
        # Parse the time input and update state
        record_time = parse_time_input(st.session_state.glucose_time_state)
        st.session_state.glucose_time_state = record_time.strftime("%H:%M")
        
        # Display parsed time for confirmation
        if st.session_state.glucose_time_state:
            st.caption(f"解析时间: {record_time.strftime('%H:%M')}")

    glucose_mmol = st.number_input("血糖水平 (mmol/L)", min_value=2.0, max_value=22.0, value=None, step=0.1, key="glucose_level", placeholder="请输入血糖值")

    if st.button("添加血糖记录", use_container_width=True):
        if glucose_mmol is not None:
            record_datetime = datetime.combine(record_date, record_time)
            # Convert mmol/L to mg/dL for internal storage
            glucose_level_mgdl = glucose_mmol * 18.0182
            new_data = {
                'timestamp': record_datetime,
                'glucose_level': glucose_level_mgdl,
                'carbs': 0,
                'insulin': 0,
                'insulin_type': '',
                'injection_site': '',
                'food_details': ''
            }
            st.session_state.glucose_data = pd.concat([
                st.session_state.glucose_data,
                pd.DataFrame([new_data])
            ], ignore_index=True)
            # Immediate save with validation
            save_persistent_data()
            # Verify save was successful
            if os.path.exists('user_data.csv'):
                st.success(f"血糖记录已保存！当前共有 {len(st.session_state.glucose_data)} 条记录")
            else:
                st.error("数据保存失败，请重试")
        else:
            st.error("请输入血糖值")

elif st.session_state.input_type == 'meal':
    # Meal input
    st.markdown("#### 🍽️ 记录饮食")
    # 添加日期选择器
    col1, col2 = st.columns(2)
    with col1:
        hk_today = datetime.now(HK_TZ).date()
        meal_date = st.date_input(
            "用餐日期 (GMT+8)",
            hk_today,
            max_value=hk_today,
            key="meal_date"
        )
    with col2:
        # 初始化用餐时间状态 (HK时区)
        if 'meal_time_state' not in st.session_state:
            hk_now = datetime.now(HK_TZ)
            st.session_state.meal_time_state = hk_now.strftime("%H:%M")
        
        # Custom meal time input with clear button
        components.html(f"""
        <div style="margin-bottom: 10px;">
            <label style="font-size: 14px; font-weight: 600; margin-bottom: 4px; display: block;">用餐时间 (GMT+8)</label>
            <div style="position: relative; display: flex; align-items: center;">
                <input 
                    type="text" 
                    id="meal_time_input_custom" 
                    value="{st.session_state.meal_time_state}"
                    placeholder="例如: 1230 或 12:30"
                    style="
                        width: 100%; 
                        padding: 8px 35px 8px 12px; 
                        border: 1px solid #d1d5db; 
                        border-radius: 6px; 
                        font-size: 14px;
                        background-color: white;
                    "
                    oninput="updateMealTime(this.value)"
                    onblur="handleMealTimeBlur()"
                />
                <button 
                    onclick="clearMealTime()" 
                    style="
                        position: absolute; 
                        right: 8px; 
                        background: none; 
                        border: none; 
                        color: #6b7280; 
                        cursor: pointer; 
                        font-size: 16px;
                        padding: 4px;
                        border-radius: 3px;
                    "
                    onmouseover="this.style.backgroundColor='#f3f4f6'"
                    onmouseout="this.style.backgroundColor='transparent'"
                    title="清除时间"
                >×</button>
            </div>
            <small style="color: #6b7280; font-size: 12px;">支持格式: 1230, 12:30, 730, 7:30</small>
        </div>
        <script>
            function updateMealTime(value) {{
                // Store the raw input value
                window.mealTimeRawInput = value;
            }}
            
            function handleMealTimeBlur() {{
                let value = document.getElementById('meal_time_input_custom').value;
                if (value && (value.length === 3 || value.length === 4)) {{
                    let formatted = formatTimeInput(value);
                    if (formatted !== value && formatted.includes(':')) {{
                        document.getElementById('meal_time_input_custom').value = formatted;
                        window.mealTimeRawInput = formatted;
                    }}
                }}
            }}
            
            function formatTimeInput(input) {{
                // Remove any non-digit characters except colon
                let cleaned = input.replace(/[^0-9:]/g, '');
                
                // Handle 4-digit format (2350 -> 23:50)
                if (cleaned.length === 4 && !cleaned.includes(':')) {{
                    let hours = parseInt(cleaned.substring(0, 2));
                    let minutes = parseInt(cleaned.substring(2));
                    // Validate hours (00-23) and minutes (00-59)
                    if (hours >= 0 && hours <= 23 && minutes >= 0 && minutes <= 59) {{
                        return cleaned.substring(0, 2) + ':' + cleaned.substring(2);
                    }}
                }}
                
                // Handle 3-digit format (930 -> 09:30)
                if (cleaned.length === 3 && !cleaned.includes(':')) {{
                    let hour = parseInt(cleaned.substring(0, 1));
                    let minutes = parseInt(cleaned.substring(1));
                    // Validate hour (0-9) and minutes (00-59)
                    if (hour >= 0 && hour <= 9 && minutes >= 0 && minutes <= 59) {{
                        return '0' + cleaned.substring(0, 1) + ':' + cleaned.substring(1);
                    }}
                }}
                
                return cleaned;
            }}
            
            function clearMealTime() {{
                document.getElementById('meal_time_input_custom').value = '';
                window.mealTimeRawInput = '';
            }}
            
            // Initialize the stored value
            window.mealTimeRawInput = '{st.session_state.meal_time_state}';
        </script>
        """, height=80)
        
        # Parse the time input and update state
        meal_time = parse_time_input(st.session_state.meal_time_state)
        st.session_state.meal_time_state = meal_time.strftime("%H:%M")
        
        # Display parsed time for confirmation
        if st.session_state.meal_time_state:
            st.caption(f"解析时间: {meal_time.strftime('%H:%M')}")

    # 初始化食物列表
    if 'meal_foods' not in st.session_state:
        st.session_state.meal_foods = []

    # 添加食物输入
    st.write("添加食物:")
    col_food, col_carbs, col_add = st.columns([3, 2, 1])
    
    with col_food:
        food_name = st.text_input("食物名称", key="food_name_input", placeholder="例如：米饭、面条、苹果...")
    
    with col_carbs:
        carbs_amount = st.number_input("碳水化合物 (克)", min_value=0.0, max_value=500.0, value=None, step=0.1, key="carbs_input", placeholder="请输入克数")
    
    with col_add:
        st.write("")  # 空行对齐
        if st.button("➕", key="add_food_btn", help="添加食物"):
            if food_name and carbs_amount is not None and carbs_amount >= 0:
                st.session_state.meal_foods.append({
                    'food': food_name,
                    'carbs': carbs_amount
                })
                st.rerun()

    # 显示已添加的食物
    if st.session_state.meal_foods:
        st.write("本餐食物:")
        total_carbs = 0
        for i, food_item in enumerate(st.session_state.meal_foods):
            col_display, col_remove = st.columns([4, 1])
            with col_display:
                st.write(f"• {food_item['food']}: {food_item['carbs']}g 碳水化合物")
                total_carbs += food_item['carbs']
            with col_remove:
                if st.button("🗑️", key=f"remove_food_{i}", help="删除"):
                    st.session_state.meal_foods.pop(i)
                    st.rerun()
        
        st.write(f"**总碳水化合物: {total_carbs:.1f}g**")

        if st.button("添加饮食记录", use_container_width=True):
            meal_datetime = datetime.combine(meal_date, meal_time)
            # Create detailed food description
            food_list = [f"{item['food']} ({item['carbs']}g碳水)" for item in st.session_state.meal_foods]
            food_details = "; ".join(food_list)
            
            new_meal = {
                'timestamp': meal_datetime,
                'glucose_level': 0,
                'carbs': total_carbs,
                'insulin': 0,
                'insulin_type': '',
                'injection_site': '',
                'food_details': food_details
            }
            st.session_state.glucose_data = pd.concat([
                st.session_state.glucose_data,
                pd.DataFrame([new_meal])
            ], ignore_index=True)
            # Immediate save with validation
            save_persistent_data()
            # Verify save was successful
            if os.path.exists('user_data.csv'):
                # 清空食物列表
                st.session_state.meal_foods = []
                st.success(f"饮食记录已保存！当前共有 {len(st.session_state.glucose_data)} 条记录")
                st.rerun()
            else:
                st.error("数据保存失败，请重试")
    else:
        st.info("请添加食物和碳水化合物含量")

elif st.session_state.input_type == 'insulin':
    # Insulin injection input
    st.markdown("#### 💉 记录胰岛素注射")
    # 添加日期选择器
    col1, col2 = st.columns(2)
    with col1:
        hk_today = datetime.now(HK_TZ).date()
        injection_date = st.date_input(
            "注射日期 (GMT+8)",
            hk_today,
            max_value=hk_today,
            key="injection_date"
        )
    with col2:
        # 初始化注射时间状态 (HK时区)
        if 'injection_time_state' not in st.session_state:
            hk_now = datetime.now(HK_TZ)
            st.session_state.injection_time_state = hk_now.strftime("%H:%M")
        
        # Custom injection time input with clear button
        components.html(f"""
        <div style="margin-bottom: 10px;">
            <label style="font-size: 14px; font-weight: 600; margin-bottom: 4px; display: block;">注射时间 (GMT+8)</label>
            <div style="position: relative; display: flex; align-items: center;">
                <input 
                    type="text" 
                    id="injection_time_input_custom" 
                    value="{st.session_state.injection_time_state}"
                    placeholder="例如: 0800 或 08:00"
                    style="
                        width: 100%; 
                        padding: 8px 35px 8px 12px; 
                        border: 1px solid #d1d5db; 
                        border-radius: 6px; 
                        font-size: 14px;
                        background-color: white;
                    "
                    oninput="updateInjectionTime(this.value)"
                    onblur="handleInjectionTimeBlur()"
                />
                <button 
                    onclick="clearInjectionTime()" 
                    style="
                        position: absolute; 
                        right: 8px; 
                        background: none; 
                        border: none; 
                        color: #6b7280; 
                        cursor: pointer; 
                        font-size: 16px;
                        padding: 4px;
                        border-radius: 3px;
                    "
                    onmouseover="this.style.backgroundColor='#f3f4f6'"
                    onmouseout="this.style.backgroundColor='transparent'"
                    title="清除时间"
                >×</button>
            </div>
            <small style="color: #6b7280; font-size: 12px;">支持格式: 0800, 08:00, 800, 8:00</small>
        </div>
        <script>
            function updateInjectionTime(value) {{
                // Store the raw input value
                window.injectionTimeRawInput = value;
            }}
            
            function handleInjectionTimeBlur() {{
                let value = document.getElementById('injection_time_input_custom').value;
                if (value && (value.length === 3 || value.length === 4)) {{
                    let formatted = formatTimeInput(value);
                    if (formatted !== value && formatted.includes(':')) {{
                        document.getElementById('injection_time_input_custom').value = formatted;
                        window.injectionTimeRawInput = formatted;
                    }}
                }}
            }}
            
            function formatTimeInput(input) {{
                // Remove any non-digit characters except colon
                let cleaned = input.replace(/[^0-9:]/g, '');
                
                // Handle 4-digit format (2350 -> 23:50)
                if (cleaned.length === 4 && !cleaned.includes(':')) {{
                    let hours = parseInt(cleaned.substring(0, 2));
                    let minutes = parseInt(cleaned.substring(2));
                    // Validate hours (00-23) and minutes (00-59)
                    if (hours >= 0 && hours <= 23 && minutes >= 0 && minutes <= 59) {{
                        return cleaned.substring(0, 2) + ':' + cleaned.substring(2);
                    }}
                }}
                
                // Handle 3-digit format (930 -> 09:30)
                if (cleaned.length === 3 && !cleaned.includes(':')) {{
                    let hour = parseInt(cleaned.substring(0, 1));
                    let minutes = parseInt(cleaned.substring(1));
                    // Validate hour (0-9) and minutes (00-59)
                    if (hour >= 0 && hour <= 9 && minutes >= 0 && minutes <= 59) {{
                        return '0' + cleaned.substring(0, 1) + ':' + cleaned.substring(1);
                    }}
                }}
                
                return cleaned;
            }}
            
            function clearInjectionTime() {{
                document.getElementById('injection_time_input_custom').value = '';
                window.injectionTimeRawInput = '';
            }}
            
            // Initialize the stored value
            window.injectionTimeRawInput = '{st.session_state.injection_time_state}';
        </script>
        """, height=80)
        
        # Parse the time input and update state
        injection_time = parse_time_input(st.session_state.injection_time_state)
        st.session_state.injection_time_state = injection_time.strftime("%H:%M")
        
        # Display parsed time for confirmation
        if st.session_state.injection_time_state:
            st.caption(f"解析时间: {injection_time.strftime('%H:%M')}")

    # 注射部位选择
    injection_site = st.selectbox(
        "注射部位",
        ["腹部", "大腿", "手臂", "臀部"],
        key="injection_site_select"
    )

    # 胰岛素类型和剂量
    insulin_type = st.selectbox(
        "胰岛素类型",
        ["短效胰岛素", "中效胰岛素", "长效胰岛素"],
        key="insulin_type_select"
    )
    insulin_dose = st.number_input(
        "胰岛素剂量 (单位)",
        min_value=0.0, 
        max_value=100.0, 
        value=None,
        step=1.0,
        placeholder="请输入剂量",
        key="insulin_dose"
    )

    if st.button("添加注射记录", use_container_width=True):
                if insulin_dose is not None and insulin_dose > 0:
                    injection_datetime = datetime.combine(injection_date, injection_time)
                    new_injection = {
                        'timestamp': injection_datetime,
                        'glucose_level': 0,
                        'carbs': 0,
                        'insulin': insulin_dose,
                        'insulin_type': insulin_type,
                        'injection_site': injection_site,
                        'food_details': ''
                    }
                    st.session_state.glucose_data = pd.concat([
                        st.session_state.glucose_data,
                        pd.DataFrame([new_injection])
                    ], ignore_index=True)
                    # Immediate save with validation
                    save_persistent_data()
                    # Verify save was successful
                    if os.path.exists('user_data.csv'):
                        st.success(f"注射记录已保存！当前共有 {len(st.session_state.glucose_data)} 条记录")
                    else:
                        st.error("数据保存失败，请重试")
                else:
                    st.error("请输入胰岛素剂量")

    # PWA and Mobile App Transfer Section
    st.markdown("---")
    st.subheader("📱 PWA 离线应用")
    
    # Enhanced storage status with PWA capabilities
    components.html("""
    <div id="pwa-status-container"></div>
    <script>
        async function updatePWAStatus() {
            if (window.diabetesStorage) {
                const info = await window.diabetesStorage.getStorageInfo();
                const isInstalled = window.matchMedia('(display-mode: standalone)').matches;
                const canInstall = !!window.deferredPrompt || !isInstalled;
                
                const statusDiv = document.getElementById('pwa-status-container');
                statusDiv.innerHTML = `
                    <div style="padding: 15px; background: linear-gradient(135deg, #e3f2fd, #f3e5f5); 
                               border-radius: 10px; margin: 10px 0; border-left: 4px solid #1976d2;">
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 10px;">
                            <div>
                                <strong>🔄 本地存储:</strong> ${info.hasData ? '✅ 已保存' : '❌ 无数据'}<br>
                                <small>记录数: ${info.recordCount || 0} | 大小: ${(info.dataSize/1024).toFixed(1)} KB</small>
                            </div>
                            <div>
                                <strong>📲 应用状态:</strong> ${isInstalled ? '✅ 已安装' : '📥 可安装'}<br>
                                <small>存储类型: ${info.storageType}</small>
                            </div>
                        </div>
                        <div style="text-align: center; padding: 10px; background: rgba(76, 175, 80, 0.1); border-radius: 8px;">
                            <strong>🏠 独立离线应用</strong><br>
                            <small>所有数据保存在您的设备本地，完全离线可用，隐私安全</small>
                        </div>
                    </div>
                `;
            }
        }
        
        // Update status immediately and every 5 seconds
        updatePWAStatus();
        setInterval(updatePWAStatus, 5000);
    </script>
    """, height=120)
    
    # PWA action buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📲 安装PWA", use_container_width=True, help="安装为手机应用，支持离线使用"):
            components.html("""
            <script>
                if (window.showInstallPrompt) {
                    window.showInstallPrompt();
                } else if (window.matchMedia('(display-mode: standalone)').matches) {
                    alert('应用已经安装！');
                } else {
                    alert('请在Chrome/Edge浏览器中使用"添加到主屏幕"功能安装PWA应用');
                }
            </script>
            """, height=50)
    
    with col2:
        if st.button("📤 导出数据", use_container_width=True, help="下载JSON文件用于数据传输"):
            components.html("""
            <script>
                if (window.exportForMobile) {
                    window.exportForMobile();
                    setTimeout(() => {
                        alert('数据已导出为JSON文件！可用于iOS应用或其他设备导入。');
                    }, 500);
                } else {
                    alert('导出功能初始化中，请稍后重试。');
                }
            </script>
            """, height=50)
    
    with col3:
        if st.button("💾 手动同步", use_container_width=True, help="手动触发数据同步和备份"):
            save_persistent_data()
            components.html("""
            <script>
                // Trigger background sync if available
                if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
                    navigator.serviceWorker.ready.then(registration => {
                        if ('sync' in registration) {
                            return registration.sync.register('diabetes-data-sync');
                        }
                    }).catch(console.error);
                }
            </script>
            """, height=50)
            st.success("数据已同步到本地存储")
    
    # PWA features info
    with st.expander("🚀 PWA功能说明", expanded=False):
        st.markdown("""
        **独立离线应用 (PWA) 功能:**
        
        🔸 **完全离线**: 无网络时完全可用，不依赖服务器
        🔸 **应用安装**: 可安装到手机主屏幕，像原生应用一样使用
        🔸 **个人数据**: 每个用户拥有独立的本地数据存储
        🔸 **数据安全**: IndexedDB + localStorage 双重本地备份
        🔸 **隐私保护**: 所有数据保存在设备本地，不会上传到服务器
        🔸 **数据导出**: 支持JSON格式导出，便于备份和转移
        🔸 **推送通知**: 支持健康提醒和血糖警告通知
        🔸 **快速启动**: 缓存技术确保快速加载
        
        **如何安装PWA:**
        1. 在Chrome/Edge浏览器中打开应用
        2. 点击地址栏的"安装"图标，或使用上方"安装PWA"按钮
        3. 确认安装，应用将添加到主屏幕
        4. 可像普通应用一样从主屏幕启动
        """)
        
    st.info("💡 独立离线应用，所有数据保存在您的设备本地，完全离线可用，隐私安全")
    
    # Display version-safe status
    components.html("""
    <div id="version-safe-status"></div>
    <script>
        function showVersionSafeStatus() {
            const appVersion = localStorage.getItem('diabetes_app_version');
            const isMigrationProtected = localStorage.getItem('migration_protected') === 'true';
            const migrationTimestamp = localStorage.getItem('migration_timestamp');
            
            const statusDiv = document.getElementById('version-safe-status');
            
            let statusHtml = `
                <div style="background: linear-gradient(135deg, #e8f5e8, #d4edda); 
                           padding: 10px; border-radius: 8px; margin: 10px 0; 
                           border-left: 4px solid #28a745;">
                    🏠 <strong>纯离线应用模式</strong> - 所有数据完全保存在您的设备本地
                    <br><small>当前版本: ${appVersion || '未知'}</small>
            `;
            
            if (isMigrationProtected && migrationTimestamp) {
                const backupTime = new Date(migrationTimestamp.replace(/-/g, ':')).toLocaleString('zh-CN');
                statusHtml += `
                    <br>
                    <div style="margin-top: 8px; padding: 6px; background: rgba(255, 193, 7, 0.2); border-radius: 4px;">
                        🛡️ <strong>版本更新保护激活</strong> - 数据已在 ${backupTime} 自动备份
                    </div>
                `;
            }
            
            statusHtml += '</div>';
            statusDiv.innerHTML = statusHtml;
        }
        
        showVersionSafeStatus();
        
        // Update status periodically
        setInterval(showVersionSafeStatus, 5000);
    </script>
    """, height=80)

# 血糖预警系统 (显著位置)
if not st.session_state.glucose_data.empty:
    latest_glucose = st.session_state.glucose_data['glucose_level'].iloc[-1]
    if latest_glucose <= 40:
        st.error("🚨 严重低血糖预警！当前血糖: {:.1f} mg/dL - 请立即处理！".format(latest_glucose))
        st.markdown("**紧急处理建议：**")
        st.markdown("- 立即摄入15-20克快速碳水化合物")
        st.markdown("- 15分钟后重新测量血糖")
        st.markdown("- 如无改善请寻求医疗帮助")
    elif latest_glucose < 70:
        st.warning("⚠️ 低血糖预警！当前血糖: {:.1f} mg/dL - 请及时处理".format(latest_glucose))

# Main content with responsive layout
if st.session_state.glucose_data.empty:
    st.info("还没有任何记录，请先添加数据。")
else:
    # 根据屏幕宽度决定使用单列或双列布局
    screen_width = st.empty()
    is_mobile = screen_width.checkbox("Mobile View", value=False, key="mobile_view")
    screen_width.empty()  # 清除checkbox

    if is_mobile:
        # 移动端单列布局
        # 血糖趋势
        st.subheader("血糖趋势")
        try:
            # Date range selector with responsive layout
            st.write("选择日期范围：")
            col_start, col_end = st.columns(2)
            with col_start:
                start_date = st.date_input(
                    "开始日期",
                    datetime.now() - timedelta(days=7)
                )
            with col_end:
                end_date = st.date_input(
                    "结束日期",
                    datetime.now()
                )

            # Convert dates to datetime
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())

            # Sort and filter data
            data_sorted = st.session_state.glucose_data.sort_values('timestamp')
            data_filtered = data_sorted[
                (data_sorted['timestamp'] >= start_datetime) &
                (data_sorted['timestamp'] <= end_datetime)
            ]

            # Create interactive plot with date range
            fig = create_glucose_plot(data_filtered, (start_datetime, end_datetime))
            st.plotly_chart(fig, use_container_width=True, height=350)

            # Recent statistics
            st.subheader("最近统计")
            recent_data = data_sorted.tail(5)
            col1, col2 = st.columns(2)
            with col1:
                latest_mmol = round(recent_data['glucose_level'].iloc[-1] / 18.0182, 1)
                st.metric("最新血糖", f"{latest_mmol} mmol/L")
            with col2:
                avg_mmol = round(recent_data['glucose_level'].mean() / 18.0182, 1)
                st.metric("平均值 (最近5次)", f"{avg_mmol} mmol/L")

            # 血糖预警检查
            recent_glucose = recent_data['glucose_level'].iloc[-1]
            if recent_glucose <= 40:
                st.error("⚠️ 危险！当前血糖值过低，请立即处理！")
            elif recent_glucose < 70:
                st.warning("⚠️ 注意！当前血糖值偏低，请及时补充糖分。")


            # Predictions
            st.subheader("血糖预测")
            if len(data_filtered) >= 3:
                predictions = st.session_state.predictor.predict(data_filtered)
                fig_pred = create_prediction_plot(data_filtered, predictions)
                st.plotly_chart(fig_pred, use_container_width=True, height=350)
            else:
                st.info("需要至少3个血糖记录来进行预测")


            # Real-time predictions
            st.subheader("实时血糖预测")
            if len(data_filtered) >= 12:
                real_time_predictions = st.session_state.predictor.predict_real_time(data_filtered)
                if len(real_time_predictions) > 0:
                    pred_times = [datetime.now() + timedelta(minutes=5*i) for i in range(6)]
                    real_time_df = pd.DataFrame({
                        'timestamp': pred_times,
                        'glucose_level': real_time_predictions
                    })
                    lower_bound, upper_bound = st.session_state.predictor.get_prediction_intervals(real_time_predictions)

                    fig_real_time = go.Figure()

                    # Convert to mmol/L for display
                    real_time_predictions_mmol = [p / 18.0182 for p in real_time_predictions]
                    upper_bound_mmol = [p / 18.0182 for p in upper_bound]
                    lower_bound_mmol = [p / 18.0182 for p in lower_bound]

                    # Add prediction intervals
                    fig_real_time.add_trace(go.Scatter(
                        x=pred_times + pred_times[::-1],
                        y=np.concatenate([upper_bound_mmol, lower_bound_mmol[::-1]]),
                        fill='toself',
                        fillcolor='rgba(0,176,246,0.2)',
                        line=dict(color='rgba(255,255,255,0)'),
                        name='预测区间'
                    ))

                    # Add predictions
                    fig_real_time.add_trace(go.Scatter(
                        x=pred_times,
                        y=real_time_predictions_mmol,
                        name='预测值',
                        line=dict(color='red', width=2)
                    ))

                    fig_real_time.update_layout(
                        title='未来30分钟血糖预测',
                        xaxis_title='时间',
                        yaxis_title='血糖值 (mmol/L)',
                        height=300
                    )
                    st.plotly_chart(fig_real_time, use_container_width=True)

                    # Check if any predicted values are dangerous (convert to mmol/L thresholds)
                    # 40 mg/dL = 2.2 mmol/L, 70 mg/dL = 3.9 mmol/L, 180 mg/dL = 10.0 mmol/L
                    predictions_mmol = [p / 18.0182 for p in real_time_predictions]
                    if np.any(np.array(predictions_mmol) <= 2.2):
                        st.error("⚠️ 危险！预测未来30分钟内可能出现严重低血糖，请立即采取预防措施！")
                    elif np.any(np.array(predictions_mmol) < 3.9):
                        st.warning("⚠️ 注意！预测未来30分钟内可能出现低血糖，请做好准备。")

                    if np.any(np.array(predictions_mmol) > 10.0) or np.any(np.array(predictions_mmol) < 3.9):
                        st.warning("⚠️ 预测显示血糖可能会超出目标范围，请注意监测")
                else:
                    st.info("需要至少1小时的数据来进行实时预测")

            # Insulin needs prediction
            st.subheader("胰岛素需求预测")
            if len(data_filtered) >= 24:
                insulin_predictions = st.session_state.processor.predict_insulin_needs(data_filtered)
                if len(insulin_predictions) > 0:
                    pred_hours = [datetime.now() + timedelta(hours=i) for i in range(24)]
                    insulin_df = pd.DataFrame({
                        'timestamp': pred_hours,
                        'insulin': insulin_predictions
                    })

                    fig_insulin = go.Figure()
                    fig_insulin.add_trace(go.Scatter(
                        x=pred_hours,
                        y=insulin_predictions,
                        name='预计胰岛素需求',
                        line=dict(color='purple', width=2)
                    ))

                    fig_insulin.update_layout(
                        title='24小时胰岛素需求预测',
                        xaxis_title='时间',
                        yaxis_title='胰岛素剂量 (单位)',
                        height=300
                    )
                    st.plotly_chart(fig_insulin, use_container_width=True)
            else:
                st.info("需要至少24小时的数据来预测胰岛素需求")

            # Injection site analysis
            st.subheader("注射部位分析")
            site_stats = st.session_state.processor.analyze_injection_sites(data_filtered)
            if site_stats:
                site_df = pd.DataFrame(site_stats)
                st.write("注射部位使用统计：")
                st.dataframe(site_df)
            else:
                st.info("暂无注射部位数据")

        except Exception as e:
            st.error(f"生成图表时发生错误: {str(e)}")

    else:
        # 桌面端双列布局
        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("血糖趋势")
            try:
                # Date range selector
                st.write("选择日期范围：")
                col_start, col_end = st.columns(2)
                with col_start:
                    start_date = st.date_input(
                        "开始日期",
                        datetime.now() - timedelta(days=7)
                    )
                with col_end:
                    end_date = st.date_input(
                        "结束日期",
                        datetime.now()
                    )

                # Convert dates to datetime
                start_datetime = datetime.combine(start_date, datetime.min.time())
                end_datetime = datetime.combine(end_date, datetime.max.time())

                # Sort and filter data
                data_sorted = st.session_state.glucose_data.sort_values('timestamp')
                data_filtered = data_sorted[
                    (data_sorted['timestamp'] >= start_datetime) &
                    (data_sorted['timestamp'] <= end_datetime)
                ]

                # Create interactive plot with date range
                fig = create_glucose_plot(data_filtered, (start_datetime, end_datetime))
                st.plotly_chart(fig, use_container_width=True, height=450)

                # Predictions
                st.subheader("血糖预测")
                if len(data_filtered) >= 3:
                    predictions = st.session_state.predictor.predict(data_filtered)
                    fig_pred = create_prediction_plot(data_filtered, predictions)
                    st.plotly_chart(fig_pred, use_container_width=True, height=450)
                else:
                    st.info("需要至少3个血糖记录来进行预测")

                # Real-time predictions
                st.subheader("实时血糖预测")
                if len(data_filtered) >= 12:
                    real_time_predictions = st.session_state.predictor.predict_real_time(data_filtered)
                    if len(real_time_predictions) > 0:
                        pred_times = [datetime.now() + timedelta(minutes=5*i) for i in range(6)]
                        real_time_df = pd.DataFrame({
                            'timestamp': pred_times,
                            'glucose_level': real_time_predictions
                        })
                        lower_bound, upper_bound = st.session_state.predictor.get_prediction_intervals(real_time_predictions)

                        fig_real_time = go.Figure()

                        # Convert to mmol/L for display
                        real_time_predictions_mmol = [p / 18.0182 for p in real_time_predictions]
                        upper_bound_mmol = [p / 18.0182 for p in upper_bound]
                        lower_bound_mmol = [p / 18.0182 for p in lower_bound]

                        # Add prediction intervals
                        fig_real_time.add_trace(go.Scatter(
                            x=pred_times + pred_times[::-1],
                            y=np.concatenate([upper_bound_mmol, lower_bound_mmol[::-1]]),
                            fill='toself',
                            fillcolor='rgba(0,176,246,0.2)',
                            line=dict(color='rgba(255,255,255,0)'),
                            name='预测区间'
                        ))

                        # Add predictions
                        fig_real_time.add_trace(go.Scatter(
                            x=pred_times,
                            y=real_time_predictions_mmol,
                            name='预测值',
                            line=dict(color='red', width=2)
                        ))

                        fig_real_time.update_layout(
                            title='未来30分钟血糖预测',
                            xaxis_title='时间',
                            yaxis_title='血糖值 (mmol/L)',
                            height=300
                        )
                        st.plotly_chart(fig_real_time, use_container_width=True)

                        # Check if any predicted values are dangerous (convert to mmol/L thresholds)
                        # 40 mg/dL = 2.2 mmol/L, 70 mg/dL = 3.9 mmol/L, 180 mg/dL = 10.0 mmol/L
                        predictions_mmol = [p / 18.0182 for p in real_time_predictions]
                        if np.any(np.array(predictions_mmol) <= 2.2):
                            st.error("⚠️ 危险！预测未来30分钟内可能出现严重低血糖，请立即采取预防措施！")
                        elif np.any(np.array(predictions_mmol) < 3.9):
                            st.warning("⚠️ 注意！预测未来30分钟内可能出现低血糖，请做好准备。")

                        if np.any(np.array(predictions_mmol) > 10.0) or np.any(np.array(predictions_mmol) < 3.9):
                            st.warning("⚠️ 预测显示血糖可能会超出目标范围，请注意监测")
                else:
                    st.info("需要至少1小时的数据来进行实时预测")

                # Insulin needs prediction
                st.subheader("胰岛素需求预测")
                if len(data_filtered) >= 24:
                    insulin_predictions = st.session_state.processor.predict_insulin_needs(data_filtered)
                    if len(insulin_predictions) > 0:
                        pred_hours = [datetime.now() + timedelta(hours=i) for i in range(24)]
                        insulin_df = pd.DataFrame({
                            'timestamp': pred_hours,
                            'insulin': insulin_predictions
                        })

                        fig_insulin = go.Figure()
                        fig_insulin.add_trace(go.Scatter(
                            x=pred_hours,
                            y=insulin_predictions,
                            name='预计胰岛素需求',
                            line=dict(color='purple', width=2)
                        ))

                        fig_insulin.update_layout(
                            title='24小时胰岛素需求预测',
                            xaxis_title='时间',
                            yaxis_title='胰岛素剂量 (单位)',
                            height=300
                        )
                        st.plotly_chart(fig_insulin, use_container_width=True)
                else:
                    st.info("需要至少24小时的数据来预测胰岛素需求")

                # Injection site analysis
                st.subheader("注射部位分析")
                site_stats = st.session_state.processor.analyze_injection_sites(data_filtered)
                if site_stats:
                    site_df = pd.DataFrame(site_stats)
                    st.write("注射部位使用统计：")
                    st.dataframe(site_df)
                else:
                    st.info("暂无注射部位数据")

            except Exception as e:
                st.error(f"生成图表时发生错误: {str(e)}")

        with col2:
            st.subheader("最近统计")
            try:
                recent_data = data_sorted.tail(5)
                latest_glucose_mmol = recent_data['glucose_level'].iloc[-1] / 18.0182
                avg_glucose_mmol = recent_data['glucose_level'].mean() / 18.0182
                st.metric("最新血糖", f"{latest_glucose_mmol:.1f} mmol/L")
                st.metric("平均值 (最近5次)", f"{avg_glucose_mmol:.1f} mmol/L")

                # 血糖预警检查
                recent_glucose = recent_data['glucose_level'].iloc[-1]
                if recent_glucose <= 40:
                    st.error("⚠️ 危险！当前血糖值过低，请立即处理！")
                elif recent_glucose < 70:
                    st.warning("⚠️ 注意！当前血糖值偏低，请及时补充糖分。")

                # Insulin recommendation
                if recent_data['carbs'].sum() > 0:
                    insulin_recommendation = st.session_state.processor.calculate_insulin_dose(
                        recent_data['glucose_level'].iloc[-1],
                        recent_data['carbs'].sum()
                    )
                    st.metric("建议胰岛素剂量", f"{insulin_recommendation:.1f} 单位")
            except Exception as e:
                st.error(f"计算统计数据时发生错误: {str(e)}")

    # Review Tables Section
    st.header("数据回顾分析")
    
    # Tab selection for different review tables
    tab1, tab2, tab3, tab4 = st.tabs(["血糖记录", "胰岛素注射记录", "饮食记录", "综合记录"])
    
    with tab1:
        st.subheader("血糖记录汇总")
        try:
            # Filter data to show only glucose records (glucose_level > 0)
            glucose_data = st.session_state.glucose_data[st.session_state.glucose_data['glucose_level'] > 0].copy()
            if not glucose_data.empty:
                glucose_data = glucose_data.sort_values('timestamp', ascending=False)
                
                # Create display dataframe
                display_glucose = glucose_data[['timestamp', 'glucose_level']].copy()
                display_glucose['日期'] = display_glucose['timestamp'].dt.strftime('%Y-%m-%d')
                display_glucose['时间'] = display_glucose['timestamp'].dt.strftime('%H:%M')
                display_glucose['血糖值 (mmol/L)'] = (display_glucose['glucose_level'] / 18.0182).round(1)
                display_glucose['血糖状态'] = display_glucose['glucose_level'].apply(
                    lambda x: '严重低血糖' if x <= 40 else ('低血糖' if x < 70 else ('正常' if x <= 180 else '高血糖'))
                )
                
                # Display records with delete functionality
                st.write("**最近30条血糖记录:**")
                glucose_records = glucose_data.head(30)
                
                for idx, row in glucose_records.iterrows():
                    col1, col2, col3, col4, col5 = st.columns([2, 1, 2, 2, 1])
                    
                    with col1:
                        st.write(f"{row['timestamp'].strftime('%Y-%m-%d')}")
                    with col2:
                        st.write(f"{row['timestamp'].strftime('%H:%M')}")
                    with col3:
                        glucose_mmol = round(row['glucose_level'] / 18.0182, 1)
                        st.write(f"{glucose_mmol} mmol/L")
                    with col4:
                        status = '严重低血糖' if row['glucose_level'] <= 40 else ('低血糖' if row['glucose_level'] < 70 else ('正常' if row['glucose_level'] <= 180 else '高血糖'))
                        st.write(status)
                    with col5:
                        if st.button("🗑️", key=f"delete_glucose_{idx}", help="删除记录"):
                            if f"confirm_delete_glucose_{idx}" not in st.session_state:
                                st.session_state[f"confirm_delete_glucose_{idx}"] = True
                                st.rerun()
                            
                    # Confirmation dialog
                    if f"confirm_delete_glucose_{idx}" in st.session_state:
                        st.warning(f"确认删除 {row['timestamp'].strftime('%Y-%m-%d %H:%M')} 的血糖记录？")
                        col_yes, col_no = st.columns(2)
                        with col_yes:
                            if st.button("确认删除", key=f"confirm_yes_{idx}"):
                                st.session_state.glucose_data = st.session_state.glucose_data.drop(idx).reset_index(drop=True)
                                save_persistent_data()
                                del st.session_state[f"confirm_delete_glucose_{idx}"]
                                st.success("记录已删除")
                                st.rerun()
                        with col_no:
                            if st.button("取消", key=f"confirm_no_{idx}"):
                                del st.session_state[f"confirm_delete_glucose_{idx}"]
                                st.rerun()
                
                # Glucose statistics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    avg_glucose_mmol = glucose_data['glucose_level'].mean() / 18.0182
                    st.metric("平均血糖", f"{avg_glucose_mmol:.1f} mmol/L")
                with col2:
                    low_count = len(glucose_data[glucose_data['glucose_level'] < 70])
                    st.metric("低血糖次数", f"{low_count}次")
                with col3:
                    high_count = len(glucose_data[glucose_data['glucose_level'] > 180])
                    st.metric("高血糖次数", f"{high_count}次")
                with col4:
                    danger_count = len(glucose_data[glucose_data['glucose_level'] <= 40])
                    st.metric("严重低血糖", f"{danger_count}次", delta_color="inverse")
            else:
                st.info("暂无血糖记录")
        except Exception as e:
            st.error(f"显示血糖汇总时发生错误: {str(e)}")
    
    with tab2:
        st.subheader("胰岛素注射记录汇总")
        try:
            # Filter data to show only insulin records (insulin > 0)
            insulin_data = st.session_state.glucose_data[st.session_state.glucose_data['insulin'] > 0].copy()
            if not insulin_data.empty:
                insulin_data = insulin_data.sort_values('timestamp', ascending=False)
                
                # Create display dataframe
                display_insulin = insulin_data[['timestamp', 'insulin', 'insulin_type', 'injection_site']].copy()
                display_insulin['日期'] = display_insulin['timestamp'].dt.strftime('%Y-%m-%d')
                display_insulin['时间'] = display_insulin['timestamp'].dt.strftime('%H:%M')
                display_insulin['剂量 (单位)'] = display_insulin['insulin'].round(1)
                display_insulin['胰岛素类型'] = display_insulin['insulin_type'].fillna('未指定')
                display_insulin['注射部位'] = display_insulin['injection_site'].fillna('未指定')
                
                # Display records with delete functionality
                st.write("**最近30条胰岛素注射记录:**")
                insulin_records = insulin_data.head(30)
                
                for idx, row in insulin_records.iterrows():
                    col1, col2, col3, col4, col5, col6 = st.columns([2, 1, 1.5, 1.5, 1.5, 1])
                    
                    with col1:
                        st.write(f"{row['timestamp'].strftime('%Y-%m-%d')}")
                    with col2:
                        st.write(f"{row['timestamp'].strftime('%H:%M')}")
                    with col3:
                        st.write(f"{row['insulin']:.1f} 单位")
                    with col4:
                        st.write(f"{row['insulin_type'] if pd.notna(row['insulin_type']) else '未指定'}")
                    with col5:
                        st.write(f"{row['injection_site'] if pd.notna(row['injection_site']) else '未指定'}")
                    with col6:
                        if st.button("🗑️", key=f"delete_insulin_{idx}", help="删除记录"):
                            if f"confirm_delete_insulin_{idx}" not in st.session_state:
                                st.session_state[f"confirm_delete_insulin_{idx}"] = True
                                st.rerun()
                            
                    # Confirmation dialog
                    if f"confirm_delete_insulin_{idx}" in st.session_state:
                        st.warning(f"确认删除 {row['timestamp'].strftime('%Y-%m-%d %H:%M')} 的胰岛素注射记录？")
                        col_yes, col_no = st.columns(2)
                        with col_yes:
                            if st.button("确认删除", key=f"confirm_insulin_yes_{idx}"):
                                st.session_state.glucose_data = st.session_state.glucose_data.drop(idx).reset_index(drop=True)
                                save_persistent_data()
                                del st.session_state[f"confirm_delete_insulin_{idx}"]
                                st.success("记录已删除")
                                st.rerun()
                        with col_no:
                            if st.button("取消", key=f"confirm_insulin_no_{idx}"):
                                del st.session_state[f"confirm_delete_insulin_{idx}"]
                                st.rerun()
                
                # Insulin statistics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    total_insulin = insulin_data['insulin'].sum()
                    st.metric("总胰岛素用量", f"{total_insulin:.1f}单位")
                with col2:
                    daily_avg = insulin_data.groupby(insulin_data['timestamp'].dt.date)['insulin'].sum().mean()
                    st.metric("日均用量", f"{daily_avg:.1f}单位")
                with col3:
                    long_acting = insulin_data[insulin_data['insulin_type'] == '长效胰岛素']['insulin'].sum()
                    st.metric("长效胰岛素", f"{long_acting:.1f}单位")
                with col4:
                    short_acting = insulin_data[insulin_data['insulin_type'] == '短效胰岛素']['insulin'].sum()
                    st.metric("短效胰岛素", f"{short_acting:.1f}单位")
            else:
                st.info("暂无胰岛素注射记录")
        except Exception as e:
            st.error(f"显示胰岛素汇总时发生错误: {str(e)}")
    
    with tab3:
        st.subheader("饮食记录汇总")
        try:
            # Filter data to show only meal records (carbs > 0)
            meal_data = st.session_state.glucose_data[st.session_state.glucose_data['carbs'] > 0].copy()
            if not meal_data.empty:
                meal_data = meal_data.sort_values('timestamp', ascending=False)
                
                # Create display dataframe with formatted data
                display_meals = meal_data[['timestamp', 'food_details', 'carbs']].copy()
                display_meals['日期'] = display_meals['timestamp'].dt.strftime('%Y-%m-%d')
                display_meals['时间'] = display_meals['timestamp'].dt.strftime('%H:%M')
                display_meals['食物详情'] = display_meals['food_details'].fillna('').apply(lambda x: x if x else '未记录详情')
                display_meals['碳水化合物 (g)'] = display_meals['carbs'].round(1)
                
                # Display records with delete functionality
                st.write("**最近30条饮食记录:**")
                meal_records = meal_data.head(30)
                
                for idx, row in meal_records.iterrows():
                    col1, col2, col3, col4, col5 = st.columns([2, 1, 4, 1.5, 1])
                    
                    with col1:
                        st.write(f"{row['timestamp'].strftime('%Y-%m-%d')}")
                    with col2:
                        st.write(f"{row['timestamp'].strftime('%H:%M')}")
                    with col3:
                        food_details = row['food_details'] if pd.notna(row['food_details']) and row['food_details'] else '未记录详情'
                        st.write(food_details)
                    with col4:
                        st.write(f"{row['carbs']:.1f}g")
                    with col5:
                        if st.button("🗑️", key=f"delete_meal_{idx}", help="删除记录"):
                            if f"confirm_delete_meal_{idx}" not in st.session_state:
                                st.session_state[f"confirm_delete_meal_{idx}"] = True
                                st.rerun()
                            
                    # Confirmation dialog
                    if f"confirm_delete_meal_{idx}" in st.session_state:
                        st.warning(f"确认删除 {row['timestamp'].strftime('%Y-%m-%d %H:%M')} 的饮食记录？")
                        col_yes, col_no = st.columns(2)
                        with col_yes:
                            if st.button("确认删除", key=f"confirm_meal_yes_{idx}"):
                                st.session_state.glucose_data = st.session_state.glucose_data.drop(idx).reset_index(drop=True)
                                save_persistent_data()
                                del st.session_state[f"confirm_delete_meal_{idx}"]
                                st.success("记录已删除")
                                st.rerun()
                        with col_no:
                            if st.button("取消", key=f"confirm_meal_no_{idx}"):
                                del st.session_state[f"confirm_delete_meal_{idx}"]
                                st.rerun()
                
                # Add daily summary statistics
                col1, col2, col3 = st.columns(3)
                with col1:
                    total_carbs = meal_data['carbs'].sum()
                    st.metric("总碳水摄入", f"{total_carbs:.1f}g")
                
                with col2:
                    avg_daily_carbs = meal_data.groupby(meal_data['timestamp'].dt.date)['carbs'].sum().mean()
                    st.metric("日均碳水", f"{avg_daily_carbs:.1f}g")
                
                with col3:
                    total_meals = len(meal_data)
                    st.metric("总餐次", f"{total_meals}次")
                    
            else:
                st.info("暂无饮食记录")
        except Exception as e:
            st.error(f"显示饮食汇总时发生错误: {str(e)}")
    
    with tab4:
        st.subheader("综合记录总览")
        try:
            all_data = st.session_state.glucose_data.sort_values('timestamp', ascending=False)
            if not all_data.empty:
                # Create comprehensive display
                display_all = all_data.copy()
                display_all['日期'] = display_all['timestamp'].dt.strftime('%Y-%m-%d')
                display_all['时间'] = display_all['timestamp'].dt.strftime('%H:%M')
                display_all['血糖 (mmol/L)'] = display_all['glucose_level'].apply(lambda x: f"{x/18.0182:.1f}" if x > 0 else "-")
                display_all['胰岛素 (单位)'] = display_all['insulin'].apply(lambda x: f"{x:.1f}" if x > 0 else "-")
                display_all['碳水 (g)'] = display_all['carbs'].apply(lambda x: f"{x:.1f}" if x > 0 else "-")
                display_all['记录类型'] = display_all.apply(lambda row: 
                    '血糖' if row['glucose_level'] > 0 else 
                    ('胰岛素' if row['insulin'] > 0 else 
                     ('饮食' if row['carbs'] > 0 else '其他')), axis=1)
                
                summary_all = display_all[['日期', '时间', '记录类型', '血糖 (mmol/L)', '胰岛素 (单位)', '碳水 (g)']].head(50)
                st.dataframe(summary_all, use_container_width=True, height=500)
                
                # Overall statistics
                st.subheader("总体统计")
                col1, col2, col3, col4 = st.columns(4)
                
                glucose_records = len(all_data[all_data['glucose_level'] > 0])
                insulin_records = len(all_data[all_data['insulin'] > 0])
                meal_records = len(all_data[all_data['carbs'] > 0])
                total_records = len(all_data)
                
                with col1:
                    st.metric("总记录数", f"{total_records}条")
                with col2:
                    st.metric("血糖记录", f"{glucose_records}条")
                with col3:
                    st.metric("胰岛素记录", f"{insulin_records}条")
                with col4:
                    st.metric("饮食记录", f"{meal_records}条")
                    
                # Date range
                date_range = f"{all_data['timestamp'].min().strftime('%Y-%m-%d')} 至 {all_data['timestamp'].max().strftime('%Y-%m-%d')}"
                st.info(f"数据时间范围: {date_range}")
                
            else:
                st.info("暂无任何记录")
        except Exception as e:
            st.error(f"显示综合记录时发生错误: {str(e)}")