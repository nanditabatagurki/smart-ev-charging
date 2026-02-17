# Smart EV Charging Controller 🚗⚡

Automatically control your EV charging based on real-time ComEd electricity pricing. Save money by charging when prices are low!

## Overview

This system monitors ComEd's hourly electricity pricing and intelligently controls your EV charging through OnStar/MyGMC:

1. **Price Check**: Fetches current ComEd hourly pricing
2. **Decision Logic**: Compares price to your threshold
3. **Battery Monitoring**: Gets battery level via MQTT from your vehicle
4. **Smart Control**: Starts/stops charging based on price and battery level
5. **Notifications**: Sends SMS alerts for charging decisions

## Features

- ✅ Real-time ComEd pricing monitoring
- ✅ MQTT integration with OnStar2MQTT
- ✅ Configurable price thresholds
- ✅ Smart battery management (min/max levels)
- ✅ SMS notifications via email-to-SMS
- ✅ Docker containerized for easy deployment
- ✅ Automatic reconnection and error handling

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   ComEd     │────▶│   Smart      │────▶│  Mosquitto  │
│  Pricing    │     │  Charging    │     │    MQTT     │
│   API       │     │  Controller  │     │   Broker    │
└─────────────┘     └──────────────┘     └─────────────┘
                           │                     ▲
                           │                     │
                           ▼                     │
                    ┌──────────────┐             │
                    │     SMS      │             │
                    │ Notification │             │
                    └──────────────┘             │
                                                 │
                    ┌──────────────┐             │
                    │ OnStar2MQTT  │─────────────┘
                    │   Bridge     │
                    └──────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   Your EV    │
                    │  (GMC/Chevy) │
                    └──────────────┘
```

## Prerequisites

- Docker and Docker Compose installed
- GMC/Chevrolet EV with OnStar account
- OnStar DeviceID (see [OnStar2MQTT docs](https://github.com/bigthundersr/onstar2mqtt))
- (Optional) Gmail account for SMS notifications

## Quick Start

### 1. Clone or Download Files

Ensure you have these files in your project directory:
```
smart-ev-charging/
├── smart_ev_charging.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your details:

```bash
cp .env.example .env
```

Edit `.env`:

```bash
# OnStar Configuration (from OnStar2MQTT setup)
ONSTAR_DEVICEID=your-device-id-here
ONSTAR_VIN=your-vin
ONSTAR_USERNAME=your-onstar-email@example.com
ONSTAR_PASSWORD=your-onstar-password
ONSTAR_PIN=1234

# Vehicle Configuration
VEHICLE_VIN=your_vin

# Charging Thresholds
CHARGE_PRICE_THRESHOLD_CENTS=3.0  # Charge when price < 5¢/kWh
MIN_CHARGE_LEVEL=20  # Emergency charge if below 20%
MAX_CHARGE_LEVEL=90  # Stop charging at 90%
CHECK_INTERVAL_SECONDS=300  # Check every 5 minutes

# SMS Notifications (Optional)
EMAIL=your-email@gmail.com
EMAIL_PASSWORD=your-app-specific-password
PHONE_NUMBER=your-phone-number
CARRIER_GATEWAY=txt.att.net  # See carrier list below
```

### 3. Build and Run

```bash
# Build the smart charging container
docker-compose build

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f smart-charging
```

### 4. Monitor Operation

```bash
# View smart charging logs
docker-compose logs -f smart-charging

# View MQTT messages
docker-compose logs -f onstar2mqtt

# Check all services status
docker-compose ps
```

## Configuration Details

### Price Threshold

Set your maximum charging price in cents per kWh:
```bash
CHARGE_PRICE_THRESHOLD_CENTS=5.0  # Charge only when ≤ 5¢/kWh
```

ComEd typical pricing ranges:
- Off-peak (night): 2-4 ¢/kWh ⚡ **Best time**
- Mid-peak: 5-8 ¢/kWh
- Peak (afternoon): 10-20+ ¢/kWh 💸 **Avoid**

### Battery Levels

```bash
MIN_CHARGE_LEVEL=20  # Force charge if below this (emergency)
MAX_CHARGE_LEVEL=90  # Stop charging at this level
```

### Check Interval

```bash
CHECK_INTERVAL_SECONDS=300  # Check every 5 minutes
```

ComEd updates pricing every 5 minutes, so checking every 5 minutes is optimal.

### SMS Carrier Gateways

Common carrier email-to-SMS gateways:

| Carrier | Gateway |
|---------|---------|
| AT&T | txt.att.net |
| Verizon | vtext.com |
| T-Mobile | tmomail.net |
| Sprint | messaging.sprintpcs.com |
| US Cellular | email.uscc.net |
| Boost Mobile | sms.myboostmobile.com |

**Gmail App Password Setup:**
1. Go to Google Account Settings
2. Security → 2-Step Verification (enable if not already)
3. App passwords → Generate new app password
4. Use this password in `EMAIL_PASSWORD`

## How It Works

### Charging Decision Logic

```python
if battery_level < MIN_CHARGE_LEVEL:
    # Emergency: Always charge
    START_CHARGING()
    
elif battery_level >= MAX_CHARGE_LEVEL:
    # Full: Stop charging
    STOP_CHARGING()
    
elif current_price <= CHARGE_PRICE_THRESHOLD_CENTS:
    # Good price: Start charging
    START_CHARGING()
    
else:
    # Too expensive: Stop charging
    STOP_CHARGING()
```

### Example Scenarios

**Scenario 1: Late Night (2 AM)**
- ComEd Price: 3.2 ¢/kWh ✅
- Battery: 45%
- Action: **START CHARGING** (price below threshold)
- SMS: "⚡ Charging STARTED\nPrice: 3.2¢/kWh\nBattery: 45%"

**Scenario 2: Afternoon Peak (4 PM)**
- ComEd Price: 15.8 ¢/kWh ❌
- Battery: 65%
- Action: **STOP CHARGING** (price too high)
- SMS: "🛑 Charging STOPPED\nPrice: 15.8¢/kWh\nBattery: 65%"

**Scenario 3: Emergency Low Battery**
- ComEd Price: 12.0 ¢/kWh ❌
- Battery: 18% ⚠️
- Action: **START CHARGING** (emergency override)
- SMS: "⚡ Charging STARTED\nPrice: 12.0¢/kWh\nBattery: 18%"

## MQTT Topics

The system uses these MQTT topics:

**Subscribe (Monitor Battery):**
```
homeassistant/sensor/{VIN}/high_voltage_battery/state
```

**Publish (Control Charging):**
```
homeassistant/sensor/{VIN}/charge_override/command
```
Payload: `START` or `STOP`

### Testing MQTT Manually

```bash
# Subscribe to all topics
docker exec -it mosquitto mosquitto_sub -t "#" -v

# Subscribe to battery updates
docker exec -it mosquitto mosquitto_sub -t "homeassistant/sensor/+/high_voltage_battery/state"

# Publish charge command manually
docker exec -it mosquitto mosquitto_pub -t "homeassistant/sensor/your-vin/charge_override/command" -m "START"
```

## Troubleshooting

### No MQTT Messages

```bash
# Check OnStar2MQTT logs
docker-compose logs onstar2mqtt

# Verify MQTT broker is running
docker-compose ps mosquitto

# Test MQTT connection
docker exec -it mosquitto mosquitto_sub -t "#" -v
```

### No Price Data

```bash
# Check smart charging logs
docker-compose logs smart-charging

# Test ComEd API manually
curl "https://hourlypricing.comed.com/api?type=5minutefeed"
```

### Not Starting/Stopping Charging

1. Verify vehicle is plugged in
2. Check OnStar subscription is active
3. Verify VIN is correct in `.env`
4. Check MQTT command topic format
5. Review OnStar2MQTT documentation for your vehicle model

### SMS Not Working

1. Verify Gmail app password (not regular password)
2. Check carrier gateway is correct
3. Ensure 2-factor auth is enabled on Gmail
4. Try sending test email to `{phone}@{gateway}`

## Advanced Usage

### Running Without Docker

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export MQTT_HOST=localhost
export VEHICLE_VIN=your_vin
# ... (set other variables)

# Run
python smart_ev_charging.py
```

### Custom MQTT Topics

Edit `smart_ev_charging.py` and modify these lines:

```python
# Battery state topic
battery_topic = f"homeassistant/sensor/{self.vehicle_vin}/high_voltage_battery/state"

# Command topic
command_topic = f"homeassistant/sensor/{self.vehicle_vin}/charge_override/command"
```

### Different Check Intervals

For real-time pricing updates:
```bash
CHECK_INTERVAL_SECONDS=60  # Check every minute
```

For slower, less frequent checks:
```bash
CHECK_INTERVAL_SECONDS=900  # Check every 15 minutes
```

## Maintenance

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f smart-charging
docker-compose logs -f onstar2mqtt
docker-compose logs -f mosquitto
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart smart-charging
```

### Update

```bash
# Pull latest changes
git pull  # if using git

# Rebuild and restart
docker-compose down
docker-compose build
docker-compose up -d
```

## Cost Savings Example

**Without Smart Charging:**
- 60 kWh charge @ 10¢/kWh average = $6.00

**With Smart Charging:**
- 60 kWh charge @ 3.5¢/kWh off-peak = $2.10

**Savings: $3.90 per charge** (65% reduction!)

If charging 3x per week:
- **Monthly savings: ~$47**
- **Annual savings: ~$560**

## Safety Notes

⚠️ **Important Considerations:**

1. **Always maintain minimum charge** for emergencies
2. **Don't set MAX_CHARGE too low** if you need range
3. **Monitor for the first few days** to ensure proper operation
4. **Keep OnStar subscription active**
5. **Vehicle must be plugged in** for commands to work

## Contributing

Feel free to submit issues and enhancement requests!

## License

MIT License - feel free to modify and use as needed.

## Support

For issues:
1. Check the troubleshooting section
2. Review Docker logs
3. Verify configuration in `.env`
4. Test MQTT connectivity
5. Check OnStar2MQTT documentation

---

**Happy Smart Charging! ⚡🚗💰**
