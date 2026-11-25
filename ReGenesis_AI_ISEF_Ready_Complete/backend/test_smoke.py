import asyncio
import httpx
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.app.main import app

async def run_smoke_test():
    print("Testing lifespan and database initialization...")
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            # 1. Health
            r1 = await client.get("/api/health")
            print("1. Health Check:", r1.status_code, r1.json())
            assert r1.status_code == 200

            # 2. Legacy Listings
            r2 = await client.get("/api/listings")
            listings = r2.json()
            print("2. Legacy Listings Count:", len(listings))
            assert len(listings) >= 5

            # 3. Create a listing
            payload = {
                "title": "قصاصات ألياف قطنية مفرومة",
                "category": "نسيج",
                "tradeType": "عرض (توفر مخلفات)",
                "qty": 12.0,
                "purity": 94.0,
                "price": 115.0,
                "factory": "مصنع المحلة للغزل",
                "city": "المحلة الكبرى",
                "desc": "قصاصات قطن 100% نقية من خطوط التفصيل."
            }
            r3 = await client.post("/api/listings", json=payload)
            print("3. Create Listing:", r3.status_code, "Matches:", len(r3.json().get("matches", [])))
            assert r3.status_code == 200

            # 4. Advisor
            r4 = await client.post("/api/advisor", json={"message": "عندي 25 طن نشارة خشب زان"})
            print("4. Advisor:", r4.status_code, r4.json()["answer"][:80] + "...")
            assert r4.status_code == 200

            # 5. Dashboard Analytics
            r5 = await client.get("/api/v1/dashboard/analytics")
            dash = r5.json()
            print("5. Dashboard KPIs:", r5.status_code, "Total Waste:", dash["kpis"]["total_waste_registered_tons"])
            assert r5.status_code == 200

            # 6. Carbon Calculator
            r6 = await client.post("/api/v1/environmental/carbon-calculator", json={"material_type": "خشب", "tonnage": 50})
            print("6. Carbon Calculator:", r6.status_code, "CO2 Avoided:", r6.json()["co2_avoided_tons"], "Trees:", r6.json()["trees_equivalent"])
            assert r6.status_code == 200

            # 7. Map Factories
            r7 = await client.get("/api/v1/map/factories")
            print("7. Map Factories:", r7.status_code, "Count:", len(r7.json()))
            assert r7.status_code == 200

            # 8. Reuse Recommendations
            r8 = await client.get("/api/v1/analysis/recommendations/خشب")
            print("8. Reuse Recommendations:", r8.status_code, "Pathways:", len(r8.json()))
            assert r8.status_code == 200

            # 9. Waste to Product
            r9 = await client.get("/api/v1/analysis/waste-to-product/بلاستيك")
            print("9. Waste to Product:", r9.status_code, "Products:", len(r9.json()))
            assert r9.status_code == 200

            # 10. Demand Predictions
            r10 = await client.get("/api/v1/dashboard/predictions")
            print("10. Demand Predictions:", r10.status_code, "Predictions Count:", len(r10.json()["predictions"]))
            assert r10.status_code == 200

            # 11. Negotiation Assistant
            r11 = await client.post("/api/v1/dashboard/negotiate", json={
                "material_type": "نشارة خشب",
                "quantity": 25.0,
                "purity": 95.0,
                "current_asking_price": 40.0,
                "city": "دمياط"
            })
            print("11. Negotiation:", r11.status_code, "Fair Price:", r11.json()["fair_market_price"])
            assert r11.status_code == 200

    print("\n🎉 ALL 11 SMOKE TESTS PASSED PERFECTLY!")

if __name__ == "__main__":
    asyncio.run(run_smoke_test())
