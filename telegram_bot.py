# ============================================================================
# TELEGRAM_BOT.PY - Telegram Bot Integration untuk POS System
# ============================================================================
# Fungsi: Handle command Telegram, send notification, real-time reporting
# Dependency: pip install python-telegram-bot requests
# ============================================================================

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
import requests

# Telegram Bot Library
try:
    from telegram import Update, Bot
    from telegram.ext import (
        Application, CommandHandler, MessageHandler, filters, 
        ContextTypes, ConversationHandler
    )
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("⚠️ python-telegram-bot not installed. Install with: pip install python-telegram-bot")

# Import dari POS modules
from database import DatabaseManager
from models import ProductManager, format_rp
from laporan import ReportGenerator, ReportFormatter

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('telegram_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# TELEGRAM CONFIG MANAGER
# ============================================================================

class TelegramConfigManager:
    """
    Manage Telegram bot configuration dari file JSON.
    
    Config file structure:
    {
        "bot_token": "YOUR_BOT_TOKEN",
        "allowed_chat_ids": [123456789],
        "enabled": true,
        "admin_chat_id": 123456789,
        "notify_transaction": true,
        "notify_low_stock": true,
        "low_stock_threshold": 20
    }
    """
    
    def __init__(self, config_path: str = "telegram_config.json"):
        """
        Inisialisasi TelegramConfigManager.
        
        Args:
            config_path (str): Path ke config file
        """
        self.config_path = config_path
        self.config = self.load_config()
    
    def load_config(self) -> Dict:
        """
        Load config dari file JSON.
        Jika file tidak ada, buat default config.
        
        Returns:
            Dict: Configuration
        """
        # Default config
        default_config = {
            "bot_token": "YOUR_BOT_TOKEN_HERE",
            "allowed_chat_ids": [],
            "enabled": False,
            "admin_chat_id": None,
            "notify_transaction": True,
            "notify_low_stock": True,
            "low_stock_threshold": 20
        }
        
        # Cek file ada atau tidak
        if not os.path.exists(self.config_path):
            self.save_config(default_config)
            print(f"\n⚠️ Config file '{self.config_path}' belum ada")
            print(f"📝 File default sudah dibuat. Edit dengan token Telegram Anda")
            return default_config
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config
        except Exception as e:
            print(f"❌ Error loading config: {e}")
            return default_config
    
    def save_config(self, config: Dict = None):
        """
        Simpan config ke file JSON.
        
        Args:
            config (Dict): Config to save (default: current config)
        """
        if config is None:
            config = self.config
        
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            print(f"✅ Config berhasil disimpan ke {self.config_path}")
        except Exception as e:
            print(f"❌ Error saving config: {e}")
    
    def is_enabled(self) -> bool:
        """Cek apakah bot enabled."""
        return self.config.get("enabled", False)
    
    def get_token(self) -> Optional[str]:
        """Ambil bot token."""
        token = self.config.get("bot_token")
        if token == "YOUR_BOT_TOKEN_HERE" or not token:
            return None
        return token
    
    def is_authorized(self, chat_id: int) -> bool:
        """
        Cek apakah chat_id authorized.
        
        Args:
            chat_id (int): Chat ID dari Telegram
            
        Returns:
            bool: True jika authorized
        """
        allowed_ids = self.config.get("allowed_chat_ids", [])
        return chat_id in allowed_ids
    
    def add_allowed_chat(self, chat_id: int):
        """
        Tambah chat ID ke allowed list.
        
        Args:
            chat_id (int): Chat ID untuk ditambahkan
        """
        if chat_id not in self.config.get("allowed_chat_ids", []):
            if "allowed_chat_ids" not in self.config:
                self.config["allowed_chat_ids"] = []
            self.config["allowed_chat_ids"].append(chat_id)
            self.save_config()
            print(f"✅ Chat ID {chat_id} ditambahkan ke allowed list")

# ============================================================================
# TELEGRAM BOT HANDLER
# ============================================================================

class POSTelegramBot:
    """
    Main Telegram Bot handler untuk POS system.
    
    Fitur:
    - /start - Inisialisasi & welcome message
    - /laporan - Laporan penjualan hari ini
    - /stok - Info stok produk
    - /terlaris - Produk paling laris
    - /help - Bantuan commands
    - /settings - Manage settings (admin only)
    
    Attributes:
        config_manager (TelegramConfigManager): Config manager
        db (DatabaseManager): Database instance
        bot (Bot): Telegram bot instance
        application (Application): Telegram Application
    """
    
    def __init__(self):
        """Inisialisasi POSTelegramBot."""
        if not TELEGRAM_AVAILABLE:
            print("❌ python-telegram-bot tidak terinstall")
            self.available = False
            return
        
        # Setup config
        self.config_manager = TelegramConfigManager()
        
        # Check bot enabled & token valid
        if not self.config_manager.is_enabled():
            print("⚠️ Telegram bot disabled. Edit telegram_config.json dan set 'enabled': true")
            self.available = False
            return
        
        token = self.config_manager.get_token()
        if not token:
            print("❌ Bot token belum dikonfigurasi. Edit telegram_config.json")
            self.available = False
            return
        
        # Setup database & services
        self.db = DatabaseManager()
        self.product_manager = ProductManager(self.db)
        self.report_generator = ReportGenerator(self.db)
        self.report_formatter = ReportFormatter()
        
        # Setup Telegram bot
        self.bot = Bot(token=token)
        self.application = Application.builder().token(token).build()
        
        # Register handlers
        self._register_handlers()
        
        self.available = True
        logger.info("[OK] Telegram Bot initialized successfully")
    
    def _register_handlers(self):
        """Register semua command handlers."""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("laporan", self.cmd_laporan))
        self.application.add_handler(CommandHandler("stok", self.cmd_stok))
        self.application.add_handler(CommandHandler("terlaris", self.cmd_terlaris))
        self.application.add_handler(CommandHandler("dashboard", self.cmd_dashboard))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        self.application.add_handler(CommandHandler("ping", self.cmd_ping))
        
        logger.info("[OK] All command handlers registered")
    
    # ========================================================================
    # AUTHORIZATION CHECK
    # ========================================================================
    
    async def check_authorization(self, update: Update) -> bool:
        """
        Check apakah user authorized.
        Jika tidak, send unauthorized message.
        
        Args:
            update (Update): Telegram update
            
        Returns:
            bool: True jika authorized
        """
        chat_id = update.effective_chat.id
        
        if not self.config_manager.is_authorized(chat_id):
            await update.message.reply_text(
                "❌ Anda tidak memiliki akses ke bot ini.\n\n"
                "Chat ID: `" + str(chat_id) + "`\n"
                "Silakan hubungi admin untuk mendapatkan akses.",
                parse_mode="Markdown"
            )
            logger.warning(f"Unauthorized access attempt from chat_id: {chat_id}")
            return False
        
        return True
    
    # ========================================================================
    # COMMAND HANDLERS
    # ========================================================================
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /start command - Welcome & setup.
        
        Kirim welcome message & add chat_id ke allowed list jika admin.
        """
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        logger.info(f"🟢 /start command received from chat_id: {chat_id}")
        
        welcome_msg = (
            f"👋 Selamat datang di *POS Telegram Bot*!\n\n"
            f"Pengguna: {user.first_name}\n"
            f"Chat ID: `{chat_id}`\n\n"
            f"Gunakan /help untuk melihat semua commands."
        )
        
        try:
            # Auto-add admin
            admin_id = self.config_manager.config.get("admin_chat_id")
            if chat_id == admin_id:
                self.config_manager.add_allowed_chat(chat_id)
                welcome_msg += "\n\n✅ Anda adalah admin, akses diberikan!"
            elif not self.config_manager.is_authorized(chat_id):
                welcome_msg += (
                    "\n\n⚠️ Akses Anda belum disetujui. Hubungi admin.\n"
                    f"Chat ID: `{chat_id}`"
                )
            
            await update.message.reply_text(welcome_msg, parse_mode="Markdown")
            logger.info(f"✅ Response sent to chat_id: {chat_id}")
        except Exception as e:
            logger.error(f"❌ Error in cmd_start: {e}", exc_info=True)
            try:
                await update.message.reply_text(f"❌ Error: {e}")
            except:
                pass
    
    async def cmd_laporan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /laporan command - Laporan penjualan harian.
        
        Tampilkan laporan penjualan hari ini dengan formatting rapi.
        """
        chat_id = update.effective_chat.id
        logger.info(f"🟢 /laporan command received from chat_id: {chat_id}")
        
        if not await self.check_authorization(update):
            return
        
        try:
            await update.message.reply_text(
                "⏳ Mengambil data laporan penjualan...",
                parse_mode="Markdown"
            )
            
            # Generate laporan
            laporan = self.report_generator.get_laporan_harian()
            
            # Format message
            msg = (
                f"📊 *LAPORAN PENJUALAN HARIAN*\n"
                f"Tanggal: {laporan['tanggal']}\n\n"
                f"💰 Total Penjualan: {format_rp(laporan['total_penjualan'])}\n"
                f"📝 Total Transaksi: {laporan['total_transaksi']}\n"
                f"📈 Rata-rata: {format_rp(int(laporan['rata_rata_transaksi']))}\n"
                f"📦 Total Item: {laporan['total_item']}\n"
                f"📌 Item/Transaksi: {laporan['rata_rata_item_per_transaksi']:.1f}\n"
            )
            
            # Top produk
            if laporan['produk_laris']:
                msg += "\n🏆 *TOP 5 PRODUK:*\n"
                for i, prod in enumerate(laporan['produk_laris'][:5], 1):
                    msg += f"{i}. {prod['nama']:<20} - {prod['total_qty']} qty ({format_rp(prod['total_revenue'])})\n"
            
            await update.message.reply_text(msg, parse_mode="Markdown")
            logger.info(f"✅ Laporan sent to chat_id: {chat_id}")
            
        except Exception as e:
            logger.error(f"❌ Error in cmd_laporan: {e}", exc_info=True)
            try:
                await update.message.reply_text(f"❌ Error: {e}")
            except:
                pass
    
    async def cmd_stok(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /stok command - Info stok produk.
        
        Tampilkan daftar stok dengan status.
        """
        if not await self.check_authorization(update):
            return
        
        try:
            stok_list = self.report_generator.get_stok_summary()
            
            if not stok_list:
                await update.message.reply_text("⚠️ Belum ada produk dalam database")
                return
            
            # Pisah by status
            ok_stock = [s for s in stok_list if 'OK' in s['status']]
            low_stock = [s for s in stok_list if 'MINIM' in s['status']]
            empty_stock = [s for s in stok_list if 'KOSONG' in s['status']]
            
            msg = f"📦 *INFO STOK PRODUK*\n\n"
            
            # OK Stock
            if ok_stock:
                msg += f"🟢 *STOK OK* ({len(ok_stock)})\n"
                for s in ok_stock[:5]:  # Show max 5
                    msg += f"  • {s['nama']}: {s['stok']} unit\n"
                if len(ok_stock) > 5:
                    msg += f"  ... dan {len(ok_stock) - 5} lainnya\n"
            
            # Low Stock
            if low_stock:
                msg += f"\n🟡 *STOK MINIM* ({len(low_stock)})\n"
                for s in low_stock:
                    msg += f"  ⚠️ {s['nama']}: {s['stok']} unit\n"
            
            # Empty Stock
            if empty_stock:
                msg += f"\n🔴 *STOK KOSONG* ({len(empty_stock)})\n"
                for s in empty_stock:
                    msg += f"  ❌ {s['nama']}: Stok habis\n"
            
            msg += f"\n📊 Total Produk: {len(stok_list)}\n"
            msg += f"📈 Total Stok: {sum(s['stok'] for s in stok_list)}\n"
            
            await update.message.reply_text(msg, parse_mode="Markdown")
            logger.info(f"Stok command from chat_id: {update.effective_chat.id}")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
            logger.error(f"Error in cmd_stok: {e}")
    
    async def cmd_terlaris(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /terlaris command - Produk paling laris.
        
        Tampilkan top 10 produk by qty.
        """
        if not await self.check_authorization(update):
            return
        
        try:
            produk_laris = self.report_generator.get_produk_terlaris(limit=10)
            
            if not produk_laris:
                await update.message.reply_text("⚠️ Belum ada data penjualan")
                return
            
            msg = f"🏆 *PRODUK PALING LARIS*\n\n"
            
            for prod in produk_laris:
                msg += (
                    f"{prod['rank']}. {prod['nama']}\n"
                    f"   Qty: {prod['total_qty']} | Revenue: {format_rp(prod['total_revenue'])}\n"
                )
            
            await update.message.reply_text(msg, parse_mode="Markdown")
            logger.info(f"Terlaris command from chat_id: {update.effective_chat.id}")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
            logger.error(f"Error in cmd_terlaris: {e}")
    
    async def cmd_dashboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /dashboard command - Quick dashboard summary.
        
        Tampilkan ringkasan lengkap untuk dashboard.
        """
        if not await self.check_authorization(update):
            return
        
        try:
            dashboard = self.report_generator.get_dashboard_summary()
            
            msg = (
                f"🎨 *DASHBOARD POS SUMMARY*\n\n"
                f"*HariIni:*\n"
                f"  💰 Penjualan: {format_rp(dashboard['hari_ini']['total_penjualan'])}\n"
                f"  📝 Transaksi: {dashboard['hari_ini']['total_transaksi']}\n"
                f"  📊 Rata-rata: {format_rp(int(dashboard['hari_ini']['rata_rata']))}\n\n"
                
                f"*Inventory:*\n"
                f"  📦 Total Produk: {dashboard['total_produk']}\n"
                f"  📈 Total Stok: {dashboard['total_stok']}\n"
                f"  ⚠️ Stok Minim: {len(dashboard['stok_minim'])}\n\n"
                
                f"*Top 3 Produk Hari Ini:*\n"
            )
            
            if dashboard['produk_terlaris']:
                for i, prod in enumerate(dashboard['produk_terlaris'][:3], 1):
                    msg += f"  {i}. {prod['nama']:<20} ({prod['total_qty']} qty)\n"
            else:
                msg += "  Belum ada penjualan hari ini\n"
            
            await update.message.reply_text(msg, parse_mode="Markdown")
            logger.info(f"Dashboard command from chat_id: {update.effective_chat.id}")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
            logger.error(f"Error in cmd_dashboard: {e}")
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /help command - Tampilkan semua commands.
        """
        chat_id = update.effective_chat.id
        logger.info(f"🟢 /help command received from chat_id: {chat_id}")
        
        help_msg = (
            "*POS Telegram Bot - BANTUAN*\n\n"
            "*Commands Tersedia:*\n\n"
            
            "📊 `/laporan` - Laporan penjualan hari ini\n"
            "  Menampilkan total penjualan, transaksi, dan top produk\n\n"
            
            "📦 `/stok` - Informasi stok produk\n"
            "  Menampilkan status stok (OK, MINIM, KOSONG)\n\n"
            
            "🏆 `/terlaris` - Produk paling laris\n"
            "  Top 10 produk berdasarkan quantity terjual\n\n"
            
            "🎨 `/dashboard` - Quick dashboard summary\n"
            "  Ringkasan lengkap penjualan dan inventory\n\n"
            
            "🔔 `/ping` - Test bot connectivity\n"
            "  Pastikan bot responsif\n\n"
            
            "❓ `/help` - Tampilkan pesan ini\n\n"
            
            "*Tips:*\n"
            "• Semua commands require authorization\n"
            "• Data real-time dari database SQLite\n"
            "• Format currency dalam Rupiah (Rp)\n"
        )
        
        try:
            await update.message.reply_text(help_msg, parse_mode="Markdown")
            logger.info(f"✅ Help sent to chat_id: {chat_id}")
        except Exception as e:
            logger.error(f"❌ Error in cmd_help: {e}", exc_info=True)
            try:
                await update.message.reply_text(f"❌ Error: {e}")
            except:
                pass
    
    async def cmd_ping(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /ping command - Test bot connectivity.
        """
        chat_id = update.effective_chat.id
        logger.info(f"🟢 /ping command received from chat_id: {chat_id}")
        
        if not await self.check_authorization(update):
            return
        
        msg = f"🔔 *PONG!*\n" \
              f"Bot Status: ✅ Online\n" \
              f"Time: {datetime.now().strftime('%H:%M:%S')}\n" \
              f"Chat ID: `{update.effective_chat.id}`"
        
        try:
            await update.message.reply_text(msg, parse_mode="Markdown")
            logger.info(f"✅ Ping response sent to chat_id: {chat_id}")
        except Exception as e:
            logger.error(f"❌ Error in cmd_ping: {e}", exc_info=True)
            try:
                await update.message.reply_text(f"❌ Error: {e}")
            except:
                pass
    
    # ========================================================================
    # NOTIFICATION METHODS
    # ========================================================================
    
    async def send_transaction_notification(self, transaction_id: int, 
                                           product_name: str, qty: int, 
                                           total: int):
        """
        Kirim notifikasi transaksi ke admin.
        
        Args:
            transaction_id (int): ID transaksi
            product_name (str): Nama produk
            qty (int): Quantity
            total (int): Total
        """
        if not self.available:
            return
        
        if not self.config_manager.config.get("notify_transaction", False):
            return
        
        admin_id = self.config_manager.config.get("admin_chat_id")
        if not admin_id:
            return
        
        try:
            msg = (
                f"💳 *TRANSAKSI BARU*\n\n"
                f"ID: #{transaction_id}\n"
                f"Produk: {product_name}\n"
                f"Qty: {qty}\n"
                f"Total: {format_rp(total)}\n"
                f"Waktu: {datetime.now().strftime('%H:%M:%S')}"
            )
            
            await self.bot.send_message(
                chat_id=admin_id,
                text=msg,
                parse_mode="Markdown"
            )
            logger.info(f"Transaction notification sent for transaction_id: {transaction_id}")
        except Exception as e:
            logger.error(f"Error sending transaction notification: {e}")
    
    async def send_low_stock_alert(self, product_name: str, stok: int):
        """
        Kirim alert stok minim ke admin.
        
        Args:
            product_name (str): Nama produk
            stok (int): Jumlah stok tersisa
        """
        if not self.available:
            return
        
        if not self.config_manager.config.get("notify_low_stock", False):
            return
        
        threshold = self.config_manager.config.get("low_stock_threshold", 20)
        if stok > threshold:
            return
        
        admin_id = self.config_manager.config.get("admin_chat_id")
        if not admin_id:
            return
        
        try:
            msg = (
                f"⚠️ *STOK PRODUK MINIM*\n\n"
                f"Produk: {product_name}\n"
                f"Stok Tersisa: {stok} unit\n"
                f"Threshold: {threshold} unit\n"
                f"Waktu: {datetime.now().strftime('%H:%M:%S')}"
            )
            
            await self.bot.send_message(
                chat_id=admin_id,
                text=msg,
                parse_mode="Markdown"
            )
            logger.info(f"Low stock alert sent for product: {product_name}")
        except Exception as e:
            logger.error(f"Error sending low stock alert: {e}")
    
    async def send_daily_report(self):
        """
        Kirim laporan harian ke admin (biasanya dijadwal setiap hari).
        """
        if not self.available:
            return
        
        admin_id = self.config_manager.config.get("admin_chat_id")
        if not admin_id:
            return
        
        try:
            laporan = self.report_generator.get_laporan_harian()
            
            msg = (
                f"📊 *LAPORAN HARIAN*\n"
                f"Tanggal: {laporan['tanggal']}\n\n"
                f"💰 Total Penjualan: {format_rp(laporan['total_penjualan'])}\n"
                f"📝 Total Transaksi: {laporan['total_transaksi']}\n"
                f"📊 Rata-rata: {format_rp(int(laporan['rata_rata_transaksi']))}\n"
            )
            
            await self.bot.send_message(
                chat_id=admin_id,
                text=msg,
                parse_mode="Markdown"
            )
            logger.info("Daily report sent to admin")
        except Exception as e:
            logger.error(f"Error sending daily report: {e}")
    
    # ========================================================================
    # BOT LIFECYCLE
    # ========================================================================
    
    def start(self):
        """Start bot polling."""
        if not self.available:
            print("❌ Bot tidak dapat dimulai (config tidak lengkap)")
            return
        
        print("\n" + "=" * 70)
        print("🤖 TELEGRAM BOT SEDANG BERJALAN".center(70))
        print("=" * 70)
        print(f"Bot Token: {self.config_manager.get_token()[:20]}...")
        print(f"Admin Chat ID: {self.config_manager.config.get('admin_chat_id')}")
        print(f"Allowed Users: {len(self.config_manager.config.get('allowed_chat_ids', []))}")
        print("=" * 70)
        print("\n💡 Tips:")
        print("   - Bot sedang menunggu commands Telegram")
        print("   - Kirim /start atau /help untuk test")
        print("   - Tekan CTRL+C untuk menghentikan")
        print("=" * 70 + "\n")
        
        try:
            # Fix for Windows asyncio event loop issue
            import asyncio
            import sys
            
            # On Windows, we need special event loop handling
            if sys.platform == 'win32':
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            
            # Run polling with better error logging
            self.application.run_polling(allowed_updates=Update.ALL_TYPES)
        except KeyboardInterrupt:
            print("\n\n❌ Bot dihentikan oleh user")
        except Exception as e:
            print(f"\n\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            logger.error(f"Error starting bot: {e}", exc_info=True)
    
    def stop(self):
        """Stop bot."""
        if self.application:
            self.application.stop()
            print("Bot stopped")

# ============================================================================
# TESTING & HELPER FUNCTIONS
# ============================================================================

def setup_telegram_config(bot_token: str, admin_chat_id: int):
    """
    Setup Telegram config dengan token dan admin ID.
    Utility function untuk quick setup.
    
    Args:
        bot_token (str): Telegram bot token
        admin_chat_id (int): Admin chat ID
    """
    config_manager = TelegramConfigManager()
    
    config_manager.config["bot_token"] = bot_token
    config_manager.config["admin_chat_id"] = admin_chat_id
    config_manager.config["enabled"] = True
    config_manager.config["allowed_chat_ids"] = [admin_chat_id]
    
    config_manager.save_config()
    print(f"✅ Telegram config updated!")
    print(f"   Bot Token: {bot_token[:20]}...")
    print(f"   Admin ID: {admin_chat_id}")

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("POS TELEGRAM BOT - Starting".center(70))
    print("=" * 70)
    
    # Check dependencies
    if not TELEGRAM_AVAILABLE:
        print("\n❌ python-telegram-bot tidak terinstall!")
        print("Install dengan command:")
        print("   pip install python-telegram-bot requests")
        exit(1)
    
    # Inisialisasi bot
    bot = POSTelegramBot()
    
    if not bot.available:
        print("\n⚠️ Bot tidak siap. Edit 'telegram_config.json' terlebih dahulu:")
        print("   1. Dapatkan bot token dari BotFather (@BotFather) di Telegram")
        print("   2. Edit telegram_config.json:")
        print("      - Set bot_token dengan token dari BotFather")
        print("      - Set admin_chat_id dengan ID Telegram Anda")
        print("      - Set 'enabled': true")
        print("   3. Jalankan lagi file ini")
        exit(1)
    
    # Start bot
    bot.start()
