"""Dashboard screen for Shoukat Sons Garments POS."""
import customtkinter as ctk
from typing import Dict, List, Optional
from ui.theme import ThemeManager
from ui.components import StatCard, DataTable
from services import inventory_service
from services.report_service import ReportService
from database.connection import ConnectionManager
from datetime import datetime, timedelta


class DashboardScreen(ctk.CTkFrame):
    """Main dashboard with stats, quick actions, and recent activity."""
    
    def __init__(self, master, user_info: Dict, router, **kwargs):
        super().__init__(master, **kwargs)
        self.theme = ThemeManager()
        self.cm = ConnectionManager()
        self.user_info = user_info
        self.router = router
        self.report_service = ReportService(self.cm)
        self.inventory_service = inventory_service
        
        self._setup_ui()
        self._refresh_data()
        
        # Auto-refresh every 30 seconds
        self._refresh_id = None
        self._start_auto_refresh()
    
    def _setup_ui(self) -> None:
        """Configure dashboard UI components."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        welcome_label = ctk.CTkLabel(
            header_frame,
            text=f"Welcome, {self.user_info['username']}!",
            font=self.theme.get_font("heading")
        )
        welcome_label.pack(side="left")
        
        date_label = ctk.CTkLabel(
            header_frame,
            text=datetime.now().strftime("%B %d, %Y"),
            font=self.theme.get_font("body"),
            text_color=self.theme.get_color("text_secondary")
        )
        date_label.pack(side="right")
        
        # Stat Cards Row
        stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        stats_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        stats_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        self.today_sales_card = StatCard(stats_frame, "Today's Sales", "Rs. 0")
        self.today_sales_card.grid(row=0, column=0, padx=5, sticky="ew")
        
        self.today_transactions_card = StatCard(stats_frame, "Transactions", "0")
        self.today_transactions_card.grid(row=0, column=1, padx=5, sticky="ew")
        
        self.low_stock_card = StatCard(stats_frame, "Low Stock", "0")
        self.low_stock_card.grid(row=0, column=2, padx=5, sticky="ew")
        
        self.credit_due_card = StatCard(stats_frame, "Credit Due", "Rs. 0")
        self.credit_due_card.grid(row=0, column=3, padx=5, sticky="ew")
        
        # Quick Actions
        actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        actions_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
        
        new_sale_btn = ctk.CTkButton(
            actions_frame,
            text="New Sale",
            command=lambda: self.router.navigate_to("new_sale"),
            width=150,
            height=50,
            font=self.theme.get_font("button"),
            fg_color=self.theme.get_color("primary")
        )
        new_sale_btn.pack(side="left", padx=5)
        
        restock_btn = ctk.CTkButton(
            actions_frame,
            text="Quick Restock",
            command=lambda: self.router.navigate_to("quick_restock"),
            width=150,
            height=50,
            font=self.theme.get_font("button")
        )
        restock_btn.pack(side="left", padx=5)
        
        labels_btn = ctk.CTkButton(
            actions_frame,
            text="Print Labels",
            command=lambda: self.router.navigate_to("print_labels"),
            width=150,
            height=50,
            font=self.theme.get_font("button")
        )
        labels_btn.pack(side="left", padx=5)
        
        reports_btn = ctk.CTkButton(
            actions_frame,
            text="View Reports",
            command=lambda: self.router.navigate_to("sales_report"),
            width=150,
            height=50,
            font=self.theme.get_font("button")
        )
        reports_btn.pack(side="left", padx=5)
        
        # Recent Activity Table
        activity_frame = ctk.CTkFrame(self)
        activity_frame.grid(row=3, column=0, sticky="nsew", padx=20, pady=10)
        activity_frame.grid_columnconfigure(0, weight=1)
        activity_frame.grid_rowconfigure(1, weight=1)
        
        activity_label = ctk.CTkLabel(
            activity_frame,
            text="Recent Sales",
            font=self.theme.get_font("subheading")
        )
        activity_label.grid(row=0, column=0, sticky="w", pady=(10, 5))
        
        columns = [
            {"name": "Invoice", "width": 150},
            {"name": "Customer", "width": 150},
            {"name": "Total", "width": 100},
            {"name": "Time", "width": 100}
        ]
        
        self.activity_table = DataTable(activity_frame, columns)
        self.activity_table.grid(row=1, column=0, sticky="nsew")
        
        # Alerts Panel
        alerts_frame = ctk.CTkFrame(self, fg_color="transparent")
        alerts_frame.grid(row=4, column=0, sticky="ew", padx=20, pady=(10, 20))
        
        alerts_label = ctk.CTkLabel(
            alerts_frame,
            text="Alerts",
            font=self.theme.get_font("subheading")
        )
        alerts_label.pack(anchor="w")
        
        self.alerts_text = ctk.CTkTextbox(alerts_frame, height=80, font=self.theme.get_font("small"))
        self.alerts_text.pack(fill="x", pady=5)
        
        self.theme.apply_to_widget(self, bg_key="bg")
    
    def _refresh_data(self) -> None:
        """Refresh all dashboard data."""
        today = datetime.now().strftime("%Y-%m-%d")
        
        try:
            conn = self.cm.get_read_connection()
            
            # Today's sales
            daily_report = self.report_service.get_daily_sales(today)
            self.today_sales_card.update_value(f"Rs. {daily_report.total_sales // 100:,}")
            self.today_transactions_card.update_value(str(daily_report.transaction_count))
            
            # Low stock - call method on service instance, not module
            low_stock = self.inventory_service.get_low_stock_variants()
            count = len(low_stock) if low_stock else 0
            self.low_stock_card.update_value(str(count))
            if count > 0:
                self.low_stock_card.configure(fg_color=self.theme.get_color("warning"))
            
            # Credit due
            credit_report = self.report_service.get_customer_credit_report()
            total_due = sum(record.total_due for record in credit_report)
            self.credit_due_card.update_value(f"Rs. {total_due // 100:,}")
            if total_due > 0:
                self.credit_due_card.configure(fg_color=self.theme.get_color("danger"))
            
            # Recent activity
            self._load_recent_sales()
            
            # Alerts
            self._update_alerts(low_stock, credit_report)
            
        except Exception as e:
            print(f"Dashboard refresh error: {e}")
    
    def _load_recent_sales(self) -> None:
        """Load last 10 sales into activity table."""
        try:
            conn = self.cm.get_read_connection()
            cursor = conn.execute("""
                SELECT invoice_number, 
                       COALESCE(c.name, 'Walk-in') as customer,
                       total_amount,
                       sale_date
                FROM sales s
                LEFT JOIN customers c ON s.customer_id = c.id
                ORDER BY s.sale_date DESC
                LIMIT 10
            """)
            
            rows = []
            for row in cursor.fetchall():
                time_str = datetime.fromisoformat(row[3]).strftime("%H:%M")
                rows.append([
                    row[0],
                    row[1],
                    f"Rs. {row[2] // 100:,}",
                    time_str
                ])
            
            self.activity_table.set_data(rows)
        except Exception as e:
            print(f"Error loading recent sales: {e}")
    
    def _update_alerts(self, low_stock: List, credit_report: List) -> None:
        """Update alerts panel."""
        alerts = []
        
        if low_stock:
            alerts.append(f"⚠️ {len(low_stock)} items low on stock")
        
        overdue = [c for c in credit_report if c.total_due > 0]
        if overdue:
            alerts.append(f"⚠️ {len(overdue)} customers have outstanding dues")
        
        if not alerts:
            alerts.append("✓ No alerts")
        
        self.alerts_text.delete("1.0", "end")
        self.alerts_text.insert("1.0", "\n".join(alerts))
    
    def _start_auto_refresh(self) -> None:
        """Start auto-refresh timer."""
        def refresh():
            self._refresh_data()
            self._refresh_id = self.after(30000, refresh)
        
        self._refresh_id = self.after(30000, refresh)
    
    def destroy(self) -> None:
        """Clean up timer on destroy."""
        if self._refresh_id:
            self.after_cancel(self._refresh_id)
        super().destroy()
