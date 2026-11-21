"""Country, state and city lists for the search form.

India is bundled so the usual sales searches work without a network call.
Other countries start with "Whole country" and fill in from geocoding as the
user types.
"""

from __future__ import annotations

COUNTRIES: tuple[tuple[str, str], ...] = (
    ("IN", "India"),
    ("AE", "United Arab Emirates"),
    ("AR", "Argentina"),
    ("AT", "Austria"),
    ("AU", "Australia"),
    ("BD", "Bangladesh"),
    ("BE", "Belgium"),
    ("BR", "Brazil"),
    ("CA", "Canada"),
    ("CH", "Switzerland"),
    ("CN", "China"),
    ("DE", "Germany"),
    ("DK", "Denmark"),
    ("EG", "Egypt"),
    ("ES", "Spain"),
    ("FI", "Finland"),
    ("FR", "France"),
    ("GB", "United Kingdom"),
    ("GH", "Ghana"),
    ("HK", "Hong Kong"),
    ("ID", "Indonesia"),
    ("IE", "Ireland"),
    ("IL", "Israel"),
    ("IT", "Italy"),
    ("JP", "Japan"),
    ("KE", "Kenya"),
    ("KR", "South Korea"),
    ("LK", "Sri Lanka"),
    ("MX", "Mexico"),
    ("MY", "Malaysia"),
    ("NG", "Nigeria"),
    ("NL", "Netherlands"),
    ("NO", "Norway"),
    ("NP", "Nepal"),
    ("NZ", "New Zealand"),
    ("PH", "Philippines"),
    ("PK", "Pakistan"),
    ("PL", "Poland"),
    ("PT", "Portugal"),
    ("QA", "Qatar"),
    ("SA", "Saudi Arabia"),
    ("SE", "Sweden"),
    ("SG", "Singapore"),
    ("TH", "Thailand"),
    ("TR", "Turkey"),
    ("US", "United States"),
    ("VN", "Vietnam"),
    ("ZA", "South Africa"),
)

INDIA_CITIES: dict[str, tuple[str, ...]] = {
    "Andhra Pradesh": ("Visakhapatnam", "Vijayawada", "Guntur", "Tirupati"),
    "Arunachal Pradesh": ("Itanagar",),
    "Assam": ("Guwahati", "Dibrugarh", "Silchar"),
    "Bihar": ("Patna", "Gaya", "Muzaffarpur"),
    "Chhattisgarh": ("Raipur", "Bhilai", "Bilaspur"),
    "Goa": ("Panaji", "Margao", "Vasco da Gama"),
    "Gujarat": (
        "Ahmedabad",
        "Anand",
        "Bharuch",
        "Bhavnagar",
        "Gandhinagar",
        "Halol",
        "Jamnagar",
        "Mehsana",
        "Rajkot",
        "Surat",
        "Vadodara",
        "Vapi",
    ),
    "Haryana": ("Gurugram", "Faridabad", "Panipat", "Ambala"),
    "Himachal Pradesh": ("Shimla", "Dharamshala", "Solan"),
    "Jharkhand": ("Ranchi", "Jamshedpur", "Dhanbad"),
    "Karnataka": ("Bengaluru", "Mysuru", "Mangaluru", "Hubballi"),
    "Kerala": ("Thiruvananthapuram", "Kochi", "Kozhikode"),
    "Madhya Pradesh": ("Bhopal", "Indore", "Gwalior", "Jabalpur"),
    "Maharashtra": ("Mumbai", "Pune", "Nagpur", "Nashik", "Aurangabad"),
    "Manipur": ("Imphal",),
    "Meghalaya": ("Shillong",),
    "Mizoram": ("Aizawl",),
    "Nagaland": ("Kohima", "Dimapur"),
    "Odisha": ("Bhubaneswar", "Cuttack", "Rourkela"),
    "Punjab": ("Ludhiana", "Amritsar", "Jalandhar", "Mohali"),
    "Rajasthan": ("Jaipur", "Jodhpur", "Udaipur", "Kota"),
    "Sikkim": ("Gangtok",),
    "Tamil Nadu": ("Chennai", "Coimbatore", "Madurai", "Tiruchirappalli"),
    "Telangana": ("Hyderabad", "Warangal", "Nizamabad"),
    "Tripura": ("Agartala",),
    "Uttar Pradesh": ("Lucknow", "Noida", "Kanpur", "Varanasi", "Agra"),
    "Uttarakhand": ("Dehradun", "Haridwar", "Haldwani"),
    "West Bengal": ("Kolkata", "Howrah", "Durgapur", "Siliguri"),
    "Andaman and Nicobar Islands": ("Port Blair",),
    "Chandigarh": ("Chandigarh",),
    "Dadra and Nagar Haveli and Daman and Diu": ("Daman", "Silvassa"),
    "Delhi": ("New Delhi", "Delhi"),
    "Jammu and Kashmir": ("Srinagar", "Jammu"),
    "Ladakh": ("Leh",),
    "Lakshadweep": ("Kavaratti",),
    "Puducherry": ("Puducherry",),
}


def country_name(code: str) -> str:
    for item_code, name in COUNTRIES:
        if item_code == code.upper():
            return name
    return ""


def countries() -> list[dict[str, str]]:
    return [{"code": code, "name": name} for code, name in COUNTRIES]


def states(country_code: str) -> list[str]:
    if country_code.upper() == "IN":
        return list(INDIA_CITIES)
    return []


def cities(country_code: str, state: str) -> list[str]:
    if country_code.upper() != "IN":
        return []
    return list(INDIA_CITIES.get(state, ()))
