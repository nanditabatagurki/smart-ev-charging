"""
Test ComEd Pricing API
This script helps verify you can fetch pricing data from ComEd.
"""

import requests
import json
from datetime import datetime

def test_comed_api():
    """Test ComEd hourly pricing API."""
    
    print("🧪 ComEd Pricing API Test")
    print("="*80)
    print()
    
    try:
        # ComEd 5-minute pricing feed
        url = "https://hourlypricing.comed.com/api?type=5minutefeed"
        print(f"📡 Fetching data from: {url}")
        print()
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        print(f"✅ Successfully fetched data!")
        print(f"📊 Number of price points: {len(data)}")
        print("="*80)
        print()
        
        # Display the most recent prices
        print("💰 MOST RECENT PRICES:")
        print("-"*80)
        
        for i, entry in enumerate(data[:5]):  # Show first 5 entries
            milliseconds = int(entry.get('millisUTC', 0))
            price = float(entry.get('price', 0))
            
            # Convert milliseconds to datetime
            timestamp = datetime.fromtimestamp(milliseconds / 1000.0)
            
            print(f"\n#{i+1}:")
            print(f"  Time: {timestamp.strftime('%Y-%m-%d %I:%M %p')}")
            print(f"  Price: {price:.2f} ¢/kWh")
            
            # Add pricing advice
            if price <= 3.0:
                print(f"  💚 EXCELLENT - Great time to charge!")
            elif price <= 5.0:
                print(f"  🟢 GOOD - Reasonable charging price")
            elif price <= 8.0:
                print(f"  🟡 MODERATE - Consider waiting if not urgent")
            elif price <= 12.0:
                print(f"  🟠 HIGH - Avoid charging unless necessary")
            else:
                print(f"  🔴 VERY HIGH - Definitely avoid charging!")
        
        print("\n" + "="*80)
        print()
        
        # Calculate statistics
        prices = [float(entry.get('price', 0)) for entry in data]
        avg_price = sum(prices) / len(prices) if prices else 0
        min_price = min(prices) if prices else 0
        max_price = max(prices) if prices else 0
        
        print("📈 PRICE STATISTICS (Recent period):")
        print("-"*80)
        print(f"  Average: {avg_price:.2f} ¢/kWh")
        print(f"  Minimum: {min_price:.2f} ¢/kWh")
        print(f"  Maximum: {max_price:.2f} ¢/kWh")
        print()
        
        # Show raw JSON of first entry
        print("="*80)
        print("📋 RAW DATA (First Entry):")
        print("-"*80)
        print(json.dumps(data[0], indent=2))
        print()
        
        # Recommendations
        current_price = prices[0] if prices else 0
        print("="*80)
        print("💡 RECOMMENDATIONS:")
        print("-"*80)
        print(f"  Current Price: {current_price:.2f} ¢/kWh")
        print()
        
        if current_price <= 4.0:
            threshold = 5.0
            print(f"  ✅ Suggested Threshold: {threshold:.1f} ¢/kWh")
            print(f"  📝 Current price is excellent! Set threshold around {threshold:.1f}¢")
        elif current_price <= 8.0:
            threshold = current_price + 1.0
            print(f"  ⚠️  Suggested Threshold: {threshold:.1f} ¢/kWh")
            print(f"  📝 Current price is moderate. Set threshold slightly above current.")
        else:
            threshold = 6.0
            print(f"  ❌ Suggested Threshold: {threshold:.1f} ¢/kWh")
            print(f"  📝 Current price is high. Set lower threshold to catch off-peak prices.")
        
        print()
        print(f"  Add to your .env file:")
        print(f"  CHARGE_PRICE_THRESHOLD_CENTS={threshold:.1f}")
        print()
        
        return True
        
    except requests.RequestException as e:
        print(f"❌ Error fetching data: {e}")
        print()
        print("Troubleshooting:")
        print("  1. Check your internet connection")
        print("  2. Verify the API URL is still valid")
        print("  3. Try accessing the URL in your browser:")
        print(f"     {url}")
        return False
        
    except (ValueError, KeyError) as e:
        print(f"❌ Error parsing response: {e}")
        print()
        print("The API response format may have changed.")
        print("Please check the ComEd API documentation.")
        return False

def main():
    """Run the test."""
    success = test_comed_api()
    
    print("="*80)
    if success:
        print("✅ TEST PASSED - ComEd API is working!")
    else:
        print("❌ TEST FAILED - Please check the errors above")
    print("="*80)

if __name__ == "__main__":
    main()
