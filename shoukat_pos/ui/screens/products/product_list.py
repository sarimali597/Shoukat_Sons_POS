"""Product list screen with card/table view and filters."""
import customtkinter as ctk
from typing import Dict, List, Optional
from ui.theme import ThemeManager
from ui.components import DataTable, SearchBar, EmptyState
from services import product_service, inventory_service
from database.connection import ConnectionManager


class ProductListScreen(ctk.CTkFrame):
    """Product list with search, filters, and card/table toggle."""
    
    def __init__(self, master, router, user_info: Dict, **kwargs):
        super().__init__(master, **kwargs)
        self.theme = ThemeManager()
        self.router = router
        self.user_info = user_info
        self.cm = ConnectionManager()
        self.product_service = product_service
        self.inventory_service = inventory_service
        
        self._setup_ui()
        self._load_products()
    
    def _setup_ui(self) -> None:
        """Configure product list UI."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        # Header with title and add button
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        title_label = ctk.CTkLabel(
            header_frame,
            text="Products",
            font=self.theme.get_font("heading")
        )
        title_label.pack(side="left")
        
        add_btn = ctk.CTkButton(
            header_frame,
            text="+ Add Product",
            command=lambda: self.router.navigate_to("add_product"),
            height=35,
            font=self.theme.get_font("button")
        )
        add_btn.pack(side="right")
        
        # Search and filters
        filters_frame = ctk.CTkFrame(self, fg_color="transparent")
        filters_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        
        self.search_bar = SearchBar(filters_frame, self._on_search, "Search products...")
        self.search_bar.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.category_var = ctk.StringVar(value="All")
        category_dropdown = ctk.CTkOptionMenu(
            filters_frame,
            variable=self.category_var,
            values=["All", "Shirt", "Pant", "Tie", "Coat"],
            command=self._on_filter_change,
            width=120
        )
        category_dropdown.pack(side="left", padx=5)
        
        self.stock_var = ctk.StringVar(value="All")
        stock_dropdown = ctk.CTkOptionMenu(
            filters_frame,
            variable=self.stock_var,
            values=["All", "In Stock", "Low Stock", "Out of Stock"],
            command=self._on_filter_change,
            width=120
        )
        stock_dropdown.pack(side="left", padx=5)
        
        # View toggle
        self.view_var = ctk.StringVar(value="table")
        view_toggle = ctk.CTkSegmentedButton(
            filters_frame,
            variable=self.view_var,
            values=["table", "card"],
            command=self._on_view_change,
            width=100
        )
        view_toggle.pack(side="right")
        
        # Product table
        self.table_frame = ctk.CTkFrame(self)
        self.table_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)
        self.table_frame.grid_columnconfigure(0, weight=1)
        self.table_frame.grid_rowconfigure(0, weight=1)
        
        columns = [
            {"name": "Barcode", "width": 150},
            {"name": "Style", "width": 200},
            {"name": "Size", "width": 60},
            {"name": "Color", "width": 80},
            {"name": "Stock", "width": 70},
            {"name": "Price", "width": 80},
            {"name": "Actions", "width": 120}
        ]
        
        self.product_table = DataTable(self.table_frame, columns)
        self.product_table.grid(row=0, column=0, sticky="nsew")
        
        # Empty state (hidden by default)
        self.empty_state = EmptyState(
            self,
            "No products found",
            "Add Your First Product",
            lambda: self.router.navigate_to("add_product")
        )
        
        self.theme.apply_to_widget(self, bg_key="bg")
    
    def _load_products(self, query: str = "", category: str = "All", stock_status: str = "All") -> None:
        """Load products into table."""
        try:
            conn = self.cm.get_read_connection()
            
            # Get all variants with style info
            cursor = conn.execute("""
                SELECT v.barcode, s.name as style_name, v.size, v.color, 
                       v.quantity, s.base_sale_price, v.id as variant_id
                FROM variants v
                JOIN styles s ON v.style_id = s.id
                ORDER BY s.name, v.size, v.color
            """)
            
            rows = []
            for row in cursor.fetchall():
                barcode, style, size, color, qty, price, variant_id = row
                
                # Apply filters
                if query and query.lower() not in barcode.lower() and query.lower() not in style.lower():
                    continue
                
                if category != "All":
                    cat_cursor = conn.execute("""
                        SELECT name FROM categories WHERE id = (
                            SELECT category_id FROM styles WHERE id = ?
                        )
                    """, (cursor.fetchone()[0] if cursor.fetchone else None,))
                
                if stock_status == "Low Stock" and qty >= 5:
                    continue
                elif stock_status == "Out of Stock" and qty > 0:
                    continue
                elif stock_status == "In Stock" and qty <= 5:
                    continue
                
                rows.append([
                    barcode,
                    style[:20],
                    size,
                    color,
                    str(qty),
                    f"Rs. {price // 100}",
                    "View | Print"
                ])
            
            if rows:
                self.product_table.set_data(rows)
                self.product_table.grid()
                self.empty_state.pack_forget()
            else:
                self.product_table.grid_remove()
                self.empty_state.pack(expand=True, fill="both")
                
        except Exception as e:
            print(f"Error loading products: {e}")
    
    def _on_search(self, query: str) -> None:
        """Handle search."""
        self._load_products(query=query)
    
    def _on_filter_change(self, *args) -> None:
        """Handle filter changes."""
        self._load_products(
            query=self.search_bar.get() if hasattr(self.search_bar, 'get') else "",
            category=self.category_var.get(),
            stock_status=self.stock_var.get()
        )
    
    def _on_view_change(self, view: str) -> None:
        """Handle view toggle."""
        # For now, just reload table - card view would require different layout
        pass
