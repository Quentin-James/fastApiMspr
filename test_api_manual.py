"""
Script de test manuel — à lancer depuis ta machine Windows.
Lance le serveur d'abord : uvicorn app.main:app --reload --port 8085
Puis : python test_api_manual.py
"""
import io
import json
import sys

import httpx
from PIL import Image, ImageDraw

BASE_URL = "http://localhost:8087"


def create_test_image() -> bytes:
    """Génère une image JPEG de test (pizza colorée) sans connexion internet."""
    img = Image.new("RGB", (320, 240), color=(200, 100, 50))
    draw = ImageDraw.Draw(img)
    draw.ellipse([60, 30, 260, 210], fill=(220, 160, 40), outline=(180, 80, 20), width=4)
    draw.ellipse([80, 50, 240, 190], fill=(210, 50, 30))
    for pos in [(120, 90), (160, 80), (200, 100), (140, 130), (180, 140), (110, 150)]:
        draw.ellipse([pos[0]-10, pos[1]-10, pos[0]+10, pos[1]+10], fill=(80, 40, 20))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    return buf.getvalue()


def print_json(label: str, data: dict) -> None:
    print(f"\n{'='*60}")
    print(f"  {label}")
    print('='*60)
    print(json.dumps(data, indent=2, ensure_ascii=False))


def test_health():
    print("\n[1] GET /health ...")
    r = httpx.get(f"{BASE_URL}/health", timeout=5)
    print_json("HEALTH CHECK", r.json())
    assert r.status_code == 200, f"Attendu 200, reçu {r.status_code}"
    print("  ✅ OK")


def test_analyze_photo():
    print("\n[2] POST /nutrition/analyze-photo ...")
    image_bytes = create_test_image()
    r = httpx.post(
        f"{BASE_URL}/nutrition/analyze-photo",
        files={"file": ("pizza_test.jpg", image_bytes, "image/jpeg")},
        timeout=60,
    )
    print_json(f"ANALYZE PHOTO  [{r.status_code}]", r.json())
    if r.status_code == 200:
        data = r.json()
        print(f"\n  Aliments détectés ({len(data['foods_detected'])}) via {data['analysis_api']} :")
        for f in data["foods_detected"]:
            cal = f.get("calories_per_100g") or "?"
            print(f"    • {f['name']:30s}  score={f['confidence']:.2f}  {cal} kcal/100g")
        m = data["total_macros"]
        print(f"\n  Macros totales estimées :")
        print(f"    Calories  : {m['calories']} kcal")
        print(f"    Protéines : {m['proteins_g']} g")
        print(f"    Glucides  : {m['carbs_g']} g")
        print(f"    Lipides   : {m['fats_g']} g")
        print("  ✅ OK")
    elif r.status_code == 503 and "chargement" in r.text.lower():
        print("  ⏳ Modèle HF en cold start — réessaie dans 20s")
    else:
        print(f"  ❌ Erreur {r.status_code}")


def test_nutrition_recommend():
    print("\n[3] POST /nutrition/recommend ...")
    payload = {
        "patient_id": "test_patient_001",
        "objective": "perte_de_poids",
        "allergies": [],
        "diet_type": "omnivore",
        "daily_calories_target": 1600,
        "excluded_foods": [],
    }
    r = httpx.post(f"{BASE_URL}/nutrition/recommend", json=payload, timeout=30)
    if r.status_code == 201:
        data = r.json()
        print(f"\n  Plan généré pour '{data['patient_id']}' ({len(data['weekly_plan'])} jours)")
        print(f"  Message : {data['personalized_message'][:100]}...")
        print(f"  Notes   : {data['nutritional_balance_notes'][:100]}")
        print("  ✅ OK")
    else:
        print_json(f"NUTRITION RECOMMEND [{r.status_code}]", r.json())


def test_sport_recommend():
    print("\n[4] POST /sport/recommend ...")
    payload = {
        "patient_id": "test_patient_001",
        "objective": "fat_loss",
        "fitness_level": "beginner",
        "equipment": "none",
        "available_days": ["lundi", "mercredi", "vendredi"],
        "limitations": [],
        "session_duration_max_minutes": 45,
    }
    r = httpx.post(f"{BASE_URL}/sport/recommend", json=payload, timeout=30)
    if r.status_code == 201:
        data = r.json()
        active = [s for s in data["weekly_program"] if s["session_type"] != "Repos"]
        print(f"\n  Programme : {len(active)} séances actives / 7 jours")
        for s in active:
            exos = ", ".join(e["name"] for e in s["exercises"][:3])
            print(f"    • {s['day']:10s} [{s['session_type']}]  {exos}...")
        print("  ✅ OK")
    else:
        print_json(f"SPORT RECOMMEND [{r.status_code}]", r.json())


if __name__ == "__main__":
    print(f"\n🚀 Test du microservice IA — {BASE_URL}")
    try:
        test_health()
        test_analyze_photo()
        test_nutrition_recommend()
        test_sport_recommend()
        print("\n\n✅ Tous les tests terminés.\n")
    except httpx.ConnectError:
        print(f"\n❌ Impossible de se connecter à {BASE_URL}")
        print("   Lance d'abord le serveur :  uvicorn app.main:app --reload --port 8085")
        sys.exit(1)
