import json
from backend.database.repositories import MedicineRepository

class MedicineService:
    """
    Provides authoritative, clinical medicine information, indications, precautions,
    contraindications, drug-drug interaction warnings, and legitimate pharmacy links.
    """

    @staticmethod
    def search(query: str = None, limit: int = 20):
        records = MedicineRepository.search(query, limit)
        for r in records:
            if r.get("pharmacy_links_json"):
                try:
                    r["pharmacy_links"] = json.loads(r["pharmacy_links_json"])
                except Exception:
                    r["pharmacy_links"] = []
            else:
                r["pharmacy_links"] = []
        return records

    @staticmethod
    def get_details(medicine_id: str):
        record = MedicineRepository.find_by_id(medicine_id)
        if not record:
            return None
        if record.get("pharmacy_links_json"):
            try:
                record["pharmacy_links"] = json.loads(record["pharmacy_links_json"])
            except Exception:
                record["pharmacy_links"] = []
        else:
            record["pharmacy_links"] = []
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
