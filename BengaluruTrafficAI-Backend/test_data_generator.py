"""
Test Data Generator for BengaluruTrafficAI
Generates sample violations for testing the dashboard and API
"""

import requests
import random
import json
from datetime import datetime, timedelta
from typing import Dict, List

API_URL = "http://localhost:8000"

# Configuration
VIOLATION_TYPES = [
    "triple_riding",
    "red_light_violation",
    "wrong_side_driving",
    "stop_line_violation",
    "illegal_parking",
    "no_helmet",
    "phone_usage"
]

CAMERAS = [
    {"id": "cam_01", "name": "Silk Board Junction", "lat": 12.9181, "lon": 77.6227},
    {"id": "cam_02", "name": "Marathahalli Bridge", "lat": 12.9590, "lon": 77.6976},
    {"id": "cam_03", "name": "Electronic City", "lat": 12.8454, "lon": 77.6645},
    {"id": "cam_04", "name": "Whitefield Main", "lat": 12.9698, "lon": 77.7499},
    {"id": "cam_05", "name": "MG Road Metro", "lat": 12.9759, "lon": 77.6067},
]

VEHICLE_TYPES = ["car", "motorcycle", "bus", "truck", "auto"]

# Indian state codes for plates
STATE_CODES = ["KA", "DL", "MH", "TN", "AP", "TS", "KL", "GJ", "RJ", "UP"]


def generate_plate_number() -> str:
    """Generate realistic Indian license plate number"""
    state = random.choice(STATE_CODES)
    district = random.randint(1, 99)
    series = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=random.randint(1, 2)))
    number = random.randint(1, 9999)
    return f"{state}{district:02d}{series}{number:04d}"


def generate_violation(hours_ago: int = 24) -> Dict:
    """Generate a single sample violation"""
    camera = random.choice(CAMERAS)
    violation_type = random.choice(VIOLATION_TYPES)
    
    # Some violations more likely to have plates detected
    has_plate_probability = {
        "triple_riding": 0.5,
        "red_light_violation": 0.7,
        "wrong_side_driving": 0.6,
        "stop_line_violation": 0.7,
        "illegal_parking": 0.8,
        "no_helmet": 0.4,
        "phone_usage": 0.7
    }
    
    has_plate = random.random() < has_plate_probability.get(violation_type, 0.6)
    
    timestamp = datetime.now() - timedelta(
        hours=random.randint(0, hours_ago),
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59)
    )
    
    violation = {
        "violation_type": violation_type,
        "camera_id": camera["id"],
        "timestamp": timestamp.isoformat(),
        "confidence": round(random.uniform(0.70, 0.96), 2),
        "plate_number": generate_plate_number() if has_plate else None,
        "location": {
            "lat": camera["lat"] + random.uniform(-0.002, 0.002),
            "lon": camera["lon"] + random.uniform(-0.002, 0.002)
        },
        "metadata": {
            "vehicle_type": random.choice(VEHICLE_TYPES),
            "frame_number": random.randint(100, 10000),
            "track_id": random.randint(1, 100),
            "camera_name": camera["name"]
        },
        "auto_approve": random.choice([True, False])
    }
    
    return violation


def populate_test_data(count: int = 50, hours_ago: int = 24, verbose: bool = True):
    """
    Populate database with sample violations
    
    Args:
        count: Number of violations to generate
        hours_ago: Generate violations within last N hours
        verbose: Print progress
    """
    print(f"\n{'='*70}")
    print(f"   Generating {count} sample violations (last {hours_ago} hours)")
    print(f"{'='*70}\n")
    
    violations = []
    success_count = 0
    failed_count = 0
    
    for i in range(count):
        violation = generate_violation(hours_ago)
        violations.append(violation)
        
        try:
            response = requests.post(
                f"{API_URL}/violations/ingest",
                json=violation,
                timeout=5
            )
            
            if response.status_code in [200, 201]:
                success_count += 1
                if verbose:
                    plate = violation.get('plate_number', 'N/A')
                    print(f"✓ {i+1:3d}/{count} | {violation['violation_type']:<25} | {violation['camera_id']} | {plate}")
            else:
                failed_count += 1
                if verbose:
                    print(f"✗ {i+1:3d}/{count} | Failed: {response.status_code} - {response.text[:50]}")
                    
        except requests.exceptions.ConnectionError:
            failed_count += 1
            if verbose and i == 0:
                print(f"\n❌ Cannot connect to API at {API_URL}")
                print(f"   Make sure backend is running: uvicorn api.app:app --reload --port 8000\n")
            if not verbose or i == 0:
                print(f"✗ {i+1:3d}/{count} | Connection failed")
                
        except Exception as e:
            failed_count += 1
            if verbose:
                print(f"✗ {i+1:3d}/{count} | Error: {str(e)[:50]}")
    
    # Summary
    print(f"\n{'='*70}")
    print(f"   SUMMARY")
    print(f"{'='*70}")
    print(f"Total generated:     {count}")
    print(f"Successfully created: {success_count} ✓")
    print(f"Failed:              {failed_count} ✗")
    print(f"\n{'='*70}\n")
    
    if success_count > 0:
        print("✅ Test data created successfully!")
        print(f"\nView violations:")
        print(f"  Dashboard: http://localhost:3000")
        print(f"  API:       {API_URL}/violations")
        print(f"  Stats:     {API_URL}/violations/stats")
    else:
        print("❌ No data created. Check if backend API is running.")
    
    return violations


def generate_distribution_by_type(total: int = 100):
    """Generate violations with realistic distribution"""
    distribution = {
        "triple_riding": 0.25,
        "red_light_violation": 0.20,
        "wrong_side_driving": 0.15,
        "stop_line_violation": 0.15,
        "illegal_parking": 0.10,
        "no_helmet": 0.10,
        "phone_usage": 0.05
    }
    
    print(f"\n{'='*70}")
    print(f"   Generating {total} violations with realistic distribution")
    print(f"{'='*70}\n")
    
    for violation_type, ratio in distribution.items():
        count = int(total * ratio)
        print(f"Generating {count:3d} × {violation_type}")
    
    print()
    
    violations = []
    for violation_type, ratio in distribution.items():
        count = int(total * ratio)
        for _ in range(count):
            violation = generate_violation()
            violation['violation_type'] = violation_type
            violations.append(violation)
    
    # Upload
    success_count = 0
    for i, violation in enumerate(violations):
        try:
            response = requests.post(f"{API_URL}/violations/ingest", json=violation, timeout=5)
            if response.status_code in [200, 201]:
                success_count += 1
                print(f"✓ {i+1:3d}/{total} uploaded")
        except:
            print(f"✗ {i+1:3d}/{total} failed")
    
    print(f"\n✅ Created {success_count}/{total} violations\n")


def generate_hourly_pattern(days: int = 1):
    """Generate violations following hourly pattern (busy hours)"""
    print(f"\n{'='*70}")
    print(f"   Generating violations with hourly pattern ({days} days)")
    print(f"{'='*70}\n")
    
    # Peak hours: 8-10 AM, 5-8 PM
    hourly_rates = {
        0: 2, 1: 1, 2: 1, 3: 1, 4: 2, 5: 3,
        6: 5, 7: 8, 8: 12, 9: 15, 10: 10, 11: 8,
        12: 6, 13: 5, 14: 5, 15: 6, 16: 8,
        17: 12, 18: 15, 19: 12, 20: 8, 21: 5,
        22: 3, 23: 2
    }
    
    violations = []
    for day in range(days):
        for hour, rate in hourly_rates.items():
            for _ in range(rate):
                violation = generate_violation(hours_ago=24)
                # Adjust timestamp to specific hour
                timestamp = datetime.now() - timedelta(days=day, hours=(23-hour), minutes=random.randint(0, 59))
                violation['timestamp'] = timestamp.isoformat()
                violations.append(violation)
    
    print(f"Generated {len(violations)} violations over {days} days")
    print(f"Uploading to API...\n")
    
    success_count = 0
    for i, violation in enumerate(violations):
        try:
            response = requests.post(f"{API_URL}/violations/ingest", json=violation, timeout=5)
            if response.status_code in [200, 201]:
                success_count += 1
                if (i + 1) % 20 == 0:
                    print(f"✓ {i+1:3d}/{len(violations)} uploaded")
        except:
            pass
    
    print(f"\n✅ Created {success_count}/{len(violations)} violations\n")


def save_to_csv(filename: str = "sample_violations.csv", count: int = 100):
    """Save sample violations to CSV file"""
    import csv
    
    print(f"\nGenerating CSV with {count} violations...")
    
    violations = [generate_violation() for _ in range(count)]
    
    with open(filename, 'w', newline='') as f:
        if violations:
            fieldnames = ['violation_type', 'camera_id', 'timestamp', 'confidence', 
                         'plate_number', 'vehicle_type', 'location_lat', 'location_lon']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for v in violations:
                writer.writerow({
                    'violation_type': v['violation_type'],
                    'camera_id': v['camera_id'],
                    'timestamp': v['timestamp'],
                    'confidence': v['confidence'],
                    'plate_number': v.get('plate_number', ''),
                    'vehicle_type': v['metadata']['vehicle_type'],
                    'location_lat': v['location']['lat'],
                    'location_lon': v['location']['lon']
                })
    
    print(f"✅ Saved {count} violations to {filename}")


# CLI Interface
if __name__ == "__main__":
    import sys
    
    print("\n" + "="*70)
    print("   BengaluruTrafficAI - Test Data Generator")
    print("="*70 + "\n")
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "quick":
            # Quick 20 violations
            populate_test_data(20, hours_ago=2)
            
        elif command == "full":
            # Full 100 violations
            populate_test_data(100, hours_ago=24)
            
        elif command == "distribution":
            # Realistic distribution
            generate_distribution_by_type(100)
            
        elif command == "hourly":
            # Hourly pattern
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 1
            generate_hourly_pattern(days)
            
        elif command == "csv":
            # Save to CSV
            count = int(sys.argv[2]) if len(sys.argv) > 2 else 100
            save_to_csv(count=count)
            
        else:
            print(f"Unknown command: {command}\n")
            print("Usage:")
            print("  python test_data_generator.py quick          # 20 violations")
            print("  python test_data_generator.py full           # 100 violations")
            print("  python test_data_generator.py distribution   # Realistic mix")
            print("  python test_data_generator.py hourly [days]  # Hourly pattern")
            print("  python test_data_generator.py csv [count]    # Save to CSV")
    else:
        # Default: 50 violations
        populate_test_data(50, hours_ago=12)
