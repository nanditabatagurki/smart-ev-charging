"""
Smart EV Charging Controller
Monitors ComEd hourly pricing and controls EV charging via MQTT based on price thresholds.
Sends SMS notifications for charging decisions.
"""

import os
import time
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any

import requests
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

# Email to SMS notification (assuming you have this module)
# from email_to_sms_notifier import EmailToSMSNotifier

# Load environment variables
load_dotenv()

# Configure logging with color support
class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for terminal output."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # Emoji icons
    ICONS = {
        'DEBUG': '🔍',
        'INFO': 'ℹ️ ',
        'WARNING': '⚠️ ',
        'ERROR': '❌',
        'CRITICAL': '🚨',
    }
    
    def format(self, record):
        # Get color and icon for log level
        color = self.COLORS.get(record.levelname, '')
        icon = self.ICONS.get(record.levelname, '')
        
        # Format timestamp
        timestamp = self.formatTime(record, '%Y-%m-%d %H:%M:%S')
        
        # Build formatted message
        log_msg = f"{color}{icon} [{timestamp}] {record.levelname}{self.RESET}"
        log_msg += f" | {record.getMessage()}"
        
        return log_msg

# Set up logger with colored formatter
handler = logging.StreamHandler()
handler.setFormatter(ColoredFormatter())

logging.basicConfig(
    level=logging.INFO,
    handlers=[handler]
)
logger = logging.getLogger(__name__)


class ComEdPriceChecker:
    """Fetches current hourly electricity pricing from ComEd API."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://hourlypricing.comed.com/api"
    
    def get_current_price(self) -> Optional[float]:
        """
        Get current hourly price in cents per kWh.
        
        Returns:
            float: Current price in cents/kWh, or None if request fails
        """
        try:
            # Get current price (5-minute intervals)
            url = f"{self.base_url}?type=5minutefeed"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # The API returns a list, get the most recent price
            if data and len(data) > 0:
                latest = data[0]
                price = float(latest.get('price', 0))
                
                # Add visual indicators based on price
                if price <= 3.0:
                    indicator = "💚 EXCELLENT"
                elif price <= 5.0:
                    indicator = "🟢 GOOD"
                elif price <= 8.0:
                    indicator = "🟡 MODERATE"
                elif price <= 12.0:
                    indicator = "🟠 HIGH"
                else:
                    indicator = "🔴 VERY HIGH"
                
                logger.info(f"💰 ComEd Price: {price:.2f}¢/kWh | {indicator}")
                return price
            
            logger.warning("No pricing data returned from ComEd API")
            return None
            
        except requests.RequestException as e:
            logger.error(f"Error fetching ComEd price: {e}")
            return None
        except (ValueError, KeyError) as e:
            logger.error(f"Error parsing ComEd response: {e}")
            return None


class EVBatteryMonitor:
    """Monitors EV battery status via MQTT."""
    
    def __init__(self, mqtt_host: str, mqtt_port: int, vehicle_vin: str):
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.vehicle_vin = vehicle_vin
        self.battery_state: Dict[str, Any] = {}
        self.connected = False
        
        # MQTT Client setup
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
    
    def _on_connect(self, client, userdata, flags, reason_code, properties):
        """Callback when connected to MQTT broker."""
        self.connected = True
        logger.info(f"Connected to MQTT broker with result code: {reason_code}")
        
        # Subscribe to battery state topic
        battery_topic = f"homeassistant/sensor/{self.vehicle_vin}/high_voltage_battery/state"
        client.subscribe(battery_topic)
        logger.info(f"Subscribed to: {battery_topic}")
    
    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        """Callback when disconnected from MQTT broker."""
        self.connected = False
        logger.warning(f"Disconnected from MQTT broker: {reason_code}")
    
    def _on_message(self, client, userdata, msg):
        """Callback when a message is received."""
        try:
            payload = json.loads(msg.payload.decode())
            self.battery_state = payload
            
            charge_level = payload.get('charge_state', 0)
            ev_range = payload.get('ev_range_mi', 0)
            plug_state = payload.get('ev_plug_state', False)
            charge_state = payload.get('ev_charge_state', False)
            temp = payload.get('ambient_air_temperature_f', 0)
            
            # Create a nice formatted battery status
            plug_icon = "🔌" if plug_state else "🔋"
            charge_icon = "⚡" if charge_state else "🛑"
            
            logger.info(f"{plug_icon} Battery: {charge_level}% | Range: {ev_range:.1f} mi | "
                       f"Temp: {temp}°F | {charge_icon} {'Charging' if charge_state else 'Not Charging'}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing MQTT message: {e}")
    
    def connect(self):
        """Connect to MQTT broker."""
        try:
            self.client.connect(self.mqtt_host, self.mqtt_port, 60)
            self.client.loop_start()
            
            # Wait for connection
            timeout = 10
            start_time = time.time()
            while not self.connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if not self.connected:
                logger.error("Failed to connect to MQTT broker within timeout")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to MQTT broker: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker."""
        self.client.loop_stop()
        self.client.disconnect()
    
    def get_charge_level(self) -> Optional[int]:
        """Get current battery charge level percentage."""
        return self.battery_state.get('charge_state')
    
    def is_plugged_in(self) -> bool:
        """Check if vehicle is plugged in."""
        return self.battery_state.get('ev_plug_state', False)
    
    def is_charging(self) -> bool:
        """Check if vehicle is currently charging."""
        return self.battery_state.get('ev_charge_state', False)
    
    def publish_charge_command(self, start_charging: bool):
        """
        Publish command to start or stop charging.
        
        Args:
            start_charging: True to start charging, False to stop
        """
        # This topic format may need adjustment based on your onstar2mqtt setup
        command_topic = f"homeassistant/sensor/{self.vehicle_vin}/charge_override/command"
        command = "START" if start_charging else "STOP"
        
        self.client.publish(command_topic, command)
        logger.info(f"Published charge command: {command} to {command_topic}")


class SMSNotifier:
    """Sends SMS notifications via email-to-SMS gateway."""
    
    def __init__(self, smtp_server: str, smtp_port: int, email: str, password: str, 
                 phone_number: str, carrier_gateway: str):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.email = email
        self.password = password
        self.sms_address = f"{phone_number}@{carrier_gateway}"
    
    def send_notification(self, message: str):
        """Send SMS notification."""
        try:
            import smtplib
            from email.mime.text import MIMEText
            
            msg = MIMEText(message)
            msg['Subject'] = 'EV Charging Alert'
            msg['From'] = self.email
            msg['To'] = self.sms_address
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email, self.password)
                server.send_message(msg)
            
            # Logging is now handled in the notify() method
            
        except Exception as e:
            logger.error(f"Error sending SMS: {e}")


class SmartEVChargingController:
    """Main controller for smart EV charging based on electricity pricing."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Initialize components
        self.price_checker = ComEdPriceChecker(config['COMED_API_KEY'])
        self.battery_monitor = EVBatteryMonitor(
            mqtt_host=config['MQTT_HOST'],
            mqtt_port=config['MQTT_PORT'],
            vehicle_vin=config['VEHICLE_VIN']
        )
        
        # Initialize SMS notifier if credentials provided
        self.sms_notifier = None
        if all(k in config for k in ['SMTP_SERVER', 'SMTP_PORT', 'EMAIL', 'EMAIL_PASSWORD', 
                                     'PHONE_NUMBER', 'CARRIER_GATEWAY']):
            self.sms_notifier = SMSNotifier(
                smtp_server=config['SMTP_SERVER'],
                smtp_port=config['SMTP_PORT'],
                email=config['EMAIL'],
                password=config['EMAIL_PASSWORD'],
                phone_number=config['PHONE_NUMBER'],
                carrier_gateway=config['CARRIER_GATEWAY']
            )
        
        self.charge_threshold = config['CHARGE_PRICE_THRESHOLD_CENTS']
        self.min_charge_level = config.get('MIN_CHARGE_LEVEL', 20)
        self.max_charge_level = config.get('MAX_CHARGE_LEVEL', 90)
        self.check_interval = config.get('CHECK_INTERVAL_SECONDS', 300)  # 5 minutes default
        
        self.currently_charging = False
    
    def notify(self, message: str):
        """Send notification if SMS is configured."""
        if self.sms_notifier:
            self.sms_notifier.send_notification(message)
            logger.info(f"📱 SMS sent: {message}")
        # Don't log if SMS is not configured - avoids misleading "Notification:" logs
    
    def should_charge(self, current_price: float, charge_level: int) -> bool:
        """
        Determine if vehicle should charge based on price and battery level.
        
        Args:
            current_price: Current electricity price in cents/kWh
            charge_level: Current battery charge level percentage
        
        Returns:
            bool: True if should charge, False otherwise
        """
        # Don't charge if battery is full enough
        if charge_level >= self.max_charge_level:
            logger.info(f"🔋 Battery sufficient: {charge_level}% (>= {self.max_charge_level}%) → No charging needed")
            return False
        
        # Always charge if battery is critically low
        if charge_level < self.min_charge_level:
            logger.warning(f"🚨 EMERGENCY: Battery low {charge_level}% (< {self.min_charge_level}%) → Force charging!")
            return True
        
        # Charge if price is below threshold
        if current_price <= self.charge_threshold:
            logger.info(f"💚 Good price: {current_price}¢ <= {self.charge_threshold}¢ → Ready to charge")
            return True
        
        logger.info(f"💸 Price too high: {current_price}¢ > {self.charge_threshold}¢ → Wait for better price")
        return False
    
    def control_charging(self):
        """Main control loop - check price and manage charging."""
        
        # Get current price
        current_price = self.price_checker.get_current_price()
        if current_price is None:
            logger.error("Could not get current price - skipping this cycle")
            return
        
        # Get battery status
        charge_level = self.battery_monitor.get_charge_level()
        if charge_level is None:
            logger.error("Could not get battery level - skipping this cycle")
            return
        
        plugged_in = self.battery_monitor.is_plugged_in()
        if not plugged_in:
            logger.info("Vehicle not plugged in - no action needed")
            if self.currently_charging:
                self.currently_charging = False
                self.notify(f"Vehicle unplugged. Battery: {charge_level}%")
            return
        
        # Determine if we should charge
        should_charge = self.should_charge(current_price, charge_level)
        is_charging = self.battery_monitor.is_charging()
        
        # Take action if state needs to change
        if should_charge and not is_charging:
            print("\n" + "─"*80)
            logger.info(f"⚡ STARTING CHARGE | Price: {current_price}¢/kWh | Battery: {charge_level}%")
            print("─"*80 + "\n")
            self.battery_monitor.publish_charge_command(start_charging=True)
            self.currently_charging = True
            self.notify(f"⚡ Charging STARTED\nPrice: {current_price}¢/kWh\nBattery: {charge_level}%")
            
        elif not should_charge and is_charging:
            print("\n" + "─"*80)
            logger.info(f"🛑 STOPPING CHARGE | Price: {current_price}¢/kWh | Battery: {charge_level}%")
            print("─"*80 + "\n")
            self.battery_monitor.publish_charge_command(start_charging=False)
            self.currently_charging = False
            self.notify(f"🛑 Charging STOPPED\nPrice: {current_price}¢/kWh\nBattery: {charge_level}%")
        
        else:
            status = "⚡ Charging" if is_charging else "🛑 Not Charging"
            logger.info(f"✓ No change needed | {status} | Price: {current_price}¢/kWh | Battery: {charge_level}%")
    
    def run(self):
        """Run the smart charging controller."""
        # Print startup banner
        print("\n" + "="*80)
        print("🚗⚡ SMART EV CHARGING CONTROLLER ⚡🚗".center(80))
        print("="*80)
        
        logger.info("Monitoring pricing and battery status to determine optimal charging")
        logger.info(f"💰 Charge threshold: {self.charge_threshold} cents/kWh")
        logger.info(f"🔋 Battery range: {self.min_charge_level}% - {self.max_charge_level}%")
        logger.info(f"⏱️  Check interval: {self.check_interval} seconds")
        logger.info(f"🚙 Vehicle VIN: {self.battery_monitor.vehicle_vin}")
        
        print("="*80 + "\n")
        
        # Connect to MQTT
        if not self.battery_monitor.connect():
            logger.error("Failed to connect to MQTT broker - exiting")
            return
        
        try:
            # Wait a moment for initial battery state
            time.sleep(2)
            
            # Don't send startup notification - only notify on actual charging decisions
            charge_level = self.battery_monitor.get_charge_level()
            if charge_level is not None:
                logger.info(f"🔋 Initial battery level: {charge_level}%")
            
            # Main control loop
            while True:
                try:
                    print("\n" + "┄"*80)
                    logger.info(f"🔄 Running check cycle...")
                    self.control_charging()
                    logger.info(f"⏰ Next check in {self.check_interval} seconds")
                    print("┄"*80 + "\n")
                except Exception as e:
                    logger.error(f"Error in control loop: {e}", exc_info=True)
                
                # Wait for next check
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            self.battery_monitor.disconnect()
            logger.info("Disconnected from MQTT broker")


def main():
    """Main entry point."""
    
    # Configuration from environment variables
    config = {
        'COMED_API_KEY': os.getenv('COMED_API_KEY', ''),  # API key if required
        'MQTT_HOST': os.getenv('MQTT_HOST', 'mosquitto'),
        'MQTT_PORT': int(os.getenv('MQTT_PORT', '1883')),
        'VEHICLE_VIN': os.getenv('VEHICLE_VIN', 'your-vin'),
        'CHARGE_PRICE_THRESHOLD_CENTS': float(os.getenv('CHARGE_PRICE_THRESHOLD_CENTS', '3.0')),
        'MIN_CHARGE_LEVEL': int(os.getenv('MIN_CHARGE_LEVEL', '20')),
        'MAX_CHARGE_LEVEL': int(os.getenv('MAX_CHARGE_LEVEL', '90')),
        'CHECK_INTERVAL_SECONDS': int(os.getenv('CHECK_INTERVAL_SECONDS', '300')),
        
        # SMS notification settings (optional)
        'SMTP_SERVER': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
        'SMTP_PORT': int(os.getenv('SMTP_PORT', '587')),
        'EMAIL': os.getenv('EMAIL', ''),
        'EMAIL_PASSWORD': os.getenv('EMAIL_PASSWORD', ''),
        'PHONE_NUMBER': os.getenv('PHONE_NUMBER', ''),
        'CARRIER_GATEWAY': os.getenv('CARRIER_GATEWAY', 'txt.att.net'),
    }
    
    # Validate required config
    if not config['VEHICLE_VIN']:
        logger.error("VEHICLE_VIN environment variable is required")
        return
    
    # Create and run controller
    controller = SmartEVChargingController(config)
    controller.run()


if __name__ == "__main__":
    main()
