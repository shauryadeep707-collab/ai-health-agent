import json
from backend.database.repositories import MedicineRepository

class MedicineService:
    """
    Provides authoritative, clinical medicine information, indications, precautions,
    contraindications, drug-drug interaction warnings, and legitimate pharmacy links.
    """

    @staticmethod
    def _generate_default_pharmacy_links(brand_name: str, generic_name: str):
        import urllib.parse
        term = brand_name or generic_name or ""
        encoded = urllib.parse.quote_plus(term)
        return [
            {"store": "Blinkit (10 min)", "url": f"https://blinkit.com/s/?q={encoded}", "badge": "⚡ 10 min", "color": "#fef08a", "textColor": "#854d0e"},
            {"store": "Zepto (10 min)", "url": f"https://www.zeptonow.com/search?q={encoded}", "badge": "⚡ 10 min", "color": "#f3e8ff", "textColor": "#6b21a8"},
            {"store": "Tata 1mg", "url": f"https://www.1mg.com/search/all?name={encoded}", "badge": "🏥 Pharmacy", "color": "#fee2e2", "textColor": "#991b1b"},
            {"store": "Apollo 24|7", "url": f"https://www.apollopharmacy.in/search-medicines/{encoded}", "badge": "🩺 24/7", "color": "#ccfbf1", "textColor": "#115e59"},
            {"store": "PharmEasy", "url": f"https://pharmeasy.in/search/all?name={encoded}", "badge": "💊 Delivery", "color": "#e0f2fe", "textColor": "#075985"},
            {"store": "Netmeds", "url": f"https://www.netmeds.com/catalogsearch/result/{encoded}/all", "badge": "📦 Online", "color": "#ede9fe", "textColor": "#5b21b6"}
        ]

    @staticmethod
    def search(query: str = None, limit: int = 20):
        records = MedicineRepository.search(query, limit)
        for r in records:
            brand = r.get("brand_name", "")
            generic = r.get("generic_name", "")
            quick_links = MedicineService._generate_default_pharmacy_links(brand, generic)
            if r.get("pharmacy_links_json"):
                try:
                    custom_links = json.loads(r["pharmacy_links_json"])
                    r["pharmacy_links"] = (custom_links if isinstance(custom_links, list) else []) + quick_links
                except Exception:
                    r["pharmacy_links"] = quick_links
            else:
                r["pharmacy_links"] = quick_links
        return records

    @staticmethod
    def get_details(medicine_id: str):
        record = MedicineRepository.find_by_id(medicine_id)
        if not record:
            return None
        brand = record.get("brand_name", "")
        generic = record.get("generic_name", "")
        quick_links = MedicineService._generate_default_pharmacy_links(brand, generic)
        if record.get("pharmacy_links_json"):
            try:
                custom_links = json.loads(record["pharmacy_links_json"])
                record["pharmacy_links"] = (custom_links if isinstance(custom_links, list) else []) + quick_links
            except Exception:
                record["pharmacy_links"] = quick_links
        else:
            record["pharmacy_links"] = quick_links
        return record

    @staticmethod
    def check_interactions(medicine_ids: list[str]):
        """
        Takes a list of medicine IDs and checks for clinical interactions.
        """
        if not medicine_ids or len(medicine_ids) < 2:
            return {
                "has_interactions": False,
                "count": 0,
                "interactions": [],
                "summary": "At least two medications are required to check for drug interactions."
            }

        interactions = MedicineRepository.check_interactions(medicine_ids)
        severe_count = sum(1 for item in interactions if item.get("severity") in ("SEVERE", "CONTRAINDICATED"))

        return {
            "has_interactions": len(interactions) > 0,
            "count": len(interactions),
            "severe_count": severe_count,
            "interactions": interactions,
            "summary": "Dangerous interaction detected! Consult your physician immediately." if severe_count > 0 else (
                "Interactions detected. Monitor closely." if interactions else "No known pairwise interactions found in database."
            )
        }
