# ============================================================================
# TELEGRAM_MAIN.PY - Telegram-based POS System dengan Transaksi Lengkap
# ============================================================================
# Fungsi: POS system berbasis Telegram dengan menu transaksi, laporan, stok
# Fitur: Transaksi, cart, checkout, receipt, laporan, notifikasi
# ============================================================================

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
import time
import asyncio
import sys
import subprocess
import threading

from telegram import (
    Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup, 
    ReplyKeyboardMarkup, ReplyKeyboardRemove, User
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)

# Import POS modules
from database import DatabaseManager
from models import ProductManager, ValidationError, format_rp
from transaction import TransactionService, TransactionHandler, ReceiptManager
from laporan import ReportGenerator, ReportFormatter, CSVExporter
from telegram_bot import TelegramConfigManager

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('telegram_pos.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configure StreamHandler to use UTF-8 encoding  
for handler in logging.root.handlers:
    if isinstance(handler, logging.StreamHandler):
        if hasattr(handler.stream, 'reconfigure'):
            try:
                handler.stream.reconfigure(encoding='utf-8')
            except:
                pass

# ============================================================================
# CONVERSATION STATES
# ============================================================================

MAIN_MENU, TRANSAKSI_MENU, TAMBAH_ITEM_KODE, TAMBAH_ITEM_QTY, PEMBAYARAN = range(5)
DISKON, PAJAK = range(5, 7)
LIHAT_STOK, LIHAT_LAPORAN = range(7, 9)
KELOLA_PRODUK_MENU, KELOLA_PRODUK_TAMBAH_KODE, KELOLA_PRODUK_TAMBAH_NAMA = range(9, 12)
KELOLA_PRODUK_TAMBAH_HARGA, KELOLA_PRODUK_TAMBAH_STOK, KELOLA_PRODUK_TAMBAH_FOTO = range(12, 15)
KELOLA_PRODUK_LIHAT, KELOLA_PRODUK_EDIT, KELOLA_PRODUK_HAPUS = range(15, 18)

# ============================================================================
# TELEGRAM POS SYSTEM - Main class untuk Telegram-based POS
# ============================================================================

class TelegramPOSSystem:
    """
    Telegram-based POS System dengan transaction support lengkap.
    
    Features:
    - Transaksi penjualan (add item, checkout, receipt)
    - Management stok produk
    - Laporan penjualan
    - User sessions per chat_id
    - Shopping cart system
    
    Attributes:
        db (DatabaseManager): Database instance
        product_manager (ProductManager): Product management
        transaction_handlers (Dict): Dict of transaction handlers per user
        report_generator (ReportGenerator): Report generation
        config_manager (TelegramConfigManager): Config management
    """
    
    def __init__(self, token: str):
        """
        Inisialisasi TelegramPOSSystem.
        
        Args:
            token (str): Telegram bot token
        """
        self.token = token
        self.db = DatabaseManager()
        self.product_manager = ProductManager(self.db)
        self.report_generator = ReportGenerator(self.db)
        self.report_formatter = ReportFormatter()
        self.receipt_manager = ReceiptManager()
        self.config_manager = TelegramConfigManager()
        
        # Per-user transaction handlers
        self.transaction_handlers: Dict[int, TransactionHandler] = {}
        
        # Cache untuk optimasi - cache products dengan TTL
        self._products_cache = None
        self._cache_timestamp = 0
        self._cache_ttl = 10  # Cache timeout 10 seconds untuk product list
        
        # Auto-restart configuration (ENABLED)
        # Auto-restart every 25 seconds
        self.restart_interval = 25  # 25 seconds
        self.auto_restart_enabled = True  # ENABLED - auto-restart every 25 seconds
        self.restart_counter = 0
        self._restart_timer = None
        
        # Setup application
        self.application = Application.builder().token(token).build()
        self._register_handlers()
        
        logger.info("[+] TelegramPOSSystem initialized")
    
    def _schedule_restart(self):
        """Schedule restart setelah interval tertentu."""
        if self._restart_timer:
            self._restart_timer.cancel()
        
        self._restart_timer = threading.Timer(
            self.restart_interval,
            self._trigger_restart
        )
        self._restart_timer.daemon = True
        self._restart_timer.start()
        logger.debug(f"[*] Restart scheduled in {self.restart_interval} seconds")
    
    def _trigger_restart(self):
        """Trigger restart dengan menghentikan polling."""
        self.restart_counter += 1
        restart_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f"[*] Auto-restart triggered #{self.restart_counter} at {restart_time}")
        print(f"\n[*] AUTO-RESTART TRIGGERED #{self.restart_counter} at {restart_time}")
        
        try:
            # Stop application gracefully
            if self.application.updater:
                self.application.updater.stop()
                logger.info("[+] Updater stopped")
        except Exception as e:
            logger.error(f"[-] Error in restart trigger: {e}")
    
    def _cleanup_restart_timer(self):
        """Cleanup restart timer saat exit."""
        if self._restart_timer:
            self._restart_timer.cancel()
            self._restart_timer = None
    
    # ========================================================================
    # HANDLER REGISTRATION
    # ========================================================================
    
    def _register_handlers(self):
        """Register semua command dan callback handlers."""
        
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("menu", self.cmd_menu))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        
        # Conversation handler untuk transaksi
        transaksi_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.transaksi_start, pattern="^transaksi$")],
            states={
                TRANSAKSI_MENU: [
                    CallbackQueryHandler(self.transaksi_tambah_item, pattern="^tambah_item$"),
                    CallbackQueryHandler(self.transaksi_lihat_item, pattern="^lihat_item$"),
                    CallbackQueryHandler(self.transaksi_hapus_item_btn, pattern="^hapus_item$"),
                    CallbackQueryHandler(self.transaksi_checkout, pattern="^checkout$"),
                    CallbackQueryHandler(self.transaksi_cancel, pattern="^cancel_transaksi$"),
                    CallbackQueryHandler(self.transaksi_back_menu, pattern="^back_menu$"),
                    CallbackQueryHandler(self.transaksi_back_menu, pattern="^transaksi$"),
                    CallbackQueryHandler(self.transaksi_exit_to_main_menu, pattern="^main_menu$"),
                    CallbackQueryHandler(self.transaksi_exit_to_kelola_produk, pattern="^kelola_produk$"),
                    CallbackQueryHandler(self.transaksi_exit_to_lihat_stok, pattern="^lihat_stok$"),
                    CallbackQueryHandler(self.transaksi_exit_to_lihat_laporan, pattern="^lihat_laporan$"),
                    CallbackQueryHandler(self.transaksi_exit_to_lihat_dashboard, pattern="^lihat_dashboard$"),
                ],
                TAMBAH_ITEM_KODE: [
                    CallbackQueryHandler(self.handle_product_selection, pattern="^(select_product_|cancel_search)"),
                    CommandHandler("cancel", self.cmd_cancel_transaksi),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_item_kode),
                ],
                TAMBAH_ITEM_QTY: [
                    CommandHandler("cancel", self.cmd_cancel_transaksi),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_item_qty),
                ],
                DISKON: [
                    CommandHandler("cancel", self.cmd_cancel_transaksi),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_diskon),
                ],
                PAJAK: [
                    CommandHandler("cancel", self.cmd_cancel_transaksi),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_pajak),
                ],
                PEMBAYARAN: [
                    CommandHandler("cancel", self.cmd_cancel_transaksi),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_pembayaran),
                ],
            },
            fallbacks=[
                CallbackQueryHandler(self.transaksi_cancel, pattern="^cancel_transaksi$"),
                CommandHandler("cancel", self.cmd_cancel_transaksi),
            ],
            per_user=True,
            per_chat=True,
            per_message=False,
        )
        self.application.add_handler(transaksi_conv)
        
        # Conversation handler untuk kelola produk
        kelola_produk_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.kelola_produk_menu, pattern="^kelola_produk$")],
            states={
                KELOLA_PRODUK_MENU: [
                    CallbackQueryHandler(self.kelola_produk_lihat, pattern="^kp_lihat$"),
                    CallbackQueryHandler(self.kelola_produk_tambah_start, pattern="^kp_tambah$"),
                    CallbackQueryHandler(self.kelola_produk_edit_select, pattern="^kp_edit_select$"),
                    CallbackQueryHandler(self.kelola_produk_hapus_select, pattern="^kp_hapus_select$"),
                    CallbackQueryHandler(self.kelola_produk_info_stok, pattern="^kp_info_stok$"),
                    CallbackQueryHandler(self.kelola_produk_menu, pattern="^kembali_kp$"),
                    CallbackQueryHandler(self.kelola_produk_exit_to_main_menu, pattern="^main_menu$"),
                    CallbackQueryHandler(self.kelola_produk_exit_to_transaksi, pattern="^transaksi$"),
                    CallbackQueryHandler(self.kelola_produk_exit_to_lihat_stok, pattern="^lihat_stok$"),
                    CallbackQueryHandler(self.kelola_produk_exit_to_lihat_laporan, pattern="^lihat_laporan$"),
                    CallbackQueryHandler(self.kelola_produk_exit_to_lihat_dashboard, pattern="^lihat_dashboard$"),
                ],
                KELOLA_PRODUK_TAMBAH_KODE: [
                    CommandHandler("cancel", self.cmd_cancel_kelola_produk),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_kp_kode),
                ],
                KELOLA_PRODUK_TAMBAH_NAMA: [
                    CommandHandler("cancel", self.cmd_cancel_kelola_produk),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_kp_nama),
                ],
                KELOLA_PRODUK_TAMBAH_HARGA: [
                    CommandHandler("cancel", self.cmd_cancel_kelola_produk),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_kp_harga),
                ],
                KELOLA_PRODUK_TAMBAH_STOK: [
                    CommandHandler("cancel", self.cmd_cancel_kelola_produk),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_kp_stok),
                ],
                KELOLA_PRODUK_TAMBAH_FOTO: [
                    CommandHandler("cancel", self.cmd_cancel_kelola_produk),
                    CallbackQueryHandler(self.handle_kp_upload_foto_btn, pattern="^kp_upload_foto$"),
                    CallbackQueryHandler(self.handle_kp_skip_foto, pattern="^kp_skip_foto$"),
                    MessageHandler(filters.PHOTO, self.handle_kp_foto),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_kp_skip_foto_text),
                ],
                KELOLA_PRODUK_LIHAT: [
                    CallbackQueryHandler(self.kelola_produk_edit_start, pattern="^kp_edit_\d+$"),
                    CallbackQueryHandler(self.kelola_produk_hapus_confirm, pattern="^kp_hapus_\d+$"),
                    CallbackQueryHandler(self.kelola_produk_menu, pattern="^kembali_kp$"),
                ],
                KELOLA_PRODUK_EDIT: [
                    CallbackQueryHandler(self.kelola_produk_edit_field, pattern="^kp_edt_.*"),
                    CallbackQueryHandler(self.kelola_produk_lihat, pattern="^kp_lihat$"),
                ],
                KELOLA_PRODUK_HAPUS: [
                    CallbackQueryHandler(self.kelola_produk_hapus_confirm_exec, pattern="^kp_hapus_yes_\d+$"),
                    CallbackQueryHandler(self.kelola_produk_lihat, pattern="^kp_hapus_no$"),
                ],
            },
            fallbacks=[
                CallbackQueryHandler(self.callback_main_menu, pattern="^main_menu$"),
                CallbackQueryHandler(self.kelola_produk_menu, pattern="^kembali_kp$"),
                CommandHandler("cancel", self.cmd_cancel_kelola_produk),
            ],
            per_user=True,
            per_chat=True,
            per_message=False,
        )
        self.application.add_handler(kelola_produk_conv)
        
        # Handler untuk hapus item (remove dari transaksi)
        # Pattern: remove_item_{idx} where idx is any digit sequence
        self.application.add_handler(CallbackQueryHandler(self.transaksi_remove_item, pattern=r"^remove_item_\d+$"))
        
        # Other callbacks
        self.application.add_handler(CallbackQueryHandler(self.callback_main_menu, pattern="^main_menu$"))
        self.application.add_handler(CallbackQueryHandler(self.lihat_stok, pattern="^lihat_stok$"))
        self.application.add_handler(CallbackQueryHandler(self.lihat_laporan, pattern="^lihat_laporan$"))
        self.application.add_handler(CallbackQueryHandler(self.lihat_dashboard, pattern="^lihat_dashboard$"))
        
        logger.info("[+] All handlers registered")
    
    # ========================================================================
    # AUTHORIZATION & UTILITY
    # ========================================================================
    
    async def check_auth(self, chat_id: int) -> bool:
        """Cek authorization user."""
        return self.config_manager.is_authorized(chat_id)
    
    def get_user_transaction(self, user_id: int) -> TransactionHandler:
        """Get atau create transaction handler untuk user."""
        if user_id not in self.transaction_handlers:
            self.transaction_handlers[user_id] = TransactionHandler(self.db)
        return self.transaction_handlers[user_id]
    
    def get_products_cached(self) -> List[Dict]:
        """
        Get all products with caching. Cache expired setelah 10 detik.
        Mengurangi database queries yang berlebihan.
        """
        current_time = time.time()
        
        # Return cache jika masih valid
        if self._products_cache is not None and (current_time - self._cache_timestamp) < self._cache_ttl:
            return self._products_cache
        
        # Fetch dari database dan cache hasilnya
        self._products_cache = self.db.get_all_products()
        self._cache_timestamp = current_time
        
        logger.debug(f"[*] Product cache refreshed - {len(self._products_cache)} items")
        return self._products_cache
    
    def invalidate_products_cache(self):
        """Invalidate product cache saat ada perubahan produk."""
        self._products_cache = None
        self._cache_timestamp = 0
        logger.debug("[*] Product cache invalidated")
    
    # ========================================================================
    # MAIN MENU & START
    # ========================================================================
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /start command - Welcome & show main menu.
        """
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        logger.info(f"[>] /start command from user: {user.first_name} (ID: {chat_id})")
        
        welcome_msg = (
            f"👋 Selamat datang di *TOKO ACCESSORIES G-LIES POS*! 🛍️\n\n"
            f"Nama: {user.first_name}\n"
            f"Chat ID: `{chat_id}`\n\n"
            f"Gunakan menu di bawah untuk memulai transaksi atau akses fitur lainnya."
        )
        
        # Auto-add admin
        admin_id = self.config_manager.config.get("admin_chat_id")
        if chat_id == admin_id:
            self.config_manager.add_allowed_chat(chat_id)
            welcome_msg += "\n\n✅ Anda adalah admin, akses diberikan!"
        
        keyboard = await self.get_main_menu_keyboard()
        
        try:
            await update.message.reply_text(
                welcome_msg,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            logger.info(f"[+] Welcome message sent to {user.first_name}")
        except Exception as e:
            logger.error(f"[-] Error in cmd_start: {e}", exc_info=True)
    
    async def cmd_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /menu command - Show main menu.
        """
        chat_id = update.effective_chat.id
        logger.info(f"[>] /menu command from chat_id: {chat_id}")
        
        keyboard = await self.get_main_menu_keyboard()
        
        try:
            await update.message.reply_text(
                "📋 *MENU UTAMA*\n\nPilih salah satu opsi di bawah:",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"[-] Error in cmd_menu: {e}", exc_info=True)
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /help command - Show available commands.
        """
        help_text = (
            "*BANTUAN - POS TELEGRAM BOT*\n\n"
            "*Commands:*\n"
            "/start - Mulai & tampilkan menu\n"
            "/menu - Tampilkan menu utama\n"
            "/help - Tampilkan bantuan ini\n\n"
            "*Fitur Utama:*\n"
            "🛒 *Transaksi Penjualan*\n"
            "  - Tambah item ke keranjang\n"
            "  - Lihat detail item\n"
            "  - Hapus item\n"
            "  - Checkout & pembayaran\n\n"
            "📦 *Manajemen Stok*\n"
            "  - Lihat daftar produk\n"
            "  - Cek ketersediaan stok\n\n"
            "📊 *Laporan*\n"
            "  - Laporan penjualan harian\n"
            "  - Dashboard ringkasan\n\n"
            "*Tips:*\n"
            "• Gunakan menu tombol untuk navigasi mudah\n"
            "• Setiap transaksi menghasilkan receipt otomatis\n"
            "• Data real-time dari database\n"
        )
        
        try:
            await update.message.reply_text(help_text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"[-] Error in cmd_help: {e}", exc_info=True)
    
    # ========================================================================
    # MAIN MENU KEYBOARD
    # ========================================================================
    
    async def get_main_menu_keyboard(self) -> InlineKeyboardMarkup:
        """Generate main menu keyboard."""
        keyboard = [
            [InlineKeyboardButton("🛒 Transaksi Penjualan", callback_data="transaksi")],
            [InlineKeyboardButton("📦 Lihat Stok", callback_data="lihat_stok")],
            [InlineKeyboardButton("⚙️  Kelola Produk", callback_data="kelola_produk")],
            [InlineKeyboardButton("📊 Laporan Harian", callback_data="lihat_laporan")],
            [InlineKeyboardButton("📈 Dashboard", callback_data="lihat_dashboard")],
        ]
        return InlineKeyboardMarkup(keyboard)
    
    async def callback_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Callback untuk kembali ke main menu."""
        query = update.callback_query
        await query.answer()
        
        keyboard = await self.get_main_menu_keyboard()
        
        try:
            await query.edit_message_text(
                text="📋 *MENU UTAMA*\n\nPilih salah satu opsi:",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"[-] Error in callback_main_menu: {e}", exc_info=True)
    
    # ========================================================================
    # TRANSACTION HANDLERS
    # ========================================================================
    
    async def transaksi_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Start transaksi - tampilkan transaksi menu."""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        logger.info(f"[>] Transaksi started for user_id: {user_id}")
        
        # Create/reset transaction untuk user
        trans_handler = self.get_user_transaction(user_id)
        trans_handler.start_transaction()
        
        await self.show_transaksi_menu(update, context)
        return TRANSAKSI_MENU
    
    async def show_transaksi_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Tampilkan transaksi menu dengan status."""
        query = update.callback_query
        user_id = update.effective_user.id
        
        trans_handler = self.get_user_transaction(user_id)
        summary = trans_handler.get_transaction_summary()
        
        # Build status message
        if summary and summary['items_count'] > 0:
            msg = (
                f"🛒 *TRANSAKSI PENJUALAN*\n\n"
                f"📊 Status Saat Ini:\n"
                f"  Item: {summary['items_count']} item ({summary['qty_total']} qty)\n"
                f"  Total: {format_rp(summary['total'])}\n\n"
                f"📋 Detail Items:\n"
            )
            
            items = trans_handler.get_items()
            if items:
                for idx, item in enumerate(items, 1):
                    msg += f"{idx}. {item['nama']} x{item['qty']} = {format_rp(item['subtotal'])}\n"
            
            msg += f"\n---------\nTotal: {format_rp(summary['total'])}\n"
        else:
            msg = (
                f"🛒 *TRANSAKSI PENJUALAN*\n\n"
                f"Keranjang kosong. Tambahkan item untuk memulai."
            )
        
        keyboard = [
            [InlineKeyboardButton("➕ Tambah Item", callback_data="tambah_item")],
            [InlineKeyboardButton("📋 Lihat Item", callback_data="lihat_item")],
            [InlineKeyboardButton("🗑️  Hapus Item", callback_data="hapus_item")],
            [InlineKeyboardButton("💳 Checkout", callback_data="checkout")],
            [InlineKeyboardButton("❌ Batalkan", callback_data="cancel_transaksi")],
            [InlineKeyboardButton("⬅️  Kembali ke Menu Utama", callback_data="main_menu")],
        ]
        
        try:
            await query.edit_message_text(
                text=msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"[-] Error in show_transaksi_menu: {e}", exc_info=True)
    
    async def transaksi_tambah_item(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle tambah item - minta input nama produk untuk pencarian."""
        query = update.callback_query
        await query.answer()
        
        # Clear previous search state
        context.user_data.pop('search_results', None)
        context.user_data.pop('current_product', None)
        
        try:
            await query.edit_message_text(
                text=(
                    "📝 *TAMBAH ITEM*\n\n"
                    "Silakan ketik *Nama Produk* atau clue pencarian\n"
                    "(contoh: COF, coff, tea, 001)\n\n"
                    "Sistem akan mencari produk yang sesuai.\n\n"
                    "Kirim /cancel untuk batalkan."
                ),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"[-] Error in transaksi_tambah_item: {e}", exc_info=True)
        
        return TAMBAH_ITEM_KODE
    
    async def handle_item_kode(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle product search by name or code."""
        search_term = update.message.text.strip()
        user_id = update.effective_user.id
        
        logger.info(f"Product search input: {search_term} from user_id: {user_id}")
        
        # Get all products and search by name or code
        all_products = self.get_products_cached()
        search_term_upper = search_term.upper()
        
        # Search results: match by nama (partial) or kode (exact or partial)
        matching_products = []
        for product in all_products:
            # Check if product name contains search term (case-insensitive)
            if search_term_upper in product['nama'].upper():
                if product['stok'] > 0:
                    matching_products.append(product)
            # Also check by kode (exact match for consistency)
            elif product['kode'].upper() == search_term_upper:
                if product['stok'] > 0:
                    matching_products.append(product)
        
        # No matches found
        if not matching_products:
            await update.message.reply_text(
                f"❌ Produk dengan nama/kode *{search_term}* tidak ditemukan!\n\n"
                f"Silakan coba pencarian lain atau ketik /cancel untuk batalkan.",
                parse_mode="Markdown"
            )
            return TAMBAH_ITEM_KODE
        
        # Only 1 match found - proceed directly to quantity input
        if len(matching_products) == 1:
            product = matching_products[0]
            context.user_data['current_product'] = product
            
            msg = (
                f"✅ *Produk Ditemukan!*\n\n"
                f"📦 Nama: {product['nama']}\n"
                f"💰 Harga: {format_rp(product['harga'])}\n"
                f"📊 Stok: {product['stok']} pcs\n\n"
                f"Berapa banyak yang akan dibeli? (1-{product['stok']})\n\n"
                f"Ketik angka atau /cancel untuk batalkan."
            )
            
            await update.message.reply_text(msg, parse_mode="Markdown")
            return TAMBAH_ITEM_QTY
        
        # Multiple matches found - show selection inline keyboard
        msg = f"🔍 *HASIL PENCARIAN: {len(matching_products)} produk ditemukan*\n\n"
        msg += "Pilih produk yang Anda maksud:\n\n"
        
        keyboard = []
        for idx, product in enumerate(matching_products, 1):
            btn_text = f"{idx}. {product['nama']} - {format_rp(product['harga'])} (Stok: {product['stok']})"
            keyboard.append([
                InlineKeyboardButton(
                    btn_text,
                    callback_data=f"select_product_{idx-1}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("❌ Batalkan", callback_data="cancel_search")])
        
        # Store search results in context for callback handler
        context.user_data['search_results'] = matching_products
        context.user_data['search_term'] = search_term
        
        try:
            await update.message.reply_text(
                msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"[-] Error showing search results: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ Terjadi kesalahan saat menampilkan hasil. Silakan coba lagi.",
                parse_mode="Markdown"
            )
        
        # Stay in TAMBAH_ITEM_KODE state waiting for callback selection
        return TAMBAH_ITEM_KODE
    
    async def handle_product_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle product selection from search results (inline button callback)."""
        query = update.callback_query
        user_id = update.effective_user.id
        
        logger.info(f"Product selection callback: {query.data} from user_id: {user_id}")
        
        try:
            await query.answer()
            
            # Handle cancel search
            if query.data == "cancel_search":
                # Clear search results and go back to transaksi menu
                context.user_data.pop('search_results', None)
                context.user_data.pop('current_product', None)
                await self.show_transaksi_menu(update, context)
                return TRANSAKSI_MENU
            
            # Extract product index from callback_data
            product_idx = int(query.data.split("_")[-1])
            
            # Get search results from context
            search_results = context.user_data.get('search_results', [])
            
            if product_idx >= len(search_results):
                await query.answer("❌ Produk tidak ditemukan!", show_alert=True)
                return TAMBAH_ITEM_KODE
            
            # Get selected product
            selected_product = search_results[product_idx]
            context.user_data['current_product'] = selected_product
            
            # Show product details and ask for quantity
            msg = (
                f"✅ *Produk Dipilih!*\n\n"
                f"📦 Nama: {selected_product['nama']}\n"
                f"💰 Harga: {format_rp(selected_product['harga'])}\n"
                f"📊 Stok: {selected_product['stok']} pcs\n\n"
                f"Berapa banyak yang akan dibeli? (1-{selected_product['stok']})\n\n"
                f"Ketik angka atau /cancel untuk batalkan."
            )
            
            # Replace the inline keyboard message with quantity request
            await query.edit_message_text(msg, parse_mode="Markdown")
            
            logger.info(f"[+] Product selected: {selected_product['nama']} for user_id: {user_id}")
            
            # Transition to quantity input state
            return TAMBAH_ITEM_QTY
            
        except Exception as e:
            logger.error(f"[-] Error in handle_product_selection: {e}", exc_info=True)
            await query.answer("❌ Terjadi kesalahan!", show_alert=True)
            return TAMBAH_ITEM_KODE
    
    async def handle_item_qty(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle quantity input."""
        try:
            qty = int(update.message.text.strip())
        except ValueError:
            await update.message.reply_text(
                "❌ Masukkan angka yang valid!\n\nSilakan coba lagi.",
                parse_mode="Markdown"
            )
            return TAMBAH_ITEM_QTY
        
        user_id = update.effective_user.id
        product = context.user_data.get('current_product')
        
        # Validate qty
        if qty < 1:
            await update.message.reply_text(
                "❌ Jumlah minimal 1 pcs!\n\nSilakan coba lagi.",
                parse_mode="Markdown"
            )
            return TAMBAH_ITEM_QTY
        
        if qty > product['stok']:
            await update.message.reply_text(
                f"❌ Stok hanya tersedia {product['stok']} pcs!\n\n"
                f"Silakan masukkan jumlah yang lebih kecil.",
                parse_mode="Markdown"
            )
            return TAMBAH_ITEM_QTY
        
        # Add item ke transaksi
        trans_handler = self.get_user_transaction(user_id)
        trans_handler.add_item(product['kode'], qty)
        
        subtotal = product['harga'] * qty
        
        msg = (
            f"✅ *Item Berhasil Ditambahkan!*\n\n"
            f"📦 {product['nama']}\n"
            f"Qty: {qty} pcs\n"
            f"Harga: {format_rp(product['harga'])} x {qty}\n"
            f"Subtotal: {format_rp(subtotal)}\n\n"
            f"Lanjutkan belanja? Pilih opsi di bawah 👇"
        )
        
        keyboard = [
            [InlineKeyboardButton("➕ Tambah Item Lagi", callback_data="tambah_item")],
            [InlineKeyboardButton("💳 Checkout", callback_data="checkout")],
            [InlineKeyboardButton("📋 Lihat Item", callback_data="lihat_item")],
            [InlineKeyboardButton("🛒 Kembali ke Transaksi", callback_data="transaksi")],
        ]
        
        await update.message.reply_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        
        logger.info(f"[+] Item added: {product['kode']} qty: {qty} for user_id: {user_id}")
        
        return TRANSAKSI_MENU
    
    async def handle_diskon(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle diskon input."""
        user_id = update.effective_user.id
        
        try:
            diskon_input = update.message.text.strip()
            diskon_percent = float(diskon_input)
        except ValueError:
            await update.message.reply_text(
                "❌ Masukkan angka yang valid (0-100)!\n\n"
                "Silakan coba lagi atau ketik /cancel untuk batalkan.",
                parse_mode="Markdown"
            )
            return DISKON
        
        # Validate diskon
        if diskon_percent < 0 or diskon_percent > 100:
            await update.message.reply_text(
                "❌ Diskon harus antara 0-100%!\n\n"
                "Silakan coba lagi atau ketik /cancel untuk batalkan.",
                parse_mode="Markdown"
            )
            return DISKON
        
        # Store diskon in context and get updated summary
        context.user_data['diskon_percent'] = diskon_percent
        trans_handler = self.get_user_transaction(user_id)
        
        # Set discount on transaction
        trans = trans_handler.transaction_service.get_current_transaction()
        if trans:
            trans.set_discount(diskon_percent)
            summary = trans_handler.get_transaction_summary()
            context.user_data['transaction_summary'] = summary
            
            logger.info(f"Discount applied: {diskon_percent}% (Rp{trans.discount_amount:,}) for user_id: {user_id}")
        
        # Ask for pajak
        summary = context.user_data.get('transaction_summary', {})
        subtotal = summary.get('total', 0)
        diskon_amount = 0
        
        if trans:
            subtotal = trans.subtotal
            diskon_amount = trans.discount_amount
        
        msg = (
            f"🏷️  *DISKON DITERAPKAN*\n"
            f"Diskon: {diskon_percent}%\n"
            f"Potongan: {format_rp(diskon_amount)}\n\n"
            f"💰 *MASUKKAN PAJAK (%)*\n"
            f"(Ketik angka 0-100 atau 0 untuk tanpa pajak)\n\n"
            f"Contoh: 10 (untuk pajak 10% PPN)"
        )
        
        await update.message.reply_text(msg, parse_mode="Markdown")
        return PAJAK
    
    async def handle_pajak(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle pajak input."""
        user_id = update.effective_user.id
        
        try:
            pajak_input = update.message.text.strip()
            pajak_percent = float(pajak_input)
        except ValueError:
            await update.message.reply_text(
                "❌ Masukkan angka yang valid (0-100)!\n\n"
                "Silakan coba lagi atau ketik /cancel untuk batalkan.",
                parse_mode="Markdown"
            )
            return PAJAK
        
        # Validate pajak
        if pajak_percent < 0 or pajak_percent > 100:
            await update.message.reply_text(
                "❌ Pajak harus antara 0-100%!\n\n"
                "Silakan coba lagi atau ketik /cancel untuk batalkan.",
                parse_mode="Markdown"
            )
            return PAJAK
        
        # Store pajak in context
        context.user_data['pajak_percent'] = pajak_percent
        trans_handler = self.get_user_transaction(user_id)
        
        # Set tax on transaction
        trans = trans_handler.transaction_service.get_current_transaction()
        if trans:
            trans.set_tax(pajak_percent)
            summary = trans_handler.get_transaction_summary()
            context.user_data['transaction_summary'] = summary
            
            logger.info(f"Tax applied: {pajak_percent}% (Rp{trans.tax_amount:,}) for user_id: {user_id}")
        
        # Show summary and ask for pembayaran
        diskon_percent = context.user_data.get('diskon_percent', 0)
        pajak_amount = 0
        diskon_amount = 0
        subtotal = 0
        total = 0
        
        if trans:
            subtotal = trans.subtotal
            diskon_amount = trans.discount_amount
            pajak_amount = trans.tax_amount
            total = trans.total
        
        msg = (
            f"📊 *RINGKASAN BELANJA*\n\n"
            f"Subtotal : {format_rp(subtotal)}\n"
            f"Diskon   : -{format_rp(diskon_amount)} ({diskon_percent}%)\n"
            f"Pajak    : +{format_rp(pajak_amount)} ({pajak_percent}%)\n"
            f"-" + "─" * 30 + "\n"
            f"💵 *TOTAL  : {format_rp(total)}*\n\n"
            f"💳 *MASUKKAN JUMLAH PEMBAYARAN*\n"
            f"(Ketik nominal atau ketik 0 untuk membatalkan)\n\n"
            f"Minimum pembayaran: {format_rp(total)}"
        )
        
        context.user_data['transaction_total'] = total
        
        await update.message.reply_text(msg, parse_mode="Markdown")
        return PEMBAYARAN
    
    async def transaksi_lihat_item(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Lihat detail items."""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        trans_handler = self.get_user_transaction(user_id)
        items = trans_handler.get_items()
        
        if not items:
            msg = "📋 Keranjang kosong. Tambahkan item terlebih dahulu."
        else:
            msg = "📋 *DETAIL ITEMS DALAM KERANJANG*\n\n"
            total = 0
            for idx, item in enumerate(items, 1):
                msg += f"{idx}. {item['nama']}\n"
                msg += f"   Qty: {item['qty']} pcs\n"
                msg += f"   Harga: {format_rp(item['harga_satuan'])}\n"
                msg += f"   Subtotal: {format_rp(item['subtotal'])}\n\n"
                total += item['subtotal']
            
            msg += f"---------\nTotal: {format_rp(total)}"
        
        keyboard = [[InlineKeyboardButton("⬅️  Kembali ke Transaksi", callback_data="back_menu")]]
        
        try:
            await query.edit_message_text(
                text=msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"[-] Error in transaksi_lihat_item: {e}", exc_info=True)
        
        return TRANSAKSI_MENU
    
    async def transaksi_hapus_item_btn(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Menu hapus item."""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        trans_handler = self.get_user_transaction(user_id)
        items = trans_handler.get_items()
        
        if not items:
            try:
                await query.edit_message_text(
                    text="📋 Keranjang kosong. Tidak ada item untuk dihapus.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️  Kembali ke Transaksi", callback_data="back_menu")]])
                )
            except:
                pass
            return TRANSAKSI_MENU
        
        msg = "🗑️  *HAPUS ITEM*\n\nPilih nomor item yang akan dihapus:\n\n"
        keyboard = []
        
        for idx, item in enumerate(items, 1):
            msg += f"{idx}. {item['nama']} x{item['qty']}\n"
            keyboard.append([InlineKeyboardButton(f"❌ Hapus Item {idx}", callback_data=f"remove_item_{idx-1}")])
        
        keyboard.append([InlineKeyboardButton("⬅️  Batal", callback_data="back_menu")])
        
        try:
            await query.edit_message_text(
                text=msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"[-] Error in transaksi_hapus_item_btn: {e}", exc_info=True)
        
        return TRANSAKSI_MENU
    
    async def transaksi_remove_item(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle hapus item."""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        trans_handler = self.get_user_transaction(user_id)
        
        # Extract item index dari callback_data
        item_idx = int(query.data.split("_")[-1])
        
        trans_handler.remove_item(item_idx)
        
        await update.callback_query.message.reply_text(
            "✅ Item berhasil dihapus!",
            parse_mode="Markdown"
        )
        
        # Show transaksi menu lagi
        await self.show_transaksi_menu(update, context)
        return TRANSAKSI_MENU
    
    async def transaksi_checkout(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle checkout & minta diskon."""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        trans_handler = self.get_user_transaction(user_id)
        items = trans_handler.get_items()
        
        # Validate ada items
        if not items:
            try:
                await query.answer("⚠️ Keranjang kosong!", show_alert=True)
            except:
                pass
            return TRANSAKSI_MENU
        
        summary = trans_handler.get_transaction_summary()
        
        msg = (
            f"💳 *KONFIRMASI CHECKOUT*\n\n"
            f"📊 Ringkasan:\n"
            f"  Total Item: {summary['items_count']}\n"
            f"  Total Qty: {summary['qty_total']}\n"
            f"  Subtotal: {format_rp(summary['total'])}\n\n"
            f"🏷️  *MASUKKAN DISKON (%)*\n"
            f"(Ketik angka 0-100 atau 0 untuk tanpa diskon)\n\n"
            f"Contoh: 10 (untuk diskon 10%)"
        )
        
        context.user_data['transaction_summary'] = summary
        
        try:
            await query.edit_message_text(text=msg, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"[-] Error in transaksi_checkout: {e}", exc_info=True)
        
        return DISKON
    
    async def handle_pembayaran(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle pembayaran input."""
        try:
            bayar = int(update.message.text.strip())
        except ValueError:
            await update.message.reply_text(
                "❌ Masukkan nominal yang valid!\n\nSilakan coba lagi.",
                parse_mode="Markdown"
            )
            return PEMBAYARAN
        
        total = context.user_data.get('transaction_total', 0)
        
        # Handle cancel
        if bayar == 0:
            await update.message.reply_text("❌ Pembayaran dibatalkan.")
            return ConversationHandler.END
        
        # Validate pembayaran
        if bayar < total:
            kurang = total - bayar
            await update.message.reply_text(
                f"❌ Uang Anda kurang {format_rp(kurang)}!\n\n"
                f"Silakan masukkan nominal yang lebih besar.",
                parse_mode="Markdown"
            )
            return PEMBAYARAN
        
        # Complete transaction
        user_id = update.effective_user.id
        trans_handler = self.get_user_transaction(user_id)
        
        trans_id = trans_handler.complete_transaction(
            bayar,
            store_name="TOKO ACCESSORIES G-LIES",
            store_address="Jl. Majalaya, Solokanjeruk, Bandung"
        )
        
        if trans_id:
            kembalian = bayar - total
            diskon_percent = context.user_data.get('diskon_percent', 0)
            pajak_percent = context.user_data.get('pajak_percent', 0)
            
            # Get transaction for detailed breakdown
            trans = trans_handler.transaction_service.get_current_transaction()
            subtotal = trans.subtotal if trans else 0
            diskon_amount = trans.discount_amount if trans else 0
            pajak_amount = trans.tax_amount if trans else 0
            
            msg = (
                f"✅ *TRANSAKSI BERHASIL*\n\n"
                f"📄 No. Invoice: {trans_id}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Subtotal     : {format_rp(subtotal)}\n"
            )
            
            if diskon_percent > 0:
                msg += f"Diskon {diskon_percent}%  : -{format_rp(diskon_amount)}\n"
            
            if pajak_percent > 0:
                msg += f"Pajak {pajak_percent}%   : +{format_rp(pajak_amount)}\n"
            
            msg += (
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💰 *Total    : {format_rp(total)}*\n"
                f"💵 Pembayaran: {format_rp(bayar)}\n"
                f"🔄 Kembalian : {format_rp(kembalian)}\n"
                f"⏰ Waktu     : {datetime.now().strftime('%H:%M:%S')}\n\n"
                f"Terima kasih telah berbelanja! 🙏"
            )
            
            keyboard = [[InlineKeyboardButton("🛒 Transaksi Baru", callback_data="transaksi")]]
            
            await update.message.reply_text(
                msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            
            logger.info(f"[+] Transaction completed: ID={trans_id}, subtotal={subtotal}, diskon={diskon_amount}, pajak={pajak_amount}, total={total}, payment={bayar}, user_id={user_id}")
            
            # Clear user transaction
            if user_id in self.transaction_handlers:
                del self.transaction_handlers[user_id]
        else:
            await update.message.reply_text(
                "❌ Error saat menyelesaikan transaksi. Silakan hubungi admin.",
                parse_mode="Markdown"
            )
        
        return ConversationHandler.END
    
    async def transaksi_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel transaksi."""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        
        if user_id in self.transaction_handlers:
            trans_handler = self.transaction_handlers[user_id]
            trans_handler.cancel_transaction()
            del self.transaction_handlers[user_id]
        
        try:
            await query.edit_message_text(
                text="❌ Transaksi dibatalkan.\n\nKembali ke menu utama.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📋 Menu Utama", callback_data="main_menu")]])
            )
        except Exception as e:
            logger.error(f"[-] Error in transaksi_cancel: {e}", exc_info=True)
        
        return ConversationHandler.END
    
    async def cmd_cancel_transaksi(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle /cancel command during transaksi conversation."""
        user_id = update.effective_user.id
        
        # Cancel transaction
        if user_id in self.transaction_handlers:
            trans_handler = self.transaction_handlers[user_id]
            trans_handler.cancel_transaction()
            del self.transaction_handlers[user_id]
        
        try:
            await update.message.reply_text(
                text="❌ Transaksi dibatalkan.\n\nKembali ke menu utama.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📋 Menu Utama", callback_data="main_menu")]])
            )
        except Exception as e:
            logger.error(f"[-] Error in cmd_cancel_transaksi: {e}", exc_info=True)
        
        return ConversationHandler.END
    
    async def transaksi_exit_to_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Exit transaksi conversation dan tampilkan main menu."""
        user_id = update.effective_user.id
        
        if user_id in self.transaction_handlers:
            del self.transaction_handlers[user_id]
        
        await self.callback_main_menu(update, context)
        return ConversationHandler.END
    
    async def transaksi_exit_to_kelola_produk(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Exit transaksi conversation dan tampilkan kelola produk menu."""
        user_id = update.effective_user.id
        
        if user_id in self.transaction_handlers:
            del self.transaction_handlers[user_id]
        
        await self.kelola_produk_menu(update, context)
        return ConversationHandler.END
    
    async def transaksi_exit_to_lihat_stok(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Exit transaksi conversation dan tampilkan lihat stok."""
        user_id = update.effective_user.id
        
        if user_id in self.transaction_handlers:
            del self.transaction_handlers[user_id]
        
        await self.lihat_stok(update, context)
        return ConversationHandler.END
    
    async def transaksi_exit_to_lihat_laporan(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Exit transaksi conversation dan tampilkan lihat laporan."""
        user_id = update.effective_user.id
        
        if user_id in self.transaction_handlers:
            del self.transaction_handlers[user_id]
        
        await self.lihat_laporan(update, context)
        return ConversationHandler.END
    
    async def transaksi_exit_to_lihat_dashboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Exit transaksi conversation dan tampilkan lihat dashboard."""
        user_id = update.effective_user.id
        
        if user_id in self.transaction_handlers:
            del self.transaction_handlers[user_id]
        
        await self.lihat_dashboard(update, context)
        return ConversationHandler.END
    
    async def transaksi_back_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Kembali ke transaksi menu."""
        await self.show_transaksi_menu(update, context)
        return TRANSAKSI_MENU
    
    # ========================================================================
    # STOK & LAPORAN
    # ========================================================================
    
    async def lihat_stok(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lihat daftar stok produk."""
        query = update.callback_query
        await query.answer("Mengambil data stok...")
        
        try:
            stok_list = self.get_products_cached()
            
            if not stok_list:
                msg = "Belum ada produk di database."
            else:
                msg = "*DAFTAR PRODUK & STOK*\n\n"
                
                ok_count = sum(1 for s in stok_list if s['stok'] > 20)
                low_count = sum(1 for s in stok_list if 0 < s['stok'] <= 20)
                empty_count = sum(1 for s in stok_list if s['stok'] == 0)
                
                msg += f"[OK]: {ok_count} | [MINIM]: {low_count} | [KOSONG]: {empty_count}\n\n"
                
                for prod in stok_list:
                    if prod['stok'] > 20:
                        icon = "[OK]"
                    elif prod['stok'] > 0:
                        icon = "[LOW]"
                    else:
                        icon = "[EMPTY]"
                    
                    msg += f"{icon} {prod['kode']}: {prod['nama']}\n"
                    msg += f"   Stok: {prod['stok']} pcs | Harga: {format_rp(prod['harga'])}\n"
                
                msg = msg[:3500]  # Telegram limit
            
            keyboard = [[InlineKeyboardButton("Kembali", callback_data="main_menu")]]
            
            await query.edit_message_text(
                text=msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            logger.info(f"[+] Stok list shown")
            
        except Exception as e:
            logger.error(f"[-] Error in lihat_stok: {e}", exc_info=True)
            await query.edit_message_text(f"Error: {e}")
    
    async def lihat_laporan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lihat laporan penjualan harian."""
        query = update.callback_query
        await query.answer("⏳ Mengambil laporan...")
        
        try:
            laporan = self.report_generator.get_laporan_harian()
            
            msg = (
                f"📊 *LAPORAN PENJUALAN HARIAN*\n"
                f"Tanggal: {laporan['tanggal']}\n\n"
                f"💰 Total Penjualan: {format_rp(laporan['total_penjualan'])}\n"
                f"📝 Total Transaksi: {laporan['total_transaksi']}\n"
                f"📈 Rata-rata: {format_rp(int(laporan['rata_rata_transaksi']))}\n"
                f"📦 Total Item: {laporan['total_item']}\n\n"
            )
            
            if laporan['produk_laris']:
                msg += "🏆 *TOP 10 PRODUK:*\n"
                for i, prod in enumerate(laporan['produk_laris'][:10], 1):
                    msg += f"{i}. {prod['nama']}: {prod['total_qty']} qty ({format_rp(prod['total_revenue'])})\n"
            
            keyboard = [[InlineKeyboardButton("⬅️  Kembali", callback_data="main_menu")]]
            
            await query.edit_message_text(
                text=msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            logger.info(f"[+] Laporan shown")
            
        except Exception as e:
            logger.error(f"[-] Error in lihat_laporan: {e}", exc_info=True)
            await query.edit_message_text(f"❌ Error: {e}")
    
    async def lihat_dashboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lihat dashboard ringkasan."""
        query = update.callback_query
        await query.answer("Mengambil dashboard...")
        
        try:
            laporan = self.report_generator.get_laporan_harian()
            stok_list = self.get_products_cached()
            
            total_stok = sum(s['stok'] for s in stok_list) if stok_list else 0
            low_stok = sum(1 for s in stok_list if 0 < s['stok'] <= 20) if stok_list else 0
            empty_stok = sum(1 for s in stok_list if s['stok'] == 0) if stok_list else 0
            
            msg = (
                f"*DASHBOARD RINGKASAN*\n\n"
                f"*PENJUALAN HARI INI*\n"
                f"  Total: {format_rp(laporan['total_penjualan'])}\n"
                f"  Transaksi: {laporan['total_transaksi']}\n"
                f"  Item Terjual: {laporan['total_item']}\n\n"
                f"*INVENTORY*\n"
                f"  Total Produk: {len(stok_list)}\n"
                f"  Total Stok: {total_stok} pcs\n"
                f"  Stok Minim: {low_stok} produk [LOW]\n"
                f"  Stok Kosong: {empty_stok} produk [EMPTY]\n\n"
                f"*PRODUK TERLARIS*\n"
            )
            
            if laporan['produk_laris']:
                for i, prod in enumerate(laporan['produk_laris'][:3], 1):
                    msg += f"{i}. {prod['nama']} ({prod['total_qty']} pcs)\n"
            
            keyboard = [[InlineKeyboardButton("Kembali", callback_data="main_menu")]]
            
            await query.edit_message_text(
                text=msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            logger.info(f"[+] Dashboard shown")
            
        except Exception as e:
            logger.error(f"[-] Error in lihat_dashboard: {e}", exc_info=True)
            await query.edit_message_text(f"Error: {e}")
    
    # ========================================================================
    # KELOLA PRODUK (Product Management)
    # ========================================================================
    
    async def cmd_cancel_kelola_produk(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel kelola produk operations and return to menu."""
        await update.message.reply_text(
            "[CANCELLED] Kembali ke menu Kelola Produk.",
            parse_mode="Markdown"
        )
        logger.info("[>] Kelola produk operation cancelled")
        return KELOLA_PRODUK_MENU
    
    async def kelola_produk_exit_to_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Exit kelola produk conversation dan tampilkan main menu."""
        await self.callback_main_menu(update, context)
        return ConversationHandler.END
    
    async def kelola_produk_exit_to_transaksi(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Exit kelola produk conversation dan tampilkan transaksi menu."""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        trans_handler = self.get_user_transaction(user_id)
        trans_handler.start_transaction()
        
        await self.show_transaksi_menu(update, context)
        return ConversationHandler.END
    
    async def kelola_produk_exit_to_lihat_stok(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Exit kelola produk conversation dan tampilkan lihat stok."""
        await self.lihat_stok(update, context)
        return ConversationHandler.END
    
    async def kelola_produk_exit_to_lihat_laporan(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Exit kelola produk conversation dan tampilkan lihat laporan."""
        await self.lihat_laporan(update, context)
        return ConversationHandler.END
    
    async def kelola_produk_exit_to_lihat_dashboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Exit kelola produk conversation dan tampilkan lihat dashboard."""
        await self.lihat_dashboard(update, context)
        return ConversationHandler.END
    
    async def kelola_produk_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Tampilkan menu kelola produk lengkap."""
        # Handle both callback_query dan regular entry
        if update.callback_query:
            query = update.callback_query
            await query.answer()
        
        msg = (
            "*KELOLA PRODUK TOKO ACCESSORIES G-LIES*\n\n"
            "Pilih menu untuk mengelola produk di database:\n\n"
            "[1] *Tambah Produk* - Menambahkan produk baru\n"
            "[2] *Lihat Daftar* - Melihat semua produk\n"
            "[3] *Edit Produk* - Mengubah data produk\n"
            "[4] *Hapus Produk* - Menghapus produk\n"
            "[5] *Info Stok* - Ringkasan stok produk\n"
            "[0] *Kembali* - Kembali ke menu utama"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("[1] Tambah", callback_data="kp_tambah"),
                InlineKeyboardButton("[2] Lihat", callback_data="kp_lihat"),
            ],
            [
                InlineKeyboardButton("[3] Edit", callback_data="kp_edit_select"),
                InlineKeyboardButton("[4] Hapus", callback_data="kp_hapus_select"),
            ],
            [InlineKeyboardButton("[5] Info Stok", callback_data="kp_info_stok")],
            [InlineKeyboardButton("[0] Kembali", callback_data="main_menu")],
        ]
        
        try:
            if update.callback_query:
                await query.edit_message_text(
                    text=msg,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text(
                    msg,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown"
                )
            logger.info(f"[+] Product management menu shown")
        except Exception as e:
            logger.error(f"[-] Error in kelola_produk_menu: {e}", exc_info=True)
        
        return KELOLA_PRODUK_MENU
    
    async def kelola_produk_edit_select(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Tampilkan daftar produk untuk dipilih untuk diedit."""
        query = update.callback_query
        await query.answer("Memilih produk untuk diedit...")
        
        try:
            products = self.get_products_cached()
            
            if not products:
                keyboard = [[InlineKeyboardButton("Kembali", callback_data="kembali_kp")]]
                await query.edit_message_text(
                    text="[INFO] Belum ada produk di database.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return KELOLA_PRODUK_MENU
            
            msg = "*PILIH PRODUK UNTUK DIEDIT*\n\n"
            msg += f"Total: {len(products)} produk\n\n"
            msg += "Klik tombol produk yang akan diedit:\n\n"
            
            keyboard = []
            for idx, prod in enumerate(products):
                stock_status = "[OK]" if prod['stok'] > 20 else "[LOW]" if prod['stok'] > 0 else "[EMPTY]"
                button_text = f"{prod['kode']} - {prod['nama']} ({stock_status})"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"kp_edit_{idx}")])
            
            keyboard.append([InlineKeyboardButton("Kembali ke Menu", callback_data="kembali_kp")])
            
            context.user_data['products_list'] = products
            
            await query.edit_message_text(
                text=msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            logger.info(f"[+] Edit product selection shown")
            
        except Exception as e:
            logger.error(f"[-] Error in kelola_produk_edit_select: {e}", exc_info=True)
            await query.edit_message_text(f"Error: {e}")
        
        return KELOLA_PRODUK_LIHAT
    
    async def kelola_produk_hapus_select(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Tampilkan daftar produk untuk dipilih untuk dihapus."""
        query = update.callback_query
        await query.answer("Memilih produk untuk dihapus...")
        
        try:
            products = self.get_products_cached()
            
            if not products:
                keyboard = [[InlineKeyboardButton("Kembali", callback_data="kembali_kp")]]
                await query.edit_message_text(
                    text="[INFO] Belum ada produk di database.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return KELOLA_PRODUK_MENU
            
            msg = "*PILIH PRODUK UNTUK DIHAPUS*\n\n"
            msg += f"Total: {len(products)} produk\n\n"
            msg += "[PERINGATAN] Tindakan ini TIDAK dapat dibatalkan!\n\n"
            msg += "Klik tombol produk yang akan dihapus:\n\n"
            
            keyboard = []
            for idx, prod in enumerate(products):
                stock_status = "[OK]" if prod['stok'] > 20 else "[LOW]" if prod['stok'] > 0 else "[EMPTY]"
                button_text = f"{prod['kode']} - {prod['nama']} ({stock_status})"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"kp_hapus_{idx}")])
            
            keyboard.append([InlineKeyboardButton("Kembali ke Menu", callback_data="kembali_kp")])
            
            context.user_data['products_list'] = products
            
            await query.edit_message_text(
                text=msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            logger.info(f"[+] Delete product selection shown")
            
        except Exception as e:
            logger.error(f"[-] Error in kelola_produk_hapus_select: {e}", exc_info=True)
            await query.edit_message_text(f"Error: {e}")
        
        return KELOLA_PRODUK_LIHAT
    
    async def kelola_produk_info_stok(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Tampilkan info stok ringkasan."""
        query = update.callback_query
        await query.answer("Mengambil info stok...")
        
        try:
            products = self.get_products_cached()
            
            if not products:
                keyboard = [[InlineKeyboardButton("Kembali", callback_data="kembali_kp")]]
                await query.edit_message_text(
                    text="[INFO] Belum ada produk di database.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return KELOLA_PRODUK_MENU
            
            # Calculate stock statistics
            total_produk = len(products)
            total_stok = sum(p['stok'] for p in products)
            ok_count = sum(1 for p in products if p['stok'] > 20)
            low_count = sum(1 for p in products if 0 < p['stok'] <= 20)
            empty_count = sum(1 for p in products if p['stok'] == 0)
            
            # Calculate stock value
            total_nilai = sum(p['stok'] * p['harga'] for p in products)
            
            msg = (
                "*INFO STOK TOKO ACCESSORIES G-LIES*\n\n"
                "*RINGKASAN UMUM*\n"
                f"Total Produk: {total_produk} item\n"
                f"Total Stok: {total_stok} pcs\n"
                f"Total Nilai Stok: {format_rp(total_nilai)}\n\n"
                f"*STATUS STOK*\n"
                f"OK (>20): {ok_count} produk\n"
                f"LOW (1-20): {low_count} produk\n"
                f"EMPTY (0): {empty_count} produk\n\n"
            )
            
            # Show top 5 best selling products by stock (highest quantity)
            sorted_products = sorted(products, key=lambda x: x['stok'], reverse=True)[:5]
            
            if sorted_products:
                msg += "*PRODUK STOK TERBANYAK*\n"
                for idx, prod in enumerate(sorted_products, 1):
                    msg += f"{idx}. {prod['nama']}\n"
                    msg += f"   Stok: {prod['stok']} pcs | Nilai: {format_rp(prod['stok'] * prod['harga'])}\n"
            
            keyboard = [
                [InlineKeyboardButton("Lihat Detail", callback_data="kp_lihat")],
                [InlineKeyboardButton("Kembali ke Menu", callback_data="kembali_kp")],
            ]
            
            await query.edit_message_text(
                text=msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            logger.info(f"[+] Stock info shown")
            
        except Exception as e:
            logger.error(f"[-] Error in kelola_produk_info_stok: {e}", exc_info=True)
            await query.edit_message_text(f"Error: {e}")
        
        return KELOLA_PRODUK_MENU
    
    async def kelola_produk_lihat(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Lihat semua produk dengan opsi edit/hapus."""
        query = update.callback_query
        await query.answer("Mengambil daftar produk...")
        
        try:
            products = self.get_products_cached()
            
            if not products:
                keyboard = [[InlineKeyboardButton("[KEMBALI]", callback_data="kembali_kp")]]
                await query.edit_message_text(
                    text="[INFO] Belum ada produk di database.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return KELOLA_PRODUK_LIHAT
            
            # Build product list message
            msg = "*DAFTAR PRODUK*\n\n"
            msg += f"Total: {len(products)} produk\n\n"
            
            # Show first 5 products in message, rest handled by buttons
            for prod in products[:5]:
                stock_status = "[OK]" if prod['stok'] > 20 else "[LOW]" if prod['stok'] > 0 else "[EMPTY]"
                msg += f"[PROD] *{prod['kode']}* - {prod['nama']}\n"
                msg += f"   Harga: {format_rp(prod['harga'])} | Stok: {prod['stok']} {stock_status}\n"
            
            if len(products) > 5:
                msg += f"\n... dan {len(products) - 5} produk lainnya\n\n"
            
            msg += "\nPilih produk untuk diedit atau dihapus:"
            
            # Build buttons for each product
            keyboard = []
            for idx, prod in enumerate(products):
                keyboard.append([
                    InlineKeyboardButton(f"EDIT: {prod['kode']}", callback_data=f"kp_edit_{idx}"),
                    InlineKeyboardButton(f"HAPUS: {prod['nama']}", callback_data=f"kp_hapus_{idx}"),
                ])
            
            keyboard.append([InlineKeyboardButton("Kembali ke Menu", callback_data="kembali_kp")])
            
            # Store products in context for later use
            context.user_data['products_list'] = products
            
            await query.edit_message_text(
                text=msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            logger.info(f"[+] Product list shown with {len(products)} items")
            
        except Exception as e:
            logger.error(f"[-] Error in kelola_produk_lihat: {e}", exc_info=True)
            await query.edit_message_text(f"Error: {e}")
        
        return KELOLA_PRODUK_LIHAT
    
    async def kelola_produk_tambah_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Mulai proses tambah produk - auto-generate kode, lalu minta nama."""
        query = update.callback_query
        await query.answer()
        
        try:
            logger.info(f"[>] kelola_produk_tambah_start triggered")
            
            # Clear any existing product data
            context.user_data.pop('new_product', None)
            
            # Auto-generate next product code
            next_kode = self.db.get_next_product_code()
            
            # Store in context
            context.user_data['new_product'] = {'kode': next_kode}
            
            # Show generated code and ask for nama (skip manual kode input)
            await query.edit_message_text(
                text=(
                    "*TAMBAH PRODUK BARU*\n\n"
                    "Step 1/3: Masukkan *Nama Produk*\n\n"
                    f"🔢 Kode Otomatis: `{next_kode}`\n\n"
                    "Kirim /cancel untuk batalkan."
                ),
                parse_mode="Markdown"
            )
            
            logger.info(f"[+] Product add started with auto-generated code: {next_kode}")
            
            # Skip KODE state and go directly to NAMA state
            return KELOLA_PRODUK_TAMBAH_NAMA
            
        except Exception as e:
            logger.error(f"[-] Error in kelola_produk_tambah_start: {e}", exc_info=True)
            try:
                await query.edit_message_text(
                    text="❌ Error saat generate kode produk. Silakan coba lagi.",
                    parse_mode="Markdown"
                )
            except:
                pass
            return KELOLA_PRODUK_MENU
    
    async def handle_kp_kode(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle kode produk input."""
        kode = update.message.text.strip().upper()
        
        # Check if kode already exists
        existing = self.db.get_product_by_kode(kode)
        if existing:
            await update.message.reply_text(
                f"[WARNING] Kode *{kode}* sudah terdaftar!\n"
                f"Gunakan kode lain atau gunakan fitur Edit.",
                parse_mode="Markdown"
            )
            return KELOLA_PRODUK_TAMBAH_KODE
        
        context.user_data['new_product']['kode'] = kode
        
        # Ask for nama
        await update.message.reply_text(
            text=(
                "*TAMBAH PRODUK BARU*\n\n"
                f"Step 2/4: Masukkan *Nama Produk*\n\n"
                f"Kode: {kode}\n\n"
                "Kirim /cancel untuk batalkan."
            ),
            parse_mode="Markdown"
        )
        
        return KELOLA_PRODUK_TAMBAH_NAMA
    
    async def handle_kp_nama(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle nama produk input."""
        nama = update.message.text.strip()
        
        context.user_data['new_product']['nama'] = nama
        
        # Ask for harga (now Step 2 instead of Step 3)
        await update.message.reply_text(
            text=(
                "*TAMBAH PRODUK BARU*\n\n"
                f"Step 2/3: Masukkan *Harga Produk* (angka saja)\n\n"
                f"🔢 Kode: `{context.user_data['new_product']['kode']}`\n"
                f"📝 Nama: {nama}\n\n"
                "Contoh: 50000, 100000\n"
                "Kirim /cancel untuk batalkan."
            ),
            parse_mode="Markdown"
        )
        
        return KELOLA_PRODUK_TAMBAH_HARGA
    
    async def handle_kp_harga(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle harga produk input."""
        try:
            harga = int(update.message.text.strip())
            if harga < 0:
                raise ValueError()
        except ValueError:
            await update.message.reply_text(
                "[ERROR] Masukkan harga dalam angka yang valid (minimal 0)!",
                parse_mode="Markdown"
            )
            return KELOLA_PRODUK_TAMBAH_HARGA
        
        context.user_data['new_product']['harga'] = harga
        
        # Ask for stok (now Step 3 instead of Step 4)
        await update.message.reply_text(
            text=(
                "*TAMBAH PRODUK BARU*\n\n"
                f"Step 3/3: Masukkan *Stok Awal* (angka saja)\n\n"
                f"🔢 Kode: `{context.user_data['new_product']['kode']}`\n"
                f"📝 Nama: {context.user_data['new_product']['nama']}\n"
                f"💰 Harga: {format_rp(harga)}\n\n"
                "Kirim /cancel untuk batalkan."
            ),
            parse_mode="Markdown"
        )
        
        return KELOLA_PRODUK_TAMBAH_STOK
    
    async def handle_kp_stok(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle stok input dan lanjut ke foto input."""
        try:
            stok = int(update.message.text.strip())
            if stok < 0:
                raise ValueError()
        except ValueError:
            await update.message.reply_text(
                "[ERROR] Masukkan stok dalam angka yang valid (minimal 0)!",
                parse_mode="Markdown"
            )
            return KELOLA_PRODUK_TAMBAH_STOK
        
        # Simpan stok ke context dan lanjut ke foto input
        prod_data = context.user_data.get('new_product', {})
        prod_data['stok'] = stok
        context.user_data['new_product'] = prod_data
        
        # Tampilkan menu foto
        keyboard = [
            [InlineKeyboardButton("📷 Upload Foto", callback_data="kp_upload_foto")],
            [InlineKeyboardButton("⏭️  Skip (Tidak Ada Foto)", callback_data="kp_skip_foto")],
        ]
        
        await update.message.reply_text(
            "📸 *TAMBAHKAN FOTO PRODUK?*\n\n"
            "Foto produk adalah optional (tidak wajib).\n"
            "Anda bisa upload foto atau langsung skip.\n\n"
            "Pilih opsi di bawah:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        
        return KELOLA_PRODUK_TAMBAH_FOTO
    
    async def handle_kp_upload_foto_btn(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle klik tombol upload foto."""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            text=(
                "📸 *UPLOAD FOTO PRODUK*\n\n"
                "Silakan kirim foto produk Anda.\n"
                "File harus berformat: JPG, PNG, atau JPEG\n\n"
                "Atau ketik '/cancel' atau tombol skip untuk melewati."
            ),
            parse_mode="Markdown"
        )
        
        return KELOLA_PRODUK_TAMBAH_FOTO
    
    async def handle_kp_foto(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle foto upload dari user."""
        try:
            prod_data = context.user_data.get('new_product', {})
            photo = update.message.photo[-1]  # Get the largest photo
            
            # Download dan simpan foto
            file = await self.application.bot.get_file(photo.file_id)
            
            # Buat folder untuk foto jika belum ada
            import os
            foto_dir = "product_photos"
            if not os.path.exists(foto_dir):
                os.makedirs(foto_dir)
            
            # Simpan dengan nama: kode_produk.jpg
            foto_filename = f"{prod_data['kode']}.jpg"
            foto_path = os.path.join(foto_dir, foto_filename)
            
            # Download file foto
            await file.download_to_drive(foto_path)
            
            # Simpan path ke context
            prod_data['foto_path'] = foto_path
            context.user_data['new_product'] = prod_data
            
            # Verifikasi dan simpan produk
            await self._save_product_to_db(update, context)
            
            logger.info(f"[+] Product with photo added: {prod_data['kode']}")
            return KELOLA_PRODUK_MENU
            
        except Exception as e:
            logger.error(f"[-] Error handling photo: {e}", exc_info=True)
            await update.message.reply_text(
                f"❌ Gagal upload foto: {e}\n\n"
                "Silakan coba lagi atau skip.",
                parse_mode="Markdown"
            )
            return KELOLA_PRODUK_TAMBAH_FOTO
    
    async def handle_kp_skip_foto(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle skip foto (callback button)."""
        query = update.callback_query
        await query.answer()
        
        context.user_data['new_product']['foto_path'] = None
        
        # Simpan produk ke database
        await self._save_product_to_db_from_callback(update, context)
        
        return KELOLA_PRODUK_MENU
    
    async def handle_kp_skip_foto_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle skip foto dari text input (user ketik apapun untuk skip)."""
        context.user_data['new_product']['foto_path'] = None
        
        # Simpan produk ke database
        await self._save_product_to_db(update, context)
        
        return KELOLA_PRODUK_MENU
    
    async def _save_product_to_db(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Simpan produk ke database (helper untuk message update)."""
        try:
            prod_data = context.user_data.get('new_product', {})
            
            self.db.add_product(
                kode=prod_data['kode'],
                nama=prod_data['nama'],
                harga=prod_data['harga'],
                stok=prod_data['stok'],
                foto_path=prod_data.get('foto_path')
            )
            
            # Invalidate cache
            self.invalidate_products_cache()
            
            foto_status = "✅ dengan foto" if prod_data.get('foto_path') else "tanpa foto"
            msg = (
                f"[+] *PRODUK BERHASIL DITAMBAHKAN!*\n\n"
                f"KODE: {prod_data['kode']}\n"
                f"NAMA: {prod_data['nama']}\n"
                f"HARGA: {format_rp(prod_data['harga'])}\n"
                f"STOK: {prod_data['stok']} pcs\n"
                f"FOTO: {foto_status}\n\n"
                f"Data produk tersimpan di database."
            )
            
            keyboard = [
                [InlineKeyboardButton("[+] Tambah Lagi", callback_data="kp_tambah")],
                [InlineKeyboardButton("[LIST] Lihat Semua", callback_data="kp_lihat")],
                [InlineKeyboardButton("[KEMBALI]", callback_data="kembali_kp")],
            ]
            
            await update.message.reply_text(
                msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            
            logger.info(f"[+] Product added: {prod_data['kode']} - {prod_data['nama']} (foto: {prod_data.get('foto_path', 'None')})")
            
            # Cleanup context
            context.user_data.pop('new_product', None)
            
        except Exception as e:
            logger.error(f"[-] Error saving product: {e}", exc_info=True)
            await update.message.reply_text(f"[ERROR] Gagal menyimpan: {e}")
            # Cleanup context even on error
            context.user_data.pop('new_product', None)
    
    async def _save_product_to_db_from_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Simpan produk ke database (helper untuk callback query update)."""
        try:
            query = update.callback_query
            prod_data = context.user_data.get('new_product', {})
            
            self.db.add_product(
                kode=prod_data['kode'],
                nama=prod_data['nama'],
                harga=prod_data['harga'],
                stok=prod_data['stok'],
                foto_path=prod_data.get('foto_path')
            )
            
            # Invalidate cache
            self.invalidate_products_cache()
            
            foto_status = "✅ dengan foto" if prod_data.get('foto_path') else "tanpa foto"
            msg = (
                f"[+] *PRODUK BERHASIL DITAMBAHKAN!*\n\n"
                f"KODE: {prod_data['kode']}\n"
                f"NAMA: {prod_data['nama']}\n"
                f"HARGA: {format_rp(prod_data['harga'])}\n"
                f"STOK: {prod_data['stok']} pcs\n"
                f"FOTO: {foto_status}\n\n"
                f"Data produk tersimpan di database."
            )
            
            keyboard = [
                [InlineKeyboardButton("[+] Tambah Lagi", callback_data="kp_tambah")],
                [InlineKeyboardButton("[LIST] Lihat Semua", callback_data="kp_lihat")],
                [InlineKeyboardButton("[KEMBALI]", callback_data="kembali_kp")],
            ]
            
            # Send NEW message instead of editing to avoid callback issues
            await query.message.reply_text(
                msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            
            logger.info(f"[+] Product added: {prod_data['kode']} - {prod_data['nama']} (foto: {prod_data.get('foto_path', 'None')})")
            
            # Cleanup context
            context.user_data.pop('new_product', None)
            
        except Exception as e:
            logger.error(f"[-] Error saving product: {e}", exc_info=True)
            await query.message.reply_text(f"[ERROR] Gagal menyimpan: {e}")
            # Cleanup context even on error
            context.user_data.pop('new_product', None)
    
    
    async def kelola_produk_edit_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Mulai edit produk - tampilkan opsi field."""
        query = update.callback_query
        await query.answer()
        
        try:
            # Get product index from callback
            prod_idx = int(query.data.split("_")[-1])
            products = context.user_data.get('products_list', [])
            
            if prod_idx >= len(products):
                await query.answer("[ERROR] Produk tidak ditemukan!")
                return KELOLA_PRODUK_LIHAT
            
            product = products[prod_idx]
            context.user_data['editing_product'] = product
            context.user_data['editing_index'] = prod_idx
            
            msg = (
                f"*EDIT PRODUK*\n\n"
                f"Kode: {product['kode']}\n"
                f"Nama: {product['nama']}\n"
                f"Harga: {format_rp(product['harga'])}\n"
                f"Stok: {product['stok']} pcs\n\n"
                f"Pilih field yang akan diubah:"
            )
            
            keyboard = [
                [InlineKeyboardButton("[EDIT] Nama", callback_data="kp_edt_nama")],
                [InlineKeyboardButton("[EDIT] Harga", callback_data="kp_edt_harga")],
                [InlineKeyboardButton("[EDIT] Stok", callback_data="kp_edt_stok")],
                [InlineKeyboardButton("[BATAL]", callback_data="kp_lihat")],
            ]
            
            await query.edit_message_text(
                text=msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            
            logger.info(f"[+] Edit mode for product: {product['kode']}")
            
        except Exception as e:
            logger.error(f"[-] Error in kelola_produk_edit_start: {e}", exc_info=True)
        
        return KELOLA_PRODUK_EDIT
    
    async def kelola_produk_edit_field(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle edit field selection."""
        query = update.callback_query
        await query.answer()
        
        field = query.data.split("_")[-1]  # nama, harga, or stok
        context.user_data['editing_field'] = field
        
        product = context.user_data.get('editing_product', {})
        
        if field == "nama":
            prompt = f"Masukkan *Nama* baru (saat ini: {product['nama']}):"
        elif field == "harga":
            prompt = f"Masukkan *Harga* baru (saat ini: {format_rp(product['harga'])}):"
        else:  # stok
            prompt = f"Masukkan *Stok* baru (saat ini: {product['stok']} pcs):"
        
        try:
            await query.edit_message_text(
                text=prompt,
                parse_mode="Markdown"
            )
        except:
            pass
        
        # Change to a state that accepts text input
        return KELOLA_PRODUK_TAMBAH_NAMA if field == "nama" else KELOLA_PRODUK_TAMBAH_HARGA if field == "harga" else KELOLA_PRODUK_TAMBAH_STOK
    
    async def kelola_produk_hapus_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Konfirmasi penghapusan produk."""
        query = update.callback_query
        await query.answer()
        
        try:
            prod_idx = int(query.data.split("_")[-1])
            products = context.user_data.get('products_list', [])
            
            if prod_idx >= len(products):
                await query.answer("[ERROR] Produk tidak ditemukan!")
                return KELOLA_PRODUK_LIHAT
            
            product = products[prod_idx]
            context.user_data['deleting_product'] = product
            context.user_data['deleting_index'] = prod_idx
            
            msg = (
                f"*KONFIRMASI PENGHAPUSAN*\n\n"
                f"[PERINGATAN] Anda yakin ingin menghapus produk ini?\n\n"
                f"KODE: {product['kode']}\n"
                f"NAMA: {product['nama']}\n"
                f"HARGA: {format_rp(product['harga'])}\n"
                f"STOK: {product['stok']} pcs\n\n"
                f"Tindakan ini TIDAK dapat dibatalkan!"
            )
            
            keyboard = [
                [
                    InlineKeyboardButton("[YA] Hapus", callback_data=f"kp_hapus_yes_{prod_idx}"),
                    InlineKeyboardButton("[TIDAK] Batal", callback_data="kp_hapus_no"),
                ]
            ]
            
            await query.edit_message_text(
                text=msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"[-] Error in kelola_produk_hapus_confirm: {e}", exc_info=True)
        
        return KELOLA_PRODUK_HAPUS
    
    async def kelola_produk_hapus_confirm_exec(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Execute penghapusan produk."""
        query = update.callback_query
        await query.answer()
        
        try:
            product = context.user_data.get('deleting_product', {})
            
            # Hapus dari database
            self.db.delete_product(product['kode'])
            
            # Invalidate cache setelah menghapus produk
            self.invalidate_products_cache()
            msg = (
                f"[+] *PRODUK BERHASIL DIHAPUS*\n\n"
                f"KODE: {product['kode']}\n"
                f"NAMA: {product['nama']}\n\n"
                f"Produk telah dihapus dari database."
            )
            
            keyboard = [
                [InlineKeyboardButton("[LIST] Lihat Semua", callback_data="kp_lihat")],
                [InlineKeyboardButton("[KEMBALI]", callback_data="kembali_kp")],
            ]
            
            await query.edit_message_text(
                text=msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            
            logger.info(f"[+] Product deleted: {product['kode']}")
            
        except Exception as e:
            logger.error(f"[-] Error deleting product: {e}", exc_info=True)
            await query.edit_message_text(f"[ERROR] Gagal menghapus: {e}")
        
        return KELOLA_PRODUK_MENU
    
    # ========================================================================
    # RUN BOT
    # ========================================================================
    
    def run(self):
        """Run Telegram bot (now without auto-restart due to event loop issues)."""
        print("\n" + "=" * 70)
        print("[TELEGRAM POS SYSTEM - STARTING]".center(70))
        print("=" * 70)
        print(f"Bot Token: {self.token[:20]}...")
        print(f"Admin Chat ID: {self.config_manager.config.get('admin_chat_id')}")
        print(f"Auto-restart: {'ENABLED' if self.auto_restart_enabled else 'DISABLED'}")
        print("=" * 70)
        print("\n[*] Bot waiting for commands...")
        print("    Send /start or /menu to begin")
        print("=" * 70 + "\n")
        
        try:
            if self.auto_restart_enabled:
                # Mode with auto-restart (NOT RECOMMENDED due to event loop issues)
                loop_count = 0
                while True:
                    loop_count += 1
                    run_start_time = datetime.now().strftime('%H:%M:%S')
                    logger.info(f"[>] Polling loop #{loop_count} started at {run_start_time}")
                    print(f"[*] Polling session #{loop_count} started at {run_start_time}")
                    
                    try:
                        # Schedule restart timer
                        self._schedule_restart()
                        
                        # Run polling - akan dihentikan oleh timer setelah interval
                        self.application.run_polling(allowed_updates=Update.ALL_TYPES)
                        
                    except Exception as e:
                        logger.error(f"[-] Polling error in loop #{loop_count}: {e}", exc_info=True)
                        print(f"[!] Polling error: {e}")
                    finally:
                        # Cleanup timer
                        self._cleanup_restart_timer()
                    
                    # Log setelah polling selesai
                    run_end_time = datetime.now().strftime('%H:%M:%S')
                    logger.info(f"[<] Polling loop #{loop_count} ended at {run_end_time}")
                    print(f"[*] Polling session #{loop_count} ended at {run_end_time}")
                    
                    # Recreate application untuk restart
                    print("\n[!] Restarting application...\n")
                    self.application = Application.builder().token(self.token).build()
                    self._register_handlers()
            else:
                # Mode tanpa restart (RECOMMENDED)
                logger.info("[+] Running bot in stable mode (without auto-restart)")
                print("[+] Running bot in stable mode (without auto-restart)\n")
                
                try:
                    # Run polling directly - stable, no event loop issues
                    self.application.run_polling(allowed_updates=Update.ALL_TYPES)
                except Exception as e:
                    logger.error(f"[-] Polling error: {e}", exc_info=True)
                    print(f"[!] Polling error: {e}")
                
        except KeyboardInterrupt:
            print("\n\n[!] Bot stopped by user (Ctrl+C)")
            logger.info("[!] Bot stopped by user (Ctrl+C)")
            self._cleanup_restart_timer()
        except Exception as e:
            print(f"\n\n[ERROR] Fatal error: {e}")
            logger.error(f"Error running bot: {e}", exc_info=True)
            import traceback
            traceback.print_exc()

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point."""
    config_manager = TelegramConfigManager()
    token = config_manager.get_token()
    
    if not token:
        print("[ERROR] Bot token tidak dikonfigurasi!")
        print("Edit telegram_config.json atau setup via CLI POS system")
        return
    
    pos_system = TelegramPOSSystem(token)
    pos_system.run()  # Blocking call

if __name__ == "__main__":
    main()
