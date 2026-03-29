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
        logging.FileHandler('telegram_pos.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONVERSATION STATES
# ============================================================================

MAIN_MENU, TRANSAKSI_MENU, TAMBAH_ITEM_KODE, TAMBAH_ITEM_QTY, PEMBAYARAN = range(5)
LIHAT_STOK, LIHAT_LAPORAN = range(5, 7)

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
        
        # Setup application
        self.application = Application.builder().token(token).build()
        self._register_handlers()
        
        logger.info("✅ TelegramPOSSystem initialized")
    
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
                ],
                TAMBAH_ITEM_KODE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_item_kode),
                ],
                TAMBAH_ITEM_QTY: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_item_qty),
                ],
                PEMBAYARAN: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_pembayaran),
                ],
            },
            fallbacks=[
                CallbackQueryHandler(self.transaksi_cancel, pattern="^cancel_transaksi$"),
            ],
            per_user=True,
            per_chat=True,
        )
        self.application.add_handler(transaksi_conv)
        
        # Other callbacks
        self.application.add_handler(CallbackQueryHandler(self.callback_main_menu, pattern="^main_menu$"))
        self.application.add_handler(CallbackQueryHandler(self.lihat_stok, pattern="^lihat_stok$"))
        self.application.add_handler(CallbackQueryHandler(self.lihat_laporan, pattern="^lihat_laporan$"))
        self.application.add_handler(CallbackQueryHandler(self.lihat_dashboard, pattern="^lihat_dashboard$"))
        
        logger.info("✅ All handlers registered")
    
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
    
    # ========================================================================
    # MAIN MENU & START
    # ========================================================================
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /start command - Welcome & show main menu.
        """
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        logger.info(f"🟢 /start command from user: {user.first_name} (ID: {chat_id})")
        
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
            logger.info(f"✅ Welcome message sent to {user.first_name}")
        except Exception as e:
            logger.error(f"❌ Error in cmd_start: {e}", exc_info=True)
    
    async def cmd_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /menu command - Show main menu.
        """
        chat_id = update.effective_chat.id
        logger.info(f"🟢 /menu command from chat_id: {chat_id}")
        
        keyboard = await self.get_main_menu_keyboard()
        
        try:
            await update.message.reply_text(
                "📋 *MENU UTAMA*\n\nPilih salah satu opsi di bawah:",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"❌ Error in cmd_menu: {e}", exc_info=True)
    
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
            logger.error(f"❌ Error in cmd_help: {e}", exc_info=True)
    
    # ========================================================================
    # MAIN MENU KEYBOARD
    # ========================================================================
    
    async def get_main_menu_keyboard(self) -> InlineKeyboardMarkup:
        """Generate main menu keyboard."""
        keyboard = [
            [InlineKeyboardButton("🛒 Transaksi Penjualan", callback_data="transaksi")],
            [InlineKeyboardButton("📦 Lihat Stok", callback_data="lihat_stok")],
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
            logger.error(f"❌ Error in callback_main_menu: {e}", exc_info=True)
    
    # ========================================================================
    # TRANSACTION HANDLERS
    # ========================================================================
    
    async def transaksi_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Start transaksi - tampilkan transaksi menu."""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        logger.info(f"🟢 Transaksi started for user_id: {user_id}")
        
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
            [InlineKeyboardButton("⬅️  Kembali", callback_data="main_menu")],
        ]
        
        try:
            await query.edit_message_text(
                text=msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"❌ Error in show_transaksi_menu: {e}", exc_info=True)
    
    async def transaksi_tambah_item(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle tambah item - minta input kode."""
        query = update.callback_query
        await query.answer()
        
        try:
            await query.edit_message_text(
                text=(
                    "📝 *TAMBAH ITEM*\n\n"
                    "Silakan ketik *Kode Produk* (contoh: COFFEE, TEA, 0001)\n\n"
                    "Kirim /cancel untuk batalkan."
                ),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"❌ Error in transaksi_tambah_item: {e}", exc_info=True)
        
        return TAMBAH_ITEM_KODE
    
    async def handle_item_kode(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle kode produk input."""
        kode = update.message.text.strip().upper()
        user_id = update.effective_user.id
        
        logger.info(f"Product code input: {kode} from user_id: {user_id}")
        
        # Lookup produk
        product = self.db.get_product_by_kode(kode)
        
        if not product:
            await update.message.reply_text(
                f"❌ Produk dengan kode *{kode}* tidak ditemukan!\n\n"
                f"Silakan coba kode lain atau ketik /cancel untuk batalkan.",
                parse_mode="Markdown"
            )
            return TAMBAH_ITEM_KODE
        
        # Check stok
        if product['stok'] <= 0:
            await update.message.reply_text(
                f"❌ Produk *{product['nama']}* stok tidak tersedia!\n\n"
                f"Silakan pilih produk lain.",
                parse_mode="Markdown"
            )
            return TAMBAH_ITEM_KODE
        
        # Display produk & minta qty
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
        
        logger.info(f"✅ Item added: {product['kode']} qty: {qty} for user_id: {user_id}")
        
        return TRANSAKSI_MENU
    
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
        
        keyboard = [[InlineKeyboardButton("⬅️  Kembali", callback_data="transaksi")]]
        
        try:
            await query.edit_message_text(
                text=msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"❌ Error in transaksi_lihat_item: {e}", exc_info=True)
        
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
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️  Kembali", callback_data="transaksi")]])
                )
            except:
                pass
            return TRANSAKSI_MENU
        
        msg = "🗑️  *HAPUS ITEM*\n\nPilih nomor item yang akan dihapus:\n\n"
        keyboard = []
        
        for idx, item in enumerate(items, 1):
            msg += f"{idx}. {item['nama']} x{item['qty']}\n"
            keyboard.append([InlineKeyboardButton(f"❌ Hapus Item {idx}", callback_data=f"remove_item_{idx-1}")])
        
        keyboard.append([InlineKeyboardButton("⬅️  Batal", callback_data="transaksi")])
        
        try:
            await query.edit_message_text(
                text=msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"❌ Error in transaksi_hapus_item_btn: {e}", exc_info=True)
        
        # Register dynamic remove handlers
        for idx in range(len(items)):
            self.application.add_handler(
                CallbackQueryHandler(
                    self.transaksi_remove_item,
                    pattern=f"^remove_item_{idx}$"
                )
            )
        
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
        """Handle checkout & minta pembayaran."""
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
            f"💳 *KONFIRMASI PEMBAYARAN*\n\n"
            f"📊 Ringkasan:\n"
            f"  Total Item: {summary['items_count']}\n"
            f"  Total Qty: {summary['qty_total']}\n"
            f"  Harga Total: {format_rp(summary['total'])}\n\n"
            f"Berapa yang akan dibayarkan?\n"
            f"(Ketik nominal atau ketik 0 untuk membatalkan)\n\n"
            f"Minimum pembayaran: {format_rp(summary['total'])}"
        )
        
        context.user_data['transaction_total'] = summary['total']
        
        try:
            await query.edit_message_text(text=msg, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"❌ Error in transaksi_checkout: {e}", exc_info=True)
        
        return PEMBAYARAN
    
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
            
            msg = (
                f"✅ *TRANSAKSI BERHASIL*\n\n"
                f"📄 No. Invoice: {trans_id}\n"
                f"💰 Total: {format_rp(total)}\n"
                f"💵 Pembayaran: {format_rp(bayar)}\n"
                f"🔄 Kembalian: {format_rp(kembalian)}\n"
                f"⏰ Waktu: {datetime.now().strftime('%H:%M:%S')}\n\n"
                f"Terima kasih telah berbelanja! 🙏"
            )
            
            keyboard = [[InlineKeyboardButton("🛒 Transaksi Baru", callback_data="transaksi")]]
            
            await update.message.reply_text(
                msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            
            logger.info(f"✅ Transaction completed: ID={trans_id}, user_id={user_id}")
            
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
            logger.error(f"❌ Error in transaksi_cancel: {e}", exc_info=True)
        
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
        await query.answer("⏳ Mengambil data stok...")
        
        try:
            stok_list = self.db.get_all_stok()
            
            if not stok_list:
                msg = "📦 Belum ada produk di database."
            else:
                msg = "📦 *DAFTAR PRODUK & STOK*\n\n"
                
                ok_count = sum(1 for s in stok_list if s['stok'] > 20)
                low_count = sum(1 for s in stok_list if 0 < s['stok'] <= 20)
                empty_count = sum(1 for s in stok_list if s['stok'] == 0)
                
                msg += f"🟢 OK: {ok_count} | 🟡 MINIM: {low_count} | 🔴 KOSONG: {empty_count}\n\n"
                
                for prod in stok_list:
                    if prod['stok'] > 20:
                        icon = "🟢"
                    elif prod['stok'] > 0:
                        icon = "🟡"
                    else:
                        icon = "🔴"
                    
                    msg += f"{icon} {prod['kode']}: {prod['nama']}\n"
                    msg += f"   Stok: {prod['stok']} pcs | Harga: {format_rp(prod['harga'])}\n"
                
                msg = msg[:3500]  # Telegram limit
            
            keyboard = [[InlineKeyboardButton("⬅️  Kembali", callback_data="main_menu")]]
            
            await query.edit_message_text(
                text=msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            logger.info(f"✅ Stok list shown")
            
        except Exception as e:
            logger.error(f"❌ Error in lihat_stok: {e}", exc_info=True)
            await query.edit_message_text(f"❌ Error: {e}")
    
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
            logger.info(f"✅ Laporan shown")
            
        except Exception as e:
            logger.error(f"❌ Error in lihat_laporan: {e}", exc_info=True)
            await query.edit_message_text(f"❌ Error: {e}")
    
    async def lihat_dashboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lihat dashboard ringkasan."""
        query = update.callback_query
        await query.answer("⏳ Mengambil dashboard...")
        
        try:
            laporan = self.report_generator.get_laporan_harian()
            stok_list = self.db.get_all_stok()
            
            total_stok = sum(s['stok'] for s in stok_list) if stok_list else 0
            low_stok = sum(1 for s in stok_list if 0 < s['stok'] <= 20) if stok_list else 0
            empty_stok = sum(1 for s in stok_list if s['stok'] == 0) if stok_list else 0
            
            msg = (
                f"📈 *DASHBOARD RINGKASAN*\n\n"
                f"💰 *PENJUALAN HARI INI*\n"
                f"  Total: {format_rp(laporan['total_penjualan'])}\n"
                f"  Transaksi: {laporan['total_transaksi']}\n"
                f"  Item Terjual: {laporan['total_item']}\n\n"
                f"📦 *INVENTORY*\n"
                f"  Total Produk: {len(stok_list)}\n"
                f"  Total Stok: {total_stok} pcs\n"
                f"  Stok Minim: {low_stok} produk 🟡\n"
                f"  Stok Kosong: {empty_stok} produk 🔴\n\n"
                f"🏆 *PRODUK TERLARIS*\n"
            )
            
            if laporan['produk_laris']:
                for i, prod in enumerate(laporan['produk_laris'][:3], 1):
                    msg += f"{i}. {prod['nama']} ({prod['total_qty']} qty)\n"
            
            keyboard = [[InlineKeyboardButton("⬅️  Kembali", callback_data="main_menu")]]
            
            await query.edit_message_text(
                text=msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            logger.info(f"✅ Dashboard shown")
            
        except Exception as e:
            logger.error(f"❌ Error in lihat_dashboard: {e}", exc_info=True)
            await query.edit_message_text(f"❌ Error: {e}")
    
    # ========================================================================
    # RUN BOT
    # ========================================================================
    
    async def run(self):
        """Run Telegram bot."""
        print("\n" + "=" * 70)
        print("🤖 TELEGRAM POS SYSTEM - MEMULAI".center(70))
        print("=" * 70)
        print(f"Bot Token: {self.token[:20]}...")
        print(f"Admin Chat ID: {self.config_manager.config.get('admin_chat_id')}")
        print("=" * 70)
        print("\n💡 Bot sedang menunggu commands...")
        print("   Kirim /start atau /menu untuk memulai")
        print("=" * 70 + "\n")
        
        try:
            import asyncio
            import sys
            
            # Windows event loop fix
            if sys.platform == 'win32':
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            
            await self.application.run_polling(allowed_updates=Update.ALL_TYPES)
        except KeyboardInterrupt:
            print("\n\n❌ Bot dihentikan oleh user")
        except Exception as e:
            print(f"\n\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            logger.error(f"Error running bot: {e}", exc_info=True)

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point."""
    config_manager = TelegramConfigManager()
    token = config_manager.get_token()
    
    if not token:
        print("❌ Bot token tidak dikonfigurasi!")
        print("Edit telegram_config.json atau setup via CLI POS system")
        return
    
    pos_system = TelegramPOSSystem(token)
    
    import asyncio
    asyncio.run(pos_system.run())

if __name__ == "__main__":
    main()
