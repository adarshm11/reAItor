"""
Test script for the full reAItor pipeline
Tests: Chat → Search → Evaluation → Argumentation → Compilation
"""

import requests
import time
import json

BASE_URL = "http://localhost:8000"

def test_full_pipeline():
    print("🚀 Starting Full Pipeline Test\n")

    # Step 1: Start chat session
    print("1️⃣ Starting chat session...")
    response = requests.post(f"{BASE_URL}/api/chat/start")
    if response.status_code != 200:
        print(f"❌ Failed to start chat: {response.text}")
        return

    chat_session_id = response.json()["session_id"]
    print(f"✅ Chat session created: {chat_session_id}\n")

    # Step 2: Simulate conversation to gather preferences
    print("2️⃣ Gathering preferences through conversation...")

    messages = [
        "I'm looking for a house in San Francisco",
        "My budget is $800,000 to $1,200,000",
        "I need at least 3 bedrooms and 2 bathrooms",
        "I want a garage and a backyard. No HOA please.",
        "Walkability and good schools are important to me",
        "Yes, that's all my preferences"
    ]

    for i, msg in enumerate(messages, 1):
        print(f"   User: {msg}")
        response = requests.post(
            f"{BASE_URL}/api/chat/{chat_session_id}/message",
            json={"message": msg}
        )

        if response.status_code != 200:
            print(f"❌ Chat failed: {response.text}")
            return

        data = response.json()
        print(f"   Bot: {data['response'][:100]}...")

        if data["preferences_complete"]:
            print(f"\n✅ Preferences complete after {i} messages\n")
            break

        time.sleep(0.5)

    # Step 3: Get extracted preferences
    print("3️⃣ Fetching extracted preferences...")
    response = requests.get(f"{BASE_URL}/api/chat/{chat_session_id}/preferences")

    if response.status_code != 200:
        print(f"❌ Failed to get preferences: {response.text}")
        return

    preferences = response.json()
    print("✅ Preferences extracted:")
    print(f"   Location: {preferences.get('location', 'Not extracted')}")

    price_min = preferences.get('price_min')
    price_max = preferences.get('price_max')
    if price_min and price_max:
        print(f"   Budget: ${price_min:,} - ${price_max:,}")
    else:
        print(f"   Budget: Not extracted (min: {price_min}, max: {price_max})")

    print(f"   Bedrooms: {preferences.get('bedrooms_min')} - {preferences.get('bedrooms_max')}")
    print(f"   Must-have: {preferences.get('must_have_features')}")
    print(f"   Deal breakers: {preferences.get('deal_breakers')}")
    print(f"\n   Full preferences: {json.dumps(preferences, indent=2)}\n")

    # Step 4: Start search
    print("4️⃣ Starting property search...")
    response = requests.post(
        f"{BASE_URL}/api/search/start",
        json={"chat_session_id": chat_session_id}
    )

    if response.status_code != 200:
        print(f"❌ Failed to start search: {response.text}")
        return

    search_session_id = response.json()["search_session_id"]
    print(f"✅ Search started: {search_session_id}\n")

    # Step 5: Monitor search progress
    print("5️⃣ Monitoring search progress...")

    max_wait = 180  # 3 minutes
    start_time = time.time()
    last_status = None

    while time.time() - start_time < max_wait:
        response = requests.get(f"{BASE_URL}/api/search/{search_session_id}/status")

        if response.status_code != 200:
            print(f"❌ Failed to get status: {response.text}")
            return

        status = response.json()

        # Only print if status changed
        if status != last_status:
            print(f"   [{status['status'].upper()}] {status['progress']:.1f}% - {status['message']}")
            print(f"   Listings found: {status['listings_found']}, Evaluated: {status['listings_evaluated']}")
            last_status = status

        if status["status"] == "complete":
            print("\n✅ Search complete!\n")
            break
        elif status["status"] == "error":
            print(f"\n❌ Search failed: {status['message']}\n")
            return

        time.sleep(2)

    if status["status"] != "complete":
        print("\n⚠️ Search timed out\n")
        return

    # Step 6: Get final results
    print("6️⃣ Fetching final results...")
    response = requests.get(f"{BASE_URL}/api/search/{search_session_id}/final-results")

    if response.status_code != 200:
        print(f"❌ Failed to get final results: {response.text}")
        return

    final_reports = response.json()
    print(f"✅ Received {len(final_reports)} final reports\n")

    # Step 7: Display results
    print("7️⃣ Top 3 Property Recommendations:\n")

    for i, report in enumerate(final_reports[:3], 1):
        listing = report["listing"]
        evaluation = report["evaluation"]
        arguments = report["arguments"]

        print(f"{'='*80}")
        print(f"#{i} - {report['recommendation']} - Score: {report['final_score']:.1f}/10")
        print(f"{'='*80}")
        print(f"Address: {listing['address']}")
        print(f"Price: ${listing['price']:,}")
        print(f"Specs: {listing['bedrooms']} bed, {listing['bathrooms']} bath, {listing['sqft']:,} sqft")
        print(f"\nExecutive Summary:")
        print(f"{report['executive_summary']}")
        print(f"\nEvaluation Scores:")
        print(f"  • Preference Match: {evaluation['preference_match_score']}/10")
        print(f"  • Crime: {evaluation['crime_score']}/10")
        print(f"  • Schools: {evaluation['school_score']}/10")
        print(f"  • Walkability: {evaluation['walkability_score']}/10")
        print(f"  • Affordability: {evaluation['affordability_score']}/10")
        print(f"\nPro Arguments ({len(arguments['pro_arguments'])}):")
        for arg in arguments['pro_arguments']:
            print(f"  ✓ {arg}")
        print(f"\nCon Arguments ({len(arguments['con_arguments'])}):")
        for arg in arguments['con_arguments']:
            print(f"  ✗ {arg}")
        print()

    print("=" * 80)
    print("🎉 Full Pipeline Test Complete!")
    print("=" * 80)

if __name__ == "__main__":
    try:
        test_full_pipeline()
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
