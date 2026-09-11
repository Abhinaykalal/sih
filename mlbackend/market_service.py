"""
Market Price Service — Real-Time Integration
Pulls LIVE daily wholesale prices directly from the Government of India (data.gov.in).
Falls back to realistic mock data when API key is not configured.
"""
import requests
from datetime import datetime
try:
    from .config import settings
except ImportError:
    from config import settings


# Base MSP values mapping (₹/quintal) for logic insight generation
MANDI_MSP = {
    "rice": 2183, "wheat": 2275, "maize": 1962, "cotton": 6620,
    "soybean": 4600, "groundnut": 6377, "sugarcane": 315, "mustard": 5650,
}

# Mock market data for demo purposes (realistic Indian mandi prices)
MOCK_MARKET_DATA = {
    "rice": {
        "Maharashtra": [
            {"market": "Mumbai APMC", "price": 2350, "min": 2200, "max": 2450},
            {"market": "Pune Mandi", "price": 2280, "min": 2150, "max": 2380},
            {"market": "Nashik Market", "price": 2310, "min": 2180, "max": 2400},
            {"market": "Nagpur APMC", "price": 2260, "min": 2140, "max": 2350},
            {"market": "Aurangabad Mandi", "price": 2290, "min": 2170, "max": 2370},
        ],
        "Punjab": [
            {"market": "Ludhiana Mandi", "price": 2420, "min": 2300, "max": 2520},
            {"market": "Amritsar APMC", "price": 2380, "min": 2260, "max": 2480},
            {"market": "Jalandhar Market", "price": 2400, "min": 2280, "max": 2500},
        ],
    },
    "wheat": {
        "Maharashtra": [
            {"market": "Mumbai APMC", "price": 2450, "min": 2320, "max": 2550},
            {"market": "Pune Mandi", "price": 2380, "min": 2250, "max": 2480},
            {"market": "Nashik Market", "price": 2410, "min": 2280, "max": 2510},
        ],
        "Punjab": [
            {"market": "Ludhiana Mandi", "price": 2520, "min": 2400, "max": 2620},
            {"market": "Amritsar APMC", "price": 2480, "min": 2360, "max": 2580},
        ],
    },
    "cotton": {
        "Maharashtra": [
            {"market": "Akola APMC", "price": 6850, "min": 6500, "max": 7100},
            {"market": "Yavatmal Mandi", "price": 6780, "min": 6450, "max": 7050},
            {"market": "Nagpur Cotton Market", "price": 6820, "min": 6480, "max": 7080},
        ],
        "Gujarat": [
            {"market": "Rajkot APMC", "price": 6920, "min": 6580, "max": 7180},
            {"market": "Ahmedabad Mandi", "price": 6880, "min": 6540, "max": 7140},
        ],
    },
}

def _get_mock_market_prices(commodity: str, state: str) -> dict:
    """
    Returns mock market prices for demo purposes.
    Uses realistic Indian mandi price data.
    """
    comm = commodity.lower()
    
    # Get mock data for commodity and state
    commodity_data = MOCK_MARKET_DATA.get(comm, {})
    state_data = commodity_data.get(state, None)
    
    # Fallback to first available state if requested state not found
    if not state_data and commodity_data:
        state = list(commodity_data.keys())[0]
        state_data = commodity_data[state]
    
    # If still no data, use default rice Maharashtra
    if not state_data:
        comm = "rice"
        state = "Maharashtra"
        state_data = MOCK_MARKET_DATA["rice"]["Maharashtra"]
    
    # Calculate statistics
    prices_list = [m["price"] for m in state_data]
    avg_price = round(sum(prices_list) / len(prices_list))
    best_mkt = max(state_data, key=lambda x: x["price"])
    lowest_mkt = min(state_data, key=lambda x: x["price"])
    
    # Generate insights
    insights = []
    msp = MANDI_MSP.get(comm)
    
    if msp:
        if avg_price < msp:
            insights.append(f"⚠️ Warning: State average (₹{avg_price}) is BELOW Govt MSP (₹{msp}). Consider storing crop.")
        elif avg_price > msp * 1.15:
            insights.append(f"📈 Excellent! Average price is well ABOVE MSP. High demand detected.")
        else:
            insights.append(f"✅ Prices are stable around MSP (₹{msp}). Good time to sell.")
            
    diff_best_avg = round(((best_mkt["price"] - avg_price) / avg_price) * 100, 1)
    if diff_best_avg > 3:
        insights.append(f"💡 Selling at {best_mkt['market']} yields {diff_best_avg}% more profit than the state average.")
        
    insights.append(f"🏆 Highest price recorded at {best_mkt['market']} @ ₹{best_mkt['price']}/Quintal")
    insights.append("📊 Demo Mode: Using simulated mandi data. Add DATA_GOV_API_KEY for live prices.")

    return {
        "commodity": commodity.capitalize(),
        "state": state.title(),
        "current_price_inr": avg_price,
        "unit": "quintal",
        "msp": msp,
        "7_day_trend": [
            {"date": "7 days ago", "price": lowest_mkt['price'] - 50},
            {"date": "5 days ago", "price": avg_price - 30},
            {"date": "3 days ago", "price": avg_price - 10},
            {"date": "Yesterday", "price": avg_price + 5},
            {"date": "Today", "price": avg_price}
        ],
        "market_centers": [
            {"market": c["market"], "price": c["price"], "change_pct": round(((c["price"] - avg_price)/avg_price)*100,1)} 
            for c in state_data
        ],
        "market_insights": insights,
        "last_updated": datetime.now().strftime("%d %b %Y, %I:%M %p") + " (Demo Data)"
    }

def get_market_prices(commodity: str, state: str) -> dict:
    """
    Returns real-time market prices for a commodity in a state.
    Pulls directly from data.gov.in official Mandi data.
    Falls back to mock data if API key not configured.
    """
    if not commodity or not state:
        return {"error": "Missing commodity or state for price lookup"}

    comm = commodity.lower()
    
    # 1. Fetch real API Key (Environment only — no hardcoded fallbacks for security)
    API_KEY = settings.DATA_GOV_API_KEY
    if not API_KEY:
        # Fallback to mock data for demo purposes
        return _get_mock_market_prices(commodity, state)
        
    url = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
    params = {
        "api-key": API_KEY,
        "format": "json",
        "filters[state]": state.title(),
        "filters[commodity]": commodity.title(),
        "limit": "10",  # Get the top 10 market centers
        "sort[arrival_date]": "desc"
    }

    try:
        resp = requests.get(url, params=params, timeout=12)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return {"error": f"Govt API Connection Failed: {str(e)}"}

    records = data.get("records", [])
    if not records:
        return {"error": f"No recent Govt Mandi records found for '{commodity.title()}' in '{state.title()}'"}

    # 2. Extract Data for Top Market Centers
    center_prices = []
    prices_list = []
    
    latest_date = None
    for r in records:
        try:
            m_price = float(r.get("modal_price", 0))
            if m_price == 0: continue
            
            latest_date = r.get("arrival_date")
            prices_list.append(m_price)
            
            center_prices.append({
                "market": r.get("market", "Unknown Mandi"),
                "price": m_price,
                "min": float(r.get("min_price", 0)),
                "max": float(r.get("max_price", 0))
            })
        except ValueError:
            continue
            
    if not center_prices:
        return {"error": "Invalid price structure returned from Govt API."}

    # 3. Calculate AgriSaathi Stats
    avg_price = sum(prices_list) / len(prices_list)
    avg_price = round(avg_price)
    best_mkt = max(center_prices, key=lambda x: x["price"])
    lowest_mkt = min(center_prices, key=lambda x: x["price"])
    
    # 4. Market Insights Generation
    insights = []
    msp = MANDI_MSP.get(comm)
    
    if msp:
        if avg_price < msp:
            insights.append(f"⚠️ Warning: State average (₹{avg_price}) is BELOW Govt MSP (₹{msp}). Consider storing crop.")
        elif avg_price > msp * 1.15:
            insights.append(f"📈 Excellent! Average price is well ABOVE MSP. High demand detected.")
            
    diff_best_avg = round(((best_mkt["price"] - avg_price) / avg_price) * 100, 1)
    if diff_best_avg > 5:
        insights.append(f"💡 Selling at {best_mkt['market']} yields {diff_best_avg}% more profit than the state average today.")
        
    insights.append(f"🏆 Highest trading volume recorded at {best_mkt['market']} @ ₹{best_mkt['price']}/Quintal")

    # 5. Build standard response expected by React UI
    return {
        "commodity": commodity.capitalize(),
        "state": state.title(),
        "current_price_inr": avg_price,
        "unit": "quintal",
        "msp": msp,
        "7_day_trend": [
            {"date": "Govt Price Min", "price": lowest_mkt['price']},
            {"date": "State Average", "price": avg_price},
            {"date": "Govt Price Max", "price": best_mkt['price']}
        ],
        "market_centers": [
            {"market": c["market"], "price": c["price"], "change_pct": round(((c["price"] - avg_price)/avg_price)*100,1)} 
            for c in center_prices[:5]
        ],
        "market_insights": insights,
        "last_updated": datetime.now().strftime("%d %b %Y, %I:%M %p") + f" (Data via Agmarknet {latest_date})"
    }
