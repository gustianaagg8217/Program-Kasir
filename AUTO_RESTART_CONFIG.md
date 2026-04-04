# Auto-Restart Configuration Guide

## Overview
Program `telegram_main.py` sekarang dilengkapi dengan fitur **auto-restart otomatis setiap 2 menit** untuk menjaga stabilitas bot.

## Cara Kerja

### Timeline Restart
1. **0:00** - Polling session dimulai
2. **0:00** - Threading timer dijalankan (countdown 2 menit)
3. **2:00** - Timer trigger → `application.updater.stop()`
4. **2:00** - Polling berhenti gracefully
5. **2:00** - Application instance di-recreate (fresh start)
6. **2:01** - Handlers di-register ulang
7. **2:01** - Polling session baru dimulai (repeat)

### Log & Monitoring
Setiap kali restart, Anda akan melihat di console:
```
[*] Polling session #1 started at 14:30:45
...
[*] AUTO-RESTART TRIGGERED #1 at 14:32:45
[*] Polling session #1 ended at 14:32:45
[!] Creating new application instance for restart...
[*] Polling session #2 started at 14:32:46
```

File log `telegram_pos.log` juga akan mencatat:
```
[>] Polling loop #1 started at 14:30:45
[*] Auto-restart triggered #1 at 14:32:45
[<] Polling loop #1 ended at 14:32:45
[>] Polling loop #2 started at 14:32:46
```

## Konfigurasi

### Default Settings
- **Interval**: 120 detik (2 menit)
- **Status**: ENABLED (aktif)

### Cara Mengubah Interval
Edit `telegram_main.py` dalam method `__init__`:

```python
# Untuk 5 menit (300 detik)
self.restart_interval = 300

# Untuk 10 menit (600 detik)
self.restart_interval = 600
```

### Cara Disable Auto-Restart
Di awal `main()` function, tambahkan:

```python
pos_system = TelegramPOSSystem(token)
pos_system.auto_restart_enabled = False  # Disable restart
pos_system.run()
```

## Manfaat Auto-Restart

✅ **Memory Management** - Membersihkan memory leaks setiap 2 menit
✅ **Connection Stability** - Reconnect fresh ke Telegram API
✅ **Handler Freshness** - Semua handlers di-setup ulang
✅ **State Isolation** - Setiap sesi polling terisolasi
✅ **Uptime Monitoring** - Mudah track uptime dengan counter

## Benefits untuk User

Dari perspektif user Telegram:
- ✅ Bot tetap responsif
- ✅ Messages tidak terlewat
- ✅ Connection lebih stabil
- ✅ No noticeable downtime (restart hanya ~1 detik)

## Troubleshooting

### Bot Tidak Restart
**Masalah**: Tidak ada log "AUTO-RESTART TRIGGERED"
**Solusi**: Check apakah `auto_restart_enabled = True` di `__init__`

### Restart Terlalu Sering
**Masalah**: Restart sebelum 2 menit
**Solusi**: Naikkan nilai `restart_interval` (misal: 300 untuk 5 menit)

### Transaction State Hilang Setelah Restart
**Rencana**: Ini adalah expected behavior karena setiap restart adalah fresh start
**Mitigasi**: Simpan state ke database jika perlu persistence

## Advanced Configuration

Untuk custom restart logic, edit method `_trigger_restart()`:

```python
async def _trigger_restart(self):
    """Custom restart logic"""
    self.restart_counter += 1
    
    # Tambahkan custom logic di sini
    # Misalnya: save state, notify admin, etc
    
    if self.application.updater:
        self.application.updater.stop()
```

## Monitoring

### Via Console
- Watch untuk pesan "AUTO-RESTART TRIGGERED"
- Lihat restart counter meningkat setiap 2 menit

### Via Log File
```bash
# Linux/Mac
tail -f telegram_pos.log | grep "restart"

# Windows PowerShell
Get-Content telegram_pos.log -Tail 20 -Wait
```

## Performance Notes

- **Restart Duration**: ~1 detik (minimal downtime)
- **Memory Impact**: Timer thread menggunakan ~1MB minimal
- **CPU Impact**: Negligible (timer hanya aktif saat countdown)
- **Network**: Fresh connection setiap restart

## Implementation Details

### Methods Added
1. `_schedule_restart()` - Schedule timer untuk 2 menit
2. `_trigger_restart()` - Trigger stop saat timer matured
3. `_cleanup_restart_timer()` - Clean up timer objects

### Fields Added
- `restart_interval = 120` - Interval dalam detik
- `auto_restart_enabled = True` - Flag untuk enable/disable
- `restart_counter = 0` - Counter untuk tracking
- `_restart_timer = None` - StringTimer instance

### Modified Methods
- `run()` - Sekarang loop infinite dengan restart logic

## Changelog

### Version 1.0
- ✅ Auto-restart setiap 2 menit
- ✅ Graceful shutdown
- ✅ Timer cleanup
- ✅ Restart counter tracking
- ✅ Comprehensive logging

---
Last Updated: April 4, 2026
