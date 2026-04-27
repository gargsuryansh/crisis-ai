import json

with open('data/protocols/emergency_protocols_enhanced.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("=== ROOT STRUCTURE ===")
print("Root type:", type(data).__name__)
print("Root keys:", list(data.keys()))
print()

# Look at each top-level key
for key in list(data.keys()):
    val = data[key]
    print(f"Key: '{key}' -> type: {type(val).__name__}", end="")
    if isinstance(val, list):
        print(f", length: {len(val)}")
        if len(val) > 0:
            first = val[0]
            print(f"  First item type: {type(first).__name__}")
            if isinstance(first, dict):
                print(f"  First item keys: {list(first.keys())}")
                # Print sample of first item
                print(f"  First item sample:")
                sample = json.dumps(first, indent=4)
                print('\n'.join(['    ' + line for line in sample.split('\n')[:30]]))
    elif isinstance(val, dict):
        print(f", sub-keys: {list(val.keys())[:5]}")
    else:
        print(f", value: {str(val)[:100]}")
    print()