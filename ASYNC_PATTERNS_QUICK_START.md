# ============================================================================
# QUICK-START GUIDE: Using Async Helpers
# ============================================================================
# Simple copy-paste examples for common async patterns
# ============================================================================

## Pattern 1: Load and Display Data

Use this pattern when you need to fetch data and display it in the UI.

```python
def show_my_data(self):
    """Load and display data asynchronously."""
    self._clear_content()
    
    # Show loading indicator
    loading = ttk.Label(
        self.content_area,
        text="⏳ Loading data...",
        font=FONTS['normal'],
        foreground=COLORS['info']
    )
    loading.pack(pady=20)
    
    # Define background task
    def load_data():
        """Heavy operation runs in background."""
        try:
            # Do heavy work here
            data = self.db.expensive_query()
            return data
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            return None
    
    # Define completion callback
    def on_data_loaded(data):
        """Called when data is ready."""
        loading.destroy()
        
        if data is None:
            error_label = ttk.Label(
                self.content_area,
                text="❌ Error loading data",
                foreground=COLORS['danger']
            )
            error_label.pack(pady=20)
            return
        
        # Display data
        for item in data:
            item_label = ttk.Label(
                self.content_area,
                text=f"Item: {item['name']}"
            )
            item_label.pack()
    
    # Execute asynchronously
    operation = AsyncOperation(
        parent=self.content_area,
        task_func=load_data,
        on_complete=on_data_loaded,
        show_loading=False
    )
    operation.start()
```

---

## Pattern 2: Populate Treeview

Use this pattern when loading data for a Treeview widget.

```python
def show_items_table(self):
    """Load items and populate treeview."""
    self._clear_content()
    
    # Create treeview frame
    tree_frame = ttk.Frame(self.content_area)
    tree_frame.pack(fill='both', expand=True, pady=10)
    
    # Create treeview (initially empty)
    columns = ('ID', 'Name', 'Value')
    tree = ttk.Treeview(tree_frame, columns=columns, height=20, show='headings')
    
    tree.heading('ID', text='ID')
    tree.heading('Name', text='Name')
    tree.heading('Value', text='Value')
    
    tree.column('ID', width=50)
    tree.column('Name', width=200)
    tree.column('Value', width=100)
    
    # Show loading message
    loading_label = ttk.Label(
        tree_frame,
        text="⏳ Loading items...",
        font=FONTS['normal']
    )
    loading_label.pack(pady=50)
    
    # Define task
    def load_items():
        """Fetch items from database."""
        return self.db.get_all_items()
    
    # Define completion
    def on_items_loaded(items):
        """Populate treeview with items."""
        if items is None:
            loading_label.config(text="❌ Error loading items")
            return
        
        loading_label.destroy()
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        tree.pack(fill='both', expand=True)
        
        # Populate treeview
        for i, item in enumerate(items, 1):
            tree.insert('', 'end', values=(
                item['id'],
                item['name'],
                f"Rp {item['value']:,}"
            ))
    
    # Execute
    op = AsyncOperation(
        parent=tree_frame,
        task_func=load_items,
        on_complete=on_items_loaded,
        show_loading=False
    )
    op.start()
```

---

## Pattern 3: Generate Report

Use this pattern for long-running report generation.

```python
def generate_report(self):
    """Generate report asynchronously."""
    # Show generating message
    status_label = ttk.Label(
        self.content_area,
        text="⏳ Generating report...",
        font=FONTS['normal'],
        foreground=COLORS['warning']
    )
    status_label.pack(pady=20)
    
    # Define task
    def generate():
        """Long-running report generation."""
        try:
            report_data = self.report_generator.generate_full_report()
            report_text = self.report_formatter.format_report(report_data)
            return report_text
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return None
    
    # Define completion
    def on_report_ready(report_text):
        """Display generated report."""
        status_label.destroy()
        
        if report_text is None:
            error_label = ttk.Label(
                self.content_area,
                text="❌ Report generation failed",
                foreground=COLORS['danger']
            )
            error_label.pack(pady=20)
            return
        
        # Display report
        text_frame = ttk.Frame(self.content_area)
        text_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        text_widget = tk.Text(text_frame, font=FONTS['mono'], height=20)
        text_widget.pack(fill='both', expand=True)
        
        text_widget.insert('1.0', report_text)
        text_widget.config(state='disabled')
        
        # Add print button
        print_btn = ttk.Button(
            self.content_area,
            text="🖨️ Print Report",
            command=lambda: self._print_report_dialog(report_text, "report")
        )
        print_btn.pack(pady=10)
    
    # Execute
    op = AsyncOperation(
        parent=self.content_area,
        task_func=generate,
        on_complete=on_report_ready
    )
    op.start()
```

---

## Pattern 4: Parallel Tasks

Use this pattern when you need to fetch multiple data sources in parallel.

```python
def show_dashboard_async(self):
    """Load multiple dashboard components in parallel."""
    self._clear_content()
    
    # Show loading
    loading = ttk.Label(
        self.content_area,
        text="⏳ Loading dashboard...",
        font=FONTS['title'],
        foreground=COLORS['info']
    )
    loading.pack(pady=50)
    
    # Create batch executor
    executor = BatchAsyncExecutor(max_workers=3)
    
    # Add tasks
    executor.add_task("stats", lambda: self.db.get_database_stats())
    executor.add_task("dashboard", lambda: self.report_generator.get_dashboard_summary())
    executor.add_task("chart_data", lambda: self.report_generator.get_7day_sales())
    
    # Execute in background
    def load_all():
        return executor.wait_all(timeout=30)
    
    # On complete
    def on_complete(results):
        loading.destroy()
        
        # Check for errors
        if results['stats'] is None or results['dashboard'] is None:
            error_label = ttk.Label(
                self.content_area,
                text="❌ Error loading dashboard",
                foreground=COLORS['danger']
            )
            error_label.pack(pady=20)
            return
        
        # Display dashboard with all data
        stats = results['stats']
        dashboard = results['dashboard']
        chart_data = results['chart_data']
        
        # Build stat cards
        cards_data = [
            ("📦 Total Produk", str(stats['total_products']), COLORS['info']),
            ("💰 Penjualan Hari Ini", format_rp(dashboard['hari_ini']['total_penjualan']), COLORS['success']),
        ]
        
        for title, value, color in cards_data:
            self._create_stat_card(self.content_area, title, value, color)
    
    op = AsyncOperation(
        parent=self.content_area,
        task_func=load_all,
        on_complete=on_complete
    )
    op.start()
```

---

## Pattern 5: Lazy Loading Tabs

Use this pattern for notebook/tab widgets to load content on-demand.

```python
def show_tabs_page(self):
    """Show tabs with lazy loading."""
    self._clear_content()
    
    # Create notebook
    notebook = ttk.Notebook(self.content_area)
    notebook.pack(fill='both', expand=True, pady=10, padx=10)
    
    # Tab configurations
    tabs = [
        ("📋 Tab 1", "tab1", self.load_tab1),
        ("📊 Tab 2", "tab2", self.load_tab2),
        ("📈 Tab 3", "tab3", self.load_tab3),
    ]
    
    # Create frames for tabs
    tab_frames = {}
    tab_loaded = {}
    
    for tab_label, tab_id, tab_func in tabs:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=tab_label)
        tab_frames[tab_id] = frame
        tab_loaded[tab_id] = False
    
    # Handle tab selection
    def on_tab_changed(event):
        """Load tab content when selected."""
        selected_index = notebook.index(notebook.select())
        tab_id = tabs[selected_index][1]
        
        if not tab_loaded[tab_id]:
            # Load this tab
            frame = tab_frames[tab_id]
            tab_func = tabs[selected_index][2]
            
            loading = ttk.Label(frame, text="⏳ Loading...")
            loading.pack(pady=50)
            
            def load_tab():
                return tab_func()
            
            def on_loaded(result):
                loading.destroy()
                # Build tab content here
                ...
            
            op = AsyncOperation(
                parent=frame,
                task_func=load_tab,
                on_complete=on_loaded,
                show_loading=False
            )
            op.start()
            
            tab_loaded[tab_id] = True
    
    # Bind tab change
    notebook.bind("<<NotebookTabChanged>>", on_tab_changed)
    
    # Load first tab
    if tabs:
        try:
            tab_func = tabs[0][2]
            tab_func(tab_frames[tabs[0][1]])
            tab_loaded[tabs[0][1]] = True
        except Exception as e:
            logger.error(f"Error loading first tab: {e}")

def load_tab1(self):
    """Load tab 1 content."""
    pass

def load_tab2(self):
    """Load tab 2 content."""
    pass

def load_tab3(self):
    """Load tab 3 content."""
    pass
```

---

## Pattern 6: Search with Live Filtering

Use this pattern for search that doesn't block UI.

```python
def show_searchable_list(self):
    """Show list with async search."""
    self._clear_content()
    
    # Header
    header = ttk.Label(
        self.content_area,
        text="🔍 Searchable Items",
        font=FONTS['title']
    )
    header.pack(pady=10)
    
    # Search bar
    search_frame = ttk.Frame(self.content_area)
    search_frame.pack(fill='x', padx=10, pady=10)
    
    search_var = tk.StringVar()
    search_entry = ttk.Entry(search_frame, textvariable=search_var, width=40)
    search_entry.pack(side='left', padx=5, fill='x', expand=True)
    
    # Results frame
    results_frame = ttk.Frame(self.content_area)
    results_frame.pack(fill='both', expand=True, padx=10, pady=10)
    
    # Initial loading
    loading_label = ttk.Label(
        results_frame,
        text="⏳ Loading items...",
        font=FONTS['normal']
    )
    loading_label.pack(pady=50)
    
    # Store all items
    all_items = []
    
    # Load all items first
    def load_all_items():
        return self.db.get_all_items()
    
    def on_items_loaded(items):
        nonlocal all_items
        loading_label.destroy()
        all_items = items
        
        # Create treeview
        tree = ttk.Treeview(results_frame, columns=('Name', 'Value'), height=15, show='headings')
        tree.pack(fill='both', expand=True)
        
        # Bind search
        def on_search(*args):
            term = search_var.get().lower()
            
            # Clear tree
            for item in tree.get_children():
                tree.delete(item)
            
            # Filter and display
            for item in all_items:
                if term in item['name'].lower():
                    tree.insert('', 'end', values=(item['name'], item['value']))
        
        search_var.trace('w', on_search)
        
        # Initial display
        on_search()
    
    # Load items async
    op = AsyncOperation(
        parent=results_frame,
        task_func=load_all_items,
        on_complete=on_items_loaded,
        show_loading=False
    )
    op.start()
```

---

## Pattern 7: Error Handling

Use this pattern for robust error handling.

```python
def show_with_error_handling(self):
    """Example with comprehensive error handling."""
    self._clear_content()
    
    # Show loading
    loading = ttk.Label(
        self.content_area,
        text="⏳ Processing...",
        font=FONTS['normal']
    )
    loading.pack(pady=20)
    
    # Define task
    def risky_operation():
        """Operation that might fail."""
        try:
            # Do something risky
            result = self.perform_risky_task()
            if not result:
                raise ValueError("Task returned no result")
            return result
        except ValueError as e:
            logger.error(f"Validation error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise
    
    # Define callbacks
    def on_success(result):
        """Called if task succeeds."""
        loading.destroy()
        label = ttk.Label(
            self.content_area,
            text=f"✅ Success: {result}",
            foreground=COLORS['success']
        )
        label.pack(pady=20)
    
    def on_error(exception):
        """Called if task fails."""
        loading.destroy()
        error_msg = str(exception)
        
        label = ttk.Label(
            self.content_area,
            text=f"❌ Error: {error_msg}",
            foreground=COLORS['danger'],
            wraplength=400
        )
        label.pack(pady=20)
        
        # Optionally show dialog
        messagebox.showerror("Operation Failed", error_msg)
    
    # Execute with error handling
    op = AsyncOperation(
        parent=self.content_area,
        task_func=risky_operation,
        on_complete=on_success,
        on_error=on_error,
        show_loading=False
    )
    op.start()
```

---

## Common Gotchas

### ❌ Wrong: Direct UI Update from Thread
```python
def background_task():
    data = expensive_operation()
    label.config(text=data)  # WRONG! Not thread-safe
```

### ✅ Correct: Use UIThreadSafeUpdater
```python
def background_task():
    data = expensive_operation()
    UIThreadSafeUpdater.safe_call(label, label.config, text=data)  # RIGHT!
```

---

### ❌ Wrong: Function Call Instead of Function Reference
```python
operation = AsyncOperation(
    parent,
    expensive_operation(),  # WRONG! Executes immediately
    on_complete=callback
)
```

### ✅ Correct: Pass Function, Not Call
```python
operation = AsyncOperation(
    parent,
    expensive_operation,  # RIGHT! Function reference
    on_complete=callback
)
operation.start()
```

---

### ❌ Wrong: Blocking Operations
```python
def on_complete(result):
    # Processing in UI thread - blocks UI!
    processed = expensive_processing(result)
    update_ui(processed)
```

### ✅ Correct: Return Data, Process in Callback
```python
def task():
    # Do heavy lifting in background
    result = expensive_operation()
    return result

def on_complete(result):
    # Only display in UI thread
    update_ui(result)
```

---

## Integration Checklist

When adding async operations to your code:

- [ ] Import `AsyncOperation` from async_helper
- [ ] Wrap heavy operation in a function
- [ ] Define callback for completion
- [ ] Add error callback (optional but recommended)
- [ ] Use `UIThreadSafeUpdater` for any UI updates
- [ ] Show loading indicator to user
- [ ] Test with slow network/large datasets
- [ ] Verify UI remains responsive
- [ ] Check logs for errors
- [ ] Test error cases

---

## Summary

These 7 patterns cover most use cases:

1. **Load and Display** - Fetch and show data
2. **Populate Treeview** - Fill tables/trees
3. **Generate Report** - Long-running operations
4. **Parallel Tasks** - Multiple async operations
5. **Lazy Loading** - Load on-demand
6. **Live Filtering** - Search without blocking
7. **Error Handling** - Robust error management

Copy-paste, customize, and enjoy responsive UIs!

