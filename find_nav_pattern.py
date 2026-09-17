"""Verify the LeafAI injection is correct."""
BUNDLE = r"F:\sih\vaibhav_apk_extracted\assets\index.android.bundle"
with open(BUNDLE, "r", encoding="utf-8") as f:
    bundle = f.read()

checks = [
    ("LeafAIScreen module injected", "LeafAIScreen" in bundle),
    ("vision case in nav switch", "case'vision'" in bundle),
    ("Leaf AI back button wired", "onBack:function(){return b('sensors')}" in bundle),
    ("crop picker present", "CROPS=" in bundle or "CROPS=[" in bundle),
    ("API endpoint wired", "vision-diagnose" in bundle),
    ("Camera/gallery picker", "launchCamera" in bundle or "launchImageLibrary" in bundle),
]

print("=== LEAF AI INJECTION VERIFICATION ===")
all_ok = True
for name, ok in checks:
    status = "PASS" if ok else "FAIL"
    if not ok:
        all_ok = False
    print(f"  [{status}] {name}")

print()
if all_ok:
    print("All checks PASSED. Ready to repackage APK.")
else:
    print("Some checks FAILED. Review injection script.")

# Show the vision case in context
idx = bundle.find("case'vision'")
if idx != -1:
    print()
    print("Vision case in nav switch:")
    print("  ...", bundle[max(0,idx-30):idx+150], "...")
