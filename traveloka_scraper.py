import requests
import json
from datetime import datetime
from typing import List, Dict
import time

class TravelokaScraper:
    def __init__(self):
        self.base_url = "https://www.traveloka.com"
        self.api_url = "https://www.traveloka.com/api/v2/hotel/search/rooms"
        self.session = requests.Session()
        self.headers = {
            'authority': 'www.traveloka.com',
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/json',
            'origin': self.base_url,
            'referer': f'{self.base_url}/en-th/hotel',
            'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'x-domain': 'accomRoom',
            'x-route-prefix': 'en-th'
        }
        
        self.initialize_session()

    def initialize_session(self):
        """Visit the homepage to get initial cookies"""
        try:
            print("Initializing session by visiting homepage...")
            response = self.session.get(
                f"{self.base_url}/en-th",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            print("Successfully initialized session with cookies:", self.session.cookies.get_dict())
        except Exception as e:
            print(f"Error initializing session: {e}")

    def generate_deep_link(self, hotel_id: str, check_in: str, check_out: str, adults=1, children=0, rooms=1) -> str:
        return f"{self.base_url}/en-th/hotel/detail?spec={check_in}.{check_out}.{rooms}.{adults}.HOTEL.{hotel_id}"

    def parse_date(self, date_str: str) -> Dict[str, str]:
        date_obj = datetime.strptime(date_str, "%d-%m-%Y")
        return {
            "day": str(date_obj.day),
            "month": str(date_obj.month),
            "year": str(date_obj.year)
        }

    def build_request_payload(self, hotel_id: str, check_in: str, check_out: str, adults=1, children=0, rooms=1) -> Dict:
        check_in_date = self.parse_date(check_in)
        check_out_date = self.parse_date(check_out)
        
        return {
            "fields": [],
            "data": {
                "contexts": {
                    "hotelDetailURL": self.generate_deep_link(hotel_id, check_in, check_out, adults, children, rooms),
                    "sourceIdentifier": "HOTEL_DETAIL",
                    "shouldDisplayAllRooms": False
                },
                "prevSearchId": "undefined",
                "numInfants": 0,
                "ccGuaranteeOptions": {
                    "ccInfoPreferences": ["CC_TOKEN", "CC_FULL_INFO"],
                    "ccGuaranteeRequirementOptions": ["CC_GUARANTEE"]
                },
                "rateTypes": ["PAY_NOW", "PAY_AT_PROPERTY"],
                "isJustLogin": False,
                "isReschedule": False,
                "preview": False,
                "monitoringSpec": {
                    "referrer": "",
                    "isPriceFinderActive": "null",
                    "dateIndicator": "null",
                    "displayPrice": "null"
                },
                "hotelId": hotel_id,
                "currency": "THB",
                "labelContext": {},
                "isExtraBedIncluded": True,
                "hasPromoLabel": False,
                "supportedRoomHighlightTypes": ["ROOM"],
                "checkInDate": check_in_date,
                "checkOutDate": check_out_date,
                "numOfNights": (datetime.strptime(check_out, "%d-%m-%Y") - datetime.strptime(check_in, "%d-%m-%Y")).days,
                "numAdults": adults,
                "numRooms": rooms,
                "numChildren": children,
                "childAges": [],
                "tid": "54ca3a2e-1b07-4434-bdcb-a2f1d85f624f"
            },
            "clientInterface": "desktop"
        }

    def extract_room_data(self, room: Dict) -> Dict:
        rate = room.get("rateDisplay", {})
        original_rate = room.get("originalRateDisplay", {})
        
        return {
            "room_name": room.get("inventoryName", ""),
            "rate_name": room.get("roomInventoryGroupOption", ""),
            "number_of_guests": room.get("maxOccupancy", 1),
            "cancellation_policy": room.get("roomCancellationPolicy", {}).get("cancellationPolicyLabel", ""),
            "breakfast": "Yes" if room.get("isBreakfastIncluded", False) else "No",
            "price": rate.get("baseFare", {}).get("amount", ""),
            "original_price": original_rate.get("baseFare", {}).get("amount", ""),
            "currency": rate.get("baseFare", {}).get("currency", "THB"),
            "total_taxes": rate.get("taxes", {}).get("amount", ""),
            "total_price": rate.get("totalFare", {}).get("amount", ""),
            "net_price": room.get("finalPrice", ""),
            "shown_price_per_stay": rate.get("totalFare", {}).get("amount", ""),
            "net_price_per_stay": room.get("finalPrice", ""),
            "total_price_per_stay": room.get("totalPrice", "")
        }

    def scrape_hotel_rooms(self, hotel_id: str, check_in: str, check_out: str, adults=1, children=0, rooms=1) -> List[Dict]:
        deep_link = self.generate_deep_link(hotel_id, check_in, check_out, adults, children, rooms)
        print(f"Visiting hotel page to get cookies: {deep_link}")
        
        try:
            hotel_page_response = self.session.get(
                deep_link,
                headers=self.headers,
                timeout=10
            )
            hotel_page_response.raise_for_status()
            print("Successfully visited hotel page, cookies updated:", self.session.cookies.get_dict())
            time.sleep(2) 
            
            payload = self.build_request_payload(hotel_id, check_in, check_out, adults, children, rooms)
            self.headers['referer'] = deep_link
            
            print("Making API request with payload...")
            api_response = self.session.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=15
            )
            
            print(f"API Response status: {api_response.status_code}")
            print(f"API Response preview: {api_response.text[:500]}")
            
            api_response.raise_for_status()
            
            try:
                data = api_response.json()
            except json.JSONDecodeError:
                print("Failed to decode JSON. Response text:")
                print(api_response.text)
                return []
            
            rooms_data = []
            for entry in data.get("data", {}).get("recommendedEntries", []):
                for inventory in entry.get("hotelRoomInventoryList", []):
                    rooms_data.append(self.extract_room_data(inventory))
            
            return rooms_data
            
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return []

    def save_to_json(self, data: List[Dict], filename: str = "traveloka_rooms.json") -> None:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Data saved to {filename}")

if __name__ == "__main__":
    scraper = TravelokaScraper()
    
    hotel_id = "1000000272980"
    check_in = "13-04-2025"
    check_out = "14-04-2025"
    
    print(f"Deep Link: {scraper.generate_deep_link(hotel_id, check_in, check_out)}")
    
    rooms = scraper.scrape_hotel_rooms(hotel_id, check_in, check_out)
    
    if rooms:
        scraper.save_to_json(rooms)
        print(f"Successfully scraped {len(rooms)} rooms")
        print("Sample room data:")
        print(json.dumps(rooms[0], indent=2))
    else:
        print("No rooms found or error occurred")