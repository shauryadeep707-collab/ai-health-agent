import difflib
from backend.database.repositories import ProductRepository

# Common catalog search terms for fuzzy matching / spelling assistance
KNOWN_KEYWORDS = [
    "blood pressure monitor", "bp monitor", "glucometer", "blood glucose",
    "pulse oximeter", "oximeter", "thermometer", "digital thermometer",
    "nebulizer", "compressor nebulizer", "test strips", "lancets"
]

class ProductService:
    """
    Search and recommendation catalog for medical devices and wellness products.
    Includes search suggestions, basic spelling tolerance, and demo indicators.
    """

    @staticmethod
    def search(query: str = None, category: str = None, limit: int = 20):
        # Basic spelling suggestion if no direct results
        corrected_query = query
        suggestion = None

        if query and len(query) > 3:
            close_matches = difflib.get_close_matches(query.lower(), KNOWN_KEYWORDS, n=1, cutoff=0.6)
            if close_matches and close_matches[0].lower() != query.lower():
                suggestion = close_matches[0]

        products = ProductRepository.search(query=query, category=category, limit=limit)

        # If zero products found and we have a spelling suggestion, try searching with suggestion
        if not products and suggestion:
            products = ProductRepository.search(query=suggestion, category=category, limit=limit)

        return {
            "products": products,
            "total_found": len(products),
            "spelling_suggestion": suggestion,
            "searched_query": query,
            "category_filter": category,
            "is_demo_catalog": any(bool(p.get("is_demo_data")) for p in products)
        }

    @staticmethod
    def get_categories():
        return ProductRepository.get_categories()

    @staticmethod
    def get_details(product_id: str):
        return ProductRepository.find_by_id(product_id)
