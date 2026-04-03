#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Low Stock Telegram Notifications

Menguji fitur pengiriman notifikasi Telegram ketika stok produk < 5 unit.
"""

import sys
import os
import json
import logging
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import modules
from database import DatabaseManager
from telegram_bot import POSTelegramBot, TELEGRAM_AVAILABLE
from models import Product


class MockTelegramBot:
    """Mock Telegram Bot for testing"""
    
    def __init__(self):
        self.sent_messages = []
        self.available = True
    
    def send_low_stock_alert_sync(self, product_name: str, stok: int) -> bool:
        """Mock send_low_stock_alert_sync method"""
        msg = f"⚠️ Stok minim: {product_name} - sisa {stok}"
        self.sent_messages.append({
            'message': msg,
            'product_name': product_name,
            'stok': stok,
            'timestamp': datetime.now()
        })
        logger.info(f"✅ Mock notification sent: {msg}")
        return True


def test_low_stock_alert_threshold():
    """Test 1: Verify low stock alert triggered when stock < 5"""
    print("\n" + "="*70)
    print("TEST 1: Low Stock Alert Trigger at < 5 units")
    print("="*70)
    
    try:
        # Setup mock telegram bot
        mock_telegram = MockTelegramBot()
        
        # Initialize database with mock telegram bot
        db = DatabaseManager(db_name="test_low_stock.db", telegram_bot=mock_telegram)
        
        # Add test product with stok = 7
        success = db.add_product("TEST001", "Test Coffee", 10000, 7)
        assert success, "Failed to add test product"
        
        products = db.get_all_products()
        test_product = [p for p in products if p['kode'] == 'TEST001'][0]
        product_id = test_product['id']
        
        logger.info(f"Created test product: {test_product['nama']} with stock={test_product['stok']}")
        
        # Test 1a: Reduce stock from 7 to 2 (should TRIGGER alert)
        logger.info("Reducing stock from 7 to 2 units (should TRIGGER alert)")
        success = db.reduce_stock(product_id, 5)
        assert success, "Stock reduction failed"
        
        if mock_telegram.sent_messages:
            alert = mock_telegram.sent_messages[-1]
            logger.info(f"Alert triggered: {alert['message']}")
            logger.info(f"   - Product: {alert['product_name']}")
            logger.info(f"   - Stock: {alert['stok']}")
            assert alert['stok'] == 2, f"Expected stock=2, got {alert['stok']}"
            print("TEST 1 PASSED: Alert triggered when stock < 5")
        else:
            logger.error("No alert sent when stock < 5")
            return False
        
        # Cleanup
        os.remove("test_low_stock.db")
        
        return True
        
    except Exception as e:
        logger.error(f"TEST 1 FAILED: {e}", exc_info=True)
        if os.path.exists("test_low_stock.db"):
            os.remove("test_low_stock.db")
        return False


def test_no_alert_when_telegram_disabled():
    """Test 2: Verify NO alert sent when telegram_bot is None"""
    print("\n" + "="*70)
    print("TEST 2: No Alert When Telegram Disabled")
    print("="*70)
    
    try:
        # Initialize database WITHOUT telegram bot
        db = DatabaseManager(db_name="test_low_stock_disabled.db", telegram_bot=None)
        
        # Add test product with stok = 7
        success = db.add_product("TEST002", "Test Product", 10000, 7)
        assert success, "Failed to add test product"
        
        products = db.get_all_products()
        test_product = [p for p in products if p['kode'] == 'TEST002'][0]
        product_id = test_product['id']
        
        logger.info(f"Created test product with stock={test_product['stok']}")
        
        # Reduce stock below 5
        logger.info("Reducing stock to 2 units (telegram_bot=None)")
        success = db.reduce_stock(product_id, 5)
        assert success, "Stock reduction failed"
        
        logger.info("Stock reduced successfully (no alert sent because telegram_bot=None)")
        print("TEST 2 PASSED: No alert when Telegram is disabled")
        
        # Cleanup
        os.remove("test_low_stock_disabled.db")
        
        return True
        
    except Exception as e:
        logger.error(f"TEST 2 FAILED: {e}", exc_info=True)
        if os.path.exists("test_low_stock_disabled.db"):
            os.remove("test_low_stock_disabled.db")
        return False


def test_no_alert_when_stock_above_threshold():
    """Test 3: Verify NO alert when stock >= 5"""
    print("\n" + "="*70)
    print("TEST 3: No Alert When Stock >= 5 units")
    print("="*70)
    
    try:
        # Setup mock telegram bot
        mock_telegram = MockTelegramBot()
        
        # Initialize database
        db = DatabaseManager(db_name="test_stock_above.db", telegram_bot=mock_telegram)
        
        # Add test product with stok = 10
        success = db.add_product("TEST003", "Test Product High Stock", 10000, 10)
        assert success, "Failed to add test product"
        
        products = db.get_all_products()
        test_product = [p for p in products if p['kode'] == 'TEST003'][0]
        product_id = test_product['id']
        
        logger.info(f"Created test product with stock={test_product['stok']}")
        
        # Reduce stock from 10 to 7 (still >= 5)
        logger.info("Reducing stock from 10 to 7 units")
        initial_alerts = len(mock_telegram.sent_messages)
        success = db.reduce_stock(product_id, 3)
        assert success, "Stock reduction failed"
        
        if len(mock_telegram.sent_messages) == initial_alerts:
            logger.info("No alert sent (stock=7 is >= 5)")
            print("TEST 3 PASSED: No alert when stock >= 5")
        else:
            logger.error(f"Alert sent when it shouldn't be: {mock_telegram.sent_messages[-1]}")
            return False
        
        # Cleanup
        os.remove("test_stock_above.db")
        
        return True
        
    except Exception as e:
        logger.error(f"TEST 3 FAILED: {e}", exc_info=True)
        if os.path.exists("test_stock_above.db"):
            os.remove("test_stock_above.db")
        return False


def test_multiple_products_reduce_below_threshold():
    """Test 4: Verify multiple alerts for multiple products going below threshold"""
    print("\n" + "="*70)
    print("TEST 4: Multiple Products Low Stock Alerts")
    print("="*70)
    
    try:
        # Setup mock telegram bot
        mock_telegram = MockTelegramBot()
        
        # Initialize database
        db = DatabaseManager(db_name="test_multiple_products.db", telegram_bot=mock_telegram)
        
        # Add multiple test products
        test_data = [
            ("PROD001", "Coffee Beans", 10),
            ("PROD002", "Tea Leaves", 15),
            ("PROD003", "Sugar", 8),
        ]
        
        for kode, nama, stok in test_data:
            success = db.add_product(kode, nama, 10000, stok)
            assert success, f"Failed to add {nama}"
        
        products = db.get_all_products()
        
        # Reduce each product below 5
        logger.info("Reducing multiple products below threshold...")
        for product in products:
            if product['kode'].startswith('PROD'):
                reduce_qty = product['stok'] - 2  # Reduce to 2 units
                logger.info(f"  - Reducing {product['nama']} by {reduce_qty}")
                success = db.reduce_stock(product['id'], reduce_qty)
                assert success, f"Failed to reduce {product['nama']}"
        
        # Verify alerts sent for all 3 products
        if len(mock_telegram.sent_messages) == 3:
            logger.info(f"All 3 alerts sent:")
            for alert in mock_telegram.sent_messages:
                logger.info(f"   - {alert['message']}")
            print("TEST 4 PASSED: Multiple product alerts working")
        else:
            logger.error(f"Expected 3 alerts, got {len(mock_telegram.sent_messages)}")
            return False
        
        # Cleanup
        os.remove("test_multiple_products.db")
        
        return True
        
    except Exception as e:
        logger.error(f"TEST 4 FAILED: {e}", exc_info=True)
        if os.path.exists("test_multiple_products.db"):
            os.remove("test_multiple_products.db")
        return False


def run_all_tests():
    """Run all low stock alert tests"""
    print("\n" + "="*70)
    print("LOW STOCK TELEGRAM NOTIFICATION TESTS")
    print("="*70)
    
    tests = [
        ("Low Stock Alert Threshold", test_low_stock_alert_threshold),
        ("Alert Disabled When Telegram Off", test_no_alert_when_telegram_disabled),
        ("Alert Disabled When Stock >= 5", test_no_alert_when_stock_above_threshold),
        ("Multiple Products Low Stock", test_multiple_products_reduce_below_threshold),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"Unexpected error in {test_name}: {e}")
            results[test_name] = False
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    for test_name, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status}: {test_name}")
    
    print("="*70 + "\n")
    
    return all(results.values())


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
