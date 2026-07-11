"""Quick restock screen for fast stock addition."""
import customtkinter as ctk
from typing import Dict, Optional
from ui.theme import ThemeManager
from ui.dialogs.password_dialog import PasswordDialog
from services import inventory_service, product_service
from database.connection import ConnectionManager


class QuickRestockScreen(ctk.CTkFrame):
    """Three-tap quick restock interface."""
    
    def __init__(self, master, router, user_info: Dict, **kwargs):
        super().__init__(master, **kwargs)
        self.theme = ThemeManager()
        self.router = router
        self.user_info = user_info
        self.cm = ConnectionManager()
        self.inventory_service = inventory_service
        self.product_service = product_service
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Configure quick restock UI."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)
        
        # Title
        title_label = ctk.CTkLabel(
            self,
            text="Quick Restock",
            font=self.theme.get_font("heading")
        )
        title_label.grid(row=0, column=0, pady=(20, 10))
        
        subtitle = ctk.CTkLabel(
            self,
            text="Scan barcode or enter manually to restock",
            font=self.theme.get_font("body"),
            text_color=self.theme.get_color("text_secondary")
        )
        subtitle.grid(row=1, column=0, pady=(0, 20))
        
        # Barcode input
        barcode_frame = ctk.CTkFrame(self, fg_color="transparent")
        barcode_frame.grid(row=2, column=0, pady=10)
        
        self.barcode_entry = ctk.CTkEntry(
            barcode_frame,
            placeholder_text="Scan or enter barcode...",
            width=400,
            height=45,
            font=self.theme.get_font("body")
        )
        self.barcode_entry.pack(side="left", padx=(0, 10))
        self.barcode_entry.bind("<Return>", lambda e: self._lookup_product())
        self.barcode_entry.focus()
        
        lookup_btn = ctk.CTkButton(
            barcode_frame,
            text="Lookup",
            command=self._lookup_product,
            height=45,
            font=self.theme.get_font("button")
        )
        lookup_btn.pack(side="left")
        
        # Product details (hidden until lookup)
        self.details_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.details_frame.grid(row=3, column=0, pady=20)
        
        self.product_label = ctk.CTkLabel(
            self.details_frame,
            text="",
            font=self.theme.get_font("subheading")
        )
        self.product_label.grid(row=0, column=0, sticky="w", pady=5)
        
        self.current_stock_label = ctk.CTkLabel(
            self.details_frame,
            text="",
            font=self.theme.get_font("body")
        )
        self.current_stock_label.grid(row=1, column=0, sticky="w", pady=5)
        
        # Quantity to add
        qty_frame = ctk.CTkFrame(self.details_frame, fg_color="transparent")
        qty_frame.grid(row=2, column=0, pady=10)
        
        qty_label = ctk.CTkLabel(
            qty_frame,
            text="Quantity to Add:",
            font=self.theme.get_font("body")
        )
        qty_label.grid(row=0, column=0, padx=(0, 10))
        
        self.qty_entry = ctk.CTkEntry(
            qty_frame,
            width=100,
            height=35,
            font=self.theme.get_font("body")
        )
        self.qty_entry.grid(row=0, column=1, padx=5)
        self.qty_entry.insert(0, "1")
        
        # Purchase price (optional)
        price_frame = ctk.CTkFrame(self.details_frame, fg_color="transparent")
        price_frame.grid(row=3, column=0, pady=10)
        
        price_label = ctk.CTkLabel(
            price_frame,
            text="Purchase Price (Rs.) - Optional:",
            font=self.theme.get_font("body")
        )
        price_label.grid(row=0, column=0, padx=(0, 10))
        
        self.price_entry = ctk.CTkEntry(
            price_frame,
            width=150,
            height=35,
            font=self.theme.get_font("body")
        )
        self.price_entry.grid(row=0, column=1, padx=5)
        
        # Action buttons
        btn_frame = ctk.CTkFrame(self.details_frame, fg_color="transparent")
        btn_frame.grid(row=4, column=0, pady=20)
        
        confirm_btn = ctk.CTkButton(
            btn_frame,
            text="Confirm Restock",
            command=self._confirm_restock,
            width=200,
            height=45,
            font=self.theme.get_font("button"),
            fg_color=self.theme.get_color("success")
        )
        confirm_btn.grid(row=0, column=0, padx=5)
        
        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Cancel",
            command=lambda: self.router.navigate_to("dashboard"),
            width=150,
            height=45,
            font=self.theme.get_font("button")
        )
        cancel_btn.grid(row=0, column=1, padx=5)
        
        # Status label
        self.status_label = ctk.CTkLabel(
            self,
            text="",
            font=self.theme.get_font("small")
        )
        self.status_label.grid(row=4, column=0, pady=10)
        
        self.theme.apply_to_widget(self, bg_key="bg")
        
        # Hide details initially
        self.details_frame.grid_remove()
        
        self.current_variant_id: Optional[int] = None
    
    def _lookup_product(self) -> None:
        """Lookup product by barcode."""
        barcode = self.barcode_entry.get().strip()
        if not barcode:
            self.status_label.configure(text="Please enter a barcode", 
                                       text_color=self.theme.get_color("danger"))
            return
        
        try:
            conn = self.cm.get_read_connection()
            variant = self.product_service.get_variant_by_barcode(conn, barcode)
            
            if variant:
                self.current_variant_id = variant.id
                self.product_label.configure(text=f"{variant.style_name} - {variant.size} {variant.color}")
                self.current_stock_label.configure(text=f"Current Stock: {variant.quantity}")
                self.details_frame.grid()
                self.qty_entry.focus()
                self.status_label.configure(text="", text_color="")
            else:
                self.status_label.configure(text="Product not found. Please add it first.",
                                           text_color=self.theme.get_color("warning"))
                self.details_frame.grid_remove()
                
        except Exception as e:
            self.status_label.configure(text=f"Error: {str(e)}",
                                       text_color=self.theme.get_color("danger"))
    
    def _confirm_restock(self) -> None:
        """Confirm and process restock."""
        if not self.current_variant_id:
            return
        
        try:
            qty_str = self.qty_entry.get().strip()
            qty = int(qty_str) if qty_str else 1
            
            if qty <= 0:
                self.status_label.configure(text="Quantity must be positive",
                                           text_color=self.theme.get_color("danger"))
                return
            
            # Get purchase price if provided
            purchase_price = None
            secret_code = None
            price_str = self.price_entry.get().strip()
            
            if price_str:
                try:
                    purchase_price = int(float(price_str) * 100)  # Convert to cents
                    # Generate secret code from settings (stub for now)
                    secret_code = str(purchase_price)
                except ValueError:
                    self.status_label.configure(text="Invalid price format",
                                               text_color=self.theme.get_color("danger"))
                    return
            
            conn = self.cm.get_write_connection()
            
            with self.cm.execute_transaction() as trans_conn:
                if purchase_price and secret_code:
                    batch_data = {
                        "vendor_id": None,
                        "bilty_no": "",
                        "bill_no": "",
                        "date_received": None
                    }
                    self.inventory_service.restock_variant(
                        trans_conn,
                        self.current_variant_id,
                        qty,
                        purchase_price,
                        secret_code,
                        batch_data
                    )
                else:
                    # Just update quantity without new batch
                    self.inventory_service.update_variant_stock(
                        trans_conn,
                        self.current_variant_id,
                        qty,
                        "Quick restock"
                    )
            
            self.status_label.configure(text=f"✓ Restocked {qty} units successfully!",
                                       text_color=self.theme.get_color("success"))
            
            # Clear form after short delay
            self.after(1500, self._clear_form)
            
        except Exception as e:
            self.status_label.configure(text=f"Error: {str(e)}",
                                       text_color=self.theme.get_color("danger"))
    
    def _clear_form(self) -> None:
        """Clear form for next entry."""
        self.barcode_entry.delete(0, 'end')
        self.qty_entry.delete(0, 'end')
        self.qty_entry.insert(0, "1")
        self.price_entry.delete(0, 'end')
        self.details_frame.grid_remove()
        self.current_variant_id = None
        self.barcode_entry.focus()
