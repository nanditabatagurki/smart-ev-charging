"""
Test MQTT Connection and Battery Monitoring
This script helps verify your MQTT setup is working correctly.
"""

import json
import time
import paho.mqtt.client as mqtt

# Configuration
MQTT_HOST = "mosquitto"  # Change to "localhost" if running outside Docker
MQTT_PORT = 1883
VEHICLE_VIN = "your-vin"  # Replace with your VIN

def on_connect(client, userdata, flags, reason_code, properties):
    """Callback when connected to MQTT broker."""
    print(f"✅ Connected to MQTT broker with result code: {reason_code}")
    print("="*80)
    
    # Subscribe to all homeassistant topics
    client.subscribe("homeassistant/#")
    print("📡 Subscribed to: homeassistant/#")
    print("Waiting for messages...\n")

def on_message(client, userdata, msg):
    """Callback when a message is received."""
    print(f"📨 Topic: {msg.topic}")
    print("-"*80)
    
    try:
        # Try to parse as JSON and pretty print
        payload = json.loads(msg.payload.decode())
        print("Payload (formatted):")
        print(json.dumps(payload, indent=2))
        
        # If this is battery data, highlight key info
        if "high_voltage_battery" in msg.topic:
            print("\n🔋 BATTERY INFO:")
            print(f"  - Charge Level: {payload.get('charge_state', 'N/A')}%")
            print(f"  - Range: {payload.get('ev_range_mi', 'N/A')} miles")
            print(f"  - Plugged In: {payload.get('ev_plug_state', 'N/A')}")
            print(f"  - Charging: {payload.get('ev_charge_state', 'N/A')}")
            print(f"  - Temperature: {payload.get('ambient_air_temperature_f', 'N/A')}°F")
        
    except json.JSONDecodeError:
        # If not JSON, just print as is
        print(f"Payload (raw): {msg.payload.decode()}")
    
    print("="*80)
    print()

def main():
    """Main test function."""
    print("🧪 MQTT Battery Monitor Test")
    print("="*80)
    print(f"MQTT Host: {MQTT_HOST}")
    print(f"MQTT Port: {MQTT_PORT}")
    print(f"Vehicle VIN: {VEHICLE_VIN}")
    print("="*80)
    print()
    
    # Create MQTT client
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        print("Connecting to MQTT broker...")
        client.connect(MQTT_HOST, MQTT_PORT, 60)
        
        print("Starting MQTT loop...")
        print("Press Ctrl+C to stop\n")
        
        # Start the loop
        client.loop_forever()
        
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping...")
        client.disconnect()
        print("✅ Disconnected from MQTT broker")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("  1. Is mosquitto container running? (docker ps)")
        print("  2. Is onstar2mqtt container running? (docker ps)")
        print("  3. Are they on the same network? (docker network inspect ev-network)")
        print("  4. Try running: docker-compose logs mosquitto")

if __name__ == "__main__":
    main()
