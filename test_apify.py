"""
Quick diagnostic script to test Apify API directly
Run: python test_apify.py
"""
import asyncio
import sys
from util.apify import scrape_reel

async def test():
    print("=" * 60)
    print("  APIFY DIAGNOSTIC TEST")
    print("=" * 60)
    
    # Test with a known valid shortcode
    test_shortcode = input("Enter Instagram shortcode to test (or press Enter for default): ").strip()
    if not test_shortcode:
        test_shortcode = "DQAEygQDPtY"
    
    print(f"\nTesting with shortcode: {test_shortcode}")
    print("-" * 60)
    
    try:
        result = await scrape_reel(test_shortcode)
        
        if not result:
            print("\n❌ Apify returned no results")
            print("This could mean:")
            print("  - The reel doesn't exist or was deleted")
            print("  - The reel is private")
            print("  - Instagram blocked the scraper")
            return
        
        reel = result["reel"]
        comments = result["comments"]
        
        print("\n" + "=" * 60)
        print("✅ SUCCESS - Apify returned data")
        print("=" * 60)
        
        print(f"\nReel Info:")
        print(f"  ID: {reel.get('id')}")
        print(f"  Shortcode: {reel.get('shortCode')}")
        print(f"  Owner: @{reel.get('ownerUsername')}")
        print(f"  Caption: {reel.get('caption', '')[:50]}...")
        print(f"  Comments: {len(comments)}")
        
        print(f"\nVideo Info:")
        print(f"  videoUrl: {reel.get('videoUrl', 'MISSING!')}")
        print(f"  videoDuration: {reel.get('videoDuration')}s")
        print(f"  videoViewCount: {reel.get('videoViewCount')}")
        
        if not reel.get('videoUrl'):
            print("\n❌ PROBLEM FOUND: videoUrl is missing or empty!")
            print("Check the debug JSON file to see what Apify actually returned.")
        else:
            print("\n✅ videoUrl looks good!")
            print(f"\nTry opening this URL in your browser:")
            print(reel['videoUrl'])
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
