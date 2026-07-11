"""Sales Report Screen - View and export sales reports."""

import customtkinter as ctk
from typing import Dict, Optional
from datetime import datetime

from ui.theme import ThemeManager
from ui.components import DataTable, StatCard


class SalesReportScreen(ctk.CTkFrame):
    """Sales report screen with date range filtering and charts."""
    
    def __init__(self, master, router, **kwargs):
        super().__init__(master, **kwargs)
        self.router = router
        self.theme = ThemeManager()
        
        self._create_ui()
    
    def _create_ui(self):
        """Create sales report interface."""
        # Header
        header_frame = ctk.CTkFrame(self)
        header_frame.pack(fill="x", padx=20, pady=10)
        
        title = ctk.CTkLabel(
            header_frame,
            text="Sales Report",
            font=self.theme.get_font("heading")
        )
        title.pack(side="left")
        
        # Date range selector
        date_frame = ctk.CTkFrame(header_frame)
        date_frame.pack(side="right")
        
        ctk.CTkLabel(date_frame, text="From:").pack(side="left", padx=5)
        self.from_date = ctk.CTkEntry(date_frame, width=100)
        self.from_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.from_date.pack(side="left", padx=5)
        
        ctk.CTkLabel(date_frame, text="To:").pack(side="left", padx=5)
        self.to_date = ctk.CTkEntry(date_frame, width=100)
        self.to_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.to_date.pack(side="left", padx=5)
        
        generate_btn = ctk.CTkButton(
            date_frame,
            text="Generate",
            command=self._generate_report
        )
        generate_btn.pack(side="left", padx=5)
        
        # Summary cards
        cards_frame = ctk.CTkFrame(self)
        cards_frame.pack(fill="x", padx=20, pady=10)
        
        self.total_sales_card = StatCard(
            cards_frame,
            title="Total Sales",
            value="Rs. 0.00"
        )
        self.total_sales_card.pack(side="left", expand=True, fill="both", padx=5)
        
        self.cash_sales_card = StatCard(
            cards_frame,
            title="Cash Sales",
            value="Rs. 0.00"
        )
        self.cash_sales_card.pack(side="left", expand=True, fill="both", padx=5)
        
        self.credit_sales_card = StatCard(
            cards_frame,
            title="Credit Sales",
            value="Rs. 0.00"
        )
        self.credit_sales_card.pack(side="left", expand=True, fill="both", padx=5)
        
        self.transactions_card = StatCard(
            cards_frame,
            title="Transactions",
            value="0"
        )
        self.transactions_card.pack(side="left", expand=True, fill="both", padx=5)
        
        # Detail table placeholder
        content_frame = ctk.CTkFrame(self)
        content_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        placeholder = ctk.CTkLabel(
            content_frame,
            text="Sales Details Table (DataTable integration coming)",
            font=self.theme.get_font("body")
        )
        placeholder.pack(expand=True)
        
        # Export button
        export_btn = ctk.CTkButton(
            self,
            text="Export to PDF",
            fg_color=self.theme.get_color("primary"),
            command=self._export_pdf
        )
        export_btn.pack(pady=10)
    
    def _generate_report(self):
        """Generate sales report for selected date range."""
        # TODO: Implement report generation via ReportService
        pass
    
    def _export_pdf(self):
        """Export report to PDF."""
        # TODO: Implement PDF export via PDFGenerator
        pass
