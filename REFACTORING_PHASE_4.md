# ============================================================================
# REFACTORING PHASE 4 - Async/Threading & Printing
# ============================================================================
# Updated: After Phase 1-3 implementation
# Status: COMPLETED ✅
# ============================================================================

## Overview

Phase 4 menambahkan kemampuan background processing dan output/printing ke arsitektur Phase 1-3:
1. **Async Manager** - Threading & task management tanpa blocking UI
2. **Print Manager** - Cross-platform printing (Windows/Linux/macOS)
3. **Report Service** - Background report generation
4. **Dashboard Service** - Real-time dashboard data aggregation

Fokus: **Non-blocking operations** dan **production-grade reporting**.

---

## Phase 4 Deliverables ✅

### 1. Async Manager (`app/utils/async_manager.py`) ✅

**Tujuan**: Manage background tasks dan threading operations.

**Key Features**:
- ThreadPoolExecutor dengan configurable worker count
- Task tracking & progress monitoring
- Error handling dengan retry logic
- Task scheduling (periodic tasks)
- Callbacks untuk success/error handling

**Classes & Methods**:
```python
class AsyncTask:
    # Represent async task dengan metadata
    task_id: str
    name: str
    status: str  # pending, running, completed, failed
    progress: int  # 0-100
    result: Any
    error: str
    
    def get_duration() -> Optional[float]
        # Get task duration dalam seconds

class AsyncManager:
    # Manager untuk background tasks
    
    def submit_task(task_id, name, func, args, kwargs, 
                   callback, error_callback) -> AsyncTask
        # Submit task untuk background execution
    
    def get_task(task_id) -> Optional[AsyncTask]
    def get_task_result(task_id, timeout) -> Any
    def get_all_tasks() -> List[AsyncTask]
    def get_running_tasks() -> List[AsyncTask]
    def get_pending_tasks() -> List[AsyncTask]
    def cancel_task(task_id) -> bool
    def wait_all(timeout) -> Dict
    def schedule_periodic(task_id, name, func, interval_seconds, 
                         args, kwargs) -> threading.Thread
    def shutdown(wait, timeout)
    def get_stats() -> Dict

def get_async_manager(max_workers) -> AsyncManager
    # Get atau create global async manager instance
```

**Usage Example**:
```python
from app.utils.async_manager import get_async_manager

# Get async manager
async_manager = get_async_manager(max_workers=5)

# Submit background task
def generate_report(start_date, end_date):
    # Long-running operation
    return report_data

def on_report_done(result):
    print(f"Report ready: {result}")

def on_report_error(error):
    print(f"Report failed: {error}")

task_id = 'report_001'
task = async_manager.submit_task(
    task_id=task_id,
    name="Generate Monthly Report",
    func=generate_report,
    args=('2024-01-01', '2024-01-31'),
    callback=on_report_done,
    error_callback=on_report_error
)

# Check task status
task = async_manager.get_task(task_id)
print(f"Status: {task.status}, Progress: {task.progress}%")

# Get result (blocking)
result = async_manager.get_task_result(task_id, timeout=60)

# Schedule periodic task (e.g., every 5 minutes)
async_manager.schedule_periodic(
    task_id='cache_refresh',
    name='Refresh Dashboard Cache',
    func=refresh_cache,
    interval_seconds=300  # 5 minutes
)

# Shutdown
async_manager.shutdown()
```

**Decorator Usage**:
```python
from app.utils.async_manager import run_async

@run_async('daily_backup', 'Daily Database Backup')
def backup_database():
    # Long-running operation
    return backup_result

# Call function returns AsyncTask
task = backup_database()
```

---

### 2. Print Manager (`app/utils/print_manager.py`) ✅

**Tujuan**: Cross-platform printing support untuk receipts & reports.

**Key Features**:
- Template-based formatting (receipts, reports, labels)
- Cross-platform support (Windows/Linux/macOS)
- Printer detection & management
- Save to file (TXT, PDF placeholder)
- Two-column layout support

**Classes & Methods**:
```python
class PrintTemplate:
    # Template untuk print output
    
    def add_line(text, align, char)
        # Add line: align='left'|'center'|'right'
    
    def add_separator(char)
    def add_blank()
    def add_two_column(left, right, width_left)
    def get_content() -> str
    def clear()

class PrintManager:
    # Manager untuk cross-platform printing
    
    def create_receipt_template(store_name, receipt_number, cashier,
                               items, subtotal, discount, tax, total,
                               payment_method, notes, width) -> PrintTemplate
        # Create formatted receipt template
    
    def create_report_template(title, report_date, data, width) -> PrintTemplate
        # Create formatted report template
    
    def print_text(text, printer) -> bool
        # Print text ke printer (Windows/Linux/macOS)
    
    def print_receipt(receipt_template, printer, also_save, 
                     output_file) -> bool
        # Print receipt ke printer dan/atau save
    
    def get_available_printers() -> List[str]
        # Get list of available printers
    
    def save_as_file(template, output_file, format) -> bool
        # Save template ke file (txt, pdf)
```

**Usage Example**:
```python
from app.utils.print_manager import get_print_manager

print_manager = get_print_manager(default_printer=None)

# Create receipt
items = [
    {'kode': 'BRD001', 'nama': 'Bread', 'qty': 2, 'harga': 15000, 'subtotal': 30000},
    {'kode': 'BVG001', 'nama': 'Beverage', 'qty': 1, 'harga': 25000, 'subtotal': 25000}
]

receipt = print_manager.create_receipt_template(
    store_name="My Store",
    receipt_number="00001",
    cashier="John",
    items=items,
    subtotal=55000,
    discount=0,
    tax=5500,
    total=60500,
    payment_method="cash",
    notes="Thank you for your purchase"
)

# Print receipt
print_manager.print_receipt(
    receipt_template=receipt,
    printer=None,  # Use default printer
    also_save=True,  # Also save to file
    output_file="receipts/receipt_00001.txt"
)

# Create report
report_template = print_manager.create_report_template(
    title="Daily Sales Report",
    report_date="2024-01-26",
    data={
        'total_revenue': 'Rp 5,000,000',
        'transactions': 42,
        'avg_transaction': 'Rp 119,048'
    }
)

# Print report
print_manager.print_receipt(report_template, also_save=True)

# Get available printers
printers = print_manager.get_available_printers()
print(f"Available printers: {printers}")

# Print template content to console
print(receipt.get_content())
```

**Platform Support**:
- **Windows**: Uses notepad `/p` command + WMIC for printer detection
- **Linux**: Uses `lp` command + `lpstat` for printer detection
- **macOS**: Uses `lp` command + `lpstat` for printer detection

---

### 3. Report Service (`app/services/report_service.py`) ✅

**Tujuan**: Generate reports dalam background tanpa blocking UI.

**Key Methods**:
```python
class ReportService:
    def generate_daily_report(date, callback, error_callback) -> str
        # Generate daily sales report background
        # Returns: task_id
    
    def generate_weekly_report(end_date, callback) -> str
        # Generate weekly sales report
    
    def generate_monthly_report(year_month, callback) -> str
        # Generate monthly sales report
    
    def generate_inventory_report(callback) -> str
        # Generate inventory status report
    
    def get_report(task_id, timeout) -> Optional[Dict]
        # Get report result (blocking)
    
    def export_report_as_text(report, output_file) -> str
        # Export report ke text file
    
    def get_all_reports() -> List[Dict]
        # Get semua report tasks dengan status
```

**Report Structure**:
```python
daily_report = {
    'report_type': 'daily',
    'date': '2024-01-26',
    'timestamp': '2024-01-26T14:30:00',
    'summary': {
        'total_transactions': 42,
        'revenue': 5000000,
        'total_items': 156
    },
    'revenue_by_method': {
        'cash': 3000000,
        'transfer': 1500000,
        'card': 500000
    },
    'avg_transaction': {
        'avg_value': 119048,
        'avg_items': 3.71
    },
    'status': 'completed'
}

weekly_report = {
    'report_type': 'weekly',
    'period': '2024-01-20 to 2024-01-26',
    'summary': {...},
    'daily_breakdown': {
        '2024-01-20': {...},
        '2024-01-21': {...},
        ...
    },
    'status': 'completed'
}
```

**Usage Example**:
```python
from app.services.report_service import ReportService

report_service = ReportService(trans_service, product_service)

# Generate daily report in background
def on_report_ready(report):
    print(f"Report ready: {report['summary']}")

task_id = report_service.generate_daily_report(
    date='2024-01-26',
    callback=on_report_ready
)

# Wait for report (with 60 second timeout)
report = report_service.get_report(task_id, timeout=60)

# Generate monthly report
task_id = report_service.generate_monthly_report(year_month='2024-01')

# Export report as text
output_file = report_service.export_report_as_text(report)

# Get all reports
all_reports = report_service.get_all_reports()
for report_meta in all_reports:
    print(f"{report_meta['name']}: {report_meta['status']}")
```

---

### 4. Dashboard Service (`app/services/dashboard_service.py`) ✅

**Tujuan**: Real-time dashboard data aggregation dengan caching.

**Key Methods**:
```python
class DashboardService:
    def get_dashboard_data(use_cache, callback) -> str
        # Aggregate dashboard data background
        # Returns: task_id atau None (dari cache)
    
    def get_cached_metrics() -> Optional[Dict]
        # Get cached metrics jika available
    
    def get_daily_comparison(days) -> Dict
        # Get daily comparison untuk trend analysis
    
    def get_performance_metrics() -> Dict
        # Get overall performance metrics dengan growth rates
    
    def get_health_check() -> Dict
        # Get system health check (database, inventory, ai)
    
    def clear_cache()
        # Clear metrics cache
```

**Dashboard Metrics Structure**:
```python
metrics = {
    'today': {
        'revenue': 5000000,
        'transactions': 42,
        'items_sold': 156,
        'avg_transaction': 119048
    },
    'week': {
        'revenue': 25000000,
        'transactions': 210,
        'avg_daily': 3571428
    },
    'month': {
        'revenue': 100000000,
        'transactions': 840,
        'avg_daily': 3333333
    },
    'inventory': {
        'total_value': 50000000,
        'total_products': 250,
        'low_stock': 8
    },
    'sales': {
        'top_products': [
            {'kode': 'PRD001', 'nama': 'Product 1', 'qty': 100, 'total_value': 5000000},
            ...
        ],
        'revenue_by_method': {
            'cash': 3000000,
            'transfer': 1500000,
            'card': 500000
        }
    },
    'last_updated': '2024-01-26T14:30:00'
}
```

**Usage Example**:
```python
from app.services.dashboard_service import DashboardService

dashboard_service = DashboardService(trans_service, product_service, restock_service)

# Get dashboard data (with caching)
def on_dashboard_ready(data):
    print(f"Dashboard ready: revenue={data['today']['revenue']}")

task_id = dashboard_service.get_dashboard_data(
    use_cache=True,
    callback=on_dashboard_ready
)

# Or use cached data if available
cached = dashboard_service.get_cached_metrics()
if cached:
    print(f"Using cached data: revenue={cached['today']['revenue']}")

# Get daily comparison (7 days)
comparison = dashboard_service.get_daily_comparison(days=7)
# {period: 'Last 7 days', data: [{date, revenue, transactions, items}, ...]}

# Get performance metrics
perf = dashboard_service.get_performance_metrics()
# {today: {revenue, vs_weekly_avg}, week: {...}, month: {...}}

# System health check
health = dashboard_service.get_health_check()
# {status: 'healthy'|'degraded'|'error', checks: {database, inventory, ai_restock}}
```

---

## Architecture After Phase 4

```
┌─────────────────────────────────────────────────────────────┐
│                     GUI LAYER (Tkinter)                     │
│  - User Interface (forms, dialogs, tables)                  │
│  - Calls services via AsyncManager (non-blocking)           │
│  - Callbacks untuk UI updates                               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                 ASYNC LAYER (Phase 4) ✅                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ AsyncManager       - ThreadPoolExecutor, task queue │   │
│  │ ReportService      - Background report generation   │   │
│  │ DashboardService   - Real-time data aggregation     │   │
│  └──────────────────────────────────────────────────────┘   │
│  - Non-blocking operations                                  │
│  - Progress tracking                                        │
│  - Error callbacks                                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    SERVICE LAYER                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ ProductService         ✅ Phase 1-2                  │   │
│  │ UserService            ✅ Phase 3                    │   │
│  │ TransactionService     ✅ Phase 3                    │   │
│  │ ReportService          ✅ Phase 4 (NEW)              │   │
│  │ DashboardService       ✅ Phase 4 (NEW)              │   │
│  │ (+ InventoryService in Phase 5)                      │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  REPOSITORY LAYER                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ ProductRepository      ✅ Phase 1-2                  │   │
│  │ UserRepository         ✅ Phase 3                    │   │
│  │ TransactionRepository  ✅ Phase 3                    │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              DATABASE LAYER (SQLite)                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                 UTILITY & OUTPUT LAYERS                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ ConfigLoader           ✅ Phase 1-2                  │   │
│  │ ErrorHandler           ✅ Phase 1-2                  │   │
│  │ PasswordManager        ✅ Phase 3                    │   │
│  │ AsyncManager           ✅ Phase 4 (NEW)              │   │
│  │ PrintManager           ✅ Phase 4 (NEW)              │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    AI LAYER                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ DemandPrediction     📦 Placeholder Phase 1-2        │   │
│  │ SmartRestock         ✅ Phase 3 (placeholder)        │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## File Structure (After Phase 4)

```
Program-Kasir/
├── app/
│   ├── services/
│   │   ├── product_service.py        ✅ Phase 1-2
│   │   ├── user_service.py           ✅ Phase 3
│   │   ├── transaction_service.py    ✅ Phase 3
│   │   ├── report_service.py         ✅ Phase 4 [NEW]
│   │   └── dashboard_service.py      ✅ Phase 4 [NEW]
│   │
│   ├── utils/
│   │   ├── config_loader.py          ✅ Phase 1-2
│   │   ├── error_handler.py          ✅ Phase 1-2
│   │   ├── password_manager.py       ✅ Phase 3
│   │   ├── async_manager.py          ✅ Phase 4 [NEW]
│   │   └── print_manager.py          ✅ Phase 4 [NEW]
│   │
│   └── ai/
│       ├── demand_prediction.py      📦 Phase 1-2
│       └── smart_restock.py          ✅ Phase 3
│
├── gui_main.py
├── config.json
└── REFACTORING_PHASE_4.md ✅
```

---

## Testing Phase 4

### Manual Testing Checklist

**AsyncManager Tests**:
```python
from app.utils.async_manager import get_async_manager

async_manager = get_async_manager(max_workers=5)

# Test 1: Submit simple task
def long_task(x):
    import time
    time.sleep(2)
    return x * 2

task = async_manager.submit_task(
    'test_1', 'Simple Task', long_task, args=(5,)
)
assert task.status == 'pending'
result = async_manager.get_task_result('test_1')
assert result == 10

# Test 2: Task with callback
results = []
def callback(result):
    results.append(result)

task = async_manager.submit_task(
    'test_2', 'Callback Task', long_task,
    args=(3,), callback=callback
)
import time
time.sleep(3)
assert results[0] == 6

# Test 3: Periodic task
counter = [0]
def increment():
    counter[0] += 1

thread = async_manager.schedule_periodic(
    'periodic', 'Increment', increment, 1
)
time.sleep(3)
assert counter[0] >= 2

# Test 4: Get stats
stats = async_manager.get_stats()
assert 'total_tasks' in stats
assert 'running' in stats
```

**PrintManager Tests**:
```python
from app.utils.print_manager import get_print_manager

print_manager = get_print_manager()

# Test 1: Create receipt template
items = [
    {'kode': 'A001', 'nama': 'Item A', 'qty': 2, 'harga': 50000, 'subtotal': 100000}
]
receipt = print_manager.create_receipt_template(
    store_name="Test Store",
    receipt_number="001",
    cashier="John",
    items=items,
    subtotal=100000,
    discount=0,
    tax=10000,
    total=110000,
    payment_method="cash"
)
content = receipt.get_content()
assert "Test Store" in content
assert "110000" in content

# Test 2: Save receipt to file
assert print_manager.save_as_file(receipt, "test_receipt.txt", "txt")

# Test 3: Get available printers
printers = print_manager.get_available_printers()
assert isinstance(printers, list)
```

**ReportService Tests**:
```python
from app.services.report_service import ReportService

report_service = ReportService(trans_service, product_service)

# Test 1: Generate daily report
task_id = report_service.generate_daily_report()
assert task_id is not None

# Test 2: Wait for report
report = report_service.get_report(task_id, timeout=30)
assert report is not None
assert 'summary' in report

# Test 3: Export report
output_file = report_service.export_report_as_text(report)
assert output_file is not None
```

**DashboardService Tests**:
```python
from app.services.dashboard_service import DashboardService

dashboard_service = DashboardService(
    trans_service, product_service, restock_service
)

# Test 1: Get dashboard data
cached = dashboard_service.get_cached_metrics()
assert cached is not None

# Test 2: Get performance metrics
perf = dashboard_service.get_performance_metrics()
assert 'today' in perf
assert 'week' in perf

# Test 3: Get health check
health = dashboard_service.get_health_check()
assert health['status'] in ['healthy', 'degraded', 'error']
```

---

## Configuration (Phase 4)

**Feature Flags di config.json**:
```json
{
  "features": {
    "async_operations": true,
    "background_reports": true,
    "dashboard_cache": true,
    "printing": true,
    "periodic_tasks": true
  },
  "async": {
    "max_workers": 5,
    "task_timeout": 300,
    "queue_size": 100
  },
  "printing": {
    "default_printer": null,
    "paper_width": 80,
    "auto_save_receipts": true,
    "receipt_folder": "receipts"
  },
  "dashboard": {
    "cache_enabled": true,
    "cache_ttl": 60,
    "refresh_interval": 300
  }
}
```

**Dependencies**:
- No new external dependencies required (uses Python standard library: threading, concurrent.futures)
- Subprocess untuk printer detection & printing (built-in)

---

## Integration Points (Phase 4 → Phase 5 GUI)

**For GUI Integration in Phase 5**:

```python
# In gui_main.py:
from app.utils.async_manager import get_async_manager
from app.services.report_service import ReportService
from app.services.dashboard_service import DashboardService
from app.utils.print_manager import get_print_manager

# Initialize services (in GUI init)
async_manager = get_async_manager(max_workers=5)
report_service = ReportService(trans_service, product_service, async_manager)
dashboard_service = DashboardService(trans_service, product_service, restock_service, async_manager)
print_manager = get_print_manager()

# Background report generation
def on_generate_report():
    task_id = report_service.generate_daily_report(
        callback=lambda r: show_report_dialog(r)
    )
    show_info("Report generating in background...")

# Real-time dashboard with caching
def refresh_dashboard():
    # Dari cache jika available
    metrics = dashboard_service.get_cached_metrics()
    if metrics:
        update_dashboard_ui(metrics)
    else:
        # Trigger background aggregation
        dashboard_service.get_dashboard_data(
            callback=lambda m: update_dashboard_ui(m)
        )

# Print receipt
def print_current_receipt():
    receipt_template = print_manager.create_receipt_template(...)
    print_manager.print_receipt(
        receipt_template=receipt_template,
        printer=config.get('printing.default_printer'),
        also_save=True,
        output_file=f"receipts/receipt_{trans_id}.txt"
    )
    show_info("Receipt printed!")

# Periodic dashboard refresh
dashboard_refresh_thread = async_manager.schedule_periodic(
    task_id='dashboard_refresh',
    name='Refresh Dashboard',
    func=refresh_dashboard,
    interval_seconds=60  # Every 1 minute
)
```

---

## Known Limitations (Phase 4)

1. **Printing**: Text-only currently
   - No PDF generation (placeholder)
   - No advanced formatting
   - **Ready for**: Phase 4+ with reportlab/fpdf library

2. **Dashboard Caching**: Simple TTL-based
   - No distributed caching
   - No cache invalidation signals
   - **Ready for**: Phase 5 with Redis

3. **Report Scheduling**: Placeholder
   - No persistent job scheduling
   - No cron-like scheduling
   - **Ready for**: Phase 5 with APScheduler

4. **Async Operations**: Thread-based only
   - No true async (asyncio)
   - No message queue (Celery)
   - **Ready for**: Phase 5+ with async refactoring

---

## Success Metrics (Phase 4)

- ✅ UI tidak pernah block ketika generate report/dashboard
- ✅ Multiple tasks dapat berjalan parallel
- ✅ Task progress dapat di-track
- ✅ Error handling dengan callbacks
- ✅ Cross-platform printing working
- ✅ Dashboard data aggregated efficiently
- ✅ Reporting dalam background selesai

---

## Roadmap: Phase 5 (GUI Migration)

**Phase 5: Full GUI Refactoring**
- [ ] Add login dialog dengan UserService
- [ ] Add transaction history viewer
- [ ] Add restock recommendations dashboard
- [ ] Refactor product CRUD to use ProductService
- [ ] Add session management
- [ ] Replace all GUI DB calls dengan services
- [ ] Add real-time dashboard updates
- [ ] Implement PrintManager untuk receipt printing

**Phase 6: Production & Optimization**
- [ ] Add database connection pooling
- [ ] Implement Redis caching
- [ ] Add APScheduler untuk job scheduling
- [ ] Implement asyncio untuk true async
- [ ] Performance profiling & optimization
- [ ] Security audit & hardening
- [ ] Docker containerization
- [ ] CI/CD pipeline setup

---

END OF PHASE 4 DOCUMENTATION ✅
