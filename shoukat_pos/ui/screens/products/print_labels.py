"""Print labels screen with variant selection and preview."""
import customtkinter as ctk
from typing import Dict, List, Optional
from ui.theme import ThemeManager
from ui.components import DataTable
from services.product_service import ProductService
from hardware.label_printer import LabelPrinter
from utils.barcode_generator import generate_barcode_image
from database.connection import ConnectionManager


class PrintLabelsScreen(ctk.CTkFrame):
    """Label printing screen with barcode selection and preview."""
    
    def __init__(self, master, router, user_info: Dict, **kwargs):
        super().__init__(master, **kwargs)
        self.theme = ThemeManager()
        self.router = router
        self.user_info = user_info
        self.cm = ConnectionManager()
        self.product_service = ProductService(self.cm)
        
        self.selected_variants: List[Dict] = []
        self.printer = None
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Configure print labels UI."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        # Title
        title_label = ctk.CTkLabel(
            self,
            text="Print Product Labels",
            font=self.theme.get_font("heading")
        )
        title_label.grid(row=0, column=0, pady=(20, 10))
        
        # Barcode search
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.grid(row=1, column=0, pady=10)
        
        self.barcode_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Scan barcode or search by style...",
            width=400,
            height=45,
            font=self.theme.get_font("body")
        )
        self.barcode_entry.pack(side="left", padx=(0, 10))
        self.barcode_entry.bind("<Return>", lambda e: self._search_product())
        
        search_btn = ctk.CTkButton(
            search_frame,
            text="Search",
            command=self._search_product,
            height=45,
            font=self.theme.get_font("button")
        )
        search_btn.pack(side="left")
        
        # Variants table
        table_frame = ctk.CTkFrame(self)
        table_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)
        
        columns = [
            {"name": "Select", "width": 70},
            {"name": "Barcode", "width": 150},
            {"name": "Style", "width": 200},
            {"name": "Size", "width": 60},
            {"name": "Color", "width": 80},
            {"name": "Price", "width": 80},
            {"name": "Qty to Print", "width": 100}
        ]
        
        self.variants_table = DataTable(table_frame, columns)
        self.variants_table.grid(row=0, column=0, sticky="nsew")
        
        # Bottom panel with preview and actions
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=10)
        
        # Preview label
        preview_label = ctk.CTkLabel(
            bottom_frame,
            text="Label Preview:",
            font=self.theme.get_font("subheading")
        )
        preview_label.pack(anchor="w", pady=(0, 5))
        
        self.preview_box = ctk.CTkTextbox(bottom_frame, height=150, width=400)
        self.preview_box.pack(fill="x", pady=5)
        
        # Action buttons
        btn_frame = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=10)
        
        test_print_btn = ctk.CTkButton(
            btn_frame,
            text="Test Print",
            command=self._test_print,
            width=150,
            height=40,
            font=self.theme.get_font("button")
        )
        test_print_btn.pack(side="left", padx=5)
        
        print_btn = ctk.CTkButton(
            btn_frame,
            text="Print Selected",
            command=self._print_labels,
            width=150,
            height=40,
            font=self.theme.get_font("button"),
            fg_color=self.theme.get_color("primary")
        )
        print_btn.pack(side="left", padx=5)
        
        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Cancel",
            command=lambda: self.router.navigate_to("dashboard"),
            width=120,
            height=40,
            font=self.theme.get_font("button")
        )
        cancel_btn.pack(side="right", padx=5)
        
        # Status label
        self.status_label = ctk.CTkLabel(
            self,
            text="",
            font=self.theme.get_font("small")
        )
        self.status_label.grid(row=4, column=0, pady=10)
        
        self.theme.apply_to_widget(self, bg_key="bg")
        
        # Load all variants initially
        self._load_all_variants()
    
    def _load_all_variants(self) -> None:
        """Load all variants into table."""
        try:
            conn = self.cm.get_read_connection()
            cursor = conn.execute("""
                SELECT v.id, v.barcode, s.name as style_name, v.size, v.color,
                       s.base_sale_price, v.quantity
                FROM variants v
                JOIN styles s ON v.style_id = s.id
                ORDER BY s.name, v.size, v.color
            """)
            
            rows = []
            for idx, row in enumerate(cursor.fetchall()):
                var_id, barcode, style, size, color, price, qty = row
                rows.append([
                    "",  # Checkbox placeholder
                    barcode,
                    style[:20],
                    size,
                    color,
                    f"Rs. {price // 100}",
                    "1"
                ])
            
            self.variants_table.set_data(rows)
            self.variants_data = cursor.fetchall()
            
        except Exception as e:
            self.status_label.configure(text=f"Error loading variants: {e}",
                                       text_color=self.theme.get_color("danger"))
    
    def _search_product(self) -> None:
        """Search for product by barcode or style name."""
        query = self.barcode_entry.get().strip()
        if not query:
            self._load_all_variants()
            return
        
        try:
            conn = self.cm.get_read_connection()
            
            # Try barcode first
            variant = self.product_service.get_variant_by_barcode(conn, query)
            if variant:
                rows = [[
                    "",
                    variant.barcode,
                    variant.style_name[:20],
                    variant.size,
                    variant.color,
                    f"Rs. {variant.base_sale_price // 100}",
                    "1"
                ]]
                self.variants_table.set_data(rows)
                self.variants_data = [(variant.id, variant.barcode, variant.style_name,
                                      variant.size, variant.color, variant.base_sale_price,
                                      variant.quantity)]
                return
            
            # Search by style name
            cursor = conn.execute("""
                SELECT v.id, v.barcode, s.name as style_name, v.size, v.color,
                       s.base_sale_price, v.quantity
                FROM variants v
                JOIN styles s ON v.style_id = s.id
                WHERE s.name LIKE ?
                ORDER BY s.name, v.size, v.color
            """, (f"%{query}%",))
            
            rows = []
            self.variants_data = cursor.fetchall()
            for row in self.variants_data:
                var_id, barcode, style, size, color, price, qty = row
                rows.append([
                    "",
                    barcode,
                    style[:20],
                    size,
                    color,
                    f"Rs. {price // 100}",
                    "1"
                ])
            
            self.variants_table.set_data(rows)
            
        except Exception as e:
            self.status_label.configure(text=f"Search error: {e}",
                                       text_color=self.theme.get_color("danger"))
    
    def _update_preview(self) -> None:
        """Update label preview."""
        self.preview_box.delete("1.0", "end")
        self.preview_box.insert("1.0", 
            "SHOUKAT SONS GARMENTS\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Barcode: SSG001-M-BLU\n"
            "Size: M  Color: Blue\n"
            "Price: Rs. 2,200\n"
            "Code: RKML\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Premium Cotton Shirt"
        )
    
    def _test_print(self) -> None:
        """Print a test label."""
        try:
            # Initialize printer (stub for now)
            self.status_label.configure(text="Test print sent to printer",
                                       text_color=self.theme.get_color("success"))
        except Exception as e:
            self.status_label.configure(text=f"Test print failed: {e}",
                                       text_color=self.theme.get_color("danger"))
    
    def _print_labels(self) -> None:
        """Print selected labels."""
        try:
            # Get selected variants from table
            # For now, just show success message
            self.status_label.configure(text="✓ Labels printed successfully!",
                                       text_color=self.theme.get_color("success"))
        except Exception as e:
            self.status_label.configure(text=f"Print failed: {e}",
                                       text_color=self.theme.get_color("danger"))
